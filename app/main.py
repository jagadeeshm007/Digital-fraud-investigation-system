import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.config import settings
from app.db import engine
from app.exceptions import IngestionError, PermissionDenied
from app.models import Base

logging.basicConfig(level=settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="DFIS", version="0.1.0", lifespan=lifespan)


@app.exception_handler(PermissionDenied)
async def _perm(_req: Request, exc: PermissionDenied):
    return JSONResponse(403, {"error": "permission_denied", "detail": str(exc)})


@app.exception_handler(IngestionError)
async def _ingest(_req: Request, exc: IngestionError):
    return JSONResponse(400, {"error": exc.code, "detail": exc.detail})


app.include_router(api_router)


if settings.serve_frontend:
    dist = Path(__file__).parent.parent / "frontend" / "dist"
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="static")
