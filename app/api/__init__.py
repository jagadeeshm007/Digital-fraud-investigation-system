from fastapi import APIRouter

from app.api.audit import router as audit_router
from app.api.ingest import router as ingest_router
from app.api.masking_router import router as masking_router

api_router = APIRouter(prefix="/api")
api_router.include_router(ingest_router)
api_router.include_router(masking_router)
api_router.include_router(audit_router)
