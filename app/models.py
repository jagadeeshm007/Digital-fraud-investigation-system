import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"
    customer_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    date_of_birth: Mapped[date] = mapped_column(Date)
    phone: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String)
    identity_number: Mapped[str] = mapped_column(String)
    onboarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_system: Mapped[str] = mapped_column(String)


class Account(Base):
    __tablename__ = "accounts"
    account_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String, ForeignKey("customers.customer_id"))
    product: Mapped[str] = mapped_column(String)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String)


class Transaction(Base):
    __tablename__ = "transactions"
    transaction_id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sender_account_id: Mapped[str] = mapped_column(String)
    beneficiary_account_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    beneficiary_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    amount_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    channel: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    device_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Device(Base):
    __tablename__ = "devices"
    device_id: Mapped[str] = mapped_column(String, primary_key=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LoginEvent(Base):
    __tablename__ = "login_events"
    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String, ForeignKey("customers.customer_id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    device_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    outcome: Mapped[str] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String)


class BeneficiaryChange(Base):
    __tablename__ = "beneficiary_changes"
    change_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String, ForeignKey("customers.customer_id"))
    payee_account_id: Mapped[str] = mapped_column(String)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LoanApplication(Base):
    __tablename__ = "loan_applications"
    application_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String, ForeignKey("customers.customer_id"))
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    amount_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    device_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    disbursement_account_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String)


class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"
    claim_id: Mapped[str] = mapped_column(String, primary_key=True)
    policy_id: Mapped[str] = mapped_column(String)
    customer_id: Mapped[str] = mapped_column(String, ForeignKey("customers.customer_id"))
    incident_date: Mapped[date] = mapped_column(Date)
    claim_date: Mapped[date] = mapped_column(Date)
    claim_type: Mapped[str] = mapped_column(String)
    amount_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    payout_account_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class AuditEntry(Base):
    __tablename__ = "audit_entries"
    audit_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    role: Mapped[str] = mapped_column(String)
    channel: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    target: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    result: Mapped[str] = mapped_column(String)


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"
    batch_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_type: Mapped[str] = mapped_column(String)
    file_name: Mapped[str] = mapped_column(String)
    format: Mapped[str] = mapped_column(String)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    accepted_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)


class RejectedRecord(Base):
    __tablename__ = "rejected_records"
    rejected_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id: Mapped[str] = mapped_column(String, ForeignKey("ingestion_batches.batch_id"))
    row_number: Mapped[int] = mapped_column(Integer)
    field: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String)
    raw_values: Mapped[dict] = mapped_column(JSON)


class RevealEvent(Base):
    __tablename__ = "reveal_events"
    reveal_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String)
    field: Mapped[str] = mapped_column(String)
    revealed_by: Mapped[str] = mapped_column(String)
    revealed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
