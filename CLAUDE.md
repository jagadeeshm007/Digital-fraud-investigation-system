# CLAUDE.md — Digital Fraud Investigation System

## Project

Hackathon MVP — multi-source fraud detection. FastAPI backend + Supabase Postgres + Vite+/React frontend.

## Commands

```bash
# Install
pip install -e .

# Run backend
uvicorn app.main:app --reload

# Lint
ruff check app/

# Format
ruff format app/
```

## Architecture

Single FastAPI process. All backend units (u1–u5) run in-process. Frontend served as static mount when `SERVE_FRONTEND=1`.

```
app/
  main.py          # FastAPI app, lifespan (creates tables), exception handlers
  config.py        # pydantic-settings — reads .env
  db.py            # async SQLAlchemy engine + session dependency
  models.py        # ALL ORM models (single file)
  exceptions.py    # PermissionDenied, IngestionError
  masking.py       # HMAC-SHA256 PII masking
  permissions.py   # PERMISSION_MATRIX + check_permission
  audit.py         # write_audit helper
  ingestion.py     # ingest pipeline + per-source writers
  api/
    ingest.py      # POST /api/ingest, GET /api/ingest/{id}/rejected
    masking_router.py  # POST /api/masking/reveal
    audit.py       # GET /api/audit
```

## Non-negotiable rules

- NEVER hardcode secrets — `DATABASE_URL`, `MASKING_HMAC_KEY`, `OPENROUTER_API_KEY` from env only
- NEVER commit real customer data or credentials
- ALWAYS mask PII before any API response, AI call, or MCP tool output
- Money fields: `Decimal(14,2)` only — no floats, JSON-serialised as strings
- Timestamps: must include timezone (`datetime(timezone=True)`)
- `PermissionDenied` must never be caught by callers — only the global exception handler

## Roles + permissions

Resolved from `X-Role` header. Unknown/absent → `analyst`.

| Action | analyst | investigator | supervisor |
|---|---|---|---|
| upload_file | ✓ | ✓ | ✓ |
| run_detection | ✗ | ✓ | ✓ |
| view_alerts/cases/audit | ✓ | ✓ | ✓ |
| record_case_decision | ✗ | ✓ | ✓ |
| change_rule | ✗ | ✗ | ✓ |
| reveal_pii | ✗ | ✗ | ✓ |

## Current state

- u1-platform functional design: complete (`aidlc/.../construction/u1-platform/functional-design/`)
- B1 backend: in progress (app/ directory)
- u2–u5: design pending

## Test strategy

TDD, pytest + pytest-cov, ≥80% line coverage. CI runs on every push to main.
Skip tests only when explicitly asked (time pressure).

## LLM budget

Hard $10 cap via OpenRouter. `FAKE_LLM=1` env flag makes all AI calls return a deterministic stub — use this in CI.
