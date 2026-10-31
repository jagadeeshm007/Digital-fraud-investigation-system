# Digital Fraud Investigation System (DFIS)

**Team Ozys · Azentio.ai Build Labs 2026**

DFIS links customer profiles, accounts, transactions, device and login logs, loan applications and insurance claims into one model. It scores suspicious patterns with a breakdown of every point, clears legitimate lookalikes with a stated reason, adds a bounded AI second opinion, and gives analysts a role-gated console where personal data stays masked and every action is audited.

---

## Level 1 coverage

| Requirement | How DFIS does it | Where |
|---|---|---|
| Ingest CSV, Excel, JSON into one model | 5 sources (`customers_accounts`, `transactions`, `devices_logins`, `loan_applications`, `insurance_claims`) linked by customer, account, device and application IDs | Data Upload (or **Load sample data**) |
| Validate, never drop silently | Every row is accepted or rejected with row number, field and reason (missing value, bad type, enum, duplicate, unknown customer, timestamp without timezone); a missing column rejects the file | Data Upload → Rejected records |
| Suspicious transfers | `R1-SUSPICIOUS-TRANSFER` (amount vs customer average, new or recently added payee), `R1-RAPID-TRANSFER` (3+ in 10 min) | Alerts |
| Shared devices | `R2-SHARED-DEVICE`, `R2-SHARED-IP` | Alerts, entity graph |
| Repeated login failures | `R3-LOGIN-FAILURES` (3+ in 30 min), `R3-ATO` (failures, success on a new device, large transfer or payee change within 30 min) | Alerts |
| Legitimate lookalikes | `R1-LOOKALIKE` (regular payee), `R2-HOUSEHOLD` (same surname and address) are stored as cleared with the reason | Alerts → status "Cleared lookalikes" |
| Extra scenarios | `R4-LOAN-RING` (shared device, phone or address across applicants), `R5-DUP-CLAIM` / `R5-CROSS-CLAIM`, `R6-SYNTHETIC-IDENTITY` / `R6-NEAR-DUPLICATE` | Alerts |
| Risk assessment | 0 to 100 from weighted factors, each with points and an evidence ID; High ≥ 70, Medium ≥ 40, Low below | Alert Detail |
| Alert dashboard | Totals, risk distribution, categories, case statuses, top alerts; alert filters by customer, transaction, risk, status, product, category and date | Dashboard, Alerts |
| Basic case queue | Medium and High alerts open cases; decisions (requires investigation, false positive, escalate) with history; the original alert is never changed | Cases |

---

## Architecture

```
 CSV / Excel / JSON
        │  POST /api/ingest          (role checked, audited)
        ▼
 Ingestion ── validate each row ──► rejected_records (row, field, reason, raw values)
        │
        ▼
 Postgres: customers, accounts, transactions, devices, login_events,
           loan_applications, insurance_claims
        │  POST /api/detection/run
        ▼
 Detection rules R1 to R6 ──► score = sum of factors (each with an evidence ID)
        │                       ├─ lookalike → alert stored as "cleared" with reason
        │                       └─ alert Low / Medium / High → case if Medium or High
        ▼
 AI review (Groq, masked evidence, citations checked, adjustment clamped to ±10)
        │
        ▼
 Cases ── decision + history ──► audit_entries (role, channel, action, target, result)
        │
        ▼
 Console (React + coss ui): roles, masked data, React Flow entity graph
```

| Path | Responsibility |
|---|---|
| `app/main.py` | FastAPI app, exception handlers, serves the built console (with SPA fallback) |
| `app/ingestion.py` | Parse, map, validate and write each source |
| `app/detection/` | Rules (`rules.py`) and scoring, alerts and cases (`engine.py`) |
| `app/graph/builder.py` | Entity graph for alerts and entities (React Flow-ready nodes and edges) |
| `app/ai/review.py` | AI review: prompt, model chain, citation guard, ±10 clamp, fake model |
| `app/masking.py`, `app/permissions.py`, `app/audit.py` | PII masking, role matrix, audit log |
| `frontend/src/` | Console: pages, entity graph, API client, role switcher |

Design documents (requirements, domain design, contracts, mockups, bolt plan) are in `aidlc/spaces/default/intents/261031-fraud-investigation-copi/`.

