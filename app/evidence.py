"""Resolve an alert's evidence IDs to the underlying records (FR6.3), masked for display."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.masking import mask_dict
from app.models import (
    Account,
    Alert,
    BeneficiaryChange,
    Customer,
    InsuranceClaim,
    LoanApplication,
    LoginEvent,
    Transaction,
)

# Tables whose primary key can appear as an evidence_id or entity_id.
_LOOKUP = (
    ("transaction", Transaction),
    ("login_event", LoginEvent),
    ("beneficiary_change", BeneficiaryChange),
    ("loan_application", LoanApplication),
    ("insurance_claim", InsuranceClaim),
    ("customer", Customer),
    ("account", Account),
)


def _plain(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)  # money stays exact (CLAUDE.md)
    return v


def _row_dict(obj) -> dict:
    return {c.key: _plain(getattr(obj, c.key)) for c in obj.__table__.columns}


async def load_evidence(session: AsyncSession, alert: Alert) -> list[dict]:
    ids = [str(f["evidence_id"]) for f in (alert.factors or []) if f.get("evidence_id")]
    ids.append(alert.entity_id)
    out: list[dict] = []
    for rid in dict.fromkeys(ids):  # dedupe, keep order
        for kind, model in _LOOKUP:
            obj = await session.get(model, rid)
            if obj is not None:
                out.append({"id": rid, "type": kind, "record": mask_dict(_row_dict(obj))})
                break
    out.sort(key=lambda e: str(e["record"].get("timestamp") or e["record"].get("applied_at") or ""))
    return out
