# Constraint Register: Digital Fraud Investigation System

Input: `ideation/intent-capture/intent-statement.md`. Answers: `feasibility-questions.md` Q1–Q8.

## Technical Constraints

| ID | Constraint | Source | Impact |
|---|---|---|---|
| TC-01 | Data arrives by upload or selection of CSV, Excel and JSON files in the organiser's formats | Q1 | Ingestion must map unknown schemas by configuration |
| TC-02 | Integrations go through adapters named after Azentio's products (alerts source, core banking source, channel events, case write-back), swappable for real APIs by configuration | Q1 | No direct coupling to any single data source |
| TC-03 | Stack: Python / FastAPI, Postgres on Supabase, Vite+ / React / TypeScript / coss ui with React Flow, LangGraph for the AI agent, paid model APIs | Q3 | Fixes the skills and tools later stages can assume |
| TC-04 | Heavy platform pieces such as mTLS / zero-trust networking and Langfuse are out of this version; observability stays in-app | intent statement (Q9, Q10) | Keeps deployment to one container |
| TC-05 | Rules and statistics produce the base score; AI may only adjust it within a bound and must cite supporting records; the rule-based result stands if AI is unavailable | intent statement (Q12) | AI is never a single point of failure |
| TC-06 | The same Dockerfile is used locally and on the deployed host | Q8 | One build artifact for local and deployed runs |

## Organisational Constraints

| ID | Constraint | Source | Impact |
|---|---|---|---|
| OC-01 | Hackathon day 2026-10-31, build window 11:00 to 18:00, Level 1 in about 3 hours, submission closes 18:00 | Q5 | Scope must be cut to fit Level 1 first |
| OC-02 | Later levels unlock only after the current one is cleared | Q5 | Each level must work on its own |
| OC-03 | The organiser checks rules on pre-written code at check-in | Q6 | What exists in the repository before the clock starts may be limited |
| OC-04 | AI spend is capped at $10 total, enforced as a credit limit on the API key | Q4 | AI runs only where it adds value |
| OC-05 | A deployed public HTTPS URL must be provided to the jury | Q7, Q8 | Deployment is part of the deliverable, not an extra |

## Regulatory Constraints

| ID | Constraint | Source | Impact |
|---|---|---|---|
| RC-01 | Synthetic or properly anonymised data only: no real customer PII, production credentials or real payments | Q2 | All demo data is generated |
| RC-02 | The prototype is not certified for regulatory compliance, but follows Indian banking practice (RBI, FIU-IND) where it can | Q2 | Shapes terminology and reports, not certification work |
| RC-03 | PII is masked before any AI call or MCP response | Q2 | Masking sits in front of every outbound path |

## Assumptions & Open Questions

- [assumption] Hosting and Supabase free or low-cost tiers impose no limit that blocks judging.
