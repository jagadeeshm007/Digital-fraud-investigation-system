"""
Investigation services (Level 2), shared by the web API and the MCP gateway so both enforce the
same rules: workspace view, prioritisation, split, notes, recommendations, risk override, report.
"""
import math
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.detection.correlation import FINAL_STATUSES, alert_identifiers
from app.evidence import load_evidence
from app.masking import mask_dict
from app.models import AiCallLog, Alert, AuditEntry, Case, CaseAlert, CaseHistory, CaseNote, Recommendation
from app.permissions import check_permission


class CaseError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(detail)


RISK_LEVELS = ("Low", "Medium", "High")
_BAND_RANK = {b: i for i, b in enumerate(RISK_LEVELS)}
_AMOUNT_TYPES = ("transaction", "loan_application", "insurance_claim")
_TIME_FIELDS = ("timestamp", "applied_at", "changed_at", "claim_date", "incident_date", "opened_at", "onboarded_at")
# Weights of the four priority parts (Level 2 §6); they sum to 1.
WEIGHTS = {"severity": 0.40, "exposure": 0.25, "related_events": 0.15, "confidence": 0.20}
NEEDS_REVIEW_CAP = 40
EXPOSURE_FULL_INR = 10_000_000  # ₹1 crore scores full exposure on the log scale


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_text(value: str | None, what: str) -> str:
    if not value or not value.strip():
        raise CaseError(400, f"{what} is required")
    return value.strip()


async def get_case_or_404(session: AsyncSession, case_id: str) -> Case:
    case = await session.get(Case, case_id)
    if not case:
        raise CaseError(404, "Case not found")
    return case


async def case_members(session: AsyncSession, case_id: str) -> list[tuple[CaseAlert, Alert]]:
    rows = (await session.execute(
        select(CaseAlert, Alert).join(Alert, Alert.alert_id == CaseAlert.alert_id)
        .where(CaseAlert.case_id == case_id).order_by(CaseAlert.linked_at, Alert.final_score.desc())
    )).all()
    return [(ca, a) for ca, a in rows]


async def case_evidence(session: AsyncSession, alerts: list[Alert]) -> list[dict]:
    seen: dict[str, dict] = {}
    for a in alerts:
        for ev in await load_evidence(session, a):
            entry = seen.setdefault(ev["id"], {**ev, "alert_ids": []})
            entry["alert_ids"].append(a.alert_id)
    return sorted(seen.values(), key=lambda e: _record_time(e["record"]) or "")


def _record_time(record: dict) -> str | None:
    for f in _TIME_FIELDS:
        if record.get(f):
            return str(record[f])
    return None


# ─── Prioritisation ──────────────────────────────────────────────────────────

def _amount(record: dict) -> Decimal:
    try:
        return Decimal(str(record.get("amount_inr") or "0"))
    except InvalidOperation:
        return Decimal("0")


def compute_priority(alerts: list[Alert], evidence: list[dict]) -> dict:
    """priority_score 0-100 from severity, exposure, related events and confidence (Level 2 §6)."""
    exposure_inr = sum((_amount(e["record"]) for e in evidence if e["type"] in _AMOUNT_TYPES), Decimal("0"))
    factors = [f for a in alerts for f in (a.factors or []) if (f.get("points") or 0) > 0]
    backed = sum(1 for f in factors if f.get("evidence_id")) / len(factors) if factors else 0.0
    reviewed = [a for a in alerts if a.ai_status == "completed"]
    if not reviewed:
        ai_agrees = 0.5  # no AI opinion yet: neutral
    else:
        ai_agrees = sum(1 for a in reviewed if (a.ai_adjustment or 0) >= 0) / len(reviewed)

    parts = {
        "severity": max((a.final_score for a in alerts), default=0) / 100,
        "exposure": min(1.0, math.log10(1 + float(exposure_inr)) / math.log10(1 + EXPOSURE_FULL_INR)),
        "related_events": min(1.0, (len(alerts) + len(evidence)) / 10),
        "confidence": 0.75 * backed + 0.25 * ai_agrees,
    }
    score = round(100 * sum(WEIGHTS[k] * v for k, v in parts.items()))

    review_reasons = []
    if len(factors) <= 1:
        review_reasons.append("only one indicator")
    if parts["confidence"] < 0.5:
        review_reasons.append("low confidence in the detection")
    if exposure_inr == 0:
        review_reasons.append("no amount in the evidence")
    if review_reasons:
        score = min(score, NEEDS_REVIEW_CAP)  # weak evidence is never automatically top priority

    return {
        "priority_score": score,
        "needs_review": bool(review_reasons),
        "parts": {
            **{k: round(v, 3) for k, v in parts.items()},
            "weights": WEIGHTS,
            "exposure_inr": str(exposure_inr.quantize(Decimal("0.01"))),
            "alert_count": len(alerts),
            "evidence_count": len(evidence),
            "factor_count": len(factors),
            "review_reasons": review_reasons,
        },
    }


