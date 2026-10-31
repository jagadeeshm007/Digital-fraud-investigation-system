# Risk and Sequencing Rationale

Inputs: `inception/units-generation/unit-of-work.md`, `inception/units-generation/unit-of-work-dependency.md`, `inception/requirements-analysis/requirements.md`, `delivery-planning-questions.md`.

## Sequencing Heuristic

**Risk-first within dependency order.** Each Bolt that must precede the next in the DAG ships the highest-risk layer first: the shared foundation (B1) before any feature, the detection core (B2) before the AI layer that consumes it, and the AI layer (B3) before the two consumer Bolts that build on it.

## Risk Register

| Risk | Bolt | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Supabase Postgres setup takes longer than expected | B1 | Medium | High | Use the free Supabase project; schema runs as a migration script; can fall back to SQLite for local dev with an env flag |
| Detection rules are hard to get right for the 7 planted scenarios | B2 | High | High | Acceptance tests are written first (TDD); each scenario has its own test with the planted data; the team knows the exact expected output before writing a line of rule code |
| OpenRouter spend exceeds $10 before CI catches it | B3 | Low | Medium | CI always uses the fake model; the $10 guard cuts off real calls; tests run against the stub |
| Deployment to chosen host fails close to the deadline | B1 | Medium | High | Deploy after B1 merges, not at the end; verify the live URL before any feature work starts on B2 |
| B4 and B5 conflict on `main` if built in parallel | B4/B5 | Low | Low | They touch different directories; no shared file writes; squash-merge either order |
| Hackathon check-in rule (no app code before 11:00) | B1+ | Low | Medium | All design artifacts committed before 11:00; app code commits start at or after 11:00 (team practices) |

## Sequencing Decisions

### Why B1 before everything
The deployment pipeline and shared schema are depended on by every other Bolt. A broken foundation discovered at B4 would require rework across all prior Bolts. B1 proves the container builds and deploys at the URL before any feature code is written.

### Why B2 before B3
`AlertRaised` is emitted by Alerts (B2). AiReview (B3) consumes it. B3 cannot be meaningfully tested without real alerts from a real detection run.

### Why B4 and B5 after B3
Both units depend on the full API surface: B4 (web console) calls every backend endpoint; B5 (MCP gateway) calls the same components in-process. Attempting either before B3 would require stubs that would be thrown away.

### Why B4 and B5 are offered as parallel
They have no shared code and no dependency edge. The only coupling is the shared backend — but the backend is read-only for both of them at construction time.

## Go/No-Go Criteria

| Gate | Criterion |
|---|---|
| B1 → B2 | Docker image deploys at the jury URL; `POST /api/ingest` returns a structured batch; CI green |
| B2 → B3 | Detection run raises the correct alerts for at least 3 of the 7 planted scenarios (full acceptance test suite green at merge) |
| B3 → B4/B5 | AI review result is stored for at least one alert; `GET /api/ai/log` returns entries; CI green |
| B4/B5 → done | All 9 screens render for all 3 roles; MCP read tools return masked results; both CIs green |

## Sources

- [desc] Digital Fraud Investigation System — hackathon MVP
- [scope] mvp
- `inception/units-generation/unit-of-work.md`
- `inception/units-generation/unit-of-work-dependency.md`
- `inception/requirements-analysis/requirements.md`
