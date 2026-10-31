"""Tests run against a real Postgres (CI service, or a local container) with FAKE_LLM=1."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://dfis:dfis_ci@localhost:55432/dfis_test")
os.environ.setdefault("MASKING_HMAC_KEY", "ab" * 32)
os.environ["FAKE_LLM"] = "1"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


async def reset_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
async def client():
    await reset_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def as_role(role: str) -> dict:
    return {"X-Role": role}
