import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.db import get_session
from app.detection.engine import run_detection
from app.exceptions import PermissionDenied
from app.models import Alert, Case, CaseHistory
from app.permissions import check_permission, resolve_role

router = APIRouter(tags=["detection"])


# ─── POST /api/detection/run ─────────────────────────────────────────────────

@router.post("/detection/run")
async def trigger_detection(
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "run_detection")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    result = await run_detection(session, triggered_by=role)
    return result


# ─── GET /api/alerts ─────────────────────────────────────────────────────────

@router.get("/alerts")
async def list_alerts(
    customer_id: str | None = Query(default=None),
    risk_band: str | None = Query(default=None),
    fraud_category: str | None = Query(default=None),
    product: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "view_alerts")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    q = select(Alert).order_by(Alert.detected_at.desc())
    if customer_id:
        q = q.where(Alert.customer_id == customer_id)
    if risk_band:
        q = q.where(Alert.risk_band == risk_band)
    if fraud_category:
        q = q.where(Alert.fraud_category.ilike(f"%{fraud_category}%"))
    if product:
        q = q.where(Alert.product == product)
    if status:
        q = q.where(Alert.status == status)

    total = (await session.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar_one()

    offset = (page - 1) * page_size
    rows = (await session.execute(q.offset(offset).limit(page_size))).scalars().all()

    return {
        "items": [_alert_dict(a) for a in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/alerts/{alert_id}")
async def get_alert(
    alert_id: str,
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "view_alerts")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    alert = (await session.execute(
        select(Alert).where(Alert.alert_id == alert_id)
    )).scalar_one_or_none()
    if not alert:
        raise HTTPException(404, detail="Alert not found")

    return _alert_dict(alert)


# ─── GET /api/cases ──────────────────────────────────────────────────────────

@router.get("/cases")
async def list_cases(
    customer_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "view_cases")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    q = select(Case).order_by(Case.created_at.desc())
    if customer_id:
        q = q.where(Case.customer_id == customer_id)
    if status:
        q = q.where(Case.status == status)
    if risk_level:
        q = q.where(Case.risk_level == risk_level)

    total = (await session.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar_one()

    offset = (page - 1) * page_size
    rows = (await session.execute(q.offset(offset).limit(page_size))).scalars().all()

    return {
        "items": [_case_dict(c) for c in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/cases/{case_id}")
async def get_case(
    case_id: str,
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "view_cases")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    case = (await session.execute(
        select(Case).where(Case.case_id == case_id)
    )).scalar_one_or_none()
    if not case:
        raise HTTPException(404, detail="Case not found")

    history = (await session.execute(
        select(CaseHistory)
        .where(CaseHistory.case_id == case_id)
        .order_by(CaseHistory.changed_at)
    )).scalars().all()

    return {**_case_dict(case), "history": [_history_dict(h) for h in history]}


# ─── PATCH /api/cases/{case_id}/decision ─────────────────────────────────────

class DecisionRequest(BaseModel):
    decision: str  # requires_investigation | false_positive | escalate
    reason: str


_VALID_DECISIONS = {"requires_investigation", "false_positive", "escalate"}

_DECISION_STATUS_MAP = {
    "requires_investigation": "under_investigation",
    "false_positive": "closed",
    "escalate": "escalated",
}

_DECISION_PERMISSION = {
    "requires_investigation": "record_case_decision",
    "false_positive": "record_case_decision",
    "escalate": "escalate_case",
}


@router.patch("/cases/{case_id}/decision")
async def record_decision(
    case_id: str,
    body: DecisionRequest,
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)

    if body.decision not in _VALID_DECISIONS:
        raise HTTPException(400, detail=f"decision must be one of {sorted(_VALID_DECISIONS)}")

    required_perm = _DECISION_PERMISSION[body.decision]
    try:
        check_permission(role, required_perm)
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    case = (await session.execute(
        select(Case).where(Case.case_id == case_id)
    )).scalar_one_or_none()
    if not case:
        raise HTTPException(404, detail="Case not found")

    if case.status in ("closed", "escalated"):
        raise HTTPException(409, detail=f"Case is already {case.status}")

    from_status = case.status
    to_status = _DECISION_STATUS_MAP[body.decision]

    history = CaseHistory(
        history_id=str(uuid.uuid4()),
        case_id=case_id,
        changed_at=datetime.now(timezone.utc),
        changed_by=role,
        from_status=from_status,
        to_status=to_status,
        decision=body.decision,
        reason=body.reason,
    )
    session.add(history)

    case.status = to_status
    case.updated_at = datetime.now(timezone.utc)

    await write_audit(
        session,
        role=role,
        channel="api",
        action="record_case_decision",
        target=case_id,
        result=f"{body.decision}: {body.reason[:80]}",
    )

    await session.commit()
    return _case_dict(case)


# ─── GET /api/detection/summary ──────────────────────────────────────────────

@router.get("/detection/summary")
async def detection_summary(
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "view_alerts")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    alerts = (await session.execute(select(Alert))).scalars().all()
    cases = (await session.execute(select(Case))).scalars().all()

    open_alerts = [a for a in alerts if a.status == "open"]
    cleared_alerts = [a for a in alerts if a.status == "cleared"]

    risk_distribution = {"Low": 0, "Medium": 0, "High": 0}
    category_counts: dict[str, int] = {}
    for a in open_alerts:
        risk_distribution[a.risk_band] = risk_distribution.get(a.risk_band, 0) + 1
        category_counts[a.fraud_category] = category_counts.get(a.fraud_category, 0) + 1

    case_status_counts: dict[str, int] = {}
    for c in cases:
        case_status_counts[c.status] = case_status_counts.get(c.status, 0) + 1

    return {
        "total_alerts": len(alerts),
        "open_alerts": len(open_alerts),
        "cleared_alerts": len(cleared_alerts),
        "risk_distribution": risk_distribution,
        "fraud_categories": category_counts,
        "case_statuses": case_status_counts,
        "open_cases": len([c for c in cases if c.status not in ("closed", "escalated")]),
    }


# ─── Serialisation helpers ────────────────────────────────────────────────────

def _alert_dict(a: Alert) -> dict:
    return {
        "alert_id": a.alert_id,
        "rule_id": a.rule_id,
        "fraud_category": a.fraud_category,
        "entity_type": a.entity_type,
        "entity_id": a.entity_id,
        "customer_id": a.customer_id,
        "product": a.product,
        "detected_at": a.detected_at.isoformat(),
        "base_score": a.base_score,
        "ai_adjustment": a.ai_adjustment,
        "final_score": a.final_score,
        "risk_band": a.risk_band,
        "factors": a.factors,
        "ai_recommendation": a.ai_recommendation,
        "ai_status": a.ai_status,
        "status": a.status,
        "cleared_reason": a.cleared_reason,
    }


def _case_dict(c: Case) -> dict:
    return {
        "case_id": c.case_id,
        "alert_id": c.alert_id,
        "customer_id": c.customer_id,
        "fraud_category": c.fraud_category,
        "risk_level": c.risk_level,
        "status": c.status,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


def _history_dict(h: CaseHistory) -> dict:
    return {
        "history_id": h.history_id,
        "changed_at": h.changed_at.isoformat(),
        "changed_by": h.changed_by,
        "from_status": h.from_status,
        "to_status": h.to_status,
        "decision": h.decision,
        "reason": h.reason,
    }