async def refresh_case(session: AsyncSession, case: Case) -> None:
    """Recompute risk level (unless an analyst overrode it) and priority after the case changes."""
    alerts = [a for _, a in await case_members(session, case.case_id)]
    if not alerts:
        return
    if case.risk_original is None:
        case.risk_level = max((a.risk_band for a in alerts), key=lambda b: _BAND_RANK.get(b, 0))
    p = compute_priority(alerts, await case_evidence(session, alerts))
    case.priority_score = p["priority_score"]
    case.needs_review = p["needs_review"]
    case.priority_parts = p["parts"]


async def refresh_cases_for_alerts(session: AsyncSession, alert_ids: list[str]) -> None:
    case_ids = set((await session.execute(
        select(CaseAlert.case_id).where(CaseAlert.alert_id.in_(alert_ids)))).scalars().all())
    for cid in case_ids:
        case = await session.get(Case, cid)
        if case:
            await refresh_case(session, case)


# ─── Writes ──────────────────────────────────────────────────────────────────

def _history(case: Case, decision: str, reason: str, role: str, user: str, to_status: str | None = None):
    return CaseHistory(
        history_id=str(uuid.uuid4()), case_id=case.case_id, changed_at=_now(), changed_by=role,
        from_status=case.status, to_status=to_status or case.status, decision=decision, reason=reason, user_id=user,
    )


def _ensure_open(case: Case) -> None:
    if case.status in FINAL_STATUSES:
        raise CaseError(409, f"Case is already {case.status}")


async def open_case_from_alert(session: AsyncSession, alert_id: str, reason: str, role: str, user: str,
                               channel: str) -> Case:
    """An investigator can open a case for an alert detection left on the dashboard (e.g. Low risk)."""
    check_permission(role, "record_case_decision")
    reason = _require_text(reason, "A reason")
    alert = await session.get(Alert, alert_id)
    if not alert:
        raise CaseError(404, "Alert not found")
    if alert.status != "open":
        raise CaseError(409, "Only open alerts can start a case")
    if (await session.execute(select(CaseAlert).where(CaseAlert.alert_id == alert_id))).first():
        raise CaseError(409, "Alert is already in a case")
    now = _now()
    case = Case(case_id=str(uuid.uuid4()), alert_id=alert_id, customer_id=alert.customer_id,
                fraud_category=alert.fraud_category, risk_level=alert.risk_band, status="new",
                created_at=now, updated_at=now)
    session.add(case)
    await session.flush()
    session.add(CaseAlert(case_id=case.case_id, alert_id=alert_id, link_reason=f"Opened by {user}: {reason}",
                          links=[], linked_at=now))
    session.add(_history(case, "open_case", reason, role, user))
    await session.flush()
    await refresh_case(session, case)
    await write_audit(session, role, channel, "open_case", case.case_id, f"alert {alert_id}: {reason[:80]}", user)
    await session.commit()
    return case


