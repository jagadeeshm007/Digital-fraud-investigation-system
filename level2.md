# Level 2: Investigate, Correlate and Manage Fraud Cases

Suggested time: 3 to 5.5 hours. Level 2 must be submitted and accepted before Level 3 can begin.

**Objective.** Extend the Level 1 detection app into an investigation system. It must connect related
activity across lending, insurance and core banking, support analyst decisions, and recommend actions.

**Expected submission.** One integrated application with:
- cross-system correlation
- relationship visualisation
- consolidated cases
- analyst workflows
- evidence management

---

## Where Level 1 leaves us

| Already built | Where |
|---|---|
| R1 to R6 alerts with explained factors and evidence ids | `app/detection/` |
| Correlation bonus (+15 per extra rule family, max 30) | `app/detection/engine.py` |
| Entity graph (customer, account, transaction, device, IP, login, beneficiary change, loan, claim, alert) | `app/graph/builder.py`, `/api/graph/*`, React Flow `EntityGraph.tsx` |
| Linked records for any entity | `/api/links/{entity_id}` |
| Evidence ids resolved to masked records | `app/evidence.py` |
| One case per Medium/High alert. Decisions: requires investigation, false positive, escalate. Reason required | `app/api/detection.py` |
| Case history and audit trail (role, channel, timestamp) | `case_history`, `audit_log` |
| AI review (adjustment of ±10 at most, cites evidence only) and an AI call log | `app/ai/review.py` |
| Role-based PII masking; Supervisor reveal | `app/masking.py`, case screen |
| MCP: read tools, plus writes that need the user's consent | `app/mcp_server.py` |

**Main gap.** A case is still one alert. Level 2 makes a case an **investigation** that holds many
alerts. That one change drives most of the requirements below.

---

## Required capabilities, gaps and plan

### 1. Cross-system fraud correlation

**Requirement.** Link suspicious activity across lending, insurance and core banking.

- **Example:** a loan applied for from a device shared by several identities, with the proceeds paid
  into a recently changed account and then sent to an unfamiliar beneficiary. This is **one**
  investigation, not three alerts.
- **Entities to support:** customers, accounts, devices, IPs, phones, applications, transactions,
  policies and claims.

**Gap.** Alerts are only linked by a score bonus. Nothing groups them.

**Plan.**
- After detection, pull each open alert's identifiers from its evidence records: customer, account,
  device, IP, phone, application, transaction, policy and claim.
- Union alerts that share an identifier, using union-find over identifier → alerts.
- Each group becomes one investigation.
- Store *which identifier* joined each pair, so every link has a concrete match behind it.
- Add a planted scenario for the brief's example, if the sample data doesn't already cover it end to
  end: device ring → loan → proceeds into a recently changed account → transfer to a new
  beneficiary.

**Done when.**
- The planted example produces one investigation that contains loan, account-change and transfer
  alerts.
- Every link names its matching identifier.

### 2. Fraud relationship analysis (visual)

**Requirement.**
- A network view of customers, devices, applications and transactions.
- Clicking an entity shows its records.
- Links must come from matching identifiers or documented evidence, **never from the AI**.

**Gap.** The graph exists per alert or entity. There is no case-level graph, and clicking a node
doesn't show its records.

**Plan.**
- `GET /api/graph/case/{case_id}`: the union of the graphs of the case's alerts.
- Label each edge with the identifier that matches.
- Clicking a node opens a side panel with the masked records from `/api/links/{id}`.

**Done when.**
- The case graph renders.
- Every edge has a matching-identifier label.
- Clicking a node lists its records.
- No edge comes from the LLM.

### 3. Intelligent case consolidation

**Requirement.**
- Group alerts that belong to the same suspected fraud.
  - **Example:** failed logins, then a new-device login, then a suspicious transfer form one
    account-takeover investigation.
- Explain why the alerts were grouped.
- Let an analyst **split** a wrongly grouped alert out.
- Keep the original alerts and their evidence.

**Gap.** There's one case per alert, and no split.

**Plan.**
- New table `case_alerts(case_id, alert_id, link_reason, linked_at)`.
- `cases.alert_id` stays as the primary alert.
- Each grouping reason is stored as text built from the shared identifiers, for example
  "shares device D-77 with alert X".
- `POST /api/cases/{id}/split {alert_id, reason}` moves the alert into a new case. Alerts are never
  deleted, and the split is audited.

**Done when.**
- The ATO sequence becomes one case with its grouping reason shown.
- A split creates a new case, and both cases still show their alerts and evidence.

### 4. Fraud investigation workspace

**Requirement.** A detailed case view with:
- a timeline of events
- affected entities
- fraud indicators
- supporting evidence
- risk assessment
- investigation notes

**Analyst actions:**
- Confirm that the activity needs further investigation.
- Mark it a false positive, with a reason.
- Request additional information.
- Escalate to a fraud specialist or supervisor.
- Recommend a temporary hold or enhanced verification.
- Record an investigation conclusion.

