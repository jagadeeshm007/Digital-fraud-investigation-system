from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.review import review_alert
from app.audit import write_audit
from app.db import get_session
from app.exceptions import PermissionDenied
from app.models import Alert
from app.permissions import check_permission, resolve_role

router = APIRouter(tags=["ai-review"])


async def _apply_review(alert: Alert, session: AsyncSession) -> dict:
    """Run review and persist results onto the alert."""
    result = await review_alert(alert)

    alert.ai_adjustment = result["risk_adjustment"]
    alert.final_score = max(0, min(100, alert.base_score + result["risk_adjustment"]))
    # Recompute risk band after AI adjustment
    if alert.final_score >= 70:
        alert.risk_band = "High"
    elif alert.final_score >= 40:
        alert.risk_band = "Medium"
    else:
        alert.risk_band = "Low"

    alert.ai_recommendation = (
        f"{result['recommended_decision'].upper()}: {result['reasoning']}"
    )
    alert.ai_status = "completed" if result["ai_available"] else "unavailable"

    await session.commit()
    return result


# ─── POST /api/ai/review/{alert_id} ──────────────────────────────────────────

@router.post("/ai/review/{alert_id}")
async def review_one(
    alert_id: str,
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "view_ai_log")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    alert = (await session.execute(
        select(Alert).where(Alert.alert_id == alert_id)
    )).scalar_one_or_none()
    if not alert:
        raise HTTPException(404, detail="Alert not found")

    if alert.status == "cleared":
        raise HTTPException(400, detail="Cleared alerts do not need AI review")

    result = await _apply_review(alert, session)

    await write_audit(
        session,
        role=role,
        channel="api",
        action="ai_review",
        target=alert_id,
        result=f"adj={result['risk_adjustment']} decision={result['recommended_decision']} available={result['ai_available']}",
    )
    await session.commit()

    return {
        "alert_id": alert_id,
        "base_score": alert.base_score,
        "ai_adjustment": alert.ai_adjustment,
        "final_score": alert.final_score,
        "risk_band": alert.risk_band,
        "fraud_category": result["fraud_category"],
        "recommended_decision": result["recommended_decision"],
        "reasoning": result["reasoning"],
        "cited_evidence": result["cited_evidence"],
        "ai_available": result["ai_available"],
        "model_used": result.get("model_used"),
        "ai_status": alert.ai_status,
    }


# ─── POST /api/ai/review/run — review all pending alerts ─────────────────────

@router.post("/ai/review/run")
async def review_all_pending(
    limit: int = Query(20, ge=1, le=100),
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "view_ai_log")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    pending = (await session.execute(
        select(Alert)
        .where(Alert.ai_status == "pending", Alert.status == "open")
        .limit(limit)
    )).scalars().all()

    completed = 0
    unavailable = 0

    for alert in pending:
        result = await _apply_review(alert, session)
        if result["ai_available"]:
            completed += 1
        else:
            unavailable += 1

    await write_audit(
        session,
        role=role,
        channel="api",
        action="ai_review_batch",
        target=None,
        result=f"completed={completed} unavailable={unavailable}",
    )
    await session.commit()

    return {
        "reviewed": len(pending),
        "completed": completed,
        "unavailable": unavailable,
    }
