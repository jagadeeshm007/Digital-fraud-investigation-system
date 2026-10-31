"""Level 2 edge cases: refused actions, incremental grouping, Level 1 backfill and AI-driven refresh."""
import pytest
from sqlalchemy import delete, select

from app.db import async_session
from app.detection.correlation import consolidate, group_alerts, reason_text
from app.models import Alert, Case, CaseAlert
from tests.conftest import as_role
from tests.test_level2 import _case_for, _seed, who


@pytest.fixture
async def client(fresh_client):
    yield fresh_client


INV = who("investigator", "inv-asha")


async def test_refused_actions_say_why(client):
    await _seed(client)
    ato = await _case_for(client, "C9300", "R3-ATO")
    cid = ato["case_id"]
    assert (await client.patch("/api/cases/nope/risk", json={"risk_level": "Low", "reason": "x"},
                               headers=INV)).status_code == 404
    assert (await client.patch(f"/api/cases/{cid}/risk", json={"risk_level": ato["risk_level"], "reason": "x"},
                               headers=INV)).status_code == 409
    assert (await client.post("/api/cases/nope/notes", json={"body": "x"}, headers=INV)).status_code == 404
    assert (await client.get("/api/cases/nope/report", headers=INV)).status_code == 404
    assert (await client.get("/api/graph/case/nope", headers=INV)).status_code == 404
    assert (await client.post("/api/recommendations/nope/decision", json={"approve": True, "reason": "x"},
                              headers=who("supervisor", "s2"))).status_code == 404

    # split: unknown alert, single-alert case
    assert (await client.post(f"/api/cases/{cid}/split", json={"alert_id": "nope", "reason": "x"},
                              headers=INV)).status_code == 404
    single = next(c for c in (await client.get("/api/cases?page_size=200", headers=INV)).json()["items"]
                  if c["alert_count"] == 1)
    r = await client.post(f"/api/cases/{single['case_id']}/split", json={"alert_id": single["alert_id"], "reason": "x"},
                          headers=INV)
    assert r.status_code == 409

    # open a case: already grouped, unknown, no reason, analyst
    assert (await client.post(f"/api/alerts/{ato['alert_id']}/case", json={"reason": "x"},
                              headers=INV)).status_code == 409
    assert (await client.post("/api/alerts/nope/case", json={"reason": "x"}, headers=INV)).status_code == 404
    assert (await client.post(f"/api/alerts/{ato['alert_id']}/case", json={"reason": " "},
                              headers=INV)).status_code == 400
    assert (await client.post(f"/api/alerts/{ato['alert_id']}/case", json={"reason": "x"},
                              headers=as_role("analyst"))).status_code == 403


async def test_reject_recommendation_and_locked_case(client):
    await _seed(client)
    case = await _case_for(client, "C9300", "R3-ATO")
    url = f"/api/cases/{case['case_id']}/decision"
    await client.patch(url, json={"decision": "recommend_verification", "reason": "Call the customer"}, headers=INV)
    rec = (await client.get("/api/recommendations?status=pending", headers=INV)).json()["items"][0]
    r = await client.post(f"/api/recommendations/{rec['recommendation_id']}/decision",
                          json={"approve": False, "reason": "Already verified at branch"},
                          headers=who("supervisor", "sup-meera"))
    assert r.json()["status"] == "rejected"
    assert (await client.get("/api/recommendations?status=", headers=INV)).json()["items"]

    await client.patch(url, json={"decision": "false_positive", "reason": "Known purchase"}, headers=INV)
    transfer = next(a for a in case["alerts"] if a["rule_id"] == "R1-SUSPICIOUS-TRANSFER")
    assert (await client.post(f"/api/cases/{case['case_id']}/split", json={"alert_id": transfer["alert_id"],
                              "reason": "x"}, headers=INV)).status_code == 409
    assert (await client.patch(f"/api/cases/{case['case_id']}/risk", json={"risk_level": "Low", "reason": "x"},
                               headers=INV)).status_code == 409


