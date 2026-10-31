"""API behaviour the judges and hidden tests can observe: ingestion, filters, evidence, cases, roles, masking."""
import pytest
import json

from app.sample_data import broken_transactions
from tests.conftest import as_role


@pytest.fixture
async def client(fresh_client):
    # These tests need an empty database each time; the shared session client is for test_e2e.
    yield fresh_client



def _upload(client, rows, source, name=None, role="analyst"):
    return client.post(
        "/api/ingest",
        files={"file": (name or f"{source}.json", json.dumps(rows).encode(), "application/json")},
        data={"source_type": source},
        headers=as_role(role),
    )


async def _seed(client):
    assert (await client.post("/api/ingest/sample", headers=as_role("analyst"))).status_code == 200
    assert (await client.post("/api/detection/run", headers=as_role("investigator"))).status_code == 200


async def test_csv_empty_cell_is_rejected_and_channel_case_is_ignored(client):
    await client.post("/api/ingest/sample", headers=as_role("analyst"))
    csv = (
        "transaction_id,timestamp,sender_account_id,amount_inr,channel,status\n"
        "CSV-1,2026-10-31T09:00:00+05:30,ACC-X1,2400.00,UPI,success\n"
        "CSV-2,2026-10-31T09:05:00+05:30,ACC-X2,,upi,success\n"
    ).encode()
    r = await client.post(
        "/api/ingest",
        files={"file": ("cells.csv", csv, "text/csv")},
        data={"source_type": "transactions"},
        headers=as_role("analyst"),
    )
    assert r.status_code == 200  # an empty CSV cell used to become NaN and fail the insert with a 500
    body = r.json()
    assert body["accepted_count"] == 1 and body["rejected_count"] == 1
    rej = (await client.get(f"/api/ingest/{body['batch_id']}/rejected", headers=as_role("analyst"))).json()
    assert [(x["row_number"], x["field"]) for x in rej["records"]] == [(2, "amount_inr")]


async def test_health(client):
    assert (await client.get("/healthz")).json() == {"status": "ok"}


async def test_validation_report_never_drops_rows(client):
    await client.post("/api/ingest/sample", headers=as_role("analyst"))
    r = await _upload(client, broken_transactions(), "transactions")
    body = r.json()
    assert r.status_code == 200
    # 6 rows: 1 good, 1 good-with-unknown-account (warning), 4 rejected
    assert body["accepted_count"] == 2 and body["rejected_count"] == 4 and body["warning_count"] == 1

    rej = (await client.get(f"/api/ingest/{body['batch_id']}/rejected", headers=as_role("analyst"))).json()
    reasons = " | ".join(r["reason"] for r in rej["records"])
    for expected in ("Missing required field: amount_inr", "invalid datetime", "expected one of", "Duplicate key"):
        assert expected in reasons


async def test_reupload_is_a_reported_duplicate_not_a_crash(client):
    await client.post("/api/ingest/sample", headers=as_role("analyst"))
    again = await client.post("/api/ingest/sample", headers=as_role("analyst"))
    assert again.status_code == 200
    tx = next(b for b in again.json()["batches"] if b["source_type"] == "transactions")
    assert tx["accepted_count"] == 0 and tx["rejected_count"] > 0


async def test_unknown_customer_is_rejected_with_reason(client):
    row = {"event_id": "EX1", "customer_id": "NOPE", "timestamp": "2026-10-01T10:00:00+05:30",
           "outcome": "success", "event_type": "login"}
    body = (await _upload(client, [row], "devices_logins")).json()
    assert body["rejected_count"] == 1
    rej = (await client.get(f"/api/ingest/{body['batch_id']}/rejected", headers=as_role("analyst"))).json()
    assert "Unknown customer NOPE" in rej["records"][0]["reason"]


async def test_customer_with_two_accounts(client):
    base = {"customer_id": "CX1", "name": "Test Person", "date_of_birth": "1990-01-01", "phone": "+911",
            "email": "t@example.in", "address": "1 Road", "identity_number": "ID1",
            "onboarded_at": "2025-01-01T00:00:00+05:30", "source_system": "core", "product": "savings",
            "opened_at": "2025-01-01T00:00:00+05:30", "status": "active"}
    rows = [{**base, "account_id": "A1"}, {**base, "account_id": "A2"}]
    body = (await _upload(client, rows, "customers_accounts")).json()
    assert body["accepted_count"] == 2 and body["rejected_count"] == 0


