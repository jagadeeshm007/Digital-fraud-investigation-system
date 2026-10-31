from fastapi import APIRouter

from app.api.ai_review import router as ai_review_router
from app.api.audit import router as audit_router
from app.api.detection import router as detection_router
from app.api.graph import router as graph_router
from app.api.ingest import router as ingest_router
from app.api.masking_router import router as masking_router

api_router = APIRouter(prefix="/api")
api_router.include_router(ingest_router)
api_router.include_router(masking_router)
api_router.include_router(audit_router)
api_router.include_router(detection_router)
api_router.include_router(ai_review_router)
api_router.include_router(graph_router)
