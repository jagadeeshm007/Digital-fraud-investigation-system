from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.exceptions import PermissionDenied
from app.models import AuditEntry
from app.permissions import check_permission, resolve_role

router = APIRouter(tags=["audit"])


@router.get("/audit")
async def get_audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "view_audit")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    offset = (page - 1) * page_size
    rows = (await session.execute(
        select(AuditEntry).order_by(AuditEntry.timestamp.desc()).offset(offset).limit(page_size)
    )).scalars().all()

    total = (await session.execute(select(func.count()).select_from(AuditEntry))).scalar_one()

    return {
        "items": [
            {
                "audit_id": e.audit_id,
                "timestamp": e.timestamp.isoformat(),
                "role": e.role,
                "channel": e.channel,
                "action": e.action,
                "target": e.target,
                "result": e.result,
            }
            for e in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }
