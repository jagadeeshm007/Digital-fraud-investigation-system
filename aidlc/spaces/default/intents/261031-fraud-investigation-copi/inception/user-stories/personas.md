# Personas

Input: `inception/requirements-analysis/requirements.md` (FR8.1 roles, FR11 MCP), `user-stories-questions.md` Q1.

## P1 Fraud Analyst — "Asha the Analyst"

- **Role:** first-line triage of alerts (FR8.1 Analyst).
- **Goals:** clear the queue quickly; tell real fraud from lookalikes; record an initial decision with a reason.
- **Pain points:** most alerts are false positives; evidence sits in separate screens.
- **Can:** view everything (masked), load data, run detection, record Requires Investigation or False Positive.
- **Cannot:** escalate, reveal masked values, change rules.
- **Tech comfort:** medium. **Frequency:** all day, every day.

## P2 Fraud Investigator — "Vikram the Investigator"

- **Role:** second-line review of cases (FR8.1 Investigator).
- **Goals:** see every linked record across lending, insurance and core banking in one place; understand why the risk is high; escalate real fraud.
- **Pain points:** cross-system links are invisible; writing up evidence takes longer than deciding.
- **Can:** everything the Analyst can, plus Escalate.
- **Tech comfort:** high. **Frequency:** daily.

## P3 Fraud Supervisor — "Meera the Supervisor"

- **Role:** oversight and configuration (FR8.1 Supervisor).
- **Goals:** decisions that can be explained to auditors; tune rules as fraud patterns change; reveal real identities only when acting on a case.
- **Pain points:** hard-to-explain past decisions; rules that need a developer to change.
- **Can:** everything the Investigator can, plus reveal masked values (audited) and change rule settings (audited).
- **Tech comfort:** medium. **Frequency:** daily reviews.

## P4 Investigator via AI assistant — "Vikram in Claude"

- **Role:** P2 working through Claude or another frontier model over the MCP server (FR11).
- **Goals:** ask questions about alerts and cases in plain language; record a decision without switching tools.
- **Pain points:** switching between chat and the case tool.
- **Can:** read through MCP with the same role permissions; perform a write only after explicitly consenting to that specific action.
- **Tech comfort:** high. **Frequency:** occasional.

## Relationships and Priority

- P2 is the primary persona: the core journey is built around the investigator's day (intent statement).
- P1 shares P2's screens with fewer permissions.
- P3 adds oversight: reveal and rule settings.
- P4 is P2 using a different channel (Should priority).

Priority ranking: P2, P1, P3, P4.

All persona names are fictional.
