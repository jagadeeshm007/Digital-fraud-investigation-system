# Units of Work

Inputs: `inception/domain-design/components.md` (13 components), `inception/domain-design/decisions.md` (ADR-001 to ADR-006), `inception/requirements-analysis/requirements.md`, `inception/user-stories/stories.md`. Plan: `units-generation-questions.md`.

| Unit ID | Directory | Kind | Components | Deployment | Complexity |
|---|---|---|---|---|---|
| U1 | u1-platform | service | ActivityStore, AccessAudit, Masking, Ingestion | Shared container | L |
| U2 | u2-detection-cases | service | LinkGraph, Detection, RiskScoring, Alerts, Cases, Dashboard | Shared container | XL |
| U3 | u3-ai-review | service | AiReview | Shared container | M |
| U4 | u4-web-console | ui | WebConsole | Static build served by the shared container | L |
| U5 | u5-mcp-gateway | service | McpGateway | Shared container (MCP endpoint) | M |

## U1 — u1-platform

- **Responsibilities:**
  - The common data model and its database schema (ActivityStore).
  - Roles, permission checks and the audit trail (AccessAudit).
  - PII masking and supervisor reveal (Masking).
  - File upload, column mapping, validation and rejected records (Ingestion).
  - The application skeleton: API server, configuration, one Dockerfile and `docker compose`.
- **Delivers:** the deployed app accepts an upload and shows a validation report (the scope's first step).
- **Notes:**
  - Money is stored as fixed-point INR.
  - Identifiers are stored as opaque strings.
  - Files are parsed with safe settings and a size limit.
  - Secrets come from the environment, never the repository.

## U2 — u2-detection-cases

- **Responsibilities:**
  - Cross-system links (LinkGraph).
  - The seven detection scenarios, lookalike clearing and rule settings (Detection).
  - Scoring and bands (RiskScoring).
  - Detection runs and immutable alerts (Alerts).
  - The case queue, decisions and history (Cases).
  - Dashboard figures (Dashboard).
- **Delivers:** the judged Level 1 core: detection, risk, alerts, cases and figures through the API.
- **Notes:**
  - Every planted scenario and lookalike gets an acceptance test (team practices).
  - Detection over 50,000 transactions finishes in under 60 seconds (NFR1).

## U3 — u3-ai-review

- **Responsibilities:** hybrid AI review on AlertRaised, citation validation, the ±10 bound, the rule-based fallback, the $10 budget, and the AI call log (AiReview).
- **Delivers:** AI recommendations and the AI activity log through the API.
- **Notes:**
  - Evidence always goes through Masking.
  - Tests use a fake model, so CI spends nothing.

## U4 — u4-web-console

- **Responsibilities:** all nine screens from the refined mockups, the role switcher and masked display.
- **Delivers:** the browser app, built by Vite+ and served as static files by the container.
- **Notes:**
  - Uses coss ui with the Azentio tokens, and React Flow for the entity graph.
  - Vitest and axe checks run in CI.

## U5 — u5-mcp-gateway

- **Responsibilities:** MCP read tools and consent-gated write tools, with masking, role checks and audit (McpGateway).
- **Delivers:** an MCP endpoint usable from Claude and other frontier models.
- **Notes:** no reveal tool exists. A write runs only after consent is approved.
