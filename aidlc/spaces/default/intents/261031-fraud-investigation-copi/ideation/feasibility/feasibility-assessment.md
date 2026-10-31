# Feasibility Assessment: Digital Fraud Investigation System

Input: `ideation/intent-capture/intent-statement.md` (problem, users, success metrics, AI role, scope signal). Answers: `feasibility-questions.md` Q1–Q8.

## Verdict

**Feasible, with a tight timeline.** Each capability the intent statement asks for can be built with the team's chosen stack and skills (Q3). The main risk is time: Level 1 is about 3 hours (Q5), and the full journey (ingest, validate, detect, assess risk, dashboard, case queue) plus visible AI, PII masking and a deployed URL is a lot for 3 hours. The plan has to put the judged Level 1 journey first and keep AI and the MCP server off the critical path.

## Capability Viability

| Capability (from the intent statement) | Viability | Why | Main risk |
|---|---|---|---|
| Ingest and validate CSV, Excel and JSON in the organiser's formats | High | Standard parsing in Python; validation reports are deterministic | The organiser's schema is unknown until the day (Q1) |
| Link records across systems (customer, account, application, device, transaction) | High | A common data model plus a link graph over shared identifiers | Identifier formats may differ between files |
| Detect the four required scenarios plus one extra | High | Rules and statistics over the linked data; the team knows the domain | Hidden tests may probe edge cases we did not plant |
| Avoid flagging legitimate lookalikes | Medium | Needs mitigating signals (customer history, household sharing), not just thresholds | Tuning takes time to get right |
| Risk score with explained factors | High | Weighted factors with a visible breakdown | None significant |
| Alert dashboard with filters and alert detail | High | Standard web UI over the stored alerts | UI time competes with detection time |
| Case queue with preserved original alerts | High | Alerts stored unchanged; decisions kept as history | None significant |
| Hybrid AI decisions (category, bounded risk adjustment, recommendation) | Medium | Team has LangGraph experience (Q3); budget is $10 (Q4) | Model latency and cost per alert; non-deterministic output |
| PII masking visible in the app | High | Known PII fields can be masked before any AI call or MCP response (Q2) | Free-text fields can still leak PII |
| In-app AI logs and observability | High | Each AI call is logged with model, tokens, latency and cost | None significant |
| MCP server with consent-gated writes | Medium | Supported by standard MCP SDKs; reuses the app's own operations | Client support for consent prompts varies |
| Deployed public URL for the jury | Medium | One container on a managed host, Postgres on Supabase (Q7, Q8) | Free tiers sleep when idle and may cold-start during judging |

## Risk Analysis

- **Timeline (High).** Level 1 has about 3 hours (Q5). Mitigation: build the judged journey first, with AI explanations added after it works end to end. Synthetic data with planted scenarios is prepared within whatever the pre-written code rules allow (Q6).
- **Unknown organiser schema (High).** Hidden tests run on the organiser's data (Q1). Mitigation: map columns through configuration rather than code, and report every rejected record with its row, field and reason so nothing is silently dropped.
- **AI budget (Medium).** The total is $10 (Q4). Mitigation: run AI only on flagged alerts, not on every record. Set a token cap per alert, enforce the limit as a credit limit on the API key, and always keep the rule-based result as the fallback.
- **AI non-determinism vs explainability (Medium).** Judges reward observable behaviour, not standalone AI output. Mitigation: AI may only adjust risk within a fixed range around the rule-based score, and must cite supporting records that the app checks exist.
- **PII leakage (Medium).** Mitigation: mask known PII fields before any AI call or MCP response, and scan free text as a second check (Q2).
- **Deployment cold start (Medium).** Mitigation: warm the deployed URL before judging, and keep a recorded backup demo.
- **New frontend toolchain (Low).** Vite+ is recent. Mitigation: the code stays the same if plain Vite is used instead.

## Conservative Estimates

These are estimates, not measurements.

- Level 1 journey without AI: about 2.5 of the 3 hours, leaving little slack.
- AI cost per flagged alert: a few cents or less on a small paid model, so the $10 budget covers several hundred AI reviews if they run only on flagged alerts.
- Deployment setup: about 30 minutes the first time, if done before the build clock where the rules allow.

## Assumptions & Open Questions

- [assumption] The organiser's sample data contains the identifiers needed to link records across systems (customer, account, application, device or transaction IDs), as the challenge describes.
- [assumption] The chosen container host's free or low-cost tier is enough for judging traffic.
- [assumption] The organiser's rules on pre-written code allow at least the data generator and project setup to exist before the build clock starts (Q6).
