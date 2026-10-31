"""
Detection engine: runs all rules, deduplicates, persists Alert + Case records.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.models import Alert, Case
from app.detection.rules import run_all_rules


def _risk_band(score: int) -> str:
    if score >= 70:
        return "High"
    elif score >= 40:
        return "Medium"
    return "Low"


# Correlation: an entity flagged by several independent rules is riskier than any one rule says
# (challenge: score from multiple indicators, not a single threshold).
_CORRELATION_POINTS = 15
_CORRELATION_CAP = 30


def _family(rule_id: str) -> str:
    return rule_id.split("-", 1)[0]  # "R3-ATO" -> "R3"


def _add_correlation(hits: list) -> None:
    families: dict[str, set[str]] = {}
    for h in hits:
        if not h.cleared and h.customer_id:
            families.setdefault(h.customer_id, set()).add(_family(h.rule_id))
    for h in hits:
        if h.cleared or not h.customer_id:
            continue
        others = sorted(families[h.customer_id] - {_family(h.rule_id)})
        if not others:
            continue
        pts = min(_CORRELATION_POINTS * len(others), _CORRELATION_CAP)
        h.factors = [*h.factors, {
            "factor": f"Same customer also flagged by rules {', '.join(others)}",
            "points": pts,
            "evidence_id": h.customer_id,
        }]
        h.base_score = min(100, h.base_score + pts)


async def run_detection(
    session: AsyncSession, triggered_by: str = "investigator", channel: str = "api"
) -> dict:
    hits = await run_all_rules(session)
    _add_correlation(hits)

    # Load existing (rule_id, entity_id) pairs to avoid duplicates
    existing = {
        (a.rule_id, a.entity_id)
        for a in (await session.execute(select(Alert))).scalars().all()
    }

    new_alerts = 0
    new_cases = 0
    cleared_count = 0
    review_ids: list[str] = []

    for hit in hits:
        key = (hit.rule_id, hit.entity_id)
        if key in existing:
            continue
        existing.add(key)

        score = hit.base_score
        band = _risk_band(score)
        status = "cleared" if hit.cleared else "open"

        alert = Alert(
            alert_id=str(uuid.uuid4()),
            rule_id=hit.rule_id,
            fraud_category=hit.fraud_category,
            entity_type=hit.entity_type,
            entity_id=hit.entity_id,
            customer_id=hit.customer_id,
            product=hit.product,
            detected_at=datetime.now(timezone.utc),
            base_score=score,
            ai_adjustment=0,
            final_score=score,
            risk_band=band,
            factors=hit.factors,
            ai_recommendation=None,
            ai_status="bypassed" if hit.cleared else "pending",
            status=status,
            cleared_reason=hit.cleared_reason,
        )
        session.add(alert)
        new_alerts += 1

        if hit.cleared:
            cleared_count += 1
        elif band in ("Medium", "High"):
            # FR7.1: only actionable (Medium/High) alerts open a case; Low stays on the dashboard
            review_ids.append(alert.alert_id)
            case = Case(
                case_id=str(uuid.uuid4()),
                alert_id=alert.alert_id,
                customer_id=hit.customer_id,
                fraud_category=hit.fraud_category,
                risk_level=band,
                status="new",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(case)
            new_cases += 1

    await session.commit()

    await write_audit(
        session,
        role=triggered_by,
        channel=channel,
        action="run_detection",
        target=None,
        result=f"new_alerts={new_alerts} new_cases={new_cases} cleared={cleared_count}",
    )
    await session.commit()

    return {
        "new_alerts": new_alerts,
        "new_cases": new_cases,
        "cleared_count": cleared_count,
        "total_hits": len(hits),
        "review_alert_ids": review_ids,
    }
