# Architecture Decision Records — Domain Design

Inputs: `inception/requirements-analysis/requirements.md`, `inception/user-stories/stories.md`, `inception/practices-discovery/team-practices.md`, `components.md`.

## ADR-001: Fine-grained components with separate Detection, RiskScoring and Alerts

- **Context.** The rules change often (FR3.8) and risk must be explained (FR4.3). Alerts must stay unchanged once raised (FR7.4), and everything is built tests-first (team practices). Mixing rule evaluation, scoring and alert storage would make each harder to test and change.
- **Decision.** Split into Detection (signals), RiskScoring (pure scoring) and Alerts (runs and immutable alerts), alongside the other components in `components.md`.
- **Consequences.** Each part is unit-testable alone, and a rule change cannot alter stored alerts. The cost is more modules and interfaces to wire up within a tight timeline.
- **Security and compliance.** Keeping scoring pure means no PII leaves through it.
- **Alternatives Rejected.** A coarse four-component split (ingest, detect, cases, UI). It is faster to scaffold, but it entangles rule changes with stored alerts and makes scoring hard to test.

## ADR-002: Alerts are immutable; Cases owns decisions and history

- **Context.** The original alert must be preserved even when the classification changes (FR7.4), and auditors need full history (FR7.3).
- **Decision.** Alerts never updates an Alert after creation. Cases owns Case and CaseDecision as an append-only history, with status before and after each decision.
- **Consequences.** Audit is straightforward and nothing is lost. The current status is derived from the latest decision.
- **Security and compliance.** History entries record the role and channel, never unmasked PII.
- **Alternatives Rejected.** A mutable alert status field, which loses the original classification. Storing decisions on the alert, which mixes two lifecycles.

## ADR-003: AI review is its own component, triggered by an event, storing results apart from the Alert

- **Context.**
  - AI must take part in decisions (intent statement) but never block alerts (FR5.3, NFR6).
  - Each AI review must finish in under 15 seconds in the background (NFR2).
  - The AI adjustment is bounded to ±10 points (FR5.1).
  - AI spend is capped at $10 (NFR8).
- **Decision.**
  - Alerts emits AlertRaised. AiReview consumes it, sends masked evidence to the model, and validates the citations and the bound.
  - The result goes into its own AiReviewResult. The final score is base plus the validated adjustment.
- **Consequences.**
  - Alerts appear immediately, and AI failure or budget exhaustion leaves the rule-based score standing.
  - Showing the final score means joining two components.
- **Security and compliance.**
  - Evidence passes through Masking first.
  - Data text is treated as data, defending against prompt injection.
  - Every call is logged.
- **Alternatives Rejected.**
  - Synchronous AI inside the detection run: slow, and it fails together with the provider.
  - AI writing the Alert directly: this would break immutability and the bound.

## ADR-004: One Masking component on every outbound path

- **Context.** The project rule says to always mask PII before any AI model call or MCP response. The UI must show masked values by default, with supervisor-only reveal (FR9).
- **Decision.**
  - Masking is the single component that masks values for the UI, AI, MCP and logs. It uses stable tokens.
  - Reveal is possible only through the app, for a Supervisor, and is audited.
- **Consequences.** One place to test and to prove the rule. Every outbound path must call it, which is checked by tests.
- **Security and compliance.** No reveal path exists over AI or MCP.
- **Alternatives Rejected.** Masking inside each consumer, which risks a path being missed. Masking only at the UI, which would let PII leak to AI and MCP.

## ADR-005: Ingestion maps organiser schemas through configuration

- **Context.** The organiser's schemas are unknown until the briefing, and hidden tests use their data (FR1.3). Azentio's products are the future data sources.
- **Decision.** Ingestion acts as an anti-corruption layer. A per-source SourceMapping maps file columns onto the ActivityStore model.
- **Consequences.** A new schema is a configuration change. A real Azentio adapter would later replace file reading behind the same mapping.
- **Security and compliance.** Files are parsed with safe settings and a size limit (NFR4).
- **Alternatives Rejected.** Hard-coded column names, which break on the organiser's schema. A generic schema-inference engine, which is too slow to build within the timeline.

## ADR-006: MCP reuses the app's components, with consent as its own entity

- **Context.** Claude and other models must read freely but write only with consent, under the same role checks and masking (FR11).
- **Decision.** McpGateway calls the same components as the WebConsole. Each write creates a ConsentRequest, and the write runs only on an approved outcome. Every call goes through AccessAudit and Masking.
- **Consequences.** There is no duplicated business logic, and consent decisions are auditable.
- **Security and compliance.** MCP has no reveal tool. Writes cannot bypass consent or role checks.
- **Alternatives Rejected.** A separate MCP backend, which would duplicate logic and checks. Writes without consent, which is against FR11.2.
