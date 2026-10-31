# Domain Design — Questions

Inputs: `inception/requirements-analysis/requirements.md`, `inception/user-stories/stories.md`, `inception/practices-discovery/team-practices.md`.

The person left this stage's questions to the architect ("don't ask, assume with what you have"). Each answer is the architect's choice, drawn from the approved upstream artifacts.

## Q1. [Architect] Where are the main component boundaries?

A. Separate components for loading data (Ingestion), the common activity model (ActivityStore), cross-system links (LinkGraph), detection rules (Detection), risk scoring (RiskScoring), alerts (Alerts), AI review (AiReview), masking (Masking), cases (Cases), roles and audit (AccessAudit), dashboard read model (Dashboard), MCP (McpGateway) and the web console (WebConsole)
B. Fewer, larger components (ingest, detect, cases, UI)
X. Other (please specify)

[Answer]: A (architect's choice, left to the architect)

## Q2. [Architect] Who owns the alert and the case decisions?

A. Alerts owns the Alert and never changes it after creation; Cases owns Case and CaseDecision (history); AiReview owns its own review results and never edits the Alert
B. One component owns alerts and decisions together
X. Other (please specify)

[Answer]: A (architect's choice, left to the architect)

## Q3. [Architect] How do components interact?

A. Synchronous calls inside the application, with one event: when an alert is raised, AiReview picks it up in the background (so alerts appear before AI finishes, NFR2)
B. Everything synchronous
X. Other (please specify)

[Answer]: A (architect's choice, left to the architect)

## Q4. [Designer] How is the UI structured?

A. One WebConsole component with a page per screen from the refined mockups, calling the other components through the application's API
X. Other (please specify)

[Answer]: A (architect's choice, left to the architect)
