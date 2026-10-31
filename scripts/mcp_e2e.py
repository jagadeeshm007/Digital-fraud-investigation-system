"""
End-to-end check of the MCP server against a running app, using a real MCP client over HTTP.

    uvicorn app.main:app --port 8000          # in another terminal (FAKE_LLM=1 is fine)
    python scripts/mcp_e2e.py http://localhost:8000
    python scripts/mcp_e2e.py https://dfis-gray.vercel.app --stateless   # serverless deployment

Loads sample data, then exercises every tool as an MCP client would: reads, consent accepted,
declined and unsupported, role refusal, PII never present, and DNS-rebinding protection.
Exits non-zero if any check fails.
"""
import asyncio
import json
import sys

import httpx
from mcp import types
from mcp.client.session import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
BASE = ARGS[0].rstrip("/") if ARGS else "http://localhost:8000"
# Stateless MCP (serverless) cannot round-trip a consent prompt, so every write must be refused.
STATELESS = "--stateless" in sys.argv
RAW_PII = ["Neelam Chawla", "10.9.3.99", "+919900000555", "SYNTH9999X"]  # planted raw values
results: list[tuple[bool, str]] = []


def check(ok: bool, what: str) -> None:
    results.append((ok, what))
    print(("PASS " if ok else "FAIL ") + what)


def payload(res) -> dict:
    return res.structured_content or json.loads(res.content[0].text)


def answer(action: str, confirm: bool = True):
    prompts: list[str] = []

    async def cb(_ctx, params):
        prompts.append(params.message)
        if action == "accept":
            return types.ElicitResult(action="accept", content={"confirm": confirm})
        return types.ElicitResult(action=action)

    cb.prompts = prompts
    return cb


async def run(role: str, fn, elicitation=None):
    async with create_mcp_http_client(headers={"X-Role": role}) as client:
        async with streamable_http_client(f"{BASE}/mcp", http_client=client) as (read, write):
            async with ClientSession(read, write, elicitation_callback=elicitation) as s:
                await s.initialize()
                return await fn(s)


