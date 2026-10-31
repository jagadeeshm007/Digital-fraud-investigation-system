import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.config import settings
from app.db import get_session
from app.detection.engine import run_detection
from app.evidence import load_evidence
from app.exceptions import PermissionDenied
from app.masking import REVEALABLE, mask
from app.models import (
    Account,
    Alert,
    Case,
    CaseHistory,
    Customer,
    InsuranceClaim,
    LoanApplication,
    LoginEvent,
    Transaction,
)
from app.permissions import check_permission, resolve_role

log = logging.getLogger(__name__)
router = APIRouter(tags=["detection"])

IST = timezone(timedelta(hours=5, minutes=30))
_SOURCE_TABLES = (Customer, Account, Transaction, LoginEvent, LoanApplication, InsuranceClaim)


# ─── POST /api/detection/run ─────────────────────────────────────────────────

async def _review_in_background(alert_ids: list[str]) -> None:
    # Own session: the request's session is closed once the response is sent.
    from app.api.ai_review import review_pending
    from app.db import async_session

    async with async_session() as session:
        try:
            await review_pending(session, alert_ids, limit=settings.ai_review_batch)
        except Exception:  # never let AI failure surface as a detection failure (NFR6)
            log.exception("background AI review failed")


@router.post("/detection/run")
async def trigger_detection(
    background: BackgroundTasks,
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "run_detection")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    result = await run_detection(session, triggered_by=role)
    if result["review_alert_ids"]:
        background.add_task(_review_in_background, result["review_alert_ids"])
    return result


# ─── GET /api/alerts ─────────────────────────────────────────────────────────

@router.get("/alerts")
async def list_alerts(
    customer_id: str | None = Query(default=None),
    transaction_id: str | None = Query(default=None),
    risk_band: str | None = Query(default=None),
    fraud_category: str | None = Query(default=None),
    rule_id: str | None = Query(default=None),
    product: str | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
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
    if rule_id:
        q = q.where(Alert.rule_id == rule_id)
    if transaction_id:
        # the transaction is either the flagged entity or cited as evidence in a factor
        q = q.where(or_(
            Alert.entity_id == transaction_id,
            cast(Alert.factors, String).contains(f'"{transaction_id}"'),
        ))
    # Day boundaries in IST, since the bank data is Indian (requirements assumption)
    if date_from:
        q = q.where(Alert.detected_at >= datetime.combine(date_from, time.min, IST))
    if date_to:
        q = q.where(Alert.detected_at < datetime.combine(date_to + timedelta(days=1), time.min, IST))

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

    case_id = (await session.execute(
        select(Case.case_id).where(Case.alert_id == alert_id)
    )).scalar_one_or_none()
    return {**_alert_dict(alert), "case_id": case_id, "evidence": await load_evidence(session, alert)}


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

    customer = await session.get(Customer, case.customer_id) if case.customer_id else None
    masked = {f: mask(str(getattr(customer, f)), f) for f in REVEALABLE} if customer else None
    return {**_case_dict(case), "customer": masked, "history": [_history_dict(h) for h in history]}


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


class DecisionError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(detail)


async def record_case_decision(
    session: AsyncSession, case_id: str, decision: str, reason: str, role: str, channel: str
) -> Case:
    """Shared by the web API and the MCP gateway, so both enforce the same rules (ADR-006)."""
    if decision not in _VALID_DECISIONS:
        raise DecisionError(400, f"decision must be one of {sorted(_VALID_DECISIONS)}")
    if not reason or not reason.strip():
        raise DecisionError(400, "A reason is required")
    check_permission(role, _DECISION_PERMISSION[decision])  # PermissionDenied -> 403

    case = (await session.execute(select(Case).where(Case.case_id == case_id))).scalar_one_or_none()
    if not case:
        raise DecisionError(404, "Case not found")
    if case.status in ("closed", "escalated"):
        raise DecisionError(409, f"Case is already {case.status}")

    from_status, to_status = case.status, _DECISION_STATUS_MAP[decision]
    now = datetime.now(timezone.utc)
    session.add(CaseHistory(
        history_id=str(uuid.uuid4()), case_id=case_id, changed_at=now, changed_by=role,
        from_status=from_status, to_status=to_status, decision=decision, reason=reason,
    ))
    case.status = to_status
    case.updated_at = now
    await write_audit(
        session, role=role, channel=channel, action="record_case_decision",
        target=case_id, result=f"{decision}: {reason[:80]}",
    )
    await session.commit()
    return case


@router.patch("/cases/{case_id}/decision")
async def record_decision(
    case_id: str,
    body: DecisionRequest,
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        case = await record_case_decision(session, case_id, body.decision, body.reason, role, "api")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))
    except DecisionError as e:
        raise HTTPException(e.status, detail=e.detail)
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
    processed = 0
    for model in _SOURCE_TABLES:
        processed += (await session.execute(select(func.count()).select_from(model))).scalar_one()

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
        "processed_records": processed,
        "flagged_events": len(open_alerts),
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
