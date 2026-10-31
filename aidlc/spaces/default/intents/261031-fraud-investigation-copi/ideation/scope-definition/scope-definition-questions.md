# Scope Definition — Questions

Inputs: `ideation/intent-capture/intent-statement.md`, `ideation/feasibility/feasibility-assessment.md`, `ideation/feasibility/constraint-register.md`, `ideation/feasibility/raid-log.md`.

## Q1. [Product owner] What is the minimum viable scope that delivers value?

Context: the feasibility assessment found Level 1 tight at about 3 hours, so this sets the smallest version worth showing.

A. The full Level 1 journey: ingest and validate data, link records across systems, detect the four required scenarios plus one extra, score risk with explained factors, show the dashboard with filters and alert detail, run the case queue with preserved alerts. Plus visible PII masking and a deployed URL for the jury.
B. Option A plus hybrid AI decisions on flagged alerts, all inside the minimum
C. Detection and the alert list only
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q2. [Product owner] Which capabilities are must-have, should-have, could-have and won't-have?

Context: a proposed split, so you can confirm or move items.

A. Must: the Level 1 journey, PII masking, the deployed URL, hybrid AI decisions on flagged alerts, in-app AI logs. Should: the MCP server with consent-gated writes. Could: the visual link graph, a draft suspicious-transaction report, investigator feedback that tunes the rules. Won't (this version): mTLS / zero-trust networking, Langfuse, real integrations.
B. As A, but the MCP server is a must too
C. As A, but hybrid AI decisions are a should, not a must
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. [Architect] What are the dependencies between capabilities?

A. Ingestion and the common data model come first. Detection depends on them, risk scoring on detection, and alerts and cases on risk. The dashboard needs alerts. Hybrid AI decisions need alerts and PII masking. The MCP server needs the app's own operations and the consent step. Deployment depends only on the app being runnable.
B. The capabilities are independent and can be built in any order
C. Not sure; work it out during design
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. [Product owner] What sequencing do you prefer?

A. Value-first along the judged path. First, a thin end-to-end slice that is deployed and accepts an upload. Then detection, risk, dashboard and cases. Then hybrid AI. Then the MCP server.
B. Risk-first: build the hybrid AI part first, because it is the least certain
C. Strict dependency order, layer by layer
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. [Product owner] Are there hard deadlines tied to specific capabilities?

A. The Level 1 journey must work about 3 hours after the 11:00 start (around 14:00). Feature freeze is around 17:00 for the backup video. The deployed URL and HackCulture submission are due by 18:00.
B. Only the 18:00 submission deadline
C. No hard deadlines
D. Not yet defined
X. Other (please specify)

[Answer]: X. Other. Exact words: "we have 3 hr to complete milestone 1". Corrected: We have 3 hours to complete milestone 1.

## Q6. [Product owner] What gives if milestone 1 cannot fit everything in 3 hours?

Context: you put hybrid AI decisions inside the minimum scope (Q1), and milestone 1 has 3 hours (Q5). The feasibility assessment estimated the Level 1 journey alone at about 2.5 hours, so hybrid AI on top may not fit.

A. Milestone 1 delivers the Level 1 journey with rule-based results, built so AI plugs in. Hybrid AI decisions follow straight after as the first work once milestone 1 is cleared. AI stays a must for the product, just not for the 3-hour mark.
B. Keep hybrid AI in milestone 1 and trim elsewhere: a simpler dashboard and only the one required extra scenario
C. Keep everything in milestone 1 and accept the risk of not finishing
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Consolidated Summary Confirmation

- Minimum viable scope: the full Level 1 journey (ingest and validate, link records, detect four required scenarios plus one extra, explained risk, dashboard with filters and alert detail, case queue with preserved alerts) plus hybrid AI decisions on flagged alerts, visible PII masking and a deployed URL (Q1).
- Must: Level 1 journey, PII masking, deployed URL, hybrid AI on flagged alerts, in-app AI logs. Should: MCP server with consent-gated writes. Could: visual link graph, draft suspicious-transaction report, investigator feedback that tunes rules. Won't (this version): mTLS / zero-trust networking, Langfuse, real integrations (Q2).
- Dependencies: ingestion and data model, then detection, risk, alerts and cases, then dashboard; hybrid AI needs alerts and masking; MCP needs the app's operations and consent; deployment needs only a runnable app (Q3).
- Sequencing: value-first along the judged path; a thin deployed slice that accepts an upload first, then detection, risk, dashboard and cases, then hybrid AI, then MCP (Q4).
- Deadline: 3 hours to complete milestone 1 (Q5); everything, including hybrid AI, stays in milestone 1 and the team accepts the risk of not finishing (Q6).

Does this all look correct?

- Looks correct
- Request changes

[Answer]: Looks correct
