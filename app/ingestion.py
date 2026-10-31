import io
import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import IngestionError
from app.models import (
    Account,
    BeneficiaryChange,
    Customer,
    Device,
    IngestionBatch,
    InsuranceClaim,
    LoanApplication,
    LoginEvent,
    RejectedRecord,
    Transaction,
)


# ── Source mappings ───────────────────────────────────────────────────────────

@dataclass
class SourceMapping:
    column_map: dict[str, str] = field(default_factory=dict)
    mandatory_fields: list[str] = field(default_factory=list)


SOURCE_MAPPINGS: dict[str, SourceMapping] = {
    "customers_accounts": SourceMapping(
        mandatory_fields=[
            "customer_id", "name", "date_of_birth", "phone", "email",
            "address", "identity_number", "onboarded_at", "source_system",
            "account_id", "product", "opened_at", "status",
        ],
    ),
    "transactions": SourceMapping(
        mandatory_fields=["transaction_id", "timestamp", "sender_account_id", "amount_inr", "channel", "status"],
    ),
    "devices_logins": SourceMapping(
        mandatory_fields=["event_id", "customer_id", "timestamp", "outcome", "event_type"],
    ),
    "loan_applications": SourceMapping(
        mandatory_fields=["application_id", "customer_id", "applied_at", "amount_inr", "status"],
    ),
    "insurance_claims": SourceMapping(
        mandatory_fields=["claim_id", "policy_id", "customer_id", "incident_date", "claim_date", "claim_type", "amount_inr"],
    ),
}


# ── Field parsers ─────────────────────────────────────────────────────────────

def _decimal(value: Any, field: str) -> Decimal:
    try:
        d = Decimal(str(value).strip())
        if d < 0:
            raise IngestionError("validation_error", f"{field}: Amount must be non-negative", field)
        return d
    except InvalidOperation:
        raise IngestionError("validation_error", f"{field}: expected decimal, got '{value}'", field)


def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except (ValueError, TypeError):
        raise IngestionError("validation_error", f"{field}: expected YYYY-MM-DD, got '{value}'", field)


def _datetime_tz(value: Any, field: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).strip())
        if dt.tzinfo is None:
            raise IngestionError("validation_error", f"{field}: Timestamp must include a timezone", field)
        return dt
    except IngestionError:
        raise
    except (ValueError, TypeError):
        raise IngestionError("validation_error", f"{field}: invalid datetime '{value}'", field)


def _enum(value: Any, allowed: set[str], field: str) -> str:
    v = str(value).strip()
    if v not in allowed:
        raise IngestionError("validation_error", f"{field}: expected one of {sorted(allowed)}, got '{v}'", field)
    return v


def _require(row: dict, fields: list[str]) -> None:
    for f in fields:
        if not row.get(f):
            raise IngestionError("missing_field", f"Missing required field: {f}", f)


def _str(row: dict, key: str) -> str | None:
    v = row.get(key)
    return str(v) if v is not None else None


# ── File parsing ──────────────────────────────────────────────────────────────

def _parse_file(file_bytes: bytes, filename: str) -> tuple[str, list[dict]]:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    def _csv():
        df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8-sig", dtype=str)
        return "csv", df.where(df.notna(), None).to_dict(orient="records")

    def _xlsx():
        df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        return "xlsx", df.where(df.notna(), None).to_dict(orient="records")

    def _json():
        data = json.loads(file_bytes.decode("utf-8"))
        if not isinstance(data, list):
            raise IngestionError("unreadable_file", "JSON must be a list of objects")
        return "json", data

    parsers = {"csv": _csv, "xlsx": _xlsx, "xls": _xlsx, "json": _json}

    if ext in parsers:
        try:
            return parsers[ext]()
        except IngestionError:
            raise
        except Exception:
            raise IngestionError("unreadable_file", "Could not read this file as CSV, Excel or JSON")

    # Unknown extension — try each
    for try_parser in [_csv, _xlsx, _json]:
        try:
            return try_parser()
        except Exception:
            continue
    raise IngestionError("unreadable_file", "Could not read this file as CSV, Excel or JSON")