async def main() -> int:
    async with httpx.AsyncClient(base_url=BASE, timeout=120) as http:
        r = await http.get("/healthz")
        check(r.status_code == 200, "server is up (/healthz)")
        r = await http.post("/api/ingest/sample", headers={"X-Role": "analyst"})
        check(r.status_code == 200, "sample data loaded over REST")

    # 1. Discovery and reads (investigator)
    async def reads(s):
        tools = {t.name for t in (await s.list_tools()).tools}
        check({"get_dashboard", "list_alerts", "get_alert", "list_cases", "get_case", "get_ai_activity",
               "record_case_decision", "run_detection"} <= tools, f"8 tools listed: {sorted(tools)}")
        check(not any("reveal" in t for t in tools), "no reveal tool exposed")
        return tools

    await run("investigator", reads)

    # 2. run_detection, user accepts the consent prompt
    accept = answer("accept")
    det = await run("investigator", lambda s: s.call_tool("run_detection", {}), accept)
    d = payload(det)
    if STATELESS:
        check(d.get("performed") is False, f"run_detection refused without a consent round-trip ({d.get('consent')})")
        async with httpx.AsyncClient(base_url=BASE, timeout=120) as http:  # detect over REST instead
            r = await http.post("/api/detection/run", headers={"X-Role": "investigator"})
            check(r.status_code == 200, f"detection over REST: {r.json().get('new_alerts')} new alerts")
    else:
        check(d.get("performed") is True and accept.prompts, f"run_detection after consent: {d.get('new_alerts')} alerts")

    async def browse(s):
        dash = payload(await s.call_tool("get_dashboard", {}))
        check(dash.get("processed_records", 0) > 1000 and dash.get("flagged_events", 0) > 0,
              f"get_dashboard: {dash.get('processed_records')} records, {dash.get('flagged_events')} flagged")
        high = payload(await s.call_tool("list_alerts", {"risk_band": "High"}))
        ato = payload(await s.call_tool("list_alerts", {"customer_id": "C9300"}))
        check(bool(ato.get("items")), f"list_alerts: {high.get('total')} High, ATO customer found")
        detail = payload(await s.call_tool("get_alert", {"alert_id": ato["items"][0]["alert_id"]}))
        check(bool(detail.get("evidence")) and detail.get("case_id"), "get_alert: evidence records + case id")
        cases = payload(await s.call_tool("list_cases", {"status": "new"}))
        case = payload(await s.call_tool("get_case", {"case_id": cases["items"][0]["case_id"]}))
        check(case.get("status") == "new", f"list_cases/get_case: {cases.get('total')} new cases")
        ai = payload(await s.call_tool("get_ai_activity", {}))
        check(ai.get("total", 0) > 0 and "budget_usd" in ai, f"get_ai_activity: {ai.get('total')} AI calls logged")
        dump = json.dumps([dash, high, ato, detail, cases, case, ai])
        leaked = [v for v in RAW_PII if v in dump]
        check(not leaked, f"no raw PII in any MCP response {leaked or ''}")
        return cases["items"][0]["case_id"], cases["items"][1]["case_id"]

    case_a, case_b = await run("investigator", browse)

    # 3. Writes: declined, unchecked box, client without consent support, analyst role
    decline = answer("decline")
    out = payload(await run("investigator", lambda s: s.call_tool(
        "record_case_decision", {"case_id": case_a, "decision": "false_positive", "reason": "e2e"}), decline))
    check(out.get("performed") is False and out.get("consent") in (("unsupported",) if STATELESS else ("declined",)),
          "declined consent changes nothing")

    untick = answer("accept", confirm=False)
    out = payload(await run("investigator", lambda s: s.call_tool(
        "record_case_decision", {"case_id": case_a, "decision": "false_positive", "reason": "e2e"}), untick))
    check(out.get("performed") is False, "accepting with the box unticked changes nothing")

    out = payload(await run("investigator", lambda s: s.call_tool(
        "record_case_decision", {"case_id": case_a, "decision": "false_positive", "reason": "e2e"})))
    check(out.get("performed") is False and out.get("consent") == "unsupported",
          "client without consent prompts is refused")

    analyst = answer("accept")
    out = payload(await run("analyst", lambda s: s.call_tool(
        "record_case_decision", {"case_id": case_a, "decision": "escalate", "reason": "e2e"}), analyst))
    check(out.get("status") == 403 and not analyst.prompts, "analyst escalate refused before any prompt")

    # 4. Accepted write, then visible through the REST API and audit trail
    ok = answer("accept")
    out = payload(await run("investigator", lambda s: s.call_tool(
        "record_case_decision",
        {"case_id": case_b, "decision": "requires_investigation", "reason": "Linked to loan ring (MCP e2e)"}), ok))
    async with httpx.AsyncClient(base_url=BASE, timeout=60) as http:
        audit = (await http.get("/api/audit?page_size=200", headers={"X-Role": "analyst"})).json()["items"]
        mcp_rows = [e for e in audit if e["channel"] == "mcp"]
        if STATELESS:
            check(out.get("performed") is False, "accepted-but-stateless write refused; nothing changed")
            check(any(e["action"] == "consent:record_case_decision" and e["result"] == "unsupported" for e in mcp_rows),
                  f"audit trail has {len(mcp_rows)} MCP rows incl. refused consents")
        else:
            check(out.get("performed") is True and out["case"]["status"] == "under_investigation",
                  "accepted decision recorded via MCP")
            case = (await http.get(f"/api/cases/{case_b}", headers={"X-Role": "analyst"})).json()
            check(case["history"][-1]["reason"] == "Linked to loan ring (MCP e2e)", "decision visible in REST case history")
            check(any(e["action"] == "consent:record_case_decision" for e in mcp_rows)
                  and any(e["action"] == "record_case_decision" for e in mcp_rows),
                  f"audit trail has {len(mcp_rows)} MCP rows incl. consent outcomes")

        # 5. DNS-rebinding protection: an unexpected Host header is refused
        r = await http.post("/mcp", headers={"Host": "evil.example.com", "Accept": "application/json, text/event-stream",
                                             "Content-Type": "application/json"},
                            content=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}))
        check(r.status_code in (400, 403, 404, 421), f"foreign Host header rejected ({r.status_code})")  # Vercel edge answers 404

    failed = [w for ok, w in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
