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


async def run_detection(session: AsyncSession, triggered_by: str = "investigator") -> dict:
    hits = await run_all_rules(session)

    # Load existing (rule_id, entity_id) pairs to avoid duplicates
    existing = {
        (a.rule_id, a.entity_id)
        for a in (await session.execute(select(Alert))).scalars().all()
    }

    new_alerts = 0
    new_cases = 0
    cleared_count = 0

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
        else:
            # Create a case for every open alert
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
        channel="api",
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
    }
