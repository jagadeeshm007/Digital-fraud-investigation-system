# Unit to Story Map

Inputs: `inception/user-stories/stories.md`, `inception/domain-design/components.md`, `inception/domain-design/decisions.md`, `inception/requirements-analysis/requirements.md`, `unit-of-work.md`.

| Story | Unit | Directory |
|---|---|---|
| US1.1 | U1; U4 | u1-platform; u4-web-console |
| US1.2 | U1; U4 | u1-platform; u4-web-console |
| US1.3 | U1; U4 | u1-platform; u4-web-console |
| US1.4 | U1; U4 | u1-platform; u4-web-console |
| US1.5 | U1 | u1-platform |
| US2.1 | U2; U4 | u2-detection-cases; u4-web-console |
| US2.2 | U2 | u2-detection-cases |
| US2.3 | U2 | u2-detection-cases |
| US2.4 | U2 | u2-detection-cases |
| US2.5 | U2 | u2-detection-cases |
| US2.6 | U2 | u2-detection-cases |
| US2.7 | U2 | u2-detection-cases |
| US2.8 | U2 | u2-detection-cases |
| US2.9 | U2; U4 | u2-detection-cases; u4-web-console |
| US3.1 | U2 | u2-detection-cases |
| US3.2 | U2; U4 | u2-detection-cases; u4-web-console |
| US4.1 | U3; U4 | u3-ai-review; u4-web-console |
| US4.2 | U3; U4 | u3-ai-review; u4-web-console |
| US4.3 | U3 | u3-ai-review |
| US5.1 | U2; U4 | u2-detection-cases; u4-web-console |
| US5.2 | U2; U4 | u2-detection-cases; u4-web-console |
| US5.3 | U4 | u4-web-console |
| US6.1 | U2 | u2-detection-cases |
| US6.2 | U2; U4 | u2-detection-cases; u4-web-console |
| US6.3 | U2; U4 | u2-detection-cases; u4-web-console |
| US7.1 | U1; U4 | u1-platform; u4-web-console |
| US7.2 | U1; U4 | u1-platform; u4-web-console |
| US8.1 | U1; U4 | u1-platform; u4-web-console |
| US8.2 | U1; U4 | u1-platform; u4-web-console |
| US8.3 | U1; U3; U5 | u1-platform; u3-ai-review; u5-mcp-gateway |
| US9.1 | U3; U4 | u3-ai-review; u4-web-console |
| US9.2 | U3; U4 | u3-ai-review; u4-web-console |
| US10.1 | U5 | u5-mcp-gateway |
| US10.2 | U5 | u5-mcp-gateway |
| US11.1 | U1 | u1-platform |

## Cross-Cutting Rows

- **US8.3 (masking on every outbound path):** touches U1 (Masking), U3 (AI calls) and U5 (MCP responses).
- **Role and audit checks (US7.1, US7.2):** live in U1 and are used by every unit.

## Implementation Order Within Each Unit

- **U1:** app skeleton and deployment (US11.1); data model; Ingestion (US1.1–US1.5); AccessAudit (US7.1, US7.2); Masking (US8.1–US8.3).
- **U2:** LinkGraph (US2.1); detection rules (US2.2–US2.8); lookalikes (US2.5); scoring (US3.1, US3.2); alerts; cases (US6.1–US6.3); rule settings (US2.9); dashboard figures (US5.1, US5.2).
- **U3:** review flow (US4.1); fallback (US4.2); injection guard (US4.3); AI log and spend (US9.1, US9.2).
- **U4:** shell and role switcher; Data Upload; Dashboard; Alerts; Alert Detail; Cases; AI Activity; Data Safety; Audit Trail.
- **U5:** read tools (US10.1); consent-gated writes (US10.2).

## Coverage Verification

All 35 stories are assigned, and every unit has rows.
