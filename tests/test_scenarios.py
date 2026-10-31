"""Acceptance tests: every planted fraud scenario is flagged, every lookalike is cleared (team practice)."""
from sqlalchemy import select

from app.db import async_session
from app.models import AiCallLog, Alert, Case
from app.sample_data import EXPECTED_CLEARED, EXPECTED_FLAGS, NEVER_FLAGGED
from tests.conftest import as_role

PLANTED_PREFIX = "C9"  # planted customers are C9xxx; everyone else is ordinary noise


async def _load_and_detect(client) -> dict:
    r = await client.post("/api/ingest/sample", headers=as_role("analyst"))
    assert r.status_code == 200, r.text
    assert all(b["rejected_count"] == 0 for b in r.json()["batches"]), r.json()
    r = await client.post("/api/detection/run", headers=as_role("investigator"))
    assert r.status_code == 200, r.text
    return r.json()


async def _alerts() -> list[Alert]:
    async with async_session() as s:
        return list((await s.execute(select(Alert))).scalars().all())


async def test_planted_scenarios_are_flagged(client):
    await _load_and_detect(client)
    alerts = await _alerts()
    open_by_rule: dict[str, set[str]] = {}
    for a in alerts:
        if a.status == "open":
            open_by_rule.setdefault(a.rule_id, set()).add(a.customer_id)

    for rule, customers in EXPECTED_FLAGS.items():
        found = open_by_rule.get(rule, set())
        if rule == "R2-SHARED-DEVICE":  # one alert per device, attributed to one ring member
            assert found & customers, f"{rule}: no alert for the ring"
        else:
            assert customers <= found, f"{rule}: expected {customers}, found {found}"


async def test_lookalikes_are_cleared_not_flagged(client):
    await _load_and_detect(client)
    alerts = await _alerts()
    cleared = {}
    for a in alerts:
        if a.status == "cleared":
            cleared.setdefault(a.rule_id, set()).add(a.customer_id)
            assert a.cleared_reason, "a cleared lookalike must say why"
    for rule, customers in EXPECTED_CLEARED.items():
        assert customers & cleared.get(rule, set()), f"{rule}: lookalike not recorded as cleared"

    flagged_customers = {a.customer_id for a in alerts if a.status == "open"}
    assert not (NEVER_FLAGGED & flagged_customers)
    assert not ({"C9010", "C9200", "C9210"} & flagged_customers), "a legitimate lookalike was flagged"


async def test_ordinary_customers_are_not_flagged(client):
    await _load_and_detect(client)
    noise = [a for a in await _alerts() if a.status == "open" and not (a.customer_id or "").startswith(PLANTED_PREFIX)]
    assert noise == [], [(a.rule_id, a.customer_id, a.factors) for a in noise]


async def test_ato_sequence_scores_high_and_opens_case(client):
    await _load_and_detect(client)
    ato = [a for a in await _alerts() if a.rule_id == "R3-ATO"]
    assert ato and ato[0].base_score >= 70
    factors = " ".join(f["factor"] for f in ato[0].factors)
    assert "new device" in factors and "Beneficiary" in factors and "Large transfer" in factors
    async with async_session() as s:
        assert (await s.execute(select(Case).where(Case.alert_id == ato[0].alert_id))).scalar_one()


async def test_only_medium_and_high_alerts_open_cases(client):
    await _load_and_detect(client)
    async with async_session() as s:
        cases = (await s.execute(select(Case))).scalars().all()
    assert cases and all(c.risk_level in ("Medium", "High") for c in cases)


async def test_detection_is_idempotent(client):
    first = await _load_and_detect(client)
    r = await client.post("/api/detection/run", headers=as_role("investigator"))
    assert first["new_alerts"] > 0 and r.json()["new_alerts"] == 0


async def test_ai_review_runs_in_background_and_logs_masked_prompt(client):
    await _load_and_detect(client)
    async with async_session() as s:
        logs = (await s.execute(select(AiCallLog))).scalars().all()
    assert logs, "background AI review should have logged calls"
    # The prompt must not carry raw PII from the data (e.g. a planted phone number or IP).
    assert all("+9199" not in log.prompt_masked and "10.9.3.99" not in log.prompt_masked for log in logs)

    r = await client.get("/api/ai/log", headers=as_role("analyst"))
    body = r.json()
    assert body["total"] == len(logs) and body["budget_usd"] == 10.0
