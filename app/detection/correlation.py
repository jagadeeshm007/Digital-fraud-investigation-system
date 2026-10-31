"""
Cross-system correlation (Level 2): alerts that share a concrete identifier in their evidence
become one investigation. Links come only from matching identifiers, never from the AI.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence import load_evidence
from app.models import Alert, Case, CaseAlert

# Evidence record field -> identifier kind. PII fields (phone, ip) arrive as masked tokens, which are
# deterministic, so equal values still match and the stored link never holds raw PII.
IDENTIFIER_FIELDS = {
    "customer_id": "customer",
    "account_id": "account",
    "sender_account_id": "account",
    "beneficiary_account_id": "account",
    "disbursement_account_id": "account",
    "payout_account_id": "account",
    "payee_account_id": "account",
    "device_id": "device",
    "ip_address": "ip",
    "phone": "phone",
    "application_id": "application",
    "transaction_id": "transaction",
    "policy_id": "policy",
    "claim_id": "claim",
}
_ENTITY_KIND = {
    "transaction": "transaction",
    "customer": "customer",
    "device": "device",
    "loan_application": "application",
    "insurance_claim": "claim",
}
# An identifier on this many alerts is a hub (a shared merchant, say), not evidence of one fraud.
MAX_FANOUT = 20
FINAL_STATUSES = ("closed", "concluded")

Ident = tuple[str, str]


async def alert_identifier_sources(session: AsyncSession, alert: Alert) -> dict[Ident, list[str]]:
    """Each identifier on an alert with where it was read from (record id + field), the documented evidence."""
    out: dict[Ident, list[str]] = {}
    if alert.customer_id:
        out.setdefault(("customer", alert.customer_id), []).append("alert.customer_id")
    kind = _ENTITY_KIND.get(alert.entity_type)
    if kind:
        out.setdefault((kind, alert.entity_id), []).append("alert.entity_id")
    for ev in await load_evidence(session, alert):
        for field, kind in IDENTIFIER_FIELDS.items():
            value = ev["record"].get(field)
            if value:
                out.setdefault((kind, str(value)), []).append(f"{ev['id']}.{field}")
    return out


async def alert_identifiers(session: AsyncSession, alert: Alert) -> set[Ident]:
    return set(await alert_identifier_sources(session, alert))


def group_alerts(idents: dict[str, set[Ident]]) -> list[tuple[list[str], dict[tuple[str, str], list[Ident]]]]:
    """Union-find over identifier -> alerts. Returns each group with the identifiers behind every pair."""
    parent = {a: a for a in idents}

    def find(a: str) -> str:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    by_ident: dict[Ident, list[str]] = {}
    for aid in sorted(idents):
        for ident in idents[aid]:
            by_ident.setdefault(ident, []).append(aid)

    pairs: dict[tuple[str, str], list[Ident]] = {}
    for ident in sorted(by_ident):
        aids = by_ident[ident]
        if len(aids) < 2 or len(aids) > MAX_FANOUT:
            continue
        for i, a in enumerate(aids):
            for b in aids[i + 1:]:
                pairs.setdefault((a, b), []).append(ident)
                parent[find(b)] = find(a)

    groups: dict[str, list[str]] = {}
    for aid in sorted(idents):
        groups.setdefault(find(aid), []).append(aid)
    out = []
    for members in groups.values():
        member_set = set(members)
        out.append((members, {p: v for p, v in pairs.items() if p[0] in member_set}))
    return out


def describe_ident(ident: Ident) -> str:
    return f"{ident[0]} {ident[1]}"


def links_for(aid: str, others: set[str], pairs: dict, alerts: dict[str, Alert]) -> list[dict]:
    links = []
    for (a, b), shared in pairs.items():
        if aid not in (a, b):
            continue
        other = b if a == aid else a
        if other not in others:
            continue
        for kind, value in shared:
            links.append({"with_alert": other, "with_rule": alerts[other].rule_id, "type": kind, "value": value})
    return links


def reason_text(links: list[dict]) -> str:
    if not links:
        return "No shared identifier"
    parts = [f"shares {k['type']} {k['value']} with {k['with_rule']} alert {k['with_alert'][:8]}" for k in links[:3]]
    more = f" (+{len(links) - 3} more links)" if len(links) > 3 else ""
    return "; ".join(parts) + more


def _band_rank(band: str) -> int:
    return {"Low": 0, "Medium": 1, "High": 2}.get(band, 0)


async def consolidate(session: AsyncSession) -> dict:
    """
    Group open alerts into investigations. Existing case membership is kept (an analyst's split is
    never undone): unassigned alerts join the open case they connect to, otherwise a group with a
    Medium/High alert opens a new case. Low-only groups stay on the dashboard (FR7.1).
    """
    await backfill_case_alerts(session)
    alerts = {a.alert_id: a for a in (await session.execute(
        select(Alert).where(Alert.status == "open"))).scalars().all()}
    membership = {ca.alert_id: ca.case_id for ca in (await session.execute(select(CaseAlert))).scalars().all()}
    cases = {c.case_id: c for c in (await session.execute(select(Case))).scalars().all()}

    idents = {aid: await alert_identifiers(session, a) for aid, a in alerts.items()}
    now = datetime.now(timezone.utc)
    new_cases, linked, touched = 0, 0, set()
    pending_links: list[CaseAlert] = []

    for members, pairs in group_alerts(idents):
        unassigned = [a for a in members if a not in membership]
        if not unassigned:
            continue
        open_cases = sorted(
            {membership[a] for a in members if a in membership and cases[membership[a]].status not in FINAL_STATUSES},
            key=lambda cid: cases[cid].created_at,
        )
        if open_cases:
            target = cases[open_cases[0]]
            in_case = {a for a, c in membership.items() if c == target.case_id}
        else:
            if not any(_band_rank(alerts[a].risk_band) >= 1 for a in unassigned):
                continue
            primary = max(unassigned, key=lambda a: (alerts[a].final_score, _band_rank(alerts[a].risk_band)))
            p = alerts[primary]
            target = Case(
                case_id=str(uuid.uuid4()), alert_id=primary, customer_id=p.customer_id,
                fraud_category=p.fraud_category, risk_level=p.risk_band, status="new",
                created_at=now, updated_at=now,
            )
            session.add(target)
            cases[target.case_id] = target
            new_cases += 1
            pending_links.append(CaseAlert(
                case_id=target.case_id, alert_id=primary, link_reason="Primary alert (highest score in the group)",
                links=links_for(primary, set(members) - {primary}, pairs, alerts), linked_at=now,
            ))
            membership[primary] = target.case_id
            in_case = {primary}
            unassigned.remove(primary)

        for aid in unassigned:
            links = links_for(aid, in_case | set(unassigned), pairs, alerts)
            pending_links.append(CaseAlert(
                case_id=target.case_id, alert_id=aid, link_reason=reason_text(links), links=links, linked_at=now,
            ))
            membership[aid] = target.case_id
            linked += 1
        touched.add(target.case_id)

    await session.flush()  # cases before their case_alerts rows (no ORM relationships, FK order)
    session.add_all(pending_links)
    await session.flush()

    from app.cases import refresh_case
    for cid in touched:
        await refresh_case(session, cases[cid])
    return {"new_cases": new_cases, "linked_alerts": linked, "touched_cases": sorted(touched)}


async def backfill_case_alerts(session: AsyncSession) -> None:
    """Level 1 cases had one alert and no case_alerts row; give each its primary row."""
    have = set((await session.execute(select(CaseAlert.case_id))).scalars().all())
    missing = [c for c in (await session.execute(select(Case))).scalars().all() if c.case_id not in have]
    for c in missing:
        session.add(CaseAlert(case_id=c.case_id, alert_id=c.alert_id, link_reason="Primary alert", links=[],
                              linked_at=c.created_at))
    if missing:
        await session.flush()
