"""
MCP gateway (u5, FR11): lets Claude and other frontier models work with DFIS.

- Read tools are free; responses are the same masked JSON the web API returns.
- Write tools (record_case_decision, run_detection, add_case_note, split_case_alert,
  recommend_action) run only after the *user* accepts an
  MCP elicitation prompt. A client that cannot show one gets a refusal, never a silent write.
- Role comes from the X-Role header, exactly as in the web app; every call is audited (channel "mcp").
- There is deliberately no reveal tool: PII never leaves through MCP (project rule).
"""
from typing import Any

from fastapi import HTTPException
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field

from app import cases as case_svc
from app.api import ai_review as ai_api
from app.api import detection as det_api
from app.api import graph as graph_api
from app.audit import write_audit
from app.config import settings
from app.db import async_session
from app.detection.engine import run_detection as _run_detection
from app.exceptions import PermissionDenied
from app.models import ConsentRequest
from app.permissions import check_permission, resolve_role, resolve_user

mcp = MCPServer(
    name="dfis",
    title="Digital Fraud Investigation System",
    instructions=(
        "Fraud alerts and cases from lending, insurance and core banking. All personal data is "
        "masked. Writes (recording a case decision, running detection) ask the user to confirm."
    ),
)


class Confirm(BaseModel):
    confirm: bool = Field(description="Tick to allow this action")


def _role(ctx: Context) -> str:
    headers = ctx.headers or {}
    return resolve_role(headers.get("x-role") or headers.get("X-Role"))


def _user(ctx: Context, role: str) -> str:
    headers = ctx.headers or {}
    return resolve_user(headers.get("x-user") or headers.get("X-User"), role)


def _error(e: Exception) -> dict:
    if isinstance(e, HTTPException):
        return {"error": e.detail, "status": e.status_code}
    if isinstance(e, PermissionDenied):
        return {"error": str(e), "status": 403}
    if isinstance(e, (det_api.DecisionError, case_svc.CaseError)):
        return {"error": e.detail, "status": e.status}
    raise e


async def _audit(role: str, action: str, target: str | None, result: str) -> None:
    async with async_session() as session:
        await write_audit(session, role=role, channel="mcp", action=action, target=target, result=result)
        await session.commit()


async def _consent(ctx: Context, role: str, tool: str, args: dict, message: str) -> str:
    """Ask the human, record the outcome, return accepted|declined|cancelled|unsupported."""
    caps = ctx.client_capabilities
    if caps is None or getattr(caps, "elicitation", None) is None:
        outcome = "unsupported"
    else:
        result = await ctx.elicit(message=message, schema=Confirm)
        if result.action == "accept":
            outcome = "accepted" if result.data.confirm else "declined"
        else:
            outcome = "declined" if result.action == "decline" else "cancelled"
    async with async_session() as session:
        session.add(ConsentRequest(tool=tool, arguments=args, role=role, outcome=outcome))
        await write_audit(session, role=role, channel="mcp", action=f"consent:{tool}",
                          target=args.get("case_id"), result=outcome)
        await session.commit()
    return outcome


_REFUSED = {
    "unsupported": "This MCP client cannot show consent prompts, so the write was not performed. "
                   "Record it in the web app instead.",
    "declined": "The user declined; nothing was changed.",
    "cancelled": "The user cancelled; nothing was changed.",
}


# ─── Read tools ──────────────────────────────────────────────────────────────

@mcp.tool()
async def get_dashboard(ctx: Context) -> dict[str, Any]:
    """Dashboard figures: processed records, flagged events, risk distribution, fraud categories, open cases."""
    role = _role(ctx)
    async with async_session() as session:
        try:
            out = await det_api.detection_summary(x_role=role, session=session)
        except Exception as e:  # noqa: BLE001 — converted to a tool error
            out = _error(e)
    await _audit(role, "mcp:get_dashboard", None, "ok" if "error" not in out else "denied")
    return out


@mcp.tool()
async def list_alerts(
    ctx: Context,
    risk_band: str | None = None,
    product: str | None = None,
    fraud_category: str | None = None,
    customer_id: str | None = None,
    status: str | None = "open",
    limit: int = 20,
) -> dict[str, Any]:
    """List fraud alerts, newest first. risk_band: Low|Medium|High. product: banking|lending|insurance."""
    role = _role(ctx)
    async with async_session() as session:
        try:
            out = await det_api.list_alerts(
                customer_id=customer_id, transaction_id=None, risk_band=risk_band,
                fraud_category=fraud_category, rule_id=None, product=product, status=status,
                date_from=None, date_to=None, page=1, page_size=max(1, min(limit, 100)),
                x_role=role, session=session,
            )
        except Exception as e:  # noqa: BLE001
            out = _error(e)
    await _audit(role, "mcp:list_alerts", None, "ok" if "error" not in out else "denied")
    return out


