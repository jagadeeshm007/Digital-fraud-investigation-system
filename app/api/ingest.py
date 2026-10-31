from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.db import get_session
from app.exceptions import IngestionError, PermissionDenied
from app.ingestion import ingest
from app.models import IngestionBatch, RejectedRecord
from app.permissions import check_permission, resolve_role

router = APIRouter(tags=["ingest"])


@router.post("/ingest")
async def upload_file(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "upload_file")
    except PermissionDenied as e:
        await write_audit(session, role, "app", "upload_file", None, "denied")
        await session.commit()
        raise HTTPException(403, detail=str(e))

    file_bytes = await file.read()
    try:
        batch = await ingest(file_bytes, file.filename or "upload", source_type, session)
    except IngestionError as e:
        raise HTTPException(400, detail={"error": e.code, "detail": e.detail})

    await write_audit(session, role, "app", "upload_file", batch.batch_id, "allowed")
    await session.commit()

    return {
        "batch_id": batch.batch_id,
        "source_type": batch.source_type,
        "accepted_count": batch.accepted_count,
        "rejected_count": batch.rejected_count,
        "warning_count": batch.warning_count,
    }


@router.get("/ingest/{batch_id}/rejected")
async def get_rejected(
    batch_id: str,
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "upload_file")
    except PermissionDenied as e:
        await write_audit(session, role, "app", "upload_file", batch_id, "denied")
        await session.commit()
        raise HTTPException(403, detail=str(e))

    batch = await session.get(IngestionBatch, batch_id)
    if not batch:
        raise HTTPException(404, detail="Batch not found")

    result = await session.execute(
        select(RejectedRecord).where(RejectedRecord.batch_id == batch_id)
    )
    records = result.scalars().all()

    return {
        "batch_id": batch_id,
        "records": [
            {
                "rejected_id": r.rejected_id,
                "row_number": r.row_number,
                "field": r.field,
                "reason": r.reason,
                "raw_values": r.raw_values,
            }
            for r in records
        ],
    }