async def test_splitting_the_primary_promotes_the_next_alert(client):
    await _seed(client)
    case = await _case_for(client, "C9300", "R3-ATO")
    r = await client.post(f"/api/cases/{case['case_id']}/split",
                          json={"alert_id": case["alert_id"], "reason": "Separate the login pattern"}, headers=INV)
    assert r.status_code == 200
    after = (await client.get(f"/api/cases/{case['case_id']}", headers=INV)).json()
    assert after["alert_id"] != case["alert_id"]
    assert after["alert_id"] in {a["alert_id"] for a in after["alerts"]}


async def test_new_alert_joins_the_open_case_it_connects_to(client):
    await _seed(client)
    case = await _case_for(client, "C9600", "R7-CHANGED-ACCOUNT-LOAN")
    joined = next(a for a in case["alerts"] if a["alert_id"] != case["alert_id"])
    async with async_session() as s:
        # simulate an alert detected after the case was built
        await s.execute(delete(CaseAlert).where(CaseAlert.alert_id == joined["alert_id"]))
        await s.commit()
        out = await consolidate(s)
        await s.commit()
        row = (await s.execute(select(CaseAlert).where(CaseAlert.alert_id == joined["alert_id"]))).scalar_one()
    assert out["new_cases"] == 0 and out["linked_alerts"] == 1
    assert row.case_id == case["case_id"] and row.links


async def test_level1_cases_get_their_primary_row(client):
    await _seed(client)
    async with async_session() as s:
        await s.execute(delete(CaseAlert))
        await s.commit()
        await consolidate(s)
        await s.commit()
        cases = (await s.execute(select(Case))).scalars().all()
        primaries = {(r.case_id, r.alert_id) for r in (await s.execute(select(CaseAlert))).scalars().all()}
    assert all((c.case_id, c.alert_id) in primaries for c in cases)


async def test_ai_review_refreshes_case_priority_but_not_links(client):
    await _seed(client)
    case = await _case_for(client, "C9300", "R3-ATO")
    before = {(a["alert_id"], a["link_reason"]) for a in case["alerts"]}
    async with async_session() as s:
        await s.execute(Case.__table__.update().where(Case.case_id == case["case_id"]).values(priority_score=0))
        await s.execute(Alert.__table__.update().where(Alert.alert_id == case["alert_id"]).values(ai_status="pending"))
        await s.commit()
    assert (await client.post(f"/api/ai/review/{case['alert_id']}", headers=INV)).status_code == 200
    after = (await client.get(f"/api/cases/{case['case_id']}", headers=INV)).json()
    assert after["priority_score"] > 0
    assert {(a["alert_id"], a["link_reason"]) for a in after["alerts"]} == before


def test_grouping_ignores_hub_identifiers_and_explains_links():
    idents = {f"a{i}": {("account", "MERCH001")} for i in range(25)}  # a merchant on 25 alerts is a hub
    idents["x"] = {("device", "D1")}
    idents["y"] = {("device", "D1")}
    groups = {tuple(m) for m, _ in group_alerts(idents)}
    assert ("x", "y") in groups and len(groups) == 26
    assert reason_text([]) == "No shared identifier"
    many = [{"type": "device", "value": f"D{i}", "with_rule": "R2", "with_alert": "abcdefgh123"} for i in range(5)]
    assert reason_text(many).endswith("(+2 more links)")


async def test_side_panel_links_for_a_case_node(client):
    """Clicking a node in the case graph lists the records that share it (/api/links), masked."""
    await _seed(client)
    links = (await client.get("/api/links/L9600", headers=as_role("analyst"))).json()
    shared = {(link["shared_type"], link["shared_value"]) for link in links["links"]}
    assert ("device", "DEV-RING2") in shared
    assert not any(v.startswith("+91") for _, v in shared)  # phones only as masked tokens
    ring = (await client.get("/api/graph/entity/DEV-RING2?depth=1", headers=as_role("analyst"))).json()
    assert {"L9600", "L9610", "L9620"} <= {n["id"] for n in ring["nodes"]}
    assert (await client.get("/api/graph/customer/C9600", headers=as_role("analyst"))).status_code == 200
    assert (await client.get("/api/graph/entity/nope", headers=as_role("analyst"))).status_code == 404