---

## Run it

### Docker (one command)

```bash
cp .env.example .env            # set MASKING_HMAC_KEY: openssl rand -hex 32
docker compose up --build       # Postgres + app on http://localhost:8000
```

The image builds the console and serves it from FastAPI at `/`; refreshing any page works. Compose uses its own Postgres; a hosted deployment provides `DATABASE_URL` and optionally `PORT`. Set `APP_PORT` or `DB_PORT` if 8000 or 5432 is taken.

### Local development

```bash
cp .env.example .env                 # DATABASE_URL, MASKING_HMAC_KEY, GROQ_API_KEY (or FAKE_LLM=1)
pip install -r requirements.txt
uvicorn app.main:app --reload        # API on :8000, docs at /docs; tables are created on start

cd frontend && npm install
npm run dev                          # console on :5173, proxies /api to :8000 (VITE_API_PROXY to change)
```

### Demo data

On **Data Upload**, press **Load sample data** (or `POST /api/ingest/sample`). It loads a synthetic Indian retail bank for all five sources: 150 ordinary customers plus planted fraud stories and legitimate lookalikes (`app/sample_data.py`, no real PII). Then, as an Investigator, press **Run detection** on Alerts.

To upload your own data, pick a source on Data Upload and press **Download template**: a CSV with the expected columns and a few synthetic example rows (`app/demo_data/`, served by `GET /api/demo/{source}`). Replace the rows and upload it. To demo uploads with files instead, `python -m app.sample_data sample_data/` writes the same data as CSV, XLSX and JSON, plus `99_broken_transactions.csv` for the validation report.

| Customer | Planted story | Expected |
|---|---|---|
| C9000 | ₹2L to a payee added the day before, usual spend ₹4k | Suspicious transfer |
| C9100, C9110, C9120 | Three unrelated applicants on one device, ₹3L loans each, then 3 × ₹95k out in minutes | Shared device, loan ring, rapid transfers |
| C9300 | 5 failed logins, success on a new device, new payee, ₹1.5L out (with a prompt-injection note for the AI) | Account takeover (High) |
| C9400 | Two identical motor claims | Duplicate claim |
| C9410, C9420 | Same health incident date and amount | Cross-customer claim |
| C9500, C9510 | Same ID number and phone, different names | Synthetic identity |
| C9520, C9530 | Near-identical names, close birth dates | Near-duplicate profile |
| C9010 | ₹50k rent to the same landlord every month | Cleared lookalike |
| C9200, C9210 | Couple sharing one phone at the same address | Cleared household |
| C9310 | Two mistyped passwords, then a normal login | No alert |

### Tests and checks

```bash
docker run -d --name dfis-pg-test -e POSTGRES_USER=dfis -e POSTGRES_PASSWORD=dfis_ci -e POSTGRES_DB=dfis_test -p 55432:5432 postgres:16-alpine
pytest --cov=app --cov-fail-under=80          # API, MCP, e2e and scenario tests against Postgres
ruff check app/
cd frontend && npx vp fmt --check && npx vp lint && npm test && npm run build
```

`tests/test_scenarios.py` is the acceptance suite: every planted scenario is flagged, every lookalike is cleared with a reason, and no ordinary customer is flagged. CI (`.github/workflows/ci.yml`) runs all of this on every push with `FAKE_LLM=1`, then builds the Docker image.

### MCP server

The app serves an MCP endpoint at `/mcp` (Streamable HTTP), for example in Claude Code:

```bash
claude mcp add --transport http dfis http://localhost:8000/mcp --header "X-Role: investigator"
```

- Read tools: `get_dashboard`, `list_alerts`, `get_alert`, `list_cases`, `get_case`, `get_ai_activity`, masked like the web API.
- Write tools: `record_case_decision`, `run_detection`. Each asks the user to confirm through an MCP consent prompt first; a client that cannot show the prompt is refused. Every call and consent is audited with channel `mcp`.
- The role comes from the `X-Role` header and is checked on the server. There is no reveal tool, so PII never leaves through MCP.
- For a deployed URL set `MCP_ALLOWED_HOSTS=<your-host>`. End-to-end check with a real MCP client: `python scripts/mcp_e2e.py http://localhost:8000`.

