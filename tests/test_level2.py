"""Level 2 acceptance tests: correlation, consolidation, split, risk override, maker-checker,
prioritisation and the case report (level2.md, "Acceptance tests to add")."""
import json

import pytest
from sqlalchemy import select

from app import mcp_server as m
from app.db import async_session
from app.models import Account, Alert, AuditEntry, CaseAlert, CaseNote, Transaction
from app.sample_data import EXPECTED_INVESTIGATIONS
from tests.conftest import as_role
from tests.test_mcp import FakeCtx


@pytest.fixture
async def client(fresh_client):
    yield fresh_client


def who(role: str, user: str) -> dict:
    return {"X-Role": role, "X-User": user}


async def _seed(client) -> None:
    assert (await client.post("/api/ingest/sample", headers=as_role("analyst"))).status_code == 200
    assert (await client.post("/api/detection/run", headers=as_role("investigator"))).status_code == 200


async def _case_for(client, customer_id: str, rule_id: str) -> dict:
    """The workspace of the case holding the customer's alert for this rule."""
    async with async_session() as s:
        alert = (await s.execute(select(Alert).where(
            Alert.customer_id == customer_id, Alert.rule_id == rule_id))).scalars().first()
        assert alert, f"no {rule_id} alert for {customer_id}"
        case_id = (await s.execute(select(CaseAlert.case_id).where(
            CaseAlert.alert_id == alert.alert_id))).scalar_one()
    r = await client.get(f"/api/cases/{case_id}", headers=as_role("analyst"))
    assert r.status_code == 200, r.text
    return r.json()


async def test_cross_system_scenario_is_one_investigation(client):
    await _seed(client)
    expected = EXPECTED_INVESTIGATIONS["cross_system"]
    case = await _case_for(client, "C9600", "R7-CHANGED-ACCOUNT-LOAN")

    rules = {a["rule_id"] for a in case["alerts"]}
    assert expected["rules"] <= rules, rules
    assert expected["customers"] <= {a["customer_id"] for a in case["alerts"]}
    products = {a["product"] for a in case["alerts"]}
    assert {"lending", "banking"} <= products  # the loan and the transfer, across systems

    # Every grouped alert names the identifier that joined it
    for a in case["alerts"]:
        if a["alert_id"] != case["alert_id"]:
            assert a["links"], a
            assert all(link["type"] and link["value"] for link in a["links"])
            assert a["link_reason"].startswith("shares ")

    # The case graph: every edge carries a matching identifier read from a record, never the AI
    g = (await client.get(f"/api/graph/case/{case['case_id']}", headers=as_role("analyst"))).json()
    assert g["nodes"] and g["edges"]
    for e in g["edges"]:
        assert e["origin"] == "identifier" and e["label"] == f"{e['match']['type']} {e['match']['value']}"
        assert e["evidence"]
    assert any(n["id"] == "device:DEV-RING2" and n["data"]["shared"] for n in g["nodes"])


async def test_ato_sequence_is_one_case_with_grouping_reason(client):
    await _seed(client)
    case = await _case_for(client, "C9300", "R3-ATO")
    rules = {a["rule_id"] for a in case["alerts"]}
    assert EXPECTED_INVESTIGATIONS["ato"]["rules"] <= rules
    transfer = next(a for a in case["alerts"] if a["rule_id"] == "R1-SUSPICIOUS-TRANSFER")
    assert "shares" in transfer["link_reason"]
    # failed logins, the new-device login and the transfer all sit on one timeline
    kinds = {(t["type"], t["summary"].split()[0]) for t in case["timeline"] if t["kind"] == "evidence"}
    assert ("login_event", "login") in kinds and any(k[0] == "transaction" for k in kinds)


async def test_split_moves_alert_and_keeps_everything(client):
    await _seed(client)
    case = await _case_for(client, "C9300", "R3-ATO")
    transfer = next(a for a in case["alerts"] if a["rule_id"] == "R1-SUSPICIOUS-TRANSFER")
    url = f"/api/cases/{case['case_id']}/split"
    body = {"alert_id": transfer["alert_id"], "reason": "Payment was a known property purchase"}

    assert (await client.post(url, json=body, headers=as_role("analyst"))).status_code == 403
    assert (await client.post(url, json={**body, "reason": " "}, headers=as_role("investigator"))).status_code == 400
    r = await client.post(url, json=body, headers=who("investigator", "inv-asha"))
    assert r.status_code == 200, r.text
    new_id = r.json()["new_case"]["case_id"]

    original = (await client.get(f"/api/cases/{case['case_id']}", headers=as_role("analyst"))).json()
    new = (await client.get(f"/api/cases/{new_id}", headers=as_role("analyst"))).json()
    assert transfer["alert_id"] not in {a["alert_id"] for a in original["alerts"]}
    assert [a["alert_id"] for a in new["alerts"]] == [transfer["alert_id"]]
    assert new["split_from"] == case["case_id"]
    assert original["evidence"] and new["evidence"]
    assert any(h["decision"] == "split_out" for h in original["history"])

    async with async_session() as s:
        assert await s.get(Alert, transfer["alert_id"])  # never deleted
        audit = (await s.execute(select(AuditEntry).where(AuditEntry.action == "split_case"))).scalars().all()
    assert audit and audit[0].user_id == "inv-asha"

    # a later detection run does not regroup the split alert
    await client.post("/api/detection/run", headers=as_role("investigator"))
    again = (await client.get(f"/api/cases/{new_id}", headers=as_role("analyst"))).json()
    assert [a["alert_id"] for a in again["alerts"]] == [transfer["alert_id"]]


