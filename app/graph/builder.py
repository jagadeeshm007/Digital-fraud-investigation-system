"""
Entity graph builder.
Loads all entities once, wires relationships as edges, exposes BFS neighbourhood.
Nodes and edges are returned React-Flow-ready (id, type, data; id, source, target, label).
All customer PII is masked before it leaves this layer.
"""
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.masking import mask
from app.models import (
    Account,
    Alert,
    BeneficiaryChange,
    Customer,
    InsuranceClaim,
    LoanApplication,
    LoginEvent,
    Transaction,
)


@dataclass
class GNode:
    id: str
    node_type: str  # customer|account|transaction|device|login_event|beneficiary_change|loan_application|insurance_claim|alert
    data: dict = field(default_factory=dict)


@dataclass
class GEdge:
    id: str
    source: str
    target: str
    label: str


class EntityGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, GNode] = {}
        self._adj: dict[str, set[str]] = defaultdict(set)
        self._edges: dict[str, GEdge] = {}

    def add_node(self, node: GNode) -> None:
        if node.id not in self.nodes:
            self.nodes[node.id] = node

    def add_edge(self, source: str, target: str, label: str) -> None:
        if source not in self.nodes or target not in self.nodes:
            return
        eid = f"{source}__{target}"
        if eid not in self._edges:
            self._edges[eid] = GEdge(id=eid, source=source, target=target, label=label)
            self._adj[source].add(target)
            self._adj[target].add(source)

    def neighbourhood(self, seed_id: str, depth: int = 2) -> tuple[list[GNode], list[GEdge]]:
        """BFS up to `depth` hops from seed_id."""
        if seed_id not in self.nodes:
            return [], []

        visited: set[str] = set()
        q: deque[tuple[str, int]] = deque([(seed_id, 0)])
        while q:
            nid, d = q.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            if d < depth:
                for nbr in self._adj[nid]:
                    if nbr not in visited:
                        q.append((nbr, d + 1))

        nodes = [self.nodes[nid] for nid in visited]
        edges = [
            e for e in self._edges.values()
            if e.source in visited and e.target in visited
        ]
        return nodes, edges

    def to_dict(self, nodes: list[GNode], edges: list[GEdge]) -> dict:
        return {
            "nodes": [{"id": n.id, "type": n.node_type, "data": n.data} for n in nodes],
            "edges": [{"id": e.id, "source": e.source, "target": e.target, "label": e.label} for e in edges],
        }


def _ensure_device(g: EntityGraph, device_id: Optional[str]) -> None:
    if device_id and device_id not in g.nodes:
        g.add_node(GNode(id=device_id, node_type="device", data={"label": device_id}))


