"""
E2E backend tests.
Runs as one ordered session: ingest → detect → review → decide → query.
The session-scoped DB accumulates state intentionally — fraud detection
requires prior history to generate alerts.
"""
import pytest
from tests.fixtures import (
    BAD_TRANSACTIONS_CSV,
    CLAIMS_CSV,
    CUSTOMERS_CSV,
    LOANS_CSV,
    LOGINS_CSV,
    TRANSACTIONS_CSV,
)

# ─── state shared across tests ────────────────────────────────────────────────
_state: dict = {"alert_id": None, "case_id": None}


async def _upload(client, filename, csv_bytes, source_type, role="analyst"):
    return await client.post(
        "/api/ingest",
        files={"file": (filename, csv_bytes, "text/csv")},
        data={"source_type": source_type},
        headers={"X-Role": role},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. INGEST
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ingest_customers(client):
    r = await _upload(client, "customers.csv", CUSTOMERS_CSV, "customers_accounts")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted_count"] == 2
    assert body["rejected_count"] == 0


@pytest.mark.asyncio
async def test_ingest_transactions(client):
    r = await _upload(client, "transactions.csv", TRANSACTIONS_CSV, "transactions")
    assert r.status_code == 200, r.text
    assert r.json()["accepted_count"] == 4


@pytest.mark.asyncio
async def test_ingest_logins(client):
    r = await _upload(client, "logins.csv", LOGINS_CSV, "devices_logins")
    assert r.status_code == 200, r.text
    assert r.json()["accepted_count"] == 5


@pytest.mark.asyncio
async def test_ingest_loans(client):
    r = await _upload(client, "loans.csv", LOANS_CSV, "loan_applications")
    assert r.status_code == 200, r.text
    assert r.json()["accepted_count"] == 2


@pytest.mark.asyncio
async def test_ingest_claims(client):
    r = await _upload(client, "claims.csv", CLAIMS_CSV, "insurance_claims")
    assert r.status_code == 200, r.text
    assert r.json()["accepted_count"] == 2


@pytest.mark.asyncio
async def test_ingest_bad_csv_rejected(client):
    r = await _upload(client, "bad.csv", BAD_TRANSACTIONS_CSV, "transactions")
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        assert r.json()["rejected_count"] >= 1


@pytest.mark.asyncio
async def test_ingest_unknown_source_type(client):
    r = await _upload(client, "x.csv", CUSTOMERS_CSV, "unknown_source")
    assert r.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_detection_analyst_forbidden(client):
    r = await client.post("/api/detection/run", headers={"X-Role": "analyst"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_detection_run(client):
    r = await client.post("/api/detection/run", headers={"X-Role": "investigator"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["new_alerts"] >= 1, "Expected at least one fraud hit from test data"
    assert "new_cases" in body
    assert "total_hits" in body


@pytest.mark.asyncio
async def test_detection_idempotent(client):
    r1 = await client.post("/api/detection/run", headers={"X-Role": "investigator"})
    r2 = await client.post("/api/detection/run", headers={"X-Role": "investigator"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["new_alerts"] == 0, "Detection is not idempotent!"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ALERTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_alerts(client):
    r = await client.get("/api/alerts", headers={"X-Role": "analyst"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    _state["alert_id"] = body["items"][0]["alert_id"]


@pytest.mark.asyncio
async def test_list_alerts_filter_risk_band(client):
    r = await client.get("/api/alerts?risk_band=High", headers={"X-Role": "analyst"})
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["risk_band"] == "High"


@pytest.mark.asyncio
async def test_list_alerts_filter_customer(client):
    r = await client.get("/api/alerts?customer_id=C001", headers={"X-Role": "analyst"})
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["customer_id"] == "C001"


@pytest.mark.asyncio
async def test_get_alert_detail(client):
    alert_id = _state["alert_id"]
    assert alert_id, "No alert from previous test"
    r = await client.get(f"/api/alerts/{alert_id}", headers={"X-Role": "analyst"})
    assert r.status_code == 200
    body = r.json()
    assert body["alert_id"] == alert_id
    assert "factors" in body
    assert "evidence" in body


@pytest.mark.asyncio
async def test_get_alert_not_found(client):
    r = await client.get("/api/alerts/nonexistent-id", headers={"X-Role": "analyst"})
    assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CASES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_cases(client):
    r = await client.get("/api/cases", headers={"X-Role": "analyst"})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["items"], list)
    if body["items"]:
        _state["case_id"] = body["items"][0]["case_id"]


@pytest.mark.asyncio
async def test_get_case_detail(client):
    case_id = _state.get("case_id")
    if not case_id:
        pytest.skip("No case created — no Medium/High alerts")
    r = await client.get(f"/api/cases/{case_id}", headers={"X-Role": "analyst"})
    assert r.status_code == 200
    body = r.json()
    assert body["case_id"] == case_id
    assert "history" in body


@pytest.mark.asyncio
async def test_case_decision_analyst_forbidden(client):
    case_id = _state.get("case_id")
    if not case_id:
        pytest.skip("No case")
    r = await client.patch(
        f"/api/cases/{case_id}/decision",
        json={"decision": "requires_investigation", "reason": "Suspicious pattern"},
        headers={"X-Role": "analyst"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_case_decision_investigator(client):
    case_id = _state.get("case_id")
    if not case_id:
        pytest.skip("No case")
    r = await client.patch(
        f"/api/cases/{case_id}/decision",
        json={"decision": "requires_investigation", "reason": "Large transfer to unknown payee"},
        headers={"X-Role": "investigator"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "under_investigation"


@pytest.mark.asyncio
async def test_case_decision_invalid(client):
    case_id = _state.get("case_id")
    if not case_id:
        pytest.skip("No case")
    r = await client.patch(
        f"/api/cases/{case_id}/decision",
        json={"decision": "approve_loan", "reason": "nope"},
        headers={"X-Role": "investigator"},
    )
    assert r.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# 5. DETECTION SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_detection_summary(client):
    r = await client.get("/api/detection/summary", headers={"X-Role": "analyst"})
    assert r.status_code == 200
    body = r.json()
    assert "processed_records" in body
    assert body["processed_records"] > 0
    assert "risk_distribution" in body
    assert "fraud_categories" in body


# ═══════════════════════════════════════════════════════════════════════════════
# 6. AI REVIEW  (FAKE_LLM=1 — no real Groq calls)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ai_review_one(client):
    alert_id = _state.get("alert_id")
    assert alert_id
    r = await client.post(f"/api/ai/review/{alert_id}", headers={"X-Role": "investigator"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["ai_available"], bool)
    assert body["recommended_decision"] in ("investigate", "clear", "escalate", "false_positive")
    assert isinstance(body["ai_adjustment"], int)


@pytest.mark.asyncio
async def test_ai_review_all_pending(client):
    r = await client.post("/api/ai/review/run?limit=5", headers={"X-Role": "investigator"})
    assert r.status_code == 200
    assert "reviewed" in r.json()


@pytest.mark.asyncio
async def test_ai_review_forbidden_analyst(client):
    alert_id = _state.get("alert_id")
    r = await client.post(f"/api/ai/review/{alert_id}", headers={"X-Role": "analyst"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_ai_review_not_found(client):
    r = await client.post("/api/ai/review/no-such-alert", headers={"X-Role": "investigator"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_ai_log(client):
    r = await client.get("/api/ai/log", headers={"X-Role": "analyst"})
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "spent_usd" in body


# ═══════════════════════════════════════════════════════════════════════════════
# 7. GRAPH
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_graph_customer(client):
    r = await client.get("/api/graph/customer/C001", headers={"X-Role": "analyst"})
    assert r.status_code == 200
    body = r.json()
    assert "nodes" in body
    assert len(body["nodes"]) >= 1


@pytest.mark.asyncio
async def test_graph_entity_device(client):
    r = await client.get("/api/graph/entity/DEV001", headers={"X-Role": "analyst"})
    assert r.status_code == 200
    assert len(r.json()["nodes"]) >= 1


@pytest.mark.asyncio
async def test_graph_entity_not_found(client):
    r = await client.get("/api/graph/entity/NOSUCHENTITY", headers={"X-Role": "analyst"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_links_entity(client):
    r = await client.get("/api/links/EV001", headers={"X-Role": "analyst"})
    assert r.status_code == 200
    body = r.json()
    assert "links" in body
    assert body["link_count"] >= 0


@pytest.mark.asyncio
async def test_links_loan_shared_device(client):
    # L001 and L002 share DEV003
    r = await client.get("/api/links/L001", headers={"X-Role": "analyst"})
    assert r.status_code == 200
    body = r.json()
    device_links = [lk for lk in body["links"] if lk["shared_type"] == "device"]
    assert len(device_links) >= 1, "L001 and L002 share DEV003 — expected device link"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. AUDIT
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_audit_log_has_entries(client):
    r = await client.get("/api/audit", headers={"X-Role": "analyst"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert all("action" in e for e in body["items"])


# ═══════════════════════════════════════════════════════════════════════════════
# 9. MASKING / REVEAL PII
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_reveal_pii_analyst_forbidden(client):
    r = await client.post(
        "/api/masking/reveal",
        json={"case_id": "case-123", "field": "phone"},
        headers={"X-Role": "analyst"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_reveal_pii_supervisor_allowed(client):
    r = await client.post(
        "/api/masking/reveal",
        json={"case_id": "case-123", "field": "phone"},
        headers={"X-Role": "supervisor"},
    )
    assert r.status_code == 200
    assert r.json()["field"] == "phone"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. DEMO DATA
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_demo_data_customers(client):
    r = await client.get("/api/demo/customers_accounts")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")


@pytest.mark.asyncio
async def test_demo_data_transactions(client):
    r = await client.get("/api/demo/transactions")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_demo_data_unknown(client):
    r = await client.get("/api/demo/nonexistent")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_demo_data_masked_hides_pii(client):
    r = await client.get("/api/demo/customers_accounts?masked=true")
    assert r.status_code == 200
    assert "Alice Kumar" not in r.text


@pytest.mark.asyncio
async def test_demo_data_unmasked_shows_pii(client):
    r = await client.get("/api/demo/customers_accounts?masked=false")
    assert r.status_code == 200
    assert "Alice Kumar" in r.text