async def split_alert(session: AsyncSession, case_id: str, alert_id: str, reason: str, role: str, user: str,
                      channel: str) -> Case:
    """Move a wrongly grouped alert into a new case. Nothing is deleted; both cases keep their evidence."""
    check_permission(role, "record_case_decision")
    reason = _require_text(reason, "A reason")
    case = await get_case_or_404(session, case_id)
    _ensure_open(case)
    members = await case_members(session, case_id)
    row = next((ca for ca, _ in members if ca.alert_id == alert_id), None)
    if row is None:
        raise CaseError(404, "Alert is not in this case")
    if len(members) < 2:
        raise CaseError(409, "A case with one alert cannot be split")

    alert = next(a for _, a in members if a.alert_id == alert_id)
    now = _now()
    new = Case(case_id=str(uuid.uuid4()), alert_id=alert_id, customer_id=alert.customer_id,
               fraud_category=alert.fraud_category, risk_level=alert.risk_band, status="new",
               created_at=now, updated_at=now, split_from=case_id)
    session.add(new)
    await session.flush()
    await session.delete(row)
    await session.flush()
    session.add(CaseAlert(case_id=new.case_id, alert_id=alert_id,
                          link_reason=f"Split from case {case_id[:8]} by {user}: {reason}", links=[], linked_at=now))

    if case.alert_id == alert_id:  # the primary left: the highest-scoring remaining alert takes over
        rest = [a for _, a in members if a.alert_id != alert_id]
        top = max(rest, key=lambda a: a.final_score)
        case.alert_id, case.fraud_category, case.customer_id = top.alert_id, top.fraud_category, top.customer_id
    session.add(_history(case, "split_out", f"Alert {alert_id} moved to case {new.case_id}: {reason}", role, user))
    session.add(_history(new, "split_in", f"Split from case {case_id}: {reason}", role, user))
    case.updated_at = now
    await session.flush()
    await refresh_case(session, case)
    await refresh_case(session, new)
    await write_audit(session, role, channel, "split_case", case_id,
                      f"alert {alert_id} -> case {new.case_id}: {reason[:80]}", user)
    await session.commit()
    return new


async def add_note(session: AsyncSession, case_id: str, body: str, role: str, user: str, channel: str) -> CaseNote:
    check_permission(role, "add_case_note")
    body = _require_text(body, "Note text")
    case = await get_case_or_404(session, case_id)
    note = CaseNote(note_id=str(uuid.uuid4()), case_id=case_id, author_user=user, author_role=role,
                    body=body[:4000], created_at=_now())
    session.add(note)
    case.updated_at = note.created_at
    await write_audit(session, role, channel, "add_case_note", case_id, f"note {note.note_id}", user)
    await session.commit()
    return note


async def decide_recommendation(session: AsyncSession, recommendation_id: str, approve: bool, reason: str,
                                role: str, user: str, channel: str) -> Recommendation:
    """Maker-checker: a Supervisor other than the maker approves or rejects. No account is ever changed."""
    check_permission(role, "approve_recommendation")
    reason = _require_text(reason, "A reason")
    rec = await session.get(Recommendation, recommendation_id)
    if not rec:
        raise CaseError(404, "Recommendation not found")
    if rec.status != "pending":
        raise CaseError(409, f"Recommendation is already {rec.status}")
    if rec.maker_user == user:
        raise CaseError(403, "The person who made a recommendation cannot approve or reject it")
    rec.status = "approved" if approve else "rejected"
    rec.decided_by, rec.decided_at, rec.decision_reason = user, _now(), reason
    case = await get_case_or_404(session, rec.case_id)
    session.add(_history(case, f"{rec.kind}_{rec.status}", reason, role, user))
    await write_audit(session, role, channel, f"recommendation_{rec.status}", rec.case_id,
                      f"{rec.kind} {rec.recommendation_id}: {reason[:80]}", user)
    await session.commit()
    return rec


async def override_risk(session: AsyncSession, case_id: str, risk_level: str, reason: str, role: str, user: str,
                        channel: str) -> Case:
    """Keeps the original classification the first time it changes, plus who changed it and why."""
    check_permission(role, "record_case_decision")
    reason = _require_text(reason, "A reason")
    if risk_level not in RISK_LEVELS:
        raise CaseError(400, f"risk_level must be one of {list(RISK_LEVELS)}")
    case = await get_case_or_404(session, case_id)
    _ensure_open(case)
    if risk_level == case.risk_level:
        raise CaseError(409, f"Case is already {risk_level}")
    old = case.risk_level
    if case.risk_original is None:
        case.risk_original = old
    case.risk_level, case.risk_reason, case.risk_changed_by = risk_level, reason, user
    case.updated_at = _now()
    session.add(_history(case, "risk_override", f"{old} -> {risk_level}: {reason}", role, user))
    await write_audit(session, role, channel, "override_risk", case_id, f"{old} -> {risk_level}: {reason[:80]}", user)
    await session.commit()
    return case


