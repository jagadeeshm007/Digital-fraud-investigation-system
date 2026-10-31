# Entities — u1-platform

Unit: u1-platform. Components: ActivityStore, AccessAudit, Masking, Ingestion.

---

## ActivityStore

### Customer

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `customer_id` | `str` | PK, opaque | Source identifier, stored exactly as given |
| `name` | `str` | required | PII — masked on all outbound paths |
| `date_of_birth` | `date` | required | |
| `phone` | `str` | required | PII |
| `email` | `str` | required | PII |
| `address` | `str` | required | PII |
| `identity_number` | `str` | required | PII |
| `onboarded_at` | `datetime(tz)` | required | |
| `source_system` | `str` | required | e.g. `lending`, `insurance`, `core_banking` |

### Account

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `account_id` | `str` | PK, opaque | |
| `customer_id` | `str` | FK → Customer | |
| `product` | `str` | required | e.g. `savings`, `loan`, `insurance` |
| `opened_at` | `datetime(tz)` | required | |
| `status` | `enum` | `active\|suspended\|closed` | |

### Transaction

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `transaction_id` | `str` | PK, opaque | |
| `timestamp` | `datetime(tz)` | required | |
| `sender_account_id` | `str` | FK → Account | |
| `beneficiary_account_id` | `str` | nullable, opaque | May be external |
| `beneficiary_name` | `str` | nullable | PII |
| `amount_inr` | `Decimal(14,2)` | required, ≥ 0 | Fixed-point; no floats |
| `channel` | `enum` | `upi\|neft\|imps\|rtgs\|atm\|branch\|online` | |
| `status` | `enum` | `success\|failed\|pending\|reversed` | |
| `device_id` | `str` | nullable, FK → Device | |
| `note` | `str` | nullable | |

### Device

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `device_id` | `str` | PK, opaque | |
| `first_seen_at` | `datetime(tz)` | required | |

### LoginEvent

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `event_id` | `str` | PK, opaque | |
| `customer_id` | `str` | FK → Customer | |
| `timestamp` | `datetime(tz)` | required | |
| `device_id` | `str` | nullable, FK → Device | |
| `ip_address` | `str` | nullable | PII |
| `location` | `str` | nullable | PII |
| `outcome` | `enum` | `success\|failure\|blocked` | |
| `event_type` | `enum` | `login\|logout\|password_reset\|device_register` | |

### BeneficiaryChange

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `change_id` | `str` | PK, opaque | |
| `customer_id` | `str` | FK → Customer | |
| `payee_account_id` | `str` | required, opaque | |
| `changed_at` | `datetime(tz)` | required | |

### LoanApplication

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `application_id` | `str` | PK, opaque | |
| `customer_id` | `str` | FK → Customer | |
| `applied_at` | `datetime(tz)` | required | |
| `amount_inr` | `Decimal(14,2)` | required, > 0 | |
| `device_id` | `str` | nullable, FK → Device | |
| `ip_address` | `str` | nullable | PII |
| `phone` | `str` | nullable | PII |
| `address` | `str` | nullable | PII |
| `disbursement_account_id` | `str` | nullable, opaque | |
| `status` | `enum` | `pending\|approved\|rejected\|disbursed` | |

### InsuranceClaim

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `claim_id` | `str` | PK, opaque | |
| `policy_id` | `str` | required, opaque | |
| `customer_id` | `str` | FK → Customer | |
| `incident_date` | `date` | required | |
| `claim_date` | `date` | required | |
| `claim_type` | `str` | required | e.g. `health`, `vehicle`, `property` |
| `amount_inr` | `Decimal(14,2)` | required, > 0 | |
| `description` | `str` | nullable | |
| `payout_account_id` | `str` | nullable, opaque | |

---

## AccessAudit

### AuditEntry

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `audit_id` | `str` | PK, auto (UUID) | |
| `timestamp` | `datetime(tz)` | required, auto-set | |
| `role` | `enum` | `analyst\|investigator\|supervisor` | |
| `channel` | `enum` | `app\|mcp` | |
| `action` | `str` | required | e.g. `upload_file`, `run_detection`, `reveal_pii` |
| `target` | `str` | nullable | e.g. batch_id, alert_id, case_id |
| `result` | `enum` | `allowed\|denied` | |

Invariant: entries are append-only; no UPDATE or DELETE is ever issued on this table.

---

## Ingestion

### IngestionBatch

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `batch_id` | `str` | PK, auto (UUID) | |
| `source_type` | `enum` | `customers_accounts\|transactions\|devices_logins\|loan_applications\|insurance_claims` | |
| `file_name` | `str` | required | Original filename |
| `format` | `enum` | `csv\|xlsx\|json` | |
| `received_at` | `datetime(tz)` | required, auto-set | |
| `accepted_count` | `int` | required, ≥ 0 | |
| `rejected_count` | `int` | required, ≥ 0 | |
| `warning_count` | `int` | required, ≥ 0 | |

### RejectedRecord

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `rejected_id` | `str` | PK, auto (UUID) | |
| `batch_id` | `str` | FK → IngestionBatch | |
| `row_number` | `int` | required, ≥ 1 | 1-indexed |
| `field` | `str` | required | Field name that caused the rejection |
| `reason` | `str` | required | Human-readable reason |
| `raw_values` | `json` | required | The entire raw row, for review |

### SourceMapping (configuration, not persisted in DB)

| Field | Type | Notes |
|---|---|---|
| `source_type` | `str` | Key |
| `column_map` | `dict[str, str]` | `{source_column: target_field}` |
| `mandatory_fields` | `list[str]` | Fields required for acceptance |

---

## Masking

### RevealEvent

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `reveal_id` | `str` | PK, auto (UUID) | |
| `case_id` | `str` | required, FK → Case (in u2) | |
| `field` | `str` | required | Field name revealed |
| `revealed_by` | `str` | required | Role: always `supervisor` |
| `revealed_at` | `datetime(tz)` | required, auto-set | |

No masking tokens are persisted — the mask function is deterministic (HMAC-based stable token), so the same value always masks to the same token within a session without storage.

## Sources

- [desc] Digital Fraud Investigation System — hackathon MVP
- [scope] mvp
- `inception/units-generation/unit-of-work.md` (u1-platform scope: ActivityStore, AccessAudit, Masking, Ingestion)
- `inception/domain-design/components.md`
- `inception/requirements-analysis/requirements.md`

## Assumptions & Open Questions

None.
