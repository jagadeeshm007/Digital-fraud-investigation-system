# Functional Spec — u1-platform

Unit: u1-platform. Components: ActivityStore, AccessAudit, Masking, Ingestion.

---

## App skeleton

The app is a single FastAPI application (`app/main.py`). On startup it:
1. Reads all config from environment variables (raises `RuntimeError` if mandatory vars are absent).
2. Initialises the Supabase Postgres connection pool.
3. Runs Alembic migrations (or applies the schema directly in demo mode).
4. Registers all routers.
5. Binds to `0.0.0.0:8000`.

The built Vite+ frontend is served as a static mount at `/` when `SERVE_FRONTEND=1` is set; otherwise the API is served alone (for local backend development).

Directory layout:
```
app/
  main.py
  config.py          # reads env vars
  db.py              # connection pool
  components/
    activity_store/
    access_audit/
    masking/
    ingestion/
  api/               # FastAPI routers, one per resource group
  migrations/        # Alembic migrations
Dockerfile
docker-compose.yml
```

---

## Flow 1 — File upload and validation

**Trigger:** `POST /api/ingest` with a `multipart/form-data` body containing `file` (binary) and `source_type` (string).

```
Client
  │  POST /api/ingest  (file, source_type, X-Role: analyst)
  ▼
IngestRouter
  │  check_permission(role=analyst, action=upload_file)   [AccessAudit]
  │  ── raises PermissionDenied → 403 if denied ──
  │
  ▼
Ingestion.ingest(file_bytes, filename, source_type)
  │
  ├─ 1. Validate file size ≤ 50 MB → IngestionError("File too large") if exceeded
  ├─ 2. Detect format (csv / xlsx / json)
  │     → IngestionError("Could not read…") if unrecognised
  ├─ 3. Parse into raw rows (list[dict])
  ├─ 4. Load SourceMapping for source_type
  ├─ 5. Map columns (source → target field names)
  │     → IngestionError("Required column X is missing") if a mandatory source column is absent
  ├─ 6. For each row:
  │     a. Validate mandatory fields → RejectedRecord if any missing
  │     b. Validate types / formats → RejectedRecord if type mismatch
  │     c. Validate allowed values  → RejectedRecord if enum violation
  │     d. Check duplicate key      → RejectedRecord if seen before in this batch
  │     e. Check unknown references → WarningRecord if FK unknown
  │     f. Write to ActivityStore   → accepted_count++
  │
  ├─ 7. Create IngestionBatch (accepted/rejected/warning counts)
  ├─ 8. Persist all RejectedRecords
  │
  └─ 9. Return IngestionBatch (with counts)
  │
IngestRouter
  │  audit(role, channel=app, action=upload_file, target=batch_id, result=allowed)
  │
  └─ 200 { batch_id, source_type, accepted_count, rejected_count, warning_count }
```

**Error responses:**
- File too large: 400 `{ "error": "file_too_large", "detail": "…" }`
- Unrecognised format: 400 `{ "error": "unreadable_file", "detail": "…" }`
- Missing source column: 400 `{ "error": "missing_column", "detail": "…" }`

---

## Flow 2 — Retrieve rejected records

**Trigger:** `GET /api/ingest/{batch_id}/rejected`

```
Client
  │  GET /api/ingest/{batch_id}/rejected  (X-Role: analyst)
  ▼
IngestRouter
  │  check_permission(role, action=upload_file)
  │  Fetch IngestionBatch by batch_id → 404 if not found
  │  Fetch all RejectedRecords for batch_id
  └─ 200 { batch_id, records: [{ rejected_id, row_number, field, reason, raw_values }] }
```

---

## Flow 3 — Permission check

**Used by:** every API endpoint as the first step.

```python
def check_permission(role: Role, action: Action) -> None:
    if not PERMISSION_MATRIX[role][action]:
        # audit the denial before raising
        audit(role=role, channel=channel, action=action, target=None, result="denied")
        raise PermissionDenied(role=role, action=action)
    # caller audits the allowance after completing the action
```

The FastAPI exception handler catches `PermissionDenied` and returns 403:
```json
{ "error": "permission_denied", "detail": "Role 'analyst' cannot perform 'run_detection'" }
```

---

## Flow 4 — PII masking (outbound)

**Used by:** every API response that includes entity data.