@mcp.tool()
async def get_alert(ctx: Context, alert_id: str) -> dict[str, Any]:
    """One alert with its risk factors, AI recommendation, case id and masked supporting records."""
    role = _role(ctx)
    async with async_session() as session:
        try:
            out = await det_api.get_alert(alert_id=alert_id, x_role=role, session=session)
        except Exception as e:  # noqa: BLE001
            out = _error(e)
    await _audit(role, "mcp:get_alert", alert_id, "ok" if "error" not in out else "denied")
    return out


@mcp.tool()
async def list_cases(
    ctx: Context, status: str | None = None, risk_level: str | None = None, limit: int = 20
) -> dict[str, Any]:
    """List investigation cases, highest priority first.
    status: new|under_investigation|info_requested|escalated|closed|concluded."""
    role = _role(ctx)
    async with async_session() as session:
        try:
            out = await det_api.list_cases(
                customer_id=None, status=status, risk_level=risk_level, needs_review=None, page=1,
                page_size=max(1, min(limit, 100)), x_role=role, session=session,
            )
        except Exception as e:  # noqa: BLE001
            out = _error(e)
    await _audit(role, "mcp:list_cases", None, "ok" if "error" not in out else "denied")
    return out


@mcp.tool()
async def get_case(ctx: Context, case_id: str) -> dict[str, Any]:
    """One case with its full decision history."""
    role = _role(ctx)
    async with async_session() as session:
        try:
            out = await det_api.get_case(case_id=case_id, x_role=role, session=session)
        except Exception as e:  # noqa: BLE001
            out = _error(e)
    await _audit(role, "mcp:get_case", case_id, "ok" if "error" not in out else "denied")
    return out


@mcp.tool()
async def get_ai_activity(ctx: Context, limit: int = 20) -> dict[str, Any]:
    """Recent AI review calls (model, tokens, latency, cost, masked prompt) and spend against the budget."""
    role = _role(ctx)
    async with async_session() as session:
        try:
            out = await ai_api.ai_log(page=1, page_size=max(1, min(limit, 100)), x_role=role, session=session)
        except Exception as e:  # noqa: BLE001
            out = _error(e)
    await _audit(role, "mcp:get_ai_activity", None, "ok" if "error" not in out else "denied")
    return out


@mcp.tool()
async def get_case_report(ctx: Context, case_id: str) -> dict[str, Any]:
    """Structured case report: alerts, indicators, masked evidence, AI reviews, history, notes,
    recommendations and audit rows. Read-only."""
    role = _role(ctx)
    async with async_session() as session:
        try:
            check_permission(role, "view_cases")
            out = await case_svc.build_report(session, await case_svc.get_case_or_404(session, case_id))
        except Exception as e:  # noqa: BLE001
            out = _error(e)
    await _audit(role, "mcp:get_case_report", case_id, "ok" if "error" not in out else "denied")
    return out


@mcp.tool()
async def get_case_graph(ctx: Context, case_id: str) -> dict[str, Any]:
    """Investigation network for a case: alerts and the identifiers in their evidence. Every edge names
    the matching identifier and the record it came from. Read-only."""
    role = _role(ctx)
    async with async_session() as session:
        try:
            out = await graph_api.graph_for_case(case_id=case_id, x_role=role, session=session)
        except Exception as e:  # noqa: BLE001
            out = _error(e)
    await _audit(role, "mcp:get_case_graph", case_id, "ok" if "error" not in out else "denied")
    return out


# ─── Write tools (consent-gated) ─────────────────────────────────────────────


async def _gated(ctx: Context, tool: str, permission: str, args: dict, message: str, write) -> dict[str, Any]:
    """Permission first, then the user's consent, then the write. Never writes without 'accepted'."""
    role = _role(ctx)
    try:
        check_permission(role, permission)
    except PermissionDenied as e:
        await _audit(role, f"mcp:{tool}", args.get("case_id"), "denied")
        return _error(e)
    outcome = await _consent(ctx, role, tool, args, message)
    if outcome != "accepted":
        return {"performed": False, "consent": outcome, "message": _REFUSED[outcome]}
    async with async_session() as session:
        try:
            result = await write(session, role, _user(ctx, role))
        except Exception as e:  # noqa: BLE001
            return _error(e)
    return {"performed": True, "consent": outcome, **result}