def _apply_column_map(rows: list[dict], column_map: dict[str, str]) -> list[dict]:
    if not column_map:
        return rows
    return [{column_map.get(k, k): v for k, v in row.items()} for row in rows]


def _check_columns(rows: list[dict], mandatory_fields: list[str]) -> None:
    if not rows:
        return
    cols = set(rows[0].keys())
    for f in mandatory_fields:
        if f not in cols:
            raise IngestionError("missing_column", f"Required column {f} is missing")


# ── Per-source writers ────────────────────────────────────────────────────────

Rejection = dict  # {row, field, reason, raw}


async def _existing_keys(session: AsyncSession, column) -> set[str]:
    """Keys already in the database, so a re-upload is a reported duplicate, not a 500."""
    return set((await session.execute(select(column))).scalars().all())


def _check_new(key: str, seen: set[str], existing: set[str], field: str) -> None:
    if key in seen:
        raise IngestionError("duplicate", f"Duplicate key {key}", field)
    if key in existing:
        raise IngestionError("duplicate", f"Duplicate key {key} (already loaded)", field)
    seen.add(key)


def _check_customer(cid: str, known: set[str]) -> None:
    # ponytail: unknown customers are rejected, not warned — the FK on these tables needs the customer row first.
    if cid not in known:
        raise IngestionError(
            "unknown_reference", f"Unknown customer {cid}: load customer profiles first", "customer_id"
        )


async def _write_customers_accounts(
    session: AsyncSession, rows: list[dict]
) -> tuple[int, list[Rejection], int]:
    accepted, rejected = 0, []
    existing_c = await _existing_keys(session, Customer.customer_id)
    existing_a = await _existing_keys(session, Account.account_id)
    seen_a: set[str] = set()

    for i, row in enumerate(rows, 1):
        raw = dict(row)
        try:
            _require(row, ["customer_id", "name", "date_of_birth", "phone", "email",
                           "address", "identity_number", "onboarded_at", "source_system",
                           "account_id", "product", "opened_at", "status"])
            cid, aid = str(row["customer_id"]), str(row["account_id"])
            _check_new(aid, seen_a, existing_a, "account_id")

            # Parse everything before adding anything, so a bad row leaves no partial customer.
            account = Account(
                account_id=aid,
                customer_id=cid,
                product=str(row["product"]),
                opened_at=_datetime_tz(row["opened_at"], "opened_at"),
                status=_enum(row["status"], {"active", "suspended", "closed"}, "status"),
            )
            customer = None
            if cid not in existing_c:  # one customer may own several accounts
                customer = Customer(
                    customer_id=cid,
                    name=str(row["name"]),
                    date_of_birth=_date(row["date_of_birth"], "date_of_birth"),
                    phone=str(row["phone"]),
                    email=str(row["email"]),
                    address=str(row["address"]),
                    identity_number=str(row["identity_number"]),
                    onboarded_at=_datetime_tz(row["onboarded_at"], "onboarded_at"),
                    source_system=str(row["source_system"]),
                )
            if customer is not None:
                session.add(customer)
                existing_c.add(cid)
            session.add(account)
            accepted += 1
        except IngestionError as e:
            rejected.append({"row": i, "field": e.field, "reason": e.detail, "raw": raw})

    return accepted, rejected, 0


