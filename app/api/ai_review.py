from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.review import estimate_cost, review_alert
from app.audit import write_audit
from app.config import settings
from app.db import get_session
from app.exceptions import PermissionDenied
from app.models import AiCallLog, Alert
from app.permissions import check_permission, resolve_role

router = APIRouter(tags=["ai-review"])


async def spent_usd(session: AsyncSession) -> float:
    total = (await session.execute(select(func.coalesce(func.sum(AiCallLog.cost_usd), 0)))).scalar_one()
    return float(total)


async def apply_review(alert: Alert, session: AsyncSession) -> dict:
    """Run one review, persist it onto the alert and log the call (FR5, FR10)."""
    budget_left = settings.ai_budget_usd - await spent_usd(session)
    result = await review_alert(alert, budget_left)

    alert.ai_adjustment = result["risk_adjustment"]
    alert.final_score = max(0, min(100, alert.base_score + result["risk_adjustment"]))
    if alert.final_score >= 70:
        alert.risk_band = "High"
    elif alert.final_score >= 40:
        alert.risk_band = "Medium"
    else:
        alert.risk_band = "Low"
    alert.ai_recommendation = f"{result['recommended_decision'].upper()}: {result['reasoning']}"
    alert.ai_status = "completed" if result["ai_available"] else "unavailable"

    model = result.get("model_used")
    session.add(AiCallLog(
        alert_id=alert.alert_id,
        model=model,
        tokens_in=result["tokens_in"],
        tokens_out=result["tokens_out"],
        latency_ms=result["latency_ms"],
        cost_usd=Decimal(str(round(estimate_cost(model, result["tokens_in"], result["tokens_out"]), 6))),
        outcome="fake" if model == "fake" else alert.ai_status,
        prompt_masked=result["prompt"],
    ))
    # The AI may move an alert's score, so its case's risk and priority are recomputed.
    # It never adds or removes links: grouping comes from matching identifiers only.
    from app.cases import refresh_cases_for_alerts
    await refresh_cases_for_alerts(session, [alert.alert_id])
    await session.commit()
    return result


async def review_pending(session: AsyncSession, alert_ids: list[str] | None = None, limit: int = 20) -> dict:
    """Review open alerts still pending AI. Called in the background after detection (NFR2)."""
    q = select(Alert).where(Alert.ai_status == "pending", Alert.status == "open")
    if alert_ids is not None:
        q = q.where(Alert.alert_id.in_(alert_ids))
    pending = (await session.execute(q.limit(limit))).scalars().all()

    completed = unavailable = 0
    for alert in pending:
        if (await apply_review(alert, session))["ai_available"]:
            completed += 1
        else:
            unavailable += 1
    return {"reviewed": len(pending), "completed": completed, "unavailable": unavailable}


def _require(x_role: str | None, action: str) -> str:
    role = resolve_role(x_role)
    try:
        check_permission(role, action)
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))
    return role


# ─── POST /api/ai/review/run — review all pending alerts ─────────────────────
# Declared before /ai/review/{alert_id} so "run" is not captured as an alert id.

@router.post("/ai/review/run")
async def review_all_pending(
    limit: int = Query(20, ge=1, le=100),
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = _require(x_role, "run_detection")
    summary = await review_pending(session, limit=limit)
    await write_audit(
        session, role=role, channel="api", action="ai_review_batch", target=None,
        result=f"completed={summary['completed']} unavailable={summary['unavailable']}",
    )
    await session.commit()
    return summary


# ─── POST /api/ai/review/{alert_id} ──────────────────────────────────────────

@router.post("/ai/review/{alert_id}")
async def review_one(
    alert_id: str,
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = _require(x_role, "run_detection")
    alert = await session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, detail="Alert not found")
    if alert.status == "cleared":
        raise HTTPException(400, detail="Cleared alerts do not need AI review")

    result = await apply_review(alert, session)
    await write_audit(
        session, role=role, channel="api", action="ai_review", target=alert_id,
        result=f"adj={result['risk_adjustment']} decision={result['recommended_decision']} "
               f"available={result['ai_available']}",
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


# ─── GET /api/ai/log — AI Activity screen (FR10) ─────────────────────────────

@router.get("/ai/log")
async def ai_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    _require(x_role, "view_ai_log")
    rows = (await session.execute(
        select(AiCallLog).order_by(AiCallLog.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    total = (await session.execute(select(func.count()).select_from(AiCallLog))).scalar_one()
    spent = await spent_usd(session)
    return {
        "items": [ai_log_dict(r) for r in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "spent_usd": round(spent, 4),
        "budget_usd": settings.ai_budget_usd,
        "budget_warning": spent >= 0.8 * settings.ai_budget_usd,
    }


def ai_log_dict(r: AiCallLog) -> dict:
    return {
        "call_id": r.call_id,
        "alert_id": r.alert_id,
        "created_at": r.created_at.isoformat(),
        "model": r.model,
        "tokens_in": r.tokens_in,
        "tokens_out": r.tokens_out,
        "latency_ms": r.latency_ms,
        "cost_usd": str(r.cost_usd),
        "outcome": r.outcome,
        "prompt_masked": r.prompt_masked,
    }