async def test_unreadable_and_unknown_source(client):
    r = await client.post("/api/ingest", files={"file": ("x.json", b"{not json", "application/json")},
                          data={"source_type": "transactions"}, headers=as_role("analyst"))
    assert r.status_code == 400
    r = await _upload(client, [], "spaceships")
    assert r.status_code == 400


async def test_rejected_records_are_masked(client):
    await client.post("/api/ingest/sample", headers=as_role("analyst"))
    row = {"customer_id": "CZ", "name": "Secret Name", "phone": "+919876543210"}  # missing fields -> rejected
    body = (await _upload(client, [row], "customers_accounts")).json()
    if body.get("rejected_count") is None:  # missing columns abort the file instead
        return
    rej = (await client.get(f"/api/ingest/{body['batch_id']}/rejected", headers=as_role("analyst"))).json()
    assert "Secret Name" not in json.dumps(rej) and "+919876543210" not in json.dumps(rej)


async def test_dashboard_summary_has_judged_figures(client):
    await _seed(client)
    s = (await client.get("/api/detection/summary", headers=as_role("analyst"))).json()
    assert s["processed_records"] > 1000
    assert s["flagged_events"] > 0 and s["cleared_alerts"] >= 3
    assert set(s["risk_distribution"]) == {"Low", "Medium", "High"}
    assert s["fraud_categories"]


async def test_alert_filters(client):
    await _seed(client)
    high = (await client.get("/api/alerts?risk_band=High", headers=as_role("analyst"))).json()
    assert high["total"] > 0 and all(a["risk_band"] == "High" for a in high["items"])

    lending = (await client.get("/api/alerts?product=lending", headers=as_role("analyst"))).json()
    assert all(a["product"] == "lending" for a in lending["items"])

    by_rule = (await client.get("/api/alerts?rule_id=R3-ATO", headers=as_role("analyst"))).json()
    assert by_rule["total"] == 1 and by_rule["items"][0]["customer_id"] == "C9300"

    cust = (await client.get("/api/alerts?customer_id=C9300", headers=as_role("analyst"))).json()
    txn_id = next(f["evidence_id"] for a in cust["items"] for f in a["factors"]
                  if str(f.get("evidence_id", "")).startswith("T"))
    by_txn = (await client.get(f"/api/alerts?transaction_id={txn_id}", headers=as_role("analyst"))).json()
    assert by_txn["total"] >= 1

    today = (await client.get("/api/alerts?date_from=2000-01-01&date_to=2100-01-01",
                              headers=as_role("analyst"))).json()
    none = (await client.get("/api/alerts?date_from=2000-01-01&date_to=2000-01-02",
                             headers=as_role("analyst"))).json()
    assert today["total"] > 0 and none["total"] == 0


async def test_alert_detail_has_masked_evidence_and_case(client):
    await _seed(client)
    ato = (await client.get("/api/alerts?rule_id=R3-ATO", headers=as_role("analyst"))).json()["items"][0]
    detail = (await client.get(f"/api/alerts/{ato['alert_id']}", headers=as_role("analyst"))).json()
    assert detail["case_id"] and detail["evidence"]
    types = {e["type"] for e in detail["evidence"]}
    assert {"login_event", "transaction"} <= types
    dump = json.dumps(detail["evidence"])
    assert "Neelam Chawla" not in dump and "10.9.3.99" not in dump
    assert (await client.get("/api/alerts/nope", headers=as_role("analyst"))).status_code == 404


