# Intent Backlog: Digital Fraud Investigation System

Inputs: `ideation/intent-capture/intent-statement.md`, `ideation/feasibility/feasibility-assessment.md`, `ideation/feasibility/constraint-register.md`, `scope-document.md`. Answers: `scope-definition-questions.md` Q1–Q6.

The proto-Units below are ordered by the value-first sequence (Q4). WSJF uses relative 1–10 scores. Cost of Delay = business value + time criticality + risk reduction, and WSJF = Cost of Delay ÷ size.

| ID | Proto-Unit | MoSCoW | Depends on | Value | Time crit. | Risk red. | Size | WSJF |
|---|---|---|---|---|---|---|---|---|
| IB-01 | Thin deployed slice: app runs locally and on the jury URL, accepts an upload | Must | none | 6 | 10 | 9 | 2 | 12.5 |
| IB-02 | Ingestion and validation: CSV, Excel and JSON; configurable column mapping; validation report; invalid records kept, never dropped | Must | IB-01 | 9 | 10 | 8 | 3 | 9.0 |
| IB-03 | Common data model and cross-system linking by customer, account, application, device and transaction IDs | Must | IB-02 | 8 | 9 | 7 | 3 | 8.0 |
| IB-04 | Detection: the four required scenarios, lookalike mitigation, plus the extra scenario (loan applications or duplicate claims) | Must | IB-03 | 10 | 10 | 6 | 4 | 6.5 |
| IB-05 | Risk scoring from several indicators, with the factors explained | Must | IB-04 | 9 | 10 | 5 | 2 | 12.0 |
| IB-06 | Alert dashboard: counts, risk distribution, categories, six filters, alert detail with reasons and records | Must | IB-05 | 9 | 10 | 4 | 3 | 7.7 |
| IB-07 | Case queue: unique case, decision recorded, original alert preserved, decision history | Must | IB-05 | 9 | 10 | 4 | 2 | 11.5 |
| IB-08 | PII masking, visible in the app and applied before any AI call or MCP response | Must | IB-03 | 8 | 8 | 9 | 2 | 12.5 |
| IB-09 | Hybrid AI decisions on flagged alerts: category, bounded risk adjustment, recommendation citing checked records, rule-based fallback | Must | IB-05, IB-08 | 9 | 8 | 5 | 4 | 5.5 |
| IB-10 | In-app AI logs: every AI call and agent step with model, tokens, latency and cost | Must | IB-09 | 6 | 7 | 6 | 2 | 9.5 |
| IB-11 | MCP server for Claude and other frontier models; reads free, consent before every write, same role checks and masking | Should | IB-07, IB-08 | 6 | 4 | 3 | 3 | 4.3 |
| IB-12 | Visual link graph of related entities | Could | IB-03 | 5 | 3 | 2 | 2 | 5.0 |
| IB-13 | Draft suspicious-transaction report for a case | Could | IB-07, IB-09 | 5 | 2 | 2 | 2 | 4.5 |
| IB-14 | Investigator feedback that tunes the rules | Could | IB-07 | 4 | 2 | 2 | 3 | 2.7 |

## Delivery Order

The order follows the dependencies (Q3) and the value-first sequence (Q4), with WSJF breaking ties within a step:

1. IB-01
2. IB-02, IB-03, IB-08
3. IB-04, IB-05
4. IB-07, IB-06
5. IB-09, IB-10
6. IB-11
7. Could-haves (IB-12, IB-13, IB-14), as time allows

## Milestone 1 Line

Every Must (IB-01 to IB-10) sits inside milestone 1's 3 hours (Q5, Q6). The team accepts the risk that the later Musts, IB-09 and IB-10, may land late. Should and Could items come after milestone 1.

## Assumptions & Open Questions

- [assumption] The WSJF scores are relative estimates by the product lead, not measured; they only break ties within the dependency order.