async def _write_transactions(
    session: AsyncSession, rows: list[dict]
) -> tuple[int, list[Rejection], int]:
    accepted, rejected, warnings = 0, [], 0
    seen: set[str] = set()
    existing = await _existing_keys(session, Transaction.transaction_id)
    known_accounts = await _existing_keys(session, Account.account_id)
    CHANNELS = {"upi", "neft", "imps", "rtgs", "atm", "branch", "online"}
    STATUSES = {"success", "failed", "pending", "reversed"}

    for i, row in enumerate(rows, 1):
        raw = dict(row)
        try:
            _require(row, ["transaction_id", "timestamp", "sender_account_id", "amount_inr", "channel", "status"])
            tid = str(row["transaction_id"])
            _check_new(tid, seen, existing, "transaction_id")
            if str(row["sender_account_id"]) not in known_accounts:
                warnings += 1  # FR1.6: unknown reference is a warning, the row still loads

            session.add(Transaction(
                transaction_id=tid,
                timestamp=_datetime_tz(row["timestamp"], "timestamp"),
                sender_account_id=str(row["sender_account_id"]),
                beneficiary_account_id=_str(row, "beneficiary_account_id"),
                beneficiary_name=_str(row, "beneficiary_name"),
                amount_inr=_decimal(row["amount_inr"], "amount_inr"),
                channel=_enum(row["channel"], CHANNELS, "channel"),
                status=_enum(row["status"], STATUSES, "status"),
                device_id=_str(row, "device_id"),
                note=_str(row, "note"),
            ))
            accepted += 1
        except IngestionError as e:
            rejected.append({"row": i, "field": e.field, "reason": e.detail, "raw": raw})

    return accepted, rejected, warnings


async def _write_devices_logins(
    session: AsyncSession, rows: list[dict]
) -> tuple[int, list[Rejection], int]:
    accepted, rejected = 0, []
    seen_events: set[str] = set()
    existing = await _existing_keys(session, LoginEvent.event_id)
    known_devices = await _existing_keys(session, Device.device_id)
    known_customers = await _existing_keys(session, Customer.customer_id)
    OUTCOMES = {"success", "failure", "blocked"}
    EVENT_TYPES = {
        "login", "logout", "password_reset", "device_register", "beneficiary_add", "profile_change",
    }

    for i, row in enumerate(rows, 1):
        raw = dict(row)
        try:
            _require(row, ["event_id", "customer_id", "timestamp", "outcome", "event_type"])
            eid, cid = str(row["event_id"]), str(row["customer_id"])
            _check_new(eid, seen_events, existing, "event_id")
            _check_customer(cid, known_customers)

            ts = _datetime_tz(row["timestamp"], "timestamp")
            did = _str(row, "device_id")
            event = LoginEvent(
                event_id=eid,
                customer_id=cid,
                timestamp=ts,
                device_id=did,
                ip_address=_str(row, "ip_address"),
                location=_str(row, "location"),
                outcome=_enum(row["outcome"], OUTCOMES, "outcome"),
                event_type=_enum(row["event_type"], EVENT_TYPES, "event_type"),
            )
            # A beneficiary_add event also records the new payee, which R1/R3 use.
            ben = None
            if event.event_type == "beneficiary_add":
                _require(row, ["payee_account_id"])
                ben = BeneficiaryChange(
                    change_id=eid, customer_id=cid,
                    payee_account_id=str(row["payee_account_id"]), changed_at=ts,
                )

            if did and did not in known_devices:
                known_devices.add(did)
                first_seen = _datetime_tz(row["first_seen_at"], "first_seen_at") if row.get("first_seen_at") else ts
                session.add(Device(device_id=did, first_seen_at=first_seen))
            session.add(event)
            if ben is not None:
                session.add(ben)
            accepted += 1
        except IngestionError as e:
            rejected.append({"row": i, "field": e.field, "reason": e.detail, "raw": raw})

    return accepted, rejected, 0