```python
def mask_entity(entity: AnyEntity) -> AnyEntity:
    """Returns a shallow copy with PII fields replaced by stable tokens."""
    copy = entity.model_copy()
    for field in PII_FIELDS.get(type(entity), []):
        raw = getattr(copy, field, None)
        if raw is not None:
            setattr(copy, field, mask(raw, field))
    return copy

def mask(value: str, field_type: str) -> str:
    token = hmac.new(SESSION_KEY, value.encode(), "sha256").hexdigest()[:6]
    return f"***-{token}"
```

All entities returned from the ActivityStore read functions are passed through `mask_entity` in the API layer before serialisation. The DB layer returns plain entities; masking is an API-layer concern.

---

## Flow 5 — Supervisor PII reveal

**Trigger:** `POST /api/masking/reveal` body `{ case_id, field }`

```
Client (Supervisor only)
  │  POST /api/masking/reveal  (X-Role: supervisor, { case_id, field })
  ▼
MaskingRouter
  │  check_permission(role=supervisor, action=reveal_pii)
  │  ── 403 if not supervisor ──
  │
  │  Look up the entity for the case's subject that owns `field`
  │     → 404 if case or field not found
  │
  │  Fetch the plaintext value from ActivityStore (direct read, no masking)
  │
  │  Record RevealEvent { case_id, field, revealed_by=supervisor, revealed_at=now }
  │
  │  audit(role=supervisor, action=reveal_pii, target=f"{case_id}:{field}", result=allowed)
  │
  └─ 200 { case_id, field, plaintext_value }
```

**Important:** The plaintext value is returned only in this response. It is never cached and never stored in the response log.

---

## Flow 6 — Audit trail retrieval

**Trigger:** `GET /api/audit?page=N&page_size=M`

Returns paginated `AuditEntry` records ordered by `timestamp DESC`. No PII appears in audit entries (the `target` field holds IDs only).

---

## Postgres schema (key tables)

```sql
-- ActivityStore
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    date_of_birth DATE NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    address TEXT NOT NULL,
    identity_number TEXT NOT NULL,
    onboarded_at TIMESTAMPTZ NOT NULL,
    source_system TEXT NOT NULL
);

CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    product TEXT NOT NULL,
    opened_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active','suspended','closed'))
);

CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    sender_account_id TEXT NOT NULL,
    beneficiary_account_id TEXT,
    beneficiary_name TEXT,
    amount_inr NUMERIC(14,2) NOT NULL CHECK (amount_inr >= 0),
    channel TEXT NOT NULL,
    status TEXT NOT NULL,
    device_id TEXT,
    note TEXT
);

-- (devices, login_events, beneficiary_changes, loan_applications, insurance_claims follow the same pattern)

-- AccessAudit
CREATE TABLE audit_entries (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    role TEXT NOT NULL,
    channel TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT,
    result TEXT NOT NULL CHECK (result IN ('allowed','denied'))
);

-- Ingestion
CREATE TABLE ingestion_batches (
    batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    format TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    accepted_count INT NOT NULL DEFAULT 0,
    rejected_count INT NOT NULL DEFAULT 0,
    warning_count INT NOT NULL DEFAULT 0
);

CREATE TABLE rejected_records (
    rejected_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES ingestion_batches(batch_id),
    row_number INT NOT NULL,
    field TEXT NOT NULL,
    reason TEXT NOT NULL,
    raw_values JSONB NOT NULL
);

-- Masking
CREATE TABLE reveal_events (
    reveal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id TEXT NOT NULL,
    field TEXT NOT NULL,
    revealed_by TEXT NOT NULL,
    revealed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Configuration (env vars)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | yes | — | Supabase Postgres connection string |
| `MASKING_HMAC_KEY` | yes | — | 32-byte hex secret for stable token generation |
| `SERVE_FRONTEND` | no | `0` | Set to `1` to serve built Vite+ bundle |
| `MAX_UPLOAD_SIZE_MB` | no | `50` | File size limit |
| `LOG_LEVEL` | no | `INFO` | Python logging level |

---

## Sources

- [desc] Digital Fraud Investigation System — hackathon MVP
- [scope] mvp
- `inception/requirements-analysis/requirements.md` (FR1, FR2, FR8, FR9, FR10)
- `inception/domain-design/components.md`
- `inception/contract-design/contract-summary.md` (C1, C3)
- `construction/u1-platform/functional-design/rules.md`
- `construction/u1-platform/functional-design/entities.md`

## Assumptions & Open Questions

None.
