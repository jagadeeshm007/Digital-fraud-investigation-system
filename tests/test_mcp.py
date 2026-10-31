"""MCP gateway: reads are masked and role-checked; writes need the user's consent (FR11)."""
import pytest
import json
from types import SimpleNamespace

from sqlalchemy import select

from app import mcp_server as m
from app.db import async_session
from app.models import Case, ConsentRequest
from tests.conftest import as_role


@pytest.fixture
async def client(fresh_client):
    # These tests need an empty database each time; the shared session client is for test_e2e.
    yield fresh_client



class FakeCtx:
    """Stands in for the MCP Context: headers, declared capabilities, and the user's answer to a prompt."""

    def __init__(self, role="investigator", elicitation=True, answer="accept", confirm=True):
        self.headers = {"x-role": role}
        self.client_capabilities = SimpleNamespace(elicitation={} if elicitation else None)
        self._answer, self._confirm = answer, confirm
        self.prompts: list[str] = []

    async def elicit(self, message, schema):
        self.prompts.append(message)
        if self._answer == "accept":
            return SimpleNamespace(action="accept", data=schema(confirm=self._confirm))
        return SimpleNamespace(action=self._answer)


async def _seed(client):
    await client.post("/api/ingest/sample", headers=as_role("analyst"))
    await client.post("/api/detection/run", headers=as_role("investigator"))


async def _first_open_case() -> str:
    async with async_session() as s:
        return (await s.execute(select(Case.case_id).where(Case.status == "new").limit(1))).scalar_one()


async def test_read_tools_are_masked(client):
    await _seed(client)
    ctx = FakeCtx(role="analyst")
    dash = await m.get_dashboard(ctx)
    assert dash["processed_records"] > 0

    alerts = await m.list_alerts(ctx, risk_band="High")
    assert alerts["items"]
    detail = await m.get_alert(ctx, alerts["items"][0]["alert_id"])
    assert "evidence" in detail
    ato = (await m.list_alerts(ctx, customer_id="C9300"))["items"][0]
    dump = json.dumps(await m.get_alert(ctx, ato["alert_id"]))
    assert "Neelam Chawla" not in dump and "10.9.3.99" not in dump

    cases = await m.list_cases(ctx)
    assert cases["items"]
    assert (await m.get_case(ctx, cases["items"][0]["case_id"]))["history"] == []
    assert "items" in await m.get_ai_activity(ctx)
    assert (await m.get_alert(ctx, "missing"))["status"] == 404


async def test_write_requires_consent(client):
    await _seed(client)
    cid = await _first_open_case()
    ctx = FakeCtx()
    out = await m.record_case_decision(ctx, cid, "requires_investigation", "Shared device with ring")
    assert out["performed"] is True and out["case"]["status"] == "under_investigation"
    assert cid in ctx.prompts[0]


async def test_declined_or_unsupported_consent_changes_nothing(client):
    await _seed(client)
    cid = await _first_open_case()
    for ctx in (FakeCtx(answer="decline"), FakeCtx(answer="cancel"), FakeCtx(confirm=False),
                FakeCtx(elicitation=False)):
        out = await m.record_case_decision(ctx, cid, "false_positive", "looks fine")
        assert out["performed"] is False
    async with async_session() as s:
        case = await s.get(Case, cid)
        outcomes = (await s.execute(select(ConsentRequest.outcome))).scalars().all()
    assert case.status == "new"
    assert set(outcomes) == {"declined", "cancelled", "unsupported"}


async def test_role_checked_before_prompting(client):
    await _seed(client)
    ctx = FakeCtx(role="analyst")
    out = await m.record_case_decision(ctx, await _first_open_case(), "escalate", "x")
    assert out["status"] == 403 and ctx.prompts == []
    assert (await m.run_detection(ctx))["status"] == 403


async def test_run_detection_with_consent(client):
    await client.post("/api/ingest/sample", headers=as_role("analyst"))
    out = await m.run_detection(FakeCtx())
    assert out["performed"] and out["new_alerts"] > 0 and out["ai_review"]["reviewed"] > 0
    audit = (await client.get("/api/audit?page_size=200", headers=as_role("analyst"))).json()
    assert any(e["channel"] == "mcp" for e in audit["items"])


async def test_mcp_endpoint_is_mounted(client):
    assert any(getattr(r, "path", "") == "/mcp" for r in client._transport.app.routes)
    tools = {t.name for t in await m.mcp.list_tools()}
    assert {"get_dashboard", "list_alerts", "get_alert", "list_cases", "get_case", "get_ai_activity",
            "record_case_decision", "run_detection"} <= tools
    assert not any("reveal" in t for t in tools)  # PII never leaves through MCP
