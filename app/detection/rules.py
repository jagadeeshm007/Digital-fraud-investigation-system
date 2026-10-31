"""
7 fraud detection rules (FR3.1–FR3.7).
Each rule is a pure async function: loads data, returns list[DetectionHit], no DB writes.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from difflib import SequenceMatcher
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Account,
    BeneficiaryChange,
    Customer,
    InsuranceClaim,
    LoanApplication,
    LoginEvent,
    Transaction,
)


@dataclass
class DetectionHit:
    rule_id: str
    fraud_category: str
    entity_type: str  # transaction | customer | device | loan_application | insurance_claim
    entity_id: str
    customer_id: Optional[str]
    factors: list[dict]  # [{"factor": str, "points": int, "evidence_id": str}]
    base_score: int
    cleared: bool = False
    cleared_reason: Optional[str] = None
    product: Optional[str] = None  # banking | lending | insurance


async def run_all_rules(session: AsyncSession) -> list[DetectionHit]:
    hits: list[DetectionHit] = []
    for fn in [
        r1_suspicious_transfer,
        r2_shared_device,
        r3_ato,
        r4_loan_ring,
        r5_dup_claim,
        r6_synthetic_identity,
    ]:
        hits.extend(await fn(session))
    return hits


# ─── R1: Suspicious Transfers (FR3.1) ────────────────────────────────────────

async def r1_suspicious_transfer(session: AsyncSession) -> list[DetectionHit]:
    txns = (await session.execute(select(Transaction))).scalars().all()
    if not txns:
        return []

    accounts = {
        a.account_id: a.customer_id
        for a in (await session.execute(select(Account))).scalars().all()
    }
    ben_changes = (await session.execute(select(BeneficiaryChange))).scalars().all()
    ben_by_cust: dict[str, list] = defaultdict(list)
    for bc in ben_changes:
        ben_by_cust[bc.customer_id].append(bc)

    # Group transactions by customer
    cust_txns: dict[str, list[Transaction]] = defaultdict(list)
    for t in txns:
        cid = accounts.get(t.sender_account_id)
        if cid:
            cust_txns[cid].append(t)

    hits: list[DetectionHit] = []

    for cid, ctxns in cust_txns.items():
        ctxns = sorted(ctxns, key=lambda t: t.timestamp)
        amounts = [float(t.amount_inr) for t in ctxns]

        # Need at least 2 transactions for a baseline
        if len(amounts) < 2:
            continue

        # Compute per-payee transaction counts for regular-payee detection
        payee_counts: dict[str, int] = defaultdict(int)
        for t in ctxns:
            if t.beneficiary_account_id:
                payee_counts[t.beneficiary_account_id] += 1

        for i, txn in enumerate(ctxns):
            if i == 0:
                continue  # skip first — no history yet

            baseline = amounts[:i]
            avg = sum(baseline) / len(baseline)
            if avg == 0:
                continue

            amount = float(txn.amount_inr)
            ratio = amount / avg
            factors: list[dict] = []
            score = 0

            if ratio > 5:
                factors.append({
                    "factor": f"Amount ₹{amount:,.0f} is {ratio:.1f}× customer average",
                    "points": 35,
                    "evidence_id": txn.transaction_id,
                })
                score += 35
            elif ratio > 3:
                factors.append({
                    "factor": f"Amount ₹{amount:,.0f} is {ratio:.1f}× customer average",
                    "points": 20,
                    "evidence_id": txn.transaction_id,
                })
                score += 20

            if score == 0:
                continue

            # New-beneficiary modifier
            if txn.beneficiary_account_id:
                payee = txn.beneficiary_account_id
                is_regular = payee_counts[payee] >= 4  # 4+ including this one = known payee
                was_recently_added = any(
                    bc.payee_account_id == payee
                    and txn.timestamp - timedelta(days=7) <= bc.changed_at <= txn.timestamp
                    for bc in ben_by_cust[cid]
                )
                if is_regular:
                    # Legitimate lookalike — regular large payment to known payee
                    hits.append(DetectionHit(
                        rule_id="R1-LOOKALIKE",
                        fraud_category="Legitimate Transaction",
                        entity_type="transaction",
                        entity_id=txn.transaction_id,
                        customer_id=cid,
                        factors=[{"factor": f"Regular payment to known payee ({payee_counts[payee]} prior transactions)", "points": 0}],
                        base_score=0,
                        cleared=True,
                        cleared_reason=f"Regular payment to known payee — seen {payee_counts[payee]} times",
                        product="banking",
                    ))
                    continue
                if was_recently_added:
                    factors.append({
                        "factor": "Transfer to beneficiary added within last 7 days",
                        "points": 15,
                        "evidence_id": txn.transaction_id,
                    })
                    score += 15

            hits.append(DetectionHit(
                rule_id="R1-SUSPICIOUS-TRANSFER",
                fraud_category="Suspicious Transfer",
                entity_type="transaction",
                entity_id=txn.transaction_id,
                customer_id=cid,
                factors=factors,
                base_score=min(100, score),
                product="banking",
            ))

    # Rapid successive transfers: 3+ transfers within 10 min for same customer
    for cid, ctxns in cust_txns.items():
        ctxns_sorted = sorted(ctxns, key=lambda t: t.timestamp)
        flagged_burst: set[str] = set()
        for i, txn in enumerate(ctxns_sorted):
            if txn.transaction_id in flagged_burst:
                continue
            window = [t for t in ctxns_sorted[i:] if t.timestamp <= txn.timestamp + timedelta(minutes=10)]
            if len(window) >= 3:
                total = sum(float(t.amount_inr) for t in window)
                hits.append(DetectionHit(
                    rule_id="R1-RAPID-TRANSFER",
                    fraud_category="Suspicious Transfer",
                    entity_type="transaction",
                    entity_id=txn.transaction_id,
                    customer_id=cid,
                    factors=[{
                        "factor": f"{len(window)} transfers in 10 minutes totalling ₹{total:,.0f}",
                        "points": 25,
                        "evidence_id": txn.transaction_id,
                    }],
                    base_score=25,
                    product="banking",
                ))
                for t in window:
                    flagged_burst.add(t.transaction_id)
                break

    return hits


# ─── R2: Shared Device / IP (FR3.2) ──────────────────────────────────────────

async def r2_shared_device(session: AsyncSession) -> list[DetectionHit]:
    logins = (await session.execute(select(LoginEvent))).scalars().all()
    loans = (await session.execute(select(LoanApplication))).scalars().all()
    customers = {
        c.customer_id: c
        for c in (await session.execute(select(Customer))).scalars().all()
    }

    # device_id -> set of customer_ids (from logins and loans)
    device_customers: dict[str, set[str]] = defaultdict(set)
    for ev in logins:
        if ev.device_id:
            device_customers[ev.device_id].add(ev.customer_id)
    for loan in loans:
        if loan.device_id:
            device_customers[loan.device_id].add(loan.customer_id)

    # ip -> set of customer_ids (from logins)
    ip_customers: dict[str, set[str]] = defaultdict(set)
    for ev in logins:
        if ev.ip_address:
            ip_customers[ev.ip_address].add(ev.customer_id)

    hits: list[DetectionHit] = []

    def _is_household(cids: set[str]) -> bool:
        custs = [customers[c] for c in cids if c in customers]
        if len(custs) < 2:
            return False
        # Same surname and address → likely household
        surnames = {c.name.strip().split()[-1].lower() for c in custs}
        addresses = {c.address.strip().lower() for c in custs}
        return len(surnames) == 1 and len(addresses) == 1

    seen_device_flags: set[str] = set()

    for device_id, cids in device_customers.items():
        if len(cids) < 2:
            continue
        key = device_id
        if key in seen_device_flags:
            continue
        seen_device_flags.add(key)

        if _is_household(cids):
            hits.append(DetectionHit(
                rule_id="R2-HOUSEHOLD",
                fraud_category="Shared Device (Household)",
                entity_type="device",
                entity_id=device_id,
                customer_id=next(iter(cids)),
                factors=[{"factor": f"Device shared by {len(cids)} customers with same surname and address", "points": 0}],
                base_score=0,
                cleared=True,
                cleared_reason="Household sharing — same surname and address, no other risk signals",
                product="banking",
            ))
        else:
            hits.append(DetectionHit(
                rule_id="R2-SHARED-DEVICE",
                fraud_category="Account Takeover / Identity Fraud",
                entity_type="device",
                entity_id=device_id,
                customer_id=next(iter(cids)),
                factors=[{
                    "factor": f"Device used by {len(cids)} unrelated customers: {', '.join(sorted(cids))}",
                    "points": 30,
                    "evidence_id": device_id,
                }],
                base_score=30,
                product="banking",
            ))

    for ip, cids in ip_customers.items():
        if len(cids) < 3:  # shared IP is less suspicious; flag at 3+
            continue
        if _is_household(cids):
            continue
        hits.append(DetectionHit(
            rule_id="R2-SHARED-IP",
            fraud_category="Identity Fraud",
            entity_type="customer",
            entity_id=next(iter(cids)),
            customer_id=next(iter(cids)),
            factors=[{
                "factor": f"IP address {ip} used by {len(cids)} different customers",
                "points": 20,
                "evidence_id": ip,
            }],
            base_score=20,
            product="banking",
        ))

    return hits


# ─── R3: ATO Pattern — repeated failures → success + suspicious follow-up (FR3.3) ──

async def r3_ato(session: AsyncSession) -> list[DetectionHit]:
    logins = (await session.execute(select(LoginEvent))).scalars().all()
    ben_changes = (await session.execute(select(BeneficiaryChange))).scalars().all()
    txns = (await session.execute(select(Transaction))).scalars().all()
    accounts = {
        a.account_id: a.customer_id
        for a in (await session.execute(select(Account))).scalars().all()
    }

    # Group logins by customer, sorted
    cust_logins: dict[str, list[LoginEvent]] = defaultdict(list)
    for ev in logins:
        cust_logins[ev.customer_id].append(ev)
    for cid in cust_logins:
        cust_logins[cid].sort(key=lambda e: e.timestamp)

    # Beneficiary changes by customer
    ben_by_cust: dict[str, list[BeneficiaryChange]] = defaultdict(list)
    for bc in ben_changes:
        ben_by_cust[bc.customer_id].append(bc)

    # Transactions by customer (via account)
    cust_txns: dict[str, list[Transaction]] = defaultdict(list)
    for t in txns:
        cid = accounts.get(t.sender_account_id)
        if cid:
            cust_txns[cid].append(t)

    hits: list[DetectionHit] = []

    for cid, events in cust_logins.items():
        i = 0
        while i < len(events):
            ev = events[i]
            if ev.outcome != "failure":
                i += 1
                continue

            # Collect consecutive failures in a 30-min window
            failures = [ev]
            j = i + 1
            while j < len(events):
                nxt = events[j]
                if (nxt.timestamp - ev.timestamp) > timedelta(minutes=30):
                    break
                if nxt.outcome == "failure":
                    failures.append(nxt)
                j += 1

            if len(failures) < 3:
                i += 1
                continue

            # Look for success within 30 min of last failure
            last_failure = failures[-1]
            success = next(
                (e for e in events[j:] if
                 e.outcome == "success" and
                 (e.timestamp - last_failure.timestamp) <= timedelta(minutes=30)),
                None,
            )

            if not success:
                # Partial ATO signal — just failures
                hits.append(DetectionHit(
                    rule_id="R3-LOGIN-FAILURES",
                    fraud_category="Account Takeover Attempt",
                    entity_type="customer",
                    entity_id=cid,
                    customer_id=cid,
                    factors=[{
                        "factor": f"{len(failures)} failed logins in 30 minutes",
                        "points": 20,
                        "evidence_id": failures[0].event_id,
                    }],
                    base_score=20,
                    product="banking",
                ))
                i = j
                continue

            # Full ATO pattern — failures + success
            score = 30
            factors: list[dict] = [
                {
                    "factor": f"{len(failures)} failed logins followed by successful login",
                    "points": 30,
                    "evidence_id": failures[0].event_id,
                }
            ]

            # New device at success?
            prior_devices = {e.device_id for e in failures if e.device_id}
            if success.device_id and success.device_id not in prior_devices:
                factors.append({
                    "factor": f"Login succeeded from new device {success.device_id}",
                    "points": 15,
                    "evidence_id": success.event_id,
                })
                score += 15

            window_end = success.timestamp + timedelta(minutes=30)

            # Beneficiary change within 30 min of success?
            recent_bens = [
                bc for bc in ben_by_cust[cid]
                if success.timestamp <= bc.changed_at <= window_end
            ]
            if recent_bens:
                factors.append({
                    "factor": "Beneficiary change within 30 minutes of successful login",
                    "points": 20,
                    "evidence_id": recent_bens[0].change_id,
                })
                score += 20

            # Large transfer within 30 min of success?
            cust_amts = [float(t.amount_inr) for t in cust_txns[cid]]
            median_amt = sorted(cust_amts)[len(cust_amts) // 2] if cust_amts else 0
            recent_transfers = [
                t for t in cust_txns[cid]
                if success.timestamp <= t.timestamp <= window_end
                and float(t.amount_inr) > max(median_amt * 1.5, 1000)
            ]
            if recent_transfers:
                total = sum(float(t.amount_inr) for t in recent_transfers)
                factors.append({
                    "factor": f"Large transfer ₹{total:,.0f} within 30 minutes of successful login",
                    "points": 20,
                    "evidence_id": recent_transfers[0].transaction_id,
                })
                score += 20

            hits.append(DetectionHit(
                rule_id="R3-ATO",
                fraud_category="Account Takeover",
                entity_type="customer",
                entity_id=cid,
                customer_id=cid,
                factors=factors,
                base_score=min(100, score),
                product="banking",
            ))
            i = j

    return hits


# ─── R4: Loan Application Ring (FR3.5) ────────────────────────────────────────

async def r4_loan_ring(session: AsyncSession) -> list[DetectionHit]:
    loans = (await session.execute(select(LoanApplication))).scalars().all()
    if not loans:
        return []

    device_custs: dict[str, set[str]] = defaultdict(set)
    phone_custs: dict[str, set[str]] = defaultdict(set)
    addr_custs: dict[str, set[str]] = defaultdict(set)

    for loan in loans:
        if loan.device_id:
            device_custs[loan.device_id].add(loan.customer_id)
        if loan.phone:
            phone_custs[loan.phone.strip()].add(loan.customer_id)
        if loan.address:
            addr_custs[loan.address.strip().lower()].add(loan.customer_id)

    hits: list[DetectionHit] = []
    flagged: set[str] = set()

    def _add_ring_hit(shared_key: str, cids: set[str], factor_desc: str) -> None:
        for cid in cids:
            key = f"R4-{cid}"
            if key in flagged:
                continue
            flagged.add(key)
            cust_loans = [ln for ln in loans if ln.customer_id == cid]
            hits.append(DetectionHit(
                rule_id="R4-LOAN-RING",
                fraud_category="Lending Fraud",
                entity_type="loan_application",
                entity_id=cust_loans[0].application_id if cust_loans else cid,
                customer_id=cid,
                factors=[{
                    "factor": factor_desc,
                    "points": 40,
                    "evidence_id": cust_loans[0].application_id if cust_loans else cid,
                }],
                base_score=40,
                product="lending",
            ))

    for device_id, cids in device_custs.items():
        if len(cids) >= 2:
            _add_ring_hit(device_id, cids, f"Loan applications from {len(cids)} customers share device {device_id}")

    for phone, cids in phone_custs.items():
        if len(cids) >= 2:
            _add_ring_hit(phone, cids, f"Loan applications from {len(cids)} customers share phone {phone[-4:]}")

    for addr, cids in addr_custs.items():
        if len(cids) >= 2:
            _add_ring_hit(addr, cids, f"Loan applications from {len(cids)} customers share the same address")

    return hits


# ─── R5: Duplicate Insurance Claims (FR3.6) ───────────────────────────────────

async def r5_dup_claim(session: AsyncSession) -> list[DetectionHit]:
    claims = (await session.execute(select(InsuranceClaim))).scalars().all()
    if not claims:
        return []

    hits: list[DetectionHit] = []
    flagged: set[str] = set()

    # Per-customer duplicates: same type + amount within 90 days
    cust_claims: dict[str, list[InsuranceClaim]] = defaultdict(list)
    for c in claims:
        cust_claims[c.customer_id].append(c)

    for cid, cclaims in cust_claims.items():
        for i, c1 in enumerate(cclaims):
            for c2 in cclaims[i + 1:]:
                if c1.claim_id in flagged and c2.claim_id in flagged:
                    continue
                days_diff = abs((c1.claim_date - c2.claim_date).days)
                if (
                    c1.claim_type == c2.claim_type
                    and abs(float(c1.amount_inr) - float(c2.amount_inr)) < 100
                    and days_diff <= 90
                ):
                    for cid_flag, claim in [(cid, c1), (cid, c2)]:
                        if claim.claim_id not in flagged:
                            flagged.add(claim.claim_id)
                            hits.append(DetectionHit(
                                rule_id="R5-DUP-CLAIM",
                                fraud_category="Insurance Fraud",
                                entity_type="insurance_claim",
                                entity_id=claim.claim_id,
                                customer_id=cid_flag,
                                factors=[{
                                    "factor": f"Duplicate {c1.claim_type} claim ₹{float(c1.amount_inr):,.0f} within {days_diff} days",
                                    "points": 40,
                                    "evidence_id": claim.claim_id,
                                }],
                                base_score=40,
                                product="insurance",
                            ))

    # Cross-customer: same incident_date + amount + claim_type
    for i, c1 in enumerate(claims):
        for c2 in claims[i + 1:]:
            if c1.customer_id == c2.customer_id:
                continue
            if c1.claim_id in flagged and c2.claim_id in flagged:
                continue
            if (
                c1.claim_type == c2.claim_type
                and c1.incident_date == c2.incident_date
                and abs(float(c1.amount_inr) - float(c2.amount_inr)) < 100
            ):
                for claim, cid in [(c1, c1.customer_id), (c2, c2.customer_id)]:
                    if claim.claim_id not in flagged:
                        flagged.add(claim.claim_id)
                        hits.append(DetectionHit(
                            rule_id="R5-CROSS-CLAIM",
                            fraud_category="Insurance Fraud",
                            entity_type="insurance_claim",
                            entity_id=claim.claim_id,
                            customer_id=cid,
                            factors=[{
                                "factor": f"Same {c1.claim_type} incident date and amount shared by multiple customers",
                                "points": 45,
                                "evidence_id": claim.claim_id,
                            }],
                            base_score=45,
                            product="insurance",
                        ))

    return hits


# ─── R6: Synthetic / Shared Identity (FR3.7) ──────────────────────────────────

async def r6_synthetic_identity(session: AsyncSession) -> list[DetectionHit]:
    customers = (await session.execute(select(Customer))).scalars().all()
    if not customers:
        return []

    phone_custs: dict[str, list[Customer]] = defaultdict(list)
    email_custs: dict[str, list[Customer]] = defaultdict(list)
    identity_custs: dict[str, list[Customer]] = defaultdict(list)

    for c in customers:
        if c.phone:
            phone_custs[c.phone.strip()].append(c)
        if c.email:
            email_custs[c.email.strip().lower()].append(c)
        if c.identity_number:
            identity_custs[c.identity_number.strip()].append(c)

    hits: list[DetectionHit] = []
    flagged: set[str] = set()

    def _add_identity_hit(custs: list[Customer], field_name: str, value: str, points: int) -> None:
        for c in custs:
            key = f"R6-{c.customer_id}-{field_name}"
            if key in flagged:
                continue
            flagged.add(key)
            others = [o.customer_id for o in custs if o.customer_id != c.customer_id]
            hits.append(DetectionHit(
                rule_id="R6-SYNTHETIC-IDENTITY",
                fraud_category="Identity Fraud",
                entity_type="customer",
                entity_id=c.customer_id,
                customer_id=c.customer_id,
                factors=[{
                    "factor": f"{field_name} shared with {len(others)} other customer(s): {', '.join(others[:3])}",
                    "points": points,
                    "evidence_id": c.customer_id,
                }],
                base_score=points,
                product="banking",
            ))

    for phone, custs in phone_custs.items():
        if len(custs) >= 2:
            _add_identity_hit(custs, "Phone number", phone[-4:], 35)

    for email, custs in email_custs.items():
        if len(custs) >= 2:
            _add_identity_hit(custs, "Email address", email, 40)

    for id_num, custs in identity_custs.items():
        if len(custs) >= 2:
            _add_identity_hit(custs, "Identity number", id_num[-4:], 45)

    # Near-duplicate profiles: similar name + DOB within 1 year
    for i, c1 in enumerate(customers):
        for c2 in customers[i + 1:]:
            name_sim = SequenceMatcher(None, c1.name.lower(), c2.name.lower()).ratio()
            dob_diff = abs((c1.date_of_birth - c2.date_of_birth).days)
            if name_sim >= 0.8 and dob_diff <= 365:
                for c, other in [(c1, c2), (c2, c1)]:
                    key = f"R6-NEAR-DUP-{c.customer_id}"
                    if key in flagged:
                        continue
                    flagged.add(key)
                    hits.append(DetectionHit(
                        rule_id="R6-NEAR-DUPLICATE",
                        fraud_category="Synthetic Identity",
                        entity_type="customer",
                        entity_id=c.customer_id,
                        customer_id=c.customer_id,
                        factors=[{
                            "factor": f"Name {name_sim:.0%} similar to customer {other.customer_id}, DOB {dob_diff} days apart",
                            "points": 35,
                            "evidence_id": c.customer_id,
                        }],
                        base_score=35,
                        product="banking",
                    ))

    return hits