@mcp.tool()
async def add_case_note(ctx: Context, case_id: str, note: str) -> dict[str, Any]:
    """Add an investigation note to a case after the user confirms."""
    async def write(session, role, user):
        return {"note": case_svc.note_dict(await case_svc.add_note(session, case_id, note, role, user, "mcp"))}
    return await _gated(ctx, "add_case_note", "add_case_note", {"case_id": case_id, "note": note},
                        f"Allow the assistant to add this note to case {case_id}: {note}?", write)


@mcp.tool()
async def split_case_alert(ctx: Context, case_id: str, alert_id: str, reason: str) -> dict[str, Any]:
    """Move a wrongly grouped alert out of a case into a new case, after the user confirms.
    Nothing is deleted; both cases keep their alerts and evidence."""
    async def write(session, role, user):
        new = await case_svc.split_alert(session, case_id, alert_id, reason, role, user, "mcp")
        return {"new_case": case_svc.case_dict(new)}
    args = {"case_id": case_id, "alert_id": alert_id, "reason": reason}
    return await _gated(ctx, "split_case_alert", "record_case_decision", args,
                        f"Allow the assistant to split alert {alert_id} out of case {case_id}? Reason: {reason}",
                        write)


@mcp.tool()
async def recommend_action(ctx: Context, case_id: str, kind: str, reason: str) -> dict[str, Any]:
    """Recommend a temporary hold or enhanced verification (kind: hold | verification) after the user
    confirms. It stays a recommendation until a different Supervisor approves it in the web app, and
    no account or transaction is ever changed."""
    if kind not in ("hold", "verification"):
        return {"error": "kind must be hold or verification", "status": 400}

    async def write(session, role, user):
        case = await det_api.record_case_decision(session, case_id, f"recommend_{kind}", reason, role, "mcp", user)
        return {"case": det_api._case_dict(case), "status": "pending supervisor approval"}
    return await _gated(ctx, "recommend_action", "record_case_decision",
                        {"case_id": case_id, "kind": kind, "reason": reason},
                        f"Allow the assistant to recommend a {kind} on case {case_id}? Reason: {reason}", write)


@mcp.tool()
async def record_case_decision(ctx: Context, case_id: str, decision: str, reason: str) -> dict[str, Any]:
    """Record a decision on a case after the user confirms. reason is required.
    decision: requires_investigation | false_positive | escalate | request_info | conclude."""
    role = _role(ctx)
    try:  # check permission before bothering the user with a prompt they cannot satisfy
        check_permission(role, det_api._DECISION_PERMISSION.get(decision, "record_case_decision"))
    except PermissionDenied as e:
        await _audit(role, "mcp:record_case_decision", case_id, "denied")
        return _error(e)

    args = {"case_id": case_id, "decision": decision, "reason": reason}
    outcome = await _consent(
        ctx, role, "record_case_decision", args,
        f"Allow the assistant to record '{decision}' on case {case_id} with reason: {reason}?",
    )
    if outcome != "accepted":
        return {"performed": False, "consent": outcome, "message": _REFUSED[outcome]}

    async with async_session() as session:
        try:
            case = await det_api.record_case_decision(session, case_id, decision, reason, role, "mcp",
                                                      _user(ctx, role))
        except Exception as e:  # noqa: BLE001
            return _error(e)
        return {"performed": True, "consent": outcome, "case": det_api._case_dict(case)}


@mcp.tool()
async def run_detection(ctx: Context) -> dict[str, Any]:
    """Run fraud detection over all loaded data after the user confirms."""
    role = _role(ctx)
    try:
        check_permission(role, "run_detection")
    except PermissionDenied as e:
        await _audit(role, "mcp:run_detection", None, "denied")
        return _error(e)

    outcome = await _consent(ctx, role, "run_detection", {}, "Allow the assistant to run fraud detection now?")
    if outcome != "accepted":
        return {"performed": False, "consent": outcome, "message": _REFUSED[outcome]}

    async with async_session() as session:
        result = await _run_detection(session, triggered_by=role, channel="mcp")
    async with async_session() as session:
        result["ai_review"] = await ai_api.review_pending(
            session, result["review_alert_ids"], limit=settings.ai_review_batch
        )
    return {"performed": True, "consent": outcome, **result}


def mcp_http_app():
    hosts = ["localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*"]
    hosts += [h.strip() for h in settings.mcp_allowed_hosts.split(",") if h.strip()]
    extra_origins = [o.strip() for o in settings.mcp_allowed_origins.split(",") if o.strip()]
    origins = [f"http://{h}" for h in hosts] + [f"https://{h}" for h in hosts] + extra_origins
    return mcp.streamable_http_app(
        streamable_http_path="/mcp",
        # Serverless instances don't share memory, so a session made on one can't be found on the next.
        stateless_http=settings.mcp_stateless,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True, allowed_hosts=hosts,
            allowed_origins=origins,
        ),
    )
