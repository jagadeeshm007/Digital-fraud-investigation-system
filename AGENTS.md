# AGENTS.md — Digital Fraud Investigation System

This file is the shared AI onboarding for all AI assistants working on this project (GitHub Copilot, Codex, Cursor, opencode, Kiro).

---

## What this project is

Digital Fraud Investigation System — hackathon MVP.
Detects fraud across lending, insurance, and core banking from ingested CSV/XLSX/JSON data.

**Stack:** FastAPI (Python 3.11) + Supabase Postgres + Vite+/React + React Flow + NetworkX

---

## This project uses AI-DLC

All design decisions, requirements, and architecture live in `aidlc/spaces/default/intents/261031-fraud-investigation-copi/`.

Before writing code, read:
- `inception/requirements-analysis/requirements.md` — functional requirements
- `inception/domain-design/components.md` — 13 components
- `inception/contract-design/contract-summary.md` — API contracts
- `inception/units-generation/unit-of-work.md` — 5 units + build order
- `inception/delivery-planning/bolt-plan.md` — bolt sequence

For u1-platform (current active unit):
- `construction/u1-platform/functional-design/entities.md`
- `construction/u1-platform/functional-design/rules.md`
- `construction/u1-platform/functional-design/functional-spec.md`

---

## Hard rules — read before writing anything

1. **No secrets in code.** `DATABASE_URL`, `MASKING_HMAC_KEY`, `OPENROUTER_API_KEY` from env only.
2. **No real data.** All demo data is synthetic. Never commit production credentials or real customer records.
3. **PII masking is mandatory.** Every API response, AI call payload, and MCP tool output must have PII masked via `app/masking.py`. Raw entity values never reach the transport layer.
4. **Money = `Decimal(14,2)`.** Never use float for amounts. JSON serialisation as string (`"1234.56"`).
5. **Timestamps must have timezone.** Naive datetimes are rejected at ingestion.
6. **`PermissionDenied` is not caught by callers.** Only the global FastAPI exception handler catches it (→ HTTP 403).
7. **Parameterised SQL only.** No string interpolation into queries.

---

## Roles

Pass `X-Role: analyst|investigator|supervisor` header. Missing/unknown → `analyst`.

Supervisor is the only role that can reveal PII (`POST /api/masking/reveal`) — app only, never via MCP.

---

## Build order

**u1 → u2 → u3 → (u4 ∥ u5)**

Do not start a unit's code until its dependency units are merged to main.

---

## Branching

Trunk-based. Short-lived branches off `main`, squash-merge when done.
No long-lived feature branches.

---

## Testing

TDD. pytest + pytest-cov (Python), Vitest (React). ≥80% line coverage floor.
`FAKE_LLM=1` env flag stubs all LLM calls — always set in CI.

---

## AI-DLC harness notes

- **Claude Code:** see `CLAUDE.md` and `.claude/CLAUDE.md`
- **GitHub Copilot:** this file (`AGENTS.md`) is your primary onboarding
- **Kiro:** `.kiro/steering/aidlc-onboarding.md`
- **Cursor:** `.cursor/rules/aidlc-onboarding.mdc`