**Rule.** Actions that affect customer accounts or transactions stay *recommendations* unless an
authorised workflow explicitly approves them.

**Gap.**
- The case screen has three decisions and a history list.
- Missing: timeline, entities, notes, request info, hold or verification recommendations, and a
  conclusion.

**Plan.**
- **Workspace tabs:** Timeline (evidence records sorted by time), Entities, Indicators (factors from
  every alert), Evidence, Risk, Notes.
- **New decisions:** `request_info`, `recommend_hold`, `recommend_verification`, `conclude`.
  - Each needs a reason or conclusion text.
- **Notes:** a `case_notes` table.
- **Recommendations:**
  - A hold or verification recommendation creates a `recommendation` row with status `pending`.
  - A **Supervisor** approves or rejects it (maker-checker: the maker can't approve their own).
  - No account or transaction is changed in any case. "Approved" only records the authorisation.

**Done when.**
- All 6 actions work from the UI.
- A hold stays "recommended" until a different user with the Supervisor role approves it.

### 5. Evidence management and audit trail

**Requirement.** Every case keeps an evidence history:
- source records
- detected indicators
- AI assessments
- analyst corrections
- decisions
- timestamps
- user identity

**Rule.** If an analyst changes a risk classification or dismisses an alert, keep the **original**
classification and the reason it changed.

**Download.** Evidence must download as a structured case report.

**Gap.**
- There's no way to override risk, so there's no original to keep.
- There's no report download.
- AI assessments sit on the alert but aren't part of the case history.

**Plan.**
- `PATCH /api/cases/{id}/risk {risk_level, reason}` writes `risk_original`, `risk_level`, the reason
  and the user.
- `GET /api/cases/{id}/report` returns JSON with:
  - the case
  - its alerts and factors
  - the evidence records (masked)
  - AI reviews
  - history
  - notes
  - recommendations
  - audit rows
- A frontend button downloads the report.
- Optional: a printable HTML/PDF view.

**Done when.**
- After a risk override, the report shows the original classification, the new one and the reason.
- The report downloads from the UI.

### 6. Fraud prioritisation

**Requirement.** Rank cases by four factors:
- severity
- financial exposure
- number of related events
- confidence in the detection

**Example.** A large transfer plus recent ATO indicators ranks above a lone failed login.

**Rule.** Weak evidence → mark the case *needs review*, never automatically top priority.

**Gap.** Cases are only banded Low, Medium or High per alert.

**Plan.** `priority_score` (0 to 100) is computed when a case is built or changed.

| Part of the score | How it's measured |
|---|---|
| Severity | The highest final score among the case's alerts |
| Exposure | The sum of transaction, loan and claim amounts in the evidence, on a log scale |
| Related events | The number of alerts and evidence records |
| Confidence | The share of factors backed by evidence, and whether AI agrees |

- **Needs review:** if the case has one factor, low confidence or no amount evidence, set
  `needs_review = true` and cap the priority.
- **Case queue:** sorted by priority, with a "needs review" filter.

**Done when.**
- The ATO plus large-transfer case ranks above an isolated failed-login case.
- A single weak alert shows "needs review".

---

## Cross-cutting rules (Level 1 rules still apply)

- **PII:** masked in every API response, AI call and MCP response. Supervisor reveal works in the app
  only.
- **AI:** can comment on, but never create, links or groupings. The AI adjustment stays capped at ±10.
- **Money:** `Decimal(14,2)`. All timestamps carry a timezone.
- **MCP:** the new read tools (`get_case_report`, `get_case_graph`) are read-only. New writes (note,
  split, recommendation) must ask for the user's consent, like the existing ones.

## Build order

1. Data model: `case_alerts`, `case_notes`, `recommendations`, plus risk-override and priority
   columns. Tests first.
2. Correlation and consolidation in the detection engine, including grouping reasons and split.
   Acceptance tests on the planted scenarios.
3. Prioritisation and needs-review flag, and a sorted case queue.
4. Workspace API: new decisions, notes, recommendations with supervisor approval, risk override,
   report.
5. Frontend workspace: Timeline, Entities, Indicators, Evidence, Risk, Notes and actions. Case graph
   with a side panel for the selected node. Report download.
6. MCP: the new read tools and the consent-gated writes.
7. Re-run all tests and the MCP e2e. Deploy to Vercel and check by hand.

## Acceptance tests to add (`tests/test_level2.py`)

- **Correlation:** the cross-system scenario produces one investigation with loan, account-change and
  transfer alerts, and every link has a matching identifier.
- **ATO consolidation:** failed logins, then a new-device login, then a transfer give one case with a
  grouping reason.
- **Split:** the alert moves to a new case. The originals and their evidence are kept, and an audit
  row is written.
- **Risk override:** the original classification and the reason are kept in the case and in the
  report.
- **Recommended hold:** stays pending until a Supervisor (not the maker) approves it, and no
  account or transaction data changes.
- **Priority:** the large transfer plus ATO case ranks above an isolated failed login, and a weak
  case is flagged needs review.
- **Report:** has every section, and contains no raw PII.
