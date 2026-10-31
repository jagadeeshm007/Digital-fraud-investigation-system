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

### Frontend (Vite+ / React)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to http://127.0.0.1:8000 (override with VITE_API_PROXY)
npm run build      # type check + production bundle in frontend/dist
npx vp lint        # Oxlint
npx vp fmt         # Oxfmt (CI runs `vp fmt --check`)
npm test           # Vitest
```

The role switcher in the header sends the chosen role as `X-Role` on every API call and remembers it in `localStorage`.

UI components come from [coss ui](https://coss.com/ui/docs) (Base UI + Tailwind), vendored in `frontend/src/components/ui` and themed with the brand tokens in `frontend/src/index.css`. Add more with `npx shadcn@latest add @coss/<component>`; that folder is excluded from `vp fmt` so it stays identical to the registry.

### Full stack with Docker

```bash
cp .env.example .env            # set MASKING_HMAC_KEY: openssl rand -hex 32
docker compose up --build       # Postgres + app on http://localhost:8000
```

The image builds the frontend into `frontend/dist` and sets `SERVE_FRONTEND=1`, so FastAPI serves the bundle at `/`. Compose points `DATABASE_URL` at the local Postgres container; a managed host provides its own `DATABASE_URL` and optional `PORT`.

### Sample data (planted fraud scenarios)

`POST /api/ingest/sample` loads a synthetic Indian retail bank: 150 ordinary customers plus planted stories (suspicious transfer to a new payee, shared-device loan ring with rapid transfers, account takeover, duplicate and cross-customer insurance claims, synthetic identities) and legitimate lookalikes (monthly rent, a household sharing one phone, two mistyped passwords). Then `POST /api/detection/run` as an investigator.

Upload files instead: `python -m app.sample_data sample_data/` writes CSV, XLSX and JSON files plus `99_broken_transactions.csv` to demo the validation report.

### MCP server (Claude, ChatGPT, Gemini)

The app serves an MCP endpoint at `/mcp` (Streamable HTTP). Add it to Claude Code:

```bash
claude mcp add --transport http dfis http://localhost:8000/mcp --header "X-Role: investigator"
```

- Read tools: `get_dashboard`, `list_alerts`, `get_alert`, `list_cases`, `get_case`, `get_ai_activity`. Responses are masked like the web API.
- Write tools: `record_case_decision`, `run_detection`. Each asks the **user** to confirm through an MCP consent prompt first; a client that cannot show the prompt is refused. Every call and consent is in the audit trail with channel `mcp`.
- The role comes from the `X-Role` header and is checked on the server. There is no reveal tool, so PII never leaves through MCP.
- For a deployed URL, set `MCP_ALLOWED_HOSTS=<your-host>`.
- End-to-end check with a real MCP client (start the app first): `python scripts/mcp_e2e.py http://localhost:8000` (19 checks: tools, reads, consent accepted/declined/unsupported, role refusal, no raw PII, DNS-rebinding protection).

### Tests

```bash
docker run -d --name dfis-pg-test -e POSTGRES_USER=dfis -e POSTGRES_PASSWORD=dfis_ci -e POSTGRES_DB=dfis_test -p 55432:5432 postgres:16-alpine
pytest --cov=app --cov-fail-under=80
```

`tests/test_scenarios.py` is the acceptance suite: every planted scenario is flagged, every lookalike is cleared with a reason, and no ordinary customer is flagged.

### CI

`.github/workflows/ci.yml` runs on every push: Ruff + pytest (with a Postgres service, `FAKE_LLM=1`, coverage floor 80% once `tests/` exists), Vite+ format check, lint, Vitest and build, then a Docker image build.

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
