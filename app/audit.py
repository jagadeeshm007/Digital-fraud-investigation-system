import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEntry


async def write_audit(
    session: AsyncSession,
    role: str,
    channel: str,
    action: str,
    target: str | None,
    result: str,
    user: str | None = None,
) -> None:
    session.add(AuditEntry(
        audit_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        role=role,
        channel=channel,
        action=action,
        target=target,
        result=result,
        user_id=user,
    ))
