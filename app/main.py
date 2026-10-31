import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import api_router
from app.config import settings
from app.db import engine
from app.exceptions import IngestionError, PermissionDenied
from app.mcp_server import mcp, mcp_http_app
from app.models import Base

logging.basicConfig(level=settings.log_level)

_mcp_app = mcp_http_app()  # builds mcp.session_manager


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="DFIS", version="0.1.0", lifespan=lifespan)


@app.exception_handler(PermissionDenied)
async def _perm(_req: Request, exc: PermissionDenied):
    return JSONResponse({"error": "permission_denied", "detail": str(exc)}, status_code=403)


@app.exception_handler(IngestionError)
async def _ingest(_req: Request, exc: IngestionError):
    return JSONResponse({"error": exc.code, "detail": exc.detail}, status_code=400)


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


app.include_router(api_router)
# MCP over Streamable HTTP at /mcp (FR11), sharing the app's process, data and checks (ADR-006).
app.router.routes.extend(_mcp_app.routes)


if settings.serve_frontend:
    # Low-priority routes: API, /mcp and /healthz always win; unknown page paths get index.html
    # so deep links like /alerts/123 survive a refresh. On Vercel the files go to the CDN.
    dist = Path(__file__).parent.parent / "frontend" / "dist"
    app.frontend("/", directory=str(dist), fallback="index.html")
