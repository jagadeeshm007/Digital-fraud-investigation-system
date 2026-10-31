# Bolt Plan

Inputs: `inception/units-generation/unit-of-work.md`, `inception/units-generation/unit-of-work-dependency.md`, `inception/units-generation/unit-of-work-story-map.md`, `inception/contract-design/contract-summary.md`, `inception/requirements-analysis/requirements.md`, `delivery-planning-questions.md`.

One Bolt per Unit. Sequencing is risk-first within the dependency order. Each Bolt merges to `main` as one squash commit before the next Bolt begins (team practices).

---

## Bolt 1 — b1-platform

**Unit:** u1-platform  
**Branch:** `bolt/b1-platform`  
**Depends on:** —  
**Confidence hypothesis:** After this Bolt merges, a Docker image builds from one `Dockerfile`, deploys to the chosen host, accepts a file upload, validates it, and returns a structured report — all API routes authenticated by role. This proves the container and the deployment pipeline before any feature logic is built on top.

### Scope

- App skeleton: FastAPI application, configuration loading from env, one `Dockerfile`, `docker-compose.yml`
- `ActivityStore` — Supabase Postgres schema and all read/write functions
- `AccessAudit` — role resolution, `check_permission`, append-only `audit` write
- `Masking` — `mask`, `mask_entity`, `reveal` (Supervisor only)
- `Ingestion` — file parse (CSV/Excel/JSON), column mapping, validation, `IngestionBatch`, `RejectedRecord`
- HTTP routes: `POST /api/ingest`, `GET /api/ingest/{batch_id}/rejected`
- TDD: write failing tests first for each layer, then implement

### Definition of Done

- [ ] `docker compose up` starts cleanly with no errors
- [ ] `POST /api/ingest` accepts a sample CSV, returns a batch with accepted/rejected counts
- [ ] A file with 12 missing-amount rows reports exactly 12 rejections with row, field and reason
- [ ] A request with the wrong role returns HTTP 403
- [ ] `pytest --cov` reports ≥ 80% line coverage
- [ ] Ruff lint passes
- [ ] Squash-merged to `main`; CI green

---

## Bolt 2 — b2-detection-cases

**Unit:** u2-detection-cases  
**Branch:** `bolt/b2-detection-cases`  
**Depends on:** b1-platform (merged)  
**Confidence hypothesis:** After this Bolt merges, running detection on the planted synthetic dataset raises the expected alerts, clears the expected lookalikes, and the case queue shows the correct Medium/High cases. This proves the core product value before the AI layer is built.

### Scope

- `LinkGraph` — build cross-system links from ActivityStore records, `EntityLink`
- `Detection` — 7 scenario rules, lookalike clearing, `RuleSetting` / `RuleChange`; Supervisor rule-setting change audited through AccessAudit
- `RiskScoring` — weighted score, sequence bonus, mitigation, bands (Low/Medium/High)
- `Alerts` — run orchestration, `DetectionRun`, immutable `Alert`, `AlertRaised` event stub
- `Cases` — case creation, decision flow (Requires Investigation / False Positive / Escalate), `Case`, `CaseDecision`
- `Dashboard` — computed figures endpoint
- HTTP routes: `POST /api/detection/run`, `GET /api/detection/settings`, `PATCH /api/detection/settings/{key}`, `GET /api/alerts`, `GET /api/alerts/{alert_id}`, `GET /api/cases`, `GET /api/cases/{case_id}`, `POST /api/cases/{case_id}/decisions`, `GET /api/dashboard`, `GET /api/links/{entity_id}`
- TDD: write acceptance tests for every planted scenario first

### Definition of Done

- [ ] Each planted synthetic fraud scenario raises at least one alert of the expected type
- [ ] Each planted legitimate lookalike produces no alert and appears as "evaluated and cleared" with a reason
- [ ] `GET /api/dashboard` returns non-zero processed records and alert counts after a run
- [ ] A Supervisor can change a rule setting; the change appears in the audit trail
- [ ] A duplicate case decision is accepted idempotently (no 4xx)
- [ ] `pytest --cov` reports ≥ 80% line coverage
- [ ] Ruff lint passes; CI green; squash-merged to `main`

---

## Bolt 3 — b3-ai-review

**Unit:** u3-ai-review  
**Branch:** `bolt/b3-ai-review`  
**Depends on:** b2-detection-cases (merged)  
**Confidence hypothesis:** After this Bolt merges, the AI review loop runs, citations are validated, the score adjustment is bounded to ±10, and the $10 spend cap stops further calls. CI uses a fake model, so no real spend occurs in the test suite.