async def _write_loan_applications(
    session: AsyncSession, rows: list[dict]
) -> tuple[int, list[Rejection], int]:
    accepted, rejected = 0, []
    seen: set[str] = set()
    existing = await _existing_keys(session, LoanApplication.application_id)
    known_customers = await _existing_keys(session, Customer.customer_id)
    STATUSES = {"pending", "approved", "rejected", "disbursed"}

    for i, row in enumerate(rows, 1):
        raw = dict(row)
        try:
            _require(row, ["application_id", "customer_id", "applied_at", "amount_inr", "status"])
            aid = str(row["application_id"])
            _check_new(aid, seen, existing, "application_id")
            _check_customer(str(row["customer_id"]), known_customers)

            amount = _decimal(row["amount_inr"], "amount_inr")
            if amount <= 0:
                raise IngestionError("validation_error", "amount_inr: must be > 0", "amount_inr")

            session.add(LoanApplication(
                application_id=aid,
                customer_id=str(row["customer_id"]),
                applied_at=_datetime_tz(row["applied_at"], "applied_at"),
                amount_inr=amount,
                device_id=_str(row, "device_id"),
                ip_address=_str(row, "ip_address"),
                phone=_str(row, "phone"),
                address=_str(row, "address"),
                disbursement_account_id=_str(row, "disbursement_account_id"),
                status=_enum(row["status"], STATUSES, "status"),
            ))
            accepted += 1
        except IngestionError as e:
            rejected.append({"row": i, "field": e.field, "reason": e.detail, "raw": raw})

    return accepted, rejected, 0


async def _write_insurance_claims(
    session: AsyncSession, rows: list[dict]
) -> tuple[int, list[Rejection], int]:
    accepted, rejected = 0, []
    seen: set[str] = set()
    existing = await _existing_keys(session, InsuranceClaim.claim_id)
    known_customers = await _existing_keys(session, Customer.customer_id)

    for i, row in enumerate(rows, 1):
        raw = dict(row)
        try:
            _require(row, ["claim_id", "policy_id", "customer_id", "incident_date", "claim_date", "claim_type", "amount_inr"])
            cid = str(row["claim_id"])
            _check_new(cid, seen, existing, "claim_id")
            _check_customer(str(row["customer_id"]), known_customers)

            amount = _decimal(row["amount_inr"], "amount_inr")
            if amount <= 0:
                raise IngestionError("validation_error", "amount_inr: must be > 0", "amount_inr")

            session.add(InsuranceClaim(
                claim_id=cid,
                policy_id=str(row["policy_id"]),
                customer_id=str(row["customer_id"]),
                incident_date=_date(row["incident_date"], "incident_date"),
                claim_date=_date(row["claim_date"], "claim_date"),
                claim_type=str(row["claim_type"]),
                amount_inr=amount,
                description=_str(row, "description"),
                payout_account_id=_str(row, "payout_account_id"),
            ))
            accepted += 1
        except IngestionError as e:
            rejected.append({"row": i, "field": e.field, "reason": e.detail, "raw": raw})

    return accepted, rejected, 0


_WRITERS = {
    "customers_accounts": _write_customers_accounts,
    "transactions": _write_transactions,
    "devices_logins": _write_devices_logins,
    "loan_applications": _write_loan_applications,
    "insurance_claims": _write_insurance_claims,
}


# ── Entry point ───────────────────────────────────────────────────────────────

async def ingest(
    file_bytes: bytes,
    filename: str,
    source_type: str,
    session: AsyncSession,
) -> IngestionBatch:
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise IngestionError("file_too_large", f"File too large (limit {settings.max_upload_size_mb} MB)")

    if source_type not in SOURCE_MAPPINGS:
        raise IngestionError("unknown_source_type", f"Unknown source_type '{source_type}'")

    mapping = SOURCE_MAPPINGS[source_type]
    fmt, rows = _parse_file(file_bytes, filename)

    if rows:
        rows = _apply_column_map(rows, mapping.column_map)
        _check_columns(rows, mapping.mandatory_fields)

    accepted, rejected_rows, warning_count = await _WRITERS[source_type](session, rows)

    batch = IngestionBatch(
        batch_id=str(uuid.uuid4()),
        source_type=source_type,
        file_name=filename,
        format=fmt,
        received_at=datetime.now(timezone.utc),
        accepted_count=accepted,
        rejected_count=len(rejected_rows),
        warning_count=warning_count,
    )
    session.add(batch)

    for r in rejected_rows:
        session.add(RejectedRecord(
            rejected_id=str(uuid.uuid4()),
            batch_id=batch.batch_id,
            row_number=r["row"],
            field=r["field"],
            reason=r["reason"],
            raw_values=r["raw"],
        ))

    await session.commit()
    return batch