async def test_risk_override_keeps_original_and_reason(client):
    await _seed(client)
    case = await _case_for(client, "C9300", "R3-ATO")
    url = f"/api/cases/{case['case_id']}/risk"
    assert (await client.patch(url, json={"risk_level": "Low", "reason": "x"},
                               headers=as_role("analyst"))).status_code == 403
    assert (await client.patch(url, json={"risk_level": "Extreme", "reason": "x"},
                               headers=as_role("investigator"))).status_code == 400

    r = await client.patch(url, json={"risk_level": "Medium", "reason": "Customer confirmed the new device"},
                           headers=who("investigator", "inv-asha"))
    assert r.status_code == 200
    await client.patch(url, json={"risk_level": "Low", "reason": "Branch verified identity"},
                       headers=who("supervisor", "sup-ravi"))

    report = (await client.get(f"/api/cases/{case['case_id']}/report", headers=as_role("analyst")))
    assert report.status_code == 200
    assert "attachment" in report.headers["content-disposition"]
    risk = report.json()["risk_assessment"]
    assert risk["risk_original"] == case["risk_level"] == "High"
    assert risk["risk_level"] == "Low" and risk["risk_reason"] == "Branch verified identity"
    assert risk["risk_changed_by"] == "sup-ravi"
    overrides = [h for h in report.json()["history"] if h["decision"] == "risk_override"]
    assert [h["reason"].split(":")[0] for h in overrides] == ["High -> Medium", "Medium -> Low"]


async def _money_snapshot() -> list:
    async with async_session() as s:
        accts = [(a.account_id, a.status) for a in (await s.execute(select(Account))).scalars().all()]
        txns = [(t.transaction_id, t.status, str(t.amount_inr))
                for t in (await s.execute(select(Transaction))).scalars().all()]
    return sorted(accts) + sorted(txns)


async def test_recommended_hold_needs_a_different_supervisor(client):
    await _seed(client)
    case = await _case_for(client, "C9300", "R3-ATO")
    before = await _money_snapshot()

    r = await client.patch(f"/api/cases/{case['case_id']}/decision",
                           json={"decision": "recommend_hold", "reason": "Freeze outgoing transfers"},
                           headers=who("supervisor", "sup-ravi"))
    assert r.status_code == 200
    rec = (await client.get(f"/api/cases/{case['case_id']}", headers=as_role("analyst"))).json()["recommendations"][0]
    assert rec["status"] == "pending" and rec["kind"] == "hold" and rec["maker_user"] == "sup-ravi"

    url = f"/api/recommendations/{rec['recommendation_id']}/decision"
    ok = {"approve": True, "reason": "Evidence supports a hold"}
    assert (await client.post(url, json=ok, headers=who("investigator", "inv-asha"))).status_code == 403
    assert (await client.post(url, json=ok, headers=who("supervisor", "sup-ravi"))).status_code == 403  # maker
    pending = (await client.get("/api/recommendations", headers=as_role("analyst"))).json()["items"]
    assert [p["recommendation_id"] for p in pending] == [rec["recommendation_id"]]

    r = await client.post(url, json=ok, headers=who("supervisor", "sup-meera"))
    assert r.status_code == 200 and r.json()["status"] == "approved" and r.json()["decided_by"] == "sup-meera"
    assert (await client.post(url, json=ok, headers=who("supervisor", "sup-meera"))).status_code == 409
    assert await _money_snapshot() == before  # approval records the authorisation only


async def test_priority_ranks_ato_above_isolated_failed_login(client):
    await _seed(client)
    ato = await _case_for(client, "C9300", "R3-ATO")

    async with async_session() as s:
        weak = (await s.execute(select(Alert).where(
            Alert.customer_id == "C9320", Alert.rule_id == "R3-LOGIN-FAILURES"))).scalar_one()
        assert weak.risk_band == "Low"
        assert not (await s.execute(select(CaseAlert).where(CaseAlert.alert_id == weak.alert_id))).first()
    r = await client.post(f"/api/alerts/{weak.alert_id}/case", json={"reason": "Check for follow-up"},
                          headers=who("investigator", "inv-asha"))
    assert r.status_code == 200, r.text
    weak_case = r.json()

    assert weak_case["needs_review"] is True and weak_case["priority_score"] <= 40
    assert ato["priority_score"] > weak_case["priority_score"]
    assert ato["needs_review"] is False

    queue = (await client.get("/api/cases?page_size=200", headers=as_role("analyst"))).json()["items"]
    scores = [c["priority_score"] for c in queue]
    assert scores == sorted(scores, reverse=True)
    ids = [c["case_id"] for c in queue]
    assert ids.index(ato["case_id"]) < ids.index(weak_case["case_id"])
    flagged = (await client.get("/api/cases?needs_review=true", headers=as_role("analyst"))).json()["items"]
    assert weak_case["case_id"] in {c["case_id"] for c in flagged}
    assert all(c["needs_review"] for c in flagged)


