# Digital Fraud Investigation System (DFIS)

**Team Ozys — Azentio Hackathon 2026**

A multi-source fraud detection platform that ingests transaction, customer, device, and loan/insurance data, runs rule-based detection with AI-assisted review, and surfaces alerts and cases through a role-gated web console.

---

## Scope

4 fraud scenarios: identity fraud, device takeover, account takeover (ATO), cross-system fraud (lending + insurance).

Level 1 deliverable: ingest CSV/XLSX/JSON → validate → explainable alerts.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11) |
| Database | Supabase Postgres |
| Frontend | Vite + React + coss ui + React Flow |
| AI review | OpenRouter (hard $10 cap) |
| Detection | NetworkX + rule engine |

---

## Architecture — 5 Units

```
u1-platform   →  u2-detection-cases  →  u3-ai-review
                                      ↘  u4-web-console (parallel)
                                      ↘  u5-mcp-gateway  (parallel)
```

| Unit | Scope |
|---|---|
| **u1-platform** | Ingest, schema, masking, auth, audit |
| **u2-detection-cases** | 7 fraud rules, scoring, alerts, cases |
| **u3-ai-review** | LLM review loop, citation guard, spend cap |
| **u4-web-console** | 9-screen React UI, role switcher |
| **u5-mcp-gateway** | MCP tools with PII consent gate |

---

## Running locally

```bash
# 1. Copy env and fill in your Supabase URL + HMAC key
cp .env.example .env

# 2. Install deps (Python 3.11+)
pip install -e .

# 3. Start
uvicorn app.main:app --reload
```

Tables are created automatically on first start via `Base.metadata.create_all`.

API docs: http://localhost:8000/docs

---

## Roles

| Role | Can do |
|---|---|
| `analyst` | Upload files, view alerts/cases/audit |
| `investigator` | + run detection, record case decisions, escalate |
| `supervisor` | + change rules, reveal PII fields |

Pass role via `X-Role` header. Defaults to `analyst` if absent.

---

## Key rules

- All PII masked (HMAC-SHA256 stable token) on every outbound path
- Supervisor reveal via `POST /api/masking/reveal` (app only, never MCP)
- Money as `Decimal(14,2)` — no floats
- Secrets from env vars only — never committed

---

## Bolt delivery sequence

| Bolt | Scope | Status |
|---|---|---|
| B1 b1-platform | FastAPI skeleton, schema, ingest, masking, auth | 🔨 in progress |
| B2 b2-detection-cases | 7 rules, scoring, alerts, cases, dashboard | ⏳ |
| B3 b3-ai-review | LLM loop, $10 cap, citation guard | ⏳ |
| B4 b4-web-console | React UI (parallel with B5) | ⏳ |
| B5 b5-mcp-gateway | MCP tools + consent gate (parallel with B4) | ⏳ |

---

## Team

- Jagadeesh — backend (FastAPI, detection engine, AI review)
- Teammate — infra + frontend (Docker, CI, React UI)
