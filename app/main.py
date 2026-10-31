import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

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


class SPAStaticFiles(StaticFiles):
    """Serve index.html for unknown paths so deep links like /alerts/123 survive a refresh."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or path.startswith("api/"):
                raise
            return await super().get_response("index.html", scope)


if settings.serve_frontend:
    dist = Path(__file__).parent.parent / "frontend" / "dist"
    app.mount("/", SPAStaticFiles(directory=str(dist), html=True), name="static")
