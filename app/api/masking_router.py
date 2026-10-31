import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.db import get_session
from app.exceptions import PermissionDenied
from app.models import RevealEvent
from app.permissions import check_permission, resolve_role

router = APIRouter(tags=["masking"])


class RevealRequest(BaseModel):
    case_id: str
    field: str


@router.post("/masking/reveal")
async def reveal_pii(
    body: RevealRequest,
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    target = f"{body.case_id}:{body.field}"

    try:
        check_permission(role, "reveal_pii")
    except PermissionDenied as e:
        await write_audit(session, role, "app", "reveal_pii", target, "denied")
        await session.commit()
        raise HTTPException(403, detail=str(e))

    session.add(RevealEvent(
        reveal_id=str(uuid.uuid4()),
        case_id=body.case_id,
        field=body.field,
        revealed_by=role,
        revealed_at=datetime.now(timezone.utc),
    ))
    await write_audit(session, role, "app", "reveal_pii", target, "allowed")
    await session.commit()

    # ponytail: plaintext lookup added in B2 once cases table exists
    return {"case_id": body.case_id, "field": body.field, "plaintext_value": None}
