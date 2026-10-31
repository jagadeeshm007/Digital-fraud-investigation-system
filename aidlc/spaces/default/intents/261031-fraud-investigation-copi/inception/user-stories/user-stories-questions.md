# User Stories — Story Plan and Questions

Input: `inception/requirements-analysis/requirements.md` (FR1–FR12, NFR1–NFR13).

## Story Plan

- **Format:** "As a [persona], I want [goal], so that [benefit]", following INVEST. Acceptance criteria use Given/When/Then, with IDs `US{group}.{seq}` and `AC{group}.{seq}.{n}`.
- **Prioritisation:** MoSCoW per story, drawn from the scope document. The MVP boundary is confirmed at Delivery Planning.

## Q1. [Product owner] Which personas should the stories be written for?

A. Three primary personas matching the roles: Fraud Analyst, Fraud Investigator, Fraud Supervisor. Plus one secondary persona: an Investigator working through Claude or another model over MCP.
B. The three role personas only
C. One generic "fraud team user"
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. [Product owner] How should the stories be broken down?

A. By the investigator's workflow, grouped into epics that follow the requirement areas: load data, link and detect, score risk, AI review, dashboard, cases, roles and audit, data safety, AI log, MCP, deployment
B. By persona
C. By screen
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. [Developer] How large should each story be?

Context: milestone 1 has 3 hours, so story size drives how the work can be split.

A. One story per meaningful user outcome, sized to about 30–60 minutes of build each, roughly 25–35 stories in total
B. Fewer, larger stories (about 10–12)
C. Very fine-grained stories (50 or more)
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. [Product owner] How should story priorities be set?

A. Follow the scope's MoSCoW. Must: the Level 1 journey, PII masking, hybrid AI, AI log, deployment. Should: MCP. Could: the graph explorer, a draft suspicious-transaction report, rule tuning from feedback.
B. Re-prioritise from scratch
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Consolidated Summary Confirmation

- Personas: Fraud Analyst, Fraud Investigator and Fraud Supervisor, plus an Investigator working through Claude or another model over MCP (Q1).
- Breakdown: by the investigator's workflow, in epics following the requirement areas (Q2).
- Size: one story per meaningful outcome, about 30–60 minutes each, roughly 25–35 stories (Q3).
- Priority: the scope's MoSCoW. Must: the Level 1 journey, masking, hybrid AI, AI log, deployment. Should: MCP. Could: graph explorer, draft report, rule tuning from feedback (Q4).

Does this all look correct?

- Looks correct
- Request changes

[Answer]: Looks correct