async def test_workspace_actions_and_notes(client):
    await _seed(client)
    case = await _case_for(client, "C9600", "R7-CHANGED-ACCOUNT-LOAN")
    url = f"/api/cases/{case['case_id']}/decision"
    inv = who("investigator", "inv-asha")
    for decision, status in [("requires_investigation", "under_investigation"),
                             ("request_info", "info_requested"),
                             ("recommend_verification", "info_requested"),
                             ("escalate", "escalated"),
                             ("conclude", "concluded")]:
        r = await client.patch(url, json={"decision": decision, "reason": f"{decision} reason"}, headers=inv)
        assert r.status_code == 200, (decision, r.text)
        assert r.json()["status"] == status
    assert r.json()["conclusion"] == "conclude reason"
    assert (await client.patch(url, json={"decision": "false_positive", "reason": "late"},
                               headers=inv)).status_code == 409

    notes = f"/api/cases/{case['case_id']}/notes"
    assert (await client.post(notes, json={"body": "hi"}, headers=as_role("analyst"))).status_code == 403
    assert (await client.post(notes, json={"body": ""}, headers=inv)).status_code == 400
    r = await client.post(notes, json={"body": "Called the branch, ring confirmed"}, headers=inv)
    assert r.status_code == 200 and r.json()["author_user"] == "inv-asha"
    ws = (await client.get(f"/api/cases/{case['case_id']}", headers=as_role("analyst"))).json()
    assert [n["body"] for n in ws["notes"]] == ["Called the branch, ring confirmed"]
    assert {"timeline", "entities", "indicators", "evidence", "risk", "recommendations"} <= set(ws)
    assert all(h["user_id"] == "inv-asha" for h in ws["history"])


async def test_report_has_every_section_and_no_raw_pii(client):
    await _seed(client)
    case = await _case_for(client, "C9300", "R3-ATO")
    await client.post(f"/api/cases/{case['case_id']}/notes", json={"body": "Reviewed"},
                      headers=who("investigator", "inv-asha"))
    report = (await client.get(f"/api/cases/{case['case_id']}/report", headers=as_role("analyst"))).json()
    for section in ("case", "alerts", "indicators", "evidence", "ai_reviews", "history", "notes",
                    "recommendations", "audit", "risk_assessment", "timeline"):
        assert section in report, section
    assert report["alerts"][0]["factors"] and report["evidence"]
    dump = json.dumps(report)
    for raw in ("Neelam Chawla", "+919900000301", "10.9.3.99", "neelam", "19 Park Avenue"):
        assert raw not in dump, raw


async def test_mcp_level2_tools(client):
    await _seed(client)
    case = await _case_for(client, "C9300", "R3-ATO")
    ctx = FakeCtx(role="analyst")
    report = await m.get_case_report(ctx, case["case_id"])
    assert report["case"]["case_id"] == case["case_id"] and "Neelam Chawla" not in json.dumps(report)
    assert (await m.get_case_graph(ctx, case["case_id"]))["edges"]
    assert (await m.get_case_report(ctx, "missing"))["status"] == 404

    # writes: role first, then consent; nothing happens without "accepted"
    assert (await m.add_case_note(FakeCtx(role="analyst"), case["case_id"], "x"))["status"] == 403
    assert (await m.add_case_note(FakeCtx(elicitation=False), case["case_id"], "x"))["performed"] is False
    out = await m.add_case_note(FakeCtx(), case["case_id"], "Looked at it via MCP")
    assert out["performed"] is True
    async with async_session() as s:
        assert len((await s.execute(select(CaseNote))).scalars().all()) == 1

    out = await m.recommend_action(FakeCtx(), case["case_id"], "hold", "Pause payouts")
    assert out["performed"] and out["status"] == "pending supervisor approval"
    assert (await m.recommend_action(FakeCtx(), case["case_id"], "freeze", "x"))["status"] == 400

    transfer = next(a for a in case["alerts"] if a["rule_id"] == "R1-SUSPICIOUS-TRANSFER")
    assert (await m.split_case_alert(FakeCtx(answer="decline"), case["case_id"], transfer["alert_id"],
                                     "x"))["performed"] is False
    out = await m.split_case_alert(FakeCtx(), case["case_id"], transfer["alert_id"], "Unrelated payment")
    assert out["performed"] and out["new_case"]["split_from"] == case["case_id"]

    tools = {t.name for t in await m.mcp.list_tools()}
    assert {"get_case_report", "get_case_graph", "add_case_note", "split_case_alert", "recommend_action"} <= tools
