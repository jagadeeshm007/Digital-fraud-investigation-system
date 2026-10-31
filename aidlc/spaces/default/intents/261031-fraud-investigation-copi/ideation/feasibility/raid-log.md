# RAID Log: Digital Fraud Investigation System

Input: `ideation/intent-capture/intent-statement.md`. Answers: `feasibility-questions.md` Q1–Q8. Constraints: `constraint-register.md`.

## Risks

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | Level 1 journey not finished in about 3 hours | Medium | High | Build the judged journey first; add AI explanations after it works end to end | Team |
| R2 | Organiser schema differs from our model, so hidden tests fail at ingestion | Medium | High | Map columns by configuration; report every rejected record with row, field and reason | Team |
| R3 | Legitimate lookalikes get flagged (false positives) | Medium | High | Mitigating signals for customer history and household device sharing; planted lookalike cases in test data | Team |
| R4 | AI spend exceeds the $10 cap | Low | Medium | AI only on flagged alerts; token cap per alert; credit limit on the API key | Team |
| R5 | AI output is non-deterministic or cites records that do not exist | Medium | Medium | Bounded risk adjustment; check that every cited record exists; rule-based fallback | Team |
| R6 | PII reaches an AI model or MCP client | Low | High | Mask known PII fields; scan free text; no unmask path over MCP | Team |
| R7 | Deployed URL is slow or asleep during judging | Medium | Medium | Warm it before judging; keep a recorded backup demo | Team |
| R8 | Vite+ toolchain blocks the frontend build | Low | Medium | Fall back to plain Vite; app code is unchanged | Team |
| R9 | Pre-written code rules disallow prepared code | Medium | Medium | Confirm the rules at check-in; keep anything doubtful out of the repository until the clock starts | Team |

## Assumptions

| ID | Assumption | Validate by |
|---|---|---|
| A1 | The organiser's data carries identifiers that link records across systems | Reading the sample data at the briefing |
| A2 | Managed host and Supabase free or low-cost tiers are enough for judging traffic | A test deployment before judging |
| A3 | Pre-written code rules allow the data generator and project setup to exist before the clock | Asking at check-in |
| A4 | A small paid model is accurate enough to categorise alerts and recommend decisions | Running it on the planted scenarios |

## Issues

| ID | Issue | Status |
|---|---|---|
| I1 | The organiser's actual schemas, sample data and hidden-test format are not yet known | Open until the briefing |

## Dependencies

| ID | Dependency | Needed for |
|---|---|---|
| D1 | Organiser schemas, sample data and rubric | Ingestion mapping and hidden tests |
| D2 | Supabase project with a working connection string | All data storage |
| D3 | Paid model API key with a $10 credit limit | Hybrid AI decisions and explanations |
| D4 | Managed container host account | Deployed jury URL |

## Assumptions & Open Questions

- [assumption] Assumptions A1 to A4 above are unvalidated until the briefing, a test deployment and a first AI run.