# ─── Reads ───────────────────────────────────────────────────────────────────

def case_dict(c: Case) -> dict:
    return {
        "case_id": c.case_id,
        "alert_id": c.alert_id,
        "customer_id": c.customer_id,
        "fraud_category": c.fraud_category,
        "risk_level": c.risk_level,
        "risk_original": c.risk_original,
        "risk_reason": c.risk_reason,
        "risk_changed_by": c.risk_changed_by,
        "status": c.status,
        "priority_score": c.priority_score or 0,
        "needs_review": bool(c.needs_review),
        "conclusion": c.conclusion,
        "split_from": c.split_from,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


def note_dict(n: CaseNote) -> dict:
    return {"note_id": n.note_id, "author_user": n.author_user, "author_role": n.author_role, "body": n.body,
            "created_at": n.created_at.isoformat()}


def recommendation_dict(r: Recommendation) -> dict:
    return {
        "recommendation_id": r.recommendation_id, "case_id": r.case_id, "kind": r.kind, "reason": r.reason,
        "status": r.status, "maker_user": r.maker_user, "maker_role": r.maker_role,
        "created_at": r.created_at.isoformat(), "decided_by": r.decided_by,
        "decided_at": r.decided_at.isoformat() if r.decided_at else None, "decision_reason": r.decision_reason,
        # Recording the authorisation is all this system does; it never touches accounts or transactions.
        "effect": "recommendation only - no account or transaction is changed",
    }


def _alert_brief(ca: CaseAlert, a: Alert) -> dict:
    return {
        "alert_id": a.alert_id, "rule_id": a.rule_id, "fraud_category": a.fraud_category, "product": a.product,
        "entity_type": a.entity_type, "entity_id": a.entity_id, "customer_id": a.customer_id,
        "detected_at": a.detected_at.isoformat(), "base_score": a.base_score, "ai_adjustment": a.ai_adjustment,
        "final_score": a.final_score, "risk_band": a.risk_band, "factors": a.factors,
        "ai_recommendation": a.ai_recommendation, "ai_status": a.ai_status, "status": a.status,
        "link_reason": ca.link_reason, "links": ca.links or [], "linked_at": ca.linked_at.isoformat(),
    }


def _summary(ev: dict) -> str:
    r = ev["record"]
    t = ev["type"]
    if t == "transaction":
        return f"Transfer ₹{r.get('amount_inr')} {r.get('sender_account_id')} → {r.get('beneficiary_account_id')}"
    if t == "login_event":
        return f"{r.get('event_type')} {r.get('outcome')} on device {r.get('device_id')}"
    if t == "beneficiary_change":
        return f"New payee {r.get('payee_account_id')} added"
    if t == "loan_application":
        return f"Loan ₹{r.get('amount_inr')} applied, paid to {r.get('disbursement_account_id')}"
    if t == "insurance_claim":
        return f"{r.get('claim_type')} claim ₹{r.get('amount_inr')} on policy {r.get('policy_id')}"
    if t == "account":
        return f"Account {r.get('account_id')} ({r.get('product')})"
    return f"Customer {r.get('customer_id')}"


async def workspace(session: AsyncSession, case: Case) -> dict:
    """Everything the investigation screen shows. All records are masked."""
    members = await case_members(session, case.case_id)
    alerts = [a for _, a in members]
    evidence = await case_evidence(session, alerts)

    timeline = [{"at": _record_time(e["record"]), "kind": "evidence", "type": e["type"], "id": e["id"],
                 "summary": _summary(e), "alert_ids": e["alert_ids"]} for e in evidence if _record_time(e["record"])]
    timeline += [{"at": a.detected_at.isoformat(), "kind": "alert", "type": a.rule_id, "id": a.alert_id,
                  "summary": f"{a.rule_id} flagged {a.entity_type} {a.entity_id} (score {a.final_score})",
                  "alert_ids": [a.alert_id]} for a in alerts]
    timeline.sort(key=lambda t: t["at"] or "")

    entities: dict[str, dict[str, list[str]]] = {}
    for a in alerts:
        for kind, value in sorted(await alert_identifiers(session, a)):
            entities.setdefault(kind, {}).setdefault(value, []).append(a.alert_id)

    indicators = [{**f, "rule_id": a.rule_id, "alert_id": a.alert_id} for a in alerts for f in (a.factors or [])]

    notes = (await session.execute(
        select(CaseNote).where(CaseNote.case_id == case.case_id).order_by(CaseNote.created_at))).scalars().all()
    recs = (await session.execute(
        select(Recommendation).where(Recommendation.case_id == case.case_id)
        .order_by(Recommendation.created_at))).scalars().all()
    history = (await session.execute(
        select(CaseHistory).where(CaseHistory.case_id == case.case_id).order_by(CaseHistory.changed_at)
    )).scalars().all()

    return {
        **case_dict(case),
        "alerts": [_alert_brief(ca, a) for ca, a in members],
        "evidence": evidence,
        "timeline": timeline,
        "entities": [{"type": k, "values": [{"value": v, "alert_ids": ids} for v, ids in vals.items()]}
                     for k, vals in sorted(entities.items())],
        "indicators": indicators,
        "risk": {
            "risk_level": case.risk_level, "risk_original": case.risk_original, "risk_reason": case.risk_reason,
            "risk_changed_by": case.risk_changed_by, "priority_score": case.priority_score or 0,
            "needs_review": bool(case.needs_review), "priority_parts": case.priority_parts or {},
        },
        "notes": [note_dict(n) for n in notes],
        "recommendations": [recommendation_dict(r) for r in recs],
        "history": [history_dict(h) for h in history],
    }


def history_dict(h: CaseHistory) -> dict:
    return {
        "history_id": h.history_id, "changed_at": h.changed_at.isoformat(), "changed_by": h.changed_by,
        "user_id": h.user_id, "from_status": h.from_status, "to_status": h.to_status, "decision": h.decision,
        "reason": h.reason,
    }


async def build_report(session: AsyncSession, case: Case) -> dict:
    """Structured, masked case report: the evidence history a reviewer needs (Level 2 §5)."""
    ws = await workspace(session, case)
    alert_ids = [a["alert_id"] for a in ws["alerts"]]
    calls = (await session.execute(
        select(AiCallLog).where(AiCallLog.alert_id.in_(alert_ids)).order_by(AiCallLog.created_at))).scalars().all()
    audit = (await session.execute(
        select(AuditEntry).where(or_(AuditEntry.target == case.case_id, AuditEntry.target.in_(alert_ids)))
        .order_by(AuditEntry.timestamp))).scalars().all()
    return {
        "report_type": "dfis_case_report",
        "generated_at": _now().isoformat(),
        "case": case_dict(case),
        "risk_assessment": ws["risk"],
        "alerts": ws["alerts"],
        "indicators": ws["indicators"],
        "evidence": ws["evidence"],
        "entities": ws["entities"],
        "timeline": ws["timeline"],
        "ai_reviews": [
            {"alert_id": a["alert_id"], "rule_id": a["rule_id"], "ai_status": a["ai_status"],
             "ai_adjustment": a["ai_adjustment"], "ai_recommendation": a["ai_recommendation"],
             "calls": [{"call_id": c.call_id, "created_at": c.created_at.isoformat(), "model": c.model,
                        "outcome": c.outcome} for c in calls if c.alert_id == a["alert_id"]]}
            for a in ws["alerts"]
        ],
        "history": ws["history"],
        "notes": ws["notes"],
        "recommendations": ws["recommendations"],
        "audit": [mask_dict({"timestamp": e.timestamp.isoformat(), "role": e.role, "user_id": e.user_id,
                             "channel": e.channel, "action": e.action, "target": e.target, "result": e.result})
                  for e in audit],
    }