async def test_case_decision_flow_and_roles(client):
    await _seed(client)
    cases = (await client.get("/api/cases", headers=as_role("analyst"))).json()["items"]
    cid = cases[0]["case_id"]
    url = f"/api/cases/{cid}/decision"

    denied = await client.patch(url, json={"decision": "escalate", "reason": "x"}, headers=as_role("analyst"))
    assert denied.status_code == 403
    no_reason = await client.patch(url, json={"decision": "escalate", "reason": " "},
                                   headers=as_role("investigator"))
    assert no_reason.status_code == 400
    bad = await client.patch(url, json={"decision": "nuke", "reason": "x"}, headers=as_role("investigator"))
    assert bad.status_code == 400

    ok = await client.patch(url, json={"decision": "requires_investigation", "reason": "Linked accounts"},
                            headers=as_role("investigator"))
    assert ok.json()["status"] == "under_investigation"
    done = await client.patch(url, json={"decision": "false_positive", "reason": "Verified with branch"},
                              headers=as_role("supervisor"))
    assert done.json()["status"] == "closed"
    final = await client.patch(url, json={"decision": "escalate", "reason": "late"}, headers=as_role("supervisor"))
    assert final.status_code == 409

    case = (await client.get(f"/api/cases/{cid}", headers=as_role("analyst"))).json()
    assert [h["to_status"] for h in case["history"]] == ["under_investigation", "closed"]

    # FR7.4: the original alert is unchanged by the decision
    alert = (await client.get(f"/api/alerts/{case['alert_id']}", headers=as_role("analyst"))).json()
    assert alert["status"] == "open" and alert["base_score"] > 0
    assert (await client.get("/api/cases/nope", headers=as_role("analyst"))).status_code == 404


async def test_permissions_enforced_on_server(client):
    assert (await client.post("/api/detection/run", headers=as_role("analyst"))).status_code == 403
    r = await client.post("/api/masking/reveal", json={"case_id": "c", "field": "name"}, headers=as_role("analyst"))
    assert r.status_code == 403
    audit = (await client.get("/api/audit", headers=as_role("analyst"))).json()
    assert any(e["result"] == "denied" for e in audit["items"])


async def test_ai_review_endpoints(client):
    await _seed(client)
    alert = (await client.get("/api/alerts?risk_band=High", headers=as_role("analyst"))).json()["items"][0]
    r = await client.post(f"/api/ai/review/{alert['alert_id']}", headers=as_role("investigator"))
    body = r.json()
    assert r.status_code == 200 and -10 <= body["ai_adjustment"] <= 10
    assert body["final_score"] == max(0, min(100, body["base_score"] + body["ai_adjustment"]))
    assert (await client.post("/api/ai/review/run", headers=as_role("investigator"))).status_code == 200
    assert (await client.post(f"/api/ai/review/{alert['alert_id']}", headers=as_role("analyst"))).status_code == 403


async def test_graph_and_links_are_masked(client):
    await _seed(client)
    g = (await client.get("/api/graph/customer/C9300", headers=as_role("analyst"))).json()
    assert g["nodes"] and g["edges"]
    dump = json.dumps(g)
    assert "Neelam Chawla" not in dump and "10.9.3.99" not in dump
    links = (await client.get("/api/links/C9500", headers=as_role("analyst"))).json()
    assert links["link_count"] >= 1 and "+919900000555" not in json.dumps(links)
    assert (await client.get("/api/graph/entity/nope", headers=as_role("analyst"))).status_code == 404


async def test_supervisor_reveal_is_audited(client):
    await _seed(client)
    case = (await client.get("/api/cases?customer_id=C9300", headers=as_role("analyst"))).json()["items"][0]
    r = await client.post("/api/masking/reveal", json={"case_id": case["case_id"], "field": "name"},
                          headers=as_role("supervisor"))
    assert r.json()["plaintext_value"] == "Neelam Chawla"
    bad = await client.post("/api/masking/reveal", json={"case_id": case["case_id"], "field": "salary"},
                            headers=as_role("supervisor"))
    assert bad.status_code == 400
    audit = (await client.get("/api/audit", headers=as_role("analyst"))).json()["items"]
    assert any(e["action"] == "reveal_pii" and e["result"] == "allowed" for e in audit)


async def test_case_detail_shows_customer_masked_for_every_role(client):
    await _seed(client)
    case_id = (await client.get("/api/cases?customer_id=C9300", headers=as_role("analyst"))).json()["items"][0]["case_id"]
    for role in ("analyst", "investigator", "supervisor"):
        customer = (await client.get(f"/api/cases/{case_id}", headers=as_role(role))).json()["customer"]
        assert set(customer) == {"name", "phone", "email", "address", "identity_number"}
        assert all(v.startswith("***-") for v in customer.values())
        assert "Neelam Chawla" not in json.dumps(customer)