async def build_graph(session: AsyncSession) -> EntityGraph:
    """Load all tables and wire the entity graph."""
    g = EntityGraph()

    customers = (await session.execute(select(Customer))).scalars().all()
    accounts = (await session.execute(select(Account))).scalars().all()
    transactions = (await session.execute(select(Transaction))).scalars().all()
    logins = (await session.execute(select(LoginEvent))).scalars().all()
    ben_changes = (await session.execute(select(BeneficiaryChange))).scalars().all()
    loans = (await session.execute(select(LoanApplication))).scalars().all()
    claims = (await session.execute(select(InsuranceClaim))).scalars().all()
    alerts = (await session.execute(
        select(Alert).where(Alert.status == "open")
    )).scalars().all()

    # ── Customers (PII masked) ───────────────────────────────────────────────
    for c in customers:
        g.add_node(GNode(
            id=c.customer_id,
            node_type="customer",
            data={
                "label": c.customer_id,
                "name": mask(c.name),
                "phone": mask(c.phone),
                "email": mask(c.email),
                "identity_number": mask(c.identity_number),
                "address": mask(c.address),
            },
        ))

    # ── Accounts ─────────────────────────────────────────────────────────────
    for a in accounts:
        g.add_node(GNode(
            id=a.account_id,
            node_type="account",
            data={"label": a.account_id, "product": a.product, "status": a.status},
        ))
        g.add_edge(a.customer_id, a.account_id, "owns")

    # ── Transactions ─────────────────────────────────────────────────────────
    for t in transactions:
        g.add_node(GNode(
            id=t.transaction_id,
            node_type="transaction",
            data={
                "label": t.transaction_id,
                "amount_inr": str(t.amount_inr),
                "channel": t.channel,
                "status": t.status,
                "timestamp": t.timestamp.isoformat(),
            },
        ))
        g.add_edge(t.sender_account_id, t.transaction_id, "sent")
        if t.beneficiary_account_id:
            g.add_edge(t.transaction_id, t.beneficiary_account_id, "to")
        if t.device_id:
            _ensure_device(g, t.device_id)
            g.add_edge(t.transaction_id, t.device_id, "via_device")

    # ── Login events ─────────────────────────────────────────────────────────
    for ev in logins:
        g.add_node(GNode(
            id=ev.event_id,
            node_type="login_event",
            data={
                "label": ev.event_id,
                "outcome": ev.outcome,
                "event_type": ev.event_type,
                "timestamp": ev.timestamp.isoformat(),
            },
        ))
        g.add_edge(ev.customer_id, ev.event_id, "logged_in")
        if ev.device_id:
            _ensure_device(g, ev.device_id)
            g.add_edge(ev.event_id, ev.device_id, "used_device")
        if ev.ip_address:
            ip_node_id = f"ip:{ev.ip_address}"
            if ip_node_id not in g.nodes:
                g.add_node(GNode(id=ip_node_id, node_type="ip_address", data={"label": ev.ip_address}))
            g.add_edge(ev.event_id, ip_node_id, "from_ip")

    # ── Beneficiary changes ───────────────────────────────────────────────────
    for bc in ben_changes:
        g.add_node(GNode(
            id=bc.change_id,
            node_type="beneficiary_change",
            data={"label": bc.change_id, "payee_account_id": bc.payee_account_id, "changed_at": bc.changed_at.isoformat()},
        ))
        g.add_edge(bc.customer_id, bc.change_id, "changed_beneficiary")
        # Link to payee account if it exists in graph
        g.add_edge(bc.change_id, bc.payee_account_id, "to_payee")

    # ── Loan applications ─────────────────────────────────────────────────────
    for ln in loans:
        g.add_node(GNode(
            id=ln.application_id,
            node_type="loan_application",
            data={
                "label": ln.application_id,
                "amount_inr": str(ln.amount_inr),
                "status": ln.status,
            },
        ))
        g.add_edge(ln.customer_id, ln.application_id, "applied")
        if ln.device_id:
            _ensure_device(g, ln.device_id)
            g.add_edge(ln.application_id, ln.device_id, "used_device")
        if ln.disbursement_account_id:
            g.add_edge(ln.application_id, ln.disbursement_account_id, "disbursed_to")

    # ── Insurance claims ──────────────────────────────────────────────────────
    for cl in claims:
        g.add_node(GNode(
            id=cl.claim_id,
            node_type="insurance_claim",
            data={
                "label": cl.claim_id,
                "claim_type": cl.claim_type,
                "amount_inr": str(cl.amount_inr),
                "incident_date": cl.incident_date.isoformat(),
            },
        ))
        g.add_edge(cl.customer_id, cl.claim_id, "filed")
        if cl.payout_account_id:
            g.add_edge(cl.claim_id, cl.payout_account_id, "paid_to")

    # ── Alert nodes (open only) ───────────────────────────────────────────────
    for al in alerts:
        g.add_node(GNode(
            id=al.alert_id,
            node_type="alert",
            data={
                "label": al.alert_id,
                "fraud_category": al.fraud_category,
                "risk_band": al.risk_band,
                "final_score": al.final_score,
                "rule_id": al.rule_id,
            },
        ))
        if al.customer_id:
            g.add_edge(al.alert_id, al.customer_id, "flags_customer")
        # Link alert to the flagged entity (may already exist as customer, txn, device, etc.)
        if al.entity_id and al.entity_id != al.customer_id:
            g.add_edge(al.alert_id, al.entity_id, "flags_entity")

    return g
