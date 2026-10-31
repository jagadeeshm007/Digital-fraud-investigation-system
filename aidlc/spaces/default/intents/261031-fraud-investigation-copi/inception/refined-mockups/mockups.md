# Refined Mockups

Inputs: `ideation/rough-mockups/wireframes.md` (8 screens, brand tokens), `ideation/rough-mockups/user-flow.md` (upload-to-decision flow), `inception/user-stories/stories.md` (US1.1–US11.1), `inception/requirements-analysis/requirements.md`, `inception/practices-discovery/team-practices.md`. Answers: `refined-mockups-questions.md` Q1–Q5.

These refine the rough wireframes with real labels, the story each region serves, and the states each needs. The layout grid is 8 px. Content width is at most 1440 px. Typography is Poppins for headings (h1 28 px, h2 20 px) and Noto Sans 14 px for body text.

## Shell

```
+----------------------------------------------------------------------------+
| [=] Fraud Investigation        Role [Investigator v]  [Masked]  AI $0.84/10 |
+--------------+-------------------------------------------------------------+
| Dashboard    |  h1 <Screen title>  ____ (mint underline)                    |
| Data Upload  |                                                             |
| Alerts   38  |                                                             |
| Cases     4  |                                                             |
| AI Activity  |                                                             |
| Data Safety  |                                                             |
| Audit Trail  |                                                             |
+--------------+-------------------------------------------------------------+
```

- **Role switcher:** US7.1.
- **Masked badge:** US8.1.
- **AI spend chip:** US9.2. It turns amber at $8.
- **Audit Trail:** a ninth navigation item added for US7.2.

## Data Upload (US1.1–US1.5)

```
+----------------------------------------------------------------------------+
| h1 Data Upload                                                             |
| Source  [Transactions v]   File [ Choose CSV / XLSX / JSON ]  [Validate]   |
|         or [Use sample data]                                               |
| Tabs: [ Report ] [ Rejected records (12) ] [ Mapping ]                     |
| Report:  Accepted 1,240 | Rejected 12 | Warnings 3          [Run detect] |
|  Row | Field     | Value        | Reason                                  |
|  17  | amount    | (empty)      | Missing mandatory value                 |
|  88  | txn_id    | T-1004       | Duplicate key                           |
|  203 | timestamp | 31/13/2026   | Not a valid date                        |
|  410 | to_acct   | ACC-...9911  | Warning: unknown account                |
+----------------------------------------------------------------------------+
```

- **Rejected records tab:** keeps rows from every upload (US1.4).
- **Mapping tab:** read-only for the Analyst. It shows source column to model field (US1.5).

## Dashboard (US5.1, US2.9)

```
+----------------------------------------------------------------------------+
| h1 Dashboard                                   [Rule settings] (Supervisor)|
| [Records 6,420] [Flagged 38] [Open cases 4] [Lookalikes cleared 9]         |
| Risk distribution (bar + table)   | Categories (bar + table)               |
| Highest-risk alerts (5 rows)                                   [All ->]   |
+----------------------------------------------------------------------------+
```

- **Rule settings drawer (US2.9):** a list of thresholds and weights with their current values, plus Save. Each change logs who, when, the old value and the new value. For Analysts the drawer is view-only.

## Alerts (US5.2)

- **Filter bar:** Customer, Transaction ID, Product (All, Lending, Insurance, Core banking), Risk, Date from and to (IST), and Detection type, with Reset.
- **Table columns:** Risk (badge with letter and number), Alert, Type, Customer (masked), Product, Time.
- **Pagination:** 20 per page.

## Alert Detail (US5.3, US3.1, US3.2, US4.1–US4.3, US2.1)

```
+----------------------------------------------------------------------------+
| h1 Alert A-31  [H 92]  Shared device ring                  [Open case ->]  |
| AI  Investigate: coordinated applications (cites L-301, L-302, T-1004)      |
|     Base 87  AI +5  Final 92                                                |
+--------------------------------------+-------------------------------------+
| h2 Why it was flagged                | h2 Related entities (React Flow)    |
|  +30 Device D-900 on 3 customers     |  [C] -- [D-900] -- [C]              |
|  +25 3 loan apps within 2 h          |    \       |       /                |
|  +20 Linked disbursement accounts    |   [A] --- [A] --- [A]               |
|  +12 Moved out within 30 min         |  (text list of the same links)      |
|  +5  AI adjustment                   |                                     |
| h2 Supporting records (timeline)                                           |
+----------------------------------------------------------------------------+
```

AI states:
- **Pending:** "AI reviewing masked evidence".
- **Unavailable:** "AI review unavailable; rule-based score shown", with final equal to base.
- **Budget reached:** the same as unavailable, with the reason "budget reached".

## Case Queue and Case Detail (US6.1–US6.3, US8.2)

- **Queue:** filters for status and risk. Columns are Case, Category, Customer (masked), Risk, Status and Opened.
- **Detail:** the evidence (read-only), the decision radio group, a reason (required), and Record decision.
- **Decision options by role:**
  - Analyst: Requires Investigation, False Positive.
  - Investigator and Supervisor: Requires Investigation, False Positive, Escalate.
- **Escalate:** opens a confirmation dialog that names the case and states that Escalated is final.
- **History:** every decision, the status before and after, and every reveal.
- **Original alert link:** opens the alert exactly as first raised.

## AI Activity Log (US9.1, US9.2)

- **Table columns:** Time, Alert, Step, Model, Tokens, Latency, Cost, Outcome.
- **Row expansion:** shows the masked text sent.
- **Spend banner:** appears at 80 percent of the limit.

## Data Safety (US8.1–US8.3)

- **What is masked:** synthetic before-and-after examples.
- **Where masking applies:** screens, AI and MCP.
- **Recent reveals:** a list of reveals.

## Audit Trail (US7.2)

- **Table columns:** Time, Role, Channel (App or MCP), Action, Target, Result.
- **Filter:** by action.

## MCP (US10.1, US10.2)

There is no screen. MCP calls appear in the Audit Trail with channel "MCP", and consented writes show their consent result.