---

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/ingest` | Upload a file (`file`, `source_type`) and get the batch report |
| POST | `/api/ingest/sample` | Load the bundled synthetic data for all five sources |
| GET | `/api/demo/{source_type}` | Preview the bundled demo data (PII masked by default) |
| GET | `/api/ingest/{batch_id}/rejected` | Rejected rows with field and reason |
| POST | `/api/detection/run` | Run all rules (Investigator, Supervisor) |
| GET | `/api/detection/summary` | Dashboard figures |
| GET | `/api/alerts` | Filters: `customer_id`, `transaction_id`, `risk_band`, `fraud_category`, `product`, `status`, `date_from`, `date_to`; paged |
| GET | `/api/alerts/{alert_id}` | Alert with factors, scores and AI status |
| GET | `/api/graph/alert/{alert_id}`, `/api/graph/entity/{id}` | Entity graph (nodes and edges, PII masked) |
| GET | `/api/links/{entity_id}` | Entities sharing a device, IP, phone, email or payee |
| GET | `/api/cases`, `/api/cases/{case_id}` | Case queue and case with history |
| PATCH | `/api/cases/{case_id}/decision` | `requires_investigation`, `false_positive` or `escalate`, with a reason |
| POST | `/api/ai/review/run`, `/api/ai/review/{alert_id}` | AI review for pending alerts or one alert |
| POST | `/api/masking/reveal` | Supervisor-only reveal of one field, audited |
| GET | `/api/audit` | Audit trail, paged |
| GET | `/healthz` | Liveness check |
| MCP | `/mcp` | MCP tools over Streamable HTTP (see MCP server), masked and audited |

Errors use `{"error": "<code>", "detail": "<message>"}`; permission failures return 403 and are audited.

---

## Roles

| Role | Can do |
|---|---|
| Analyst | Upload, view alerts, cases, audit and AI activity |
| Investigator | + run detection, record case decisions, escalate |
| Supervisor | + change rules, reveal PII |

The role comes from the `X-Role` header (the console's role switcher sets it); unknown or missing means Analyst. Checks run on the server.

---

## AI review

- **Models:** Groq `llama-3.3-70b-versatile`, falling back to `llama-3.1-8b-instant` on rate limits.
- **Prompt:** `_SYSTEM_PROMPT` and `_build_prompt` in `app/ai/review.py`. The model receives masked evidence only and must answer in a fixed JSON shape.
- **Guards:** the adjustment is clamped to ±10; reasoning must cite evidence IDs that exist in the alert; any failure, timeout or invalid answer leaves the rule-based score in place.
- **Offline:** `FAKE_LLM=1` returns a deterministic stub (used in CI and demos without a key).

---

## Security and data

- PII (name, phone, email, address, ID number, IP) is HMAC-masked on every API response, graph and AI call; the same value always gives the same token, so links still work.
- Secrets come from environment variables only. All demo data is synthetic.
- Parameterised SQL through SQLAlchemy; money stored as `Numeric(14,2)`; timestamps must carry a timezone.

---

## Tools and components used

- Backend: FastAPI, SQLAlchemy (async) with asyncpg, pandas, openpyxl, pydantic-settings, Groq SDK.
- Frontend: React 19, TypeScript, Vite+ (Vite, Oxlint, Oxfmt, Vitest), Tailwind CSS v4, coss ui (Base UI), React Flow (`@xyflow/react`), d3-force, React Router, lucide-react.
- Delivery: Docker, docker-compose, GitHub Actions, Supabase Postgres.
- AI tools used during development: _to be filled in by the team (required by hackathon rule 6)._

---

## Known limits

- Roles come from a header for the demo; there is no login.
- `/api/graph/*` has no node cap; a very busy device can return a large graph.
- Beneficiary changes have no upload source yet, so the takeover's payee-change factor is not exercised by uploads.
- Automated tests cover the API, MCP and scenarios; the console has no component tests yet.

---

## Team

- **Jagadeesh:** backend platform, detection rules, scoring, AI review, entity graph API, MCP server, sample data, test suite.
- **Vijay Lingoju:** Docker, CI, React console, role switcher, all console screens, React Flow graph, ingestion fixes.
