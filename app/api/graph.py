from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.exceptions import PermissionDenied
from app.graph.builder import build_graph
from app.models import Customer
from app.permissions import check_permission, resolve_role

router = APIRouter(tags=["graph"])


async def _graph_response(session: AsyncSession, seed_id: str, depth: int) -> dict:
    g = await build_graph(session)
    nodes, edges = g.neighbourhood(seed_id, depth)
    if not nodes:
        raise HTTPException(404, detail=f"Entity '{seed_id}' not found in loaded data")
    return g.to_dict(nodes, edges)


# ── GET /api/graph/alert/{alert_id} ──────────────────────────────────────────
# Returns the full evidence graph for one alert (alert node + all linked entities).

@router.get("/graph/alert/{alert_id}")
async def graph_for_alert(
    alert_id: str,
    depth: int = Query(2, ge=1, le=3),
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "view_alerts")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    return await _graph_response(session, alert_id, depth)


# ── GET /api/graph/case/{case_id} ────────────────────────────────────────────
# Investigation network: the case's alerts and the identifiers in their evidence. Every edge is an
# identifier read from a record (never from the AI); an identifier shared by 2+ alerts is a match.

@router.get("/graph/case/{case_id}")
async def graph_for_case(
    case_id: str,
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    check_permission(resolve_role(x_role), "view_cases")
    from app.cases import case_members
    from app.detection.correlation import alert_identifier_sources
    from app.models import Case

    if not await session.get(Case, case_id):
        raise HTTPException(404, detail="Case not found")
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    shared: dict[str, set[str]] = {}
    for _ca, a in await case_members(session, case_id):
        nodes[a.alert_id] = {"id": a.alert_id, "type": "alert", "data": {
            "label": a.rule_id, "rule_id": a.rule_id, "risk_band": a.risk_band, "final_score": a.final_score,
            "fraud_category": a.fraud_category, "product": a.product}}
        for (kind, value), sources in sorted((await alert_identifier_sources(session, a)).items()):
            nid = f"{kind}:{value}"
            nodes.setdefault(nid, {"id": nid, "type": _NODE_TYPE.get(kind, kind),
                                   "data": {"label": value, "kind": kind, "entity_id": value}})
            shared.setdefault(nid, set()).add(a.alert_id)
            edges.append({"id": f"{a.alert_id}__{nid}", "source": a.alert_id, "target": nid,
                          "label": f"{kind} {value}", "match": {"type": kind, "value": value},
                          "evidence": sources, "origin": "identifier"})
    for nid, alert_ids in shared.items():
        nodes[nid]["data"]["alert_count"] = len(alert_ids)
        nodes[nid]["data"]["shared"] = len(alert_ids) > 1
    for e in edges:
        e["shared"] = len(shared[e["target"]]) > 1
    return {"case_id": case_id, "nodes": list(nodes.values()), "edges": edges}


_NODE_TYPE = {"application": "loan_application", "claim": "insurance_claim", "ip": "ip_address",
              "policy": "policy", "phone": "phone"}


# ── GET /api/graph/customer/{customer_id} ────────────────────────────────────
# Full entity graph centred on a customer.

@router.get("/graph/customer/{customer_id}")
async def graph_for_customer(
    customer_id: str,
    depth: int = Query(2, ge=1, le=3),
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "view_alerts")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    return await _graph_response(session, customer_id, depth)


# ── GET /api/graph/entity/{entity_id} ────────────────────────────────────────
# Generic neighbourhood — works for any node id (device, transaction, account …).

@router.get("/graph/entity/{entity_id}")
async def graph_for_entity(
    entity_id: str,
    depth: int = Query(2, ge=1, le=3),
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "view_alerts")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    return await _graph_response(session, entity_id, depth)


# ── GET /api/links/{entity_id}  (B2 LinkGraph) ───────────────────────────────
# Lightweight cross-source link list: which other entities share a device,
# IP address, phone, email, or payee account with this entity.
# Masked shared values. Used by the frontend link-graph panel.

@router.get("/links/{entity_id}")
async def links_for_entity(
    entity_id: str,
    x_role: str | None = Header(default=None, alias="X-Role"),
    session: AsyncSession = Depends(get_session),
):
    role = resolve_role(x_role)
    try:
        check_permission(role, "view_alerts")
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e))

    from collections import defaultdict

    from app.masking import mask
    from app.models import (
        Account, BeneficiaryChange, LoanApplication, LoginEvent, Transaction
    )

    # Load all data needed for cross-source linking
    customers = {c.customer_id: c for c in (await session.execute(select(Customer))).scalars().all()}
    accounts = {a.account_id: a for a in (await session.execute(select(Account))).scalars().all()}
    logins = (await session.execute(select(LoginEvent))).scalars().all()
    loans = (await session.execute(select(LoanApplication))).scalars().all()
    ben_changes = (await session.execute(select(BeneficiaryChange))).scalars().all()
    transactions = (await session.execute(select(Transaction))).scalars().all()


    # ── Build shared-value indexes ────────────────────────────────────────────
    # device_id → list[(entity_id, entity_type, customer_id)]
    device_idx: dict[str, list[dict]] = defaultdict(list)
    ip_idx: dict[str, list[dict]] = defaultdict(list)
    phone_idx: dict[str, list[dict]] = defaultdict(list)
    payee_idx: dict[str, list[dict]] = defaultdict(list)

    acct_to_cust = {a.account_id: a.customer_id for a in accounts.values()}

    for ev in logins:
        rec = {"id": ev.event_id, "type": "login_event", "customer_id": ev.customer_id}
        if ev.device_id:
            device_idx[ev.device_id].append(rec)
        if ev.ip_address:
            ip_idx[ev.ip_address].append(rec)

    for ln in loans:
        rec = {"id": ln.application_id, "type": "loan_application", "customer_id": ln.customer_id}
        if ln.device_id:
            device_idx[ln.device_id].append(rec)
        if ln.phone:
            phone_idx[ln.phone.strip()].append(rec)

    for bc in ben_changes:
        rec = {"id": bc.change_id, "type": "beneficiary_change", "customer_id": bc.customer_id}
        payee_idx[bc.payee_account_id].append(rec)

    for t in transactions:
        if t.device_id:
            cid = acct_to_cust.get(t.sender_account_id)
            device_idx[t.device_id].append({"id": t.transaction_id, "type": "transaction", "customer_id": cid})
        if t.beneficiary_account_id:
            cid = acct_to_cust.get(t.sender_account_id)
            payee_idx[t.beneficiary_account_id].append({"id": t.transaction_id, "type": "transaction", "customer_id": cid})

    # customer phone/email index
    cust_phone_idx: dict[str, list[dict]] = defaultdict(list)
    cust_email_idx: dict[str, list[dict]] = defaultdict(list)
    for c in customers.values():
        if c.phone:
            cust_phone_idx[c.phone.strip()].append({"id": c.customer_id, "type": "customer", "customer_id": c.customer_id})
        if c.email:
            cust_email_idx[c.email.strip().lower()].append({"id": c.customer_id, "type": "customer", "customer_id": c.customer_id})

    # ── Find which shared values touch entity_id ──────────────────────────────
    links: list[dict] = []

    def _collect(idx: dict[str, list[dict]], shared_type: str, mask_fn) -> None:
        for shared_val, members in idx.items():
            ids = {m["id"] for m in members}
            if entity_id not in ids:
                continue
            others = [m for m in members if m["id"] != entity_id]
            if not others:
                continue
            links.append({
                "shared_type": shared_type,
                "shared_value": mask_fn(shared_val),
                "linked_entities": [
                    {"id": o["id"], "entity_type": o["type"], "customer_id": o["customer_id"]}
                    for o in others
                ],
            })

    _collect(device_idx, "device", lambda v: v)          # device IDs are not PII
    _collect(ip_idx, "ip_address", lambda v: mask(v, "ip_address"))
    _collect(phone_idx, "phone", lambda v: mask(v, "phone"))
    _collect(payee_idx, "payee_account", lambda v: v)     # account IDs are opaque
    _collect(cust_phone_idx, "customer_phone", lambda v: mask(v, "phone"))
    _collect(cust_email_idx, "customer_email", lambda v: mask(v, "email"))

    return {
        "entity_id": entity_id,
        "link_count": len(links),
        "links": links,
    }