### Scope

- `AiReview` — handle `AlertRaised` event, mask evidence via Masking, call model via OpenRouter, validate citation structure, bound ±10 adjustment, store `AiReviewResult`
- `AiCallLog` — log every call with token counts, cost, latency, masked prompt
- Spend guard — stop calls when cumulative cost reaches $10; log the cut-off; rule-based result stands
- Injection guard — treat evidence text as data; discard any result whose format does not match the expected schema
- HTTP routes: `GET /api/ai/reviews/{alert_id}`, `GET /api/ai/log`
- CI fake model: a deterministic stub that returns a valid schema response at zero cost
- TDD: write tests against the fake model first

### Definition of Done

- [ ] A `AlertRaised` event triggers the review flow and stores an `AiReviewResult`
- [ ] A result that cites an ID not in the evidence is discarded and logged
- [ ] A result that would push the score above ±10 is clamped to ±10
- [ ] Cumulative spend is tracked; no further calls are made after $10 is reached
- [ ] `GET /api/ai/log` returns call entries with model, cost, latency
- [ ] CI fake model: tests pass with zero OpenRouter calls
- [ ] `pytest --cov` ≥ 80%; Ruff passes; CI green; squash-merged to `main`

---

## Bolt 4 — b4-web-console

**Unit:** u4-web-console  
**Branch:** `bolt/b4-web-console`  
**Depends on:** b3-ai-review (merged)  
**Parallel opportunity:** can be built alongside b5-mcp-gateway (no edge between them)  
**Confidence hypothesis:** After this Bolt merges, every screen in the refined mockups is reachable and functional for each of the three roles. PII is masked in every view by default.

### Scope

- All 9 screens: Dashboard, Data Upload, Alerts, Alert Detail, Case Queue, Case Detail, AI Activity, Data Safety, Audit Trail
- Role switcher (sets `X-Role` header on every request)
- Masked value display; Supervisor-only reveal flow
- React Flow entity graph on Alert Detail
- Vite+ build, coss ui with Azentio tokens
- Vitest component tests and axe accessibility checks for each screen

### Definition of Done

- [ ] All 9 screens render without console errors for each role
- [ ] Role switcher changes the active role and the server enforces it (403 on unauthorised actions)
- [ ] Upload screen accepts a file, shows validation report
- [ ] Alert Detail shows factors, masked evidence, entity graph, and AI recommendation
- [ ] Case Detail shows decision history and allows a decision (role-permitting)
- [ ] Supervisor reveal shows plaintext for one field; non-Supervisor sees masked value
- [ ] Vitest passes; axe reports no critical violations; CI green; squash-merged to `main`

---

## Bolt 5 — b5-mcp-gateway

**Unit:** u5-mcp-gateway  
**Branch:** `bolt/b5-mcp-gateway`  
**Depends on:** b3-ai-review (merged)  
**Parallel opportunity:** can be built alongside b4-web-console  
**Confidence hypothesis:** After this Bolt merges, Claude (or another frontier model) can call the read tools and get masked results, and a write tool runs only after the user explicitly consents in the session.

### Scope

- `McpGateway` — 5 read tools + 2 write tools (see contract C5)
- Consent gate: `ConsentRequest` record, approval / denial flow, no-reveal rule
- Role checks and `AccessAudit` calls for every tool invocation
- MCP protocol endpoint (stdio or HTTP, team picks at construction time)
- Pytest tests covering each tool, a denied consent (nothing written), and a duplicate read

### Definition of Done

- [ ] `get_dashboard`, `list_alerts`, `get_alert`, `get_case`, `get_ai_log` return masked results
- [ ] `record_case_decision` records a `ConsentRequest` and proceeds only on approval
- [ ] `run_detection` requires consent; a declined consent leaves state unchanged
- [ ] A tool call with an insufficient role returns `permission_denied`
- [ ] Every tool call appears in the audit trail
- [ ] `pytest --cov` ≥ 80%; Ruff passes; CI green; squash-merged to `main`

---

## Bolt Sequence

```
B1 platform ──► B2 detection-cases ──► B3 ai-review ──► B4 web-console
                                                    └──► B5 mcp-gateway  (parallel with B4)
```

## Sources

- [desc] Digital Fraud Investigation System — hackathon MVP
- [scope] mvp
- `inception/units-generation/unit-of-work.md`
- `inception/units-generation/unit-of-work-dependency.md`
- `inception/contract-design/contract-summary.md`
- `inception/requirements-analysis/requirements.md`

## Assumptions & Open Questions

None.
