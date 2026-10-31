"""
Test configuration.
- CI:    DATABASE_URL is set to a postgres test service
- Local: falls back to SQLite so no extra DB setup is needed
Supabase production URLs are never used in tests.
"""
import os

# Set env vars BEFORE any app import so pydantic-settings picks them up
_db_url = os.environ.get("DATABASE_URL", "")
if not _db_url or "supabase" in _db_url or "pooler.supabase" in _db_url:
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_dfis.db"

os.environ.setdefault("MASKING_HMAC_KEY", "ab" * 32)
os.environ["FAKE_LLM"] = "1"
os.environ.setdefault("GROQ_API_KEY", "fake-key-for-tests")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


async def _reset_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(scope="session")
async def client():
    """Session-scoped client — DB is reset once, tests build state on each other."""
    await _reset_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def as_role(role: str) -> dict:
    return {"X-Role": role}


def pytest_sessionfinish(session, exitstatus):
    try:
        os.unlink("./test_dfis.db")
    except FileNotFoundError:
        pass


@pytest_asyncio.fixture
async def fresh_client():
    """Function-scoped client on an empty database (scenario, API and MCP tests)."""
    await _reset_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
