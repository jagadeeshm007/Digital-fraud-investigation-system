# Wireframes: Digital Fraud Investigation System

Inputs: `ideation/intent-capture/intent-statement.md` (users, success metrics, AI role), `ideation/scope-definition/scope-document.md` (minimum scope, MoSCoW), `ideation/scope-definition/intent-backlog.md` (IB-01 to IB-14). Answers: `rough-mockups-questions.md` Q1–Q8.

Low fidelity. Boxes show structure only. Visual style is Azentio's look on top of coss ui (Q4, Q8). Layout is desktop first at 1280 px and wider, and still usable on a tablet (Q5).

## Brand Look

Sampled from a printed copy of Azentio's public homepage that the person supplied (2026-10-31), applied on top of coss ui. No Azentio logo or trademarks are used (Q8).

| Token | Value | Seen on the site as | Use in the app |
|---|---|---|---|
| Ink | `#16303D` | Headings and body text (navy) | Primary text, side navigation background in dark theme |
| Ink 2 | `#212D3A` | Secondary dark text | Secondary text, borders in dark theme |
| Mint accent | `#55FFBE` | Heading underlines, pill-button outlines | Focus rings, active nav underline, primary button outline |
| Green | `#2ED88E` | Logo mark, "+" in key stats | Success states, "Low" risk band (always with a text label) |
| Deep green | `#39AB7F` | Large green headline | Links and primary button fill (white text) |
| Grey | `#ABABAB` / `#959494` | Muted captions | Muted text and placeholders, checked for 4.5:1 on white |
| Red | `#E51520` | Rare highlights | "High" risk band and errors (always with an icon and text) |
| Background | `#FFFFFF` | Page background | Light theme surface |

Typography: Poppins (semibold or bold) for headings, with a mint underline under page titles as on the site. Noto Sans for body and table text.

Shape: rounded pill buttons with a thin outline, as on the site.

## Information Architecture

```
App shell (header + side navigation + main)
|
+-- Data Upload ............ IB-02  ingest, validate, report
+-- Dashboard .............. IB-06  counts, risk distribution, categories
+-- Alerts ................. IB-06  filterable list
|     +-- Alert Detail ..... IB-05, IB-09, IB-12  factors, records, AI, graph
+-- Case Queue ............. IB-07  open cases
|     +-- Case Detail ...... IB-07  decision + history
+-- AI Activity Log ........ IB-10  every AI call and step
+-- Data Safety ............ IB-08  what is masked and why
```

Every screen is reachable in one click from the side navigation. Detail screens are one click from their list.

## Shared App Shell

```
+--------------------------------------------------------------------------+
| [Product name]          Role: [Analyst v]   Data: masked [badge]    [?]  |
+----------------+---------------------------------------------------------+
| > Dashboard    |                                                         |
|   Data Upload  |                  <main content area>                    |
|   Alerts  (12) |                                                         |
|   Case Queue(4)|                                                         |
|   AI Activity  |                                                         |
|   Data Safety  |                                                         |
+----------------+---------------------------------------------------------+
```

- The role switcher (Analyst, Investigator, Supervisor) decides who may reveal masked data or record decisions.
- The "Data: masked" badge is always visible (Q7).

Accessibility: a skip-to-content link comes first. Landmarks are `header`, `nav` and `main`. The side navigation is the keyboard entry point after the skip link (Q6).

## Screen 1: Data Upload

```
+--------------------------------------------------------------------------+
| h1 Data Upload                                                           |
| Source: ( ) Customers & accounts ( ) Transactions ( ) Devices & logins   |
|         ( ) Loan applications    ( ) Insurance claims                    |
| +----------------------------------------------+  [Use sample data v]    |
| |  Drop CSV, Excel or JSON here, or [Browse]   |                         |
| +----------------------------------------------+  [Validate & load]      |
|                                                                          |
| h2 Validation report: transactions.xlsx                                  |
| Accepted 1,240   Rejected 12   Warnings 3                                |
| +------+------------+---------------------------------------------------+|
| | Row  | Field      | Reason                                            ||
| +------+------------+---------------------------------------------------+|
| | 17   | amount     | Missing mandatory value                           ||
| | 203  | timestamp  | Not a valid date: "31/13/2026"                    ||
| +------+------------+---------------------------------------------------+|
| Rejected rows are kept for review, never dropped.   [Download report]    |
|                                                       [Run detection ->] |
+--------------------------------------------------------------------------+
```

States:
- Empty: a source picker with the hint "Upload a file or use sample data".
- Loading: a progress bar showing "Validating 1,240 rows".
- Error: an unreadable file shows "Could not read this file as CSV, Excel or JSON", and the upload control keeps the file name.
- Partial: when every row is rejected, the report shows that with the reasons, and "Run detection" is disabled with an explanation.

Accessibility: h1 page title, h2 for the report. The report is a real table with column headers. Keyboard entry is the source radio group.

## Screen 2: Dashboard

```
+--------------------------------------------------------------------------+
| h1 Dashboard                                         Last run 11:42      |
| +------------+ +------------+ +------------+ +---------------------+     |
| | Records    | | Flagged    | | Cases open | | Lookalikes cleared  |     |
| | 6,420      | | 38         | | 4          | | 9                   |     |
| +------------+ +------------+ +------------+ +---------------------+     |
| h2 Risk distribution          | h2 Fraud categories                     |
| High   ######## 9             | Suspicious transfer   ###### 14         |
| Medium ############ 17        | Shared device         #### 8            |
| Low    ###### 12              | Login failures        ### 6             |
|                               | Loan application      ## 5              |
|                               | Identity / synthetic  ## 5              |
| h2 Highest-risk alerts                                    [All alerts ->]|
| [H 92] Shared device ring - 3 customers, 1 device          11:40        |
| [H 88] Transfer after 5 failed logins + new device          11:38        |
+--------------------------------------------------------------------------+
```

States:
- Empty: "No data loaded yet", with a button to Data Upload.
- Loading: skeleton tiles.
- Error: "Could not load results; try again".

Risk bands carry their letter and number as well as colour (Q6).

Accessibility: h1 page, h2 for each panel. Each chart has a text table alternative. Keyboard entry is the first tile.

## Screen 3: Alerts

```
+--------------------------------------------------------------------------+
| h1 Alerts                                                                |
| Customer [______] Transaction [______] Product [All v] Risk [All v]      |
| Date [from]-[to]  Detection type [All v]          [Reset filters]        |
| Showing 1-20 of 38                                                       |
| +------+------+------------------------+-----------+---------+--------+  |
| | Risk | ID   | Detection type         | Customer  | Product | Time   |  |
| +------+------+------------------------+-----------+---------+--------+  |
| | H 92 | A-31 | Shared device ring     | Ravi K... | Lending | 11:40  |  |
| | H 88 | A-27 | Transfer after failures| Meera S...| Banking | 11:38  |  |
| +------+------+------------------------+-----------+---------+--------+  |
|                                         [< Prev]  1 2 3  [Next >]        |
+--------------------------------------------------------------------------+
```

States:
- Empty because of filters: "No alerts match these filters", with Reset.
- Empty because no detection has run: a link to Data Upload.
- Loading: skeleton rows.

Customer names are masked (Q7).

Accessibility: h1 page. Filters sit in a labelled `form` region and every filter has a visible label. The table has sortable column headers. Keyboard entry is the first filter.

## Screen 4: Alert Detail

```
+--------------------------------------------------------------------------+
| h1 Alert A-31                                           [Open case ->]   |
| Risk HIGH 92/100   Category: Shared device ring                          |
| AI: "Coordinated applications; recommend investigation" (cites 4 records)|
+--------------------------------------------------------------------------+
| h2 Why it was flagged                                                    |
| +30 Device D-900 used by 3 unrelated customers                           |
| +25 3 loan applications within 2 hours from that device                  |
| +20 Disbursement accounts linked to each other                           |
| +12 Transfers out within 30 minutes of disbursement                      |
|  -0 Household check: different surnames and addresses (no reduction)     |
| AI adjustment: +5 (allowed range +/-10)          Base 87 -> Final 92     |
+--------------------------------------------------------------------------+
| h2 Supporting records (timeline)                                         |
| 10:02 Loan application L-301  Customer Ravi K...  Device D-900  [view]   |
| 10:40 Loan application L-302  Customer Asha P...  Device D-900  [view]   |
| 11:05 Disbursement T-1004 -> Account ACC-9002 ...                [view]  |
+--------------------------------------------------------------------------+
| h2 Related entities (graph)                                              |
|   [Customer] --- [Device D-900] --- [Customer]                           |
|        \              |                 /                                |
|      [Account] --- [Account] --- [Account]                               |
+--------------------------------------------------------------------------+
```

States:
- AI unavailable: the AI line reads "AI review unavailable; rule-based score shown", and Final equals Base.
- AI pending: a placeholder that says "AI reviewing masked evidence".
- No graph links: "No related entities found".

Accessibility: h1 alert ID, h2 for each section. The factor list is an ordered list. The graph has a text list of the same links beside it. Keyboard entry is the Open case button.

## Screen 5: Case Queue

```
+--------------------------------------------------------------------------+
| h1 Case Queue                         Status [Open v]  Risk [All v]      |
| +--------+---------------------+-----------+------+-------------------+  |
| | Case   | Category            | Customer  | Risk | Status            |  |
| +--------+---------------------+-----------+------+-------------------+  |
| | C-0007 | Shared device ring  | Ravi K... | H 92 | New               |  |
| | C-0006 | Transfer after fails| Meera S...| H 88 | Requires investig.|  |
| +--------+---------------------+-----------+------+-------------------+  |
+--------------------------------------------------------------------------+
```

States:
- Empty: "No open cases. Cases appear when alerts need action."
- Loading: skeleton rows.

Accessibility: h1 page and a data table. Keyboard entry is the Status filter.

## Screen 6: Case Detail

```
+--------------------------------------------------------------------------+
| h1 Case C-0007        Status: New        Original alert: A-31 [view]     |
| Customer Ravi K... [Reveal]   Account ACC-9002...   Risk HIGH 92         |
| h2 Evidence      (same factors and records as the alert, read-only)      |
| h2 Decision                                                              |
| ( ) Requires investigation  ( ) False positive  ( ) Escalate             |
| Reason [__________________________________________]   [Record decision]  |
| h2 History                                                               |
| 11:41 Case opened from alert A-31 (risk 92)                 system       |
| 11:52 Decision: Requires investigation - "Shared device..." Investigator |
| 11:55 Value revealed: customer name                          Supervisor  |
+--------------------------------------------------------------------------+
```

The original alert link always shows the alert exactly as it was first raised.

"Reveal" is shown only to a Supervisor, and every reveal adds a history line (Q7).

States:
- Recording: the button is disabled while saving, so a double click never makes two decisions.
- Error: the message keeps the typed reason.

Accessibility: h1 case ID, h2 sections. The decision is a radio group in a `fieldset` with a `legend`. Keyboard entry is the first decision option.

## Screen 7: AI Activity Log

```
+--------------------------------------------------------------------------+
| h1 AI Activity Log          Spend today $0.84 of $10.00 limit            |
| +-------+-------+-------------+--------+--------+--------+-------------+ |
| | Time  | Alert | Step        | Model  | Tokens | Latency| Cost        | |
| +-------+-------+-------------+--------+--------+--------+-------------+ |
| | 11:40 | A-31  | Categorise  | [model]| 1,820  | 2.1 s  | $0.002      | |
| | 11:40 | A-31  | Recommend   | [model]| 2,340  | 3.4 s  | $0.003      | |
| +-------+-------+-------------+--------+--------+--------+-------------+ |
| [Expand row] -> masked text sent: "Customer CUST_014 used device ..."    |
+--------------------------------------------------------------------------+
```

States:
- Empty: "No AI calls yet".
- Limit near: a warning banner at 80 percent of the $10 limit.
- Call failed: the row shows "Failed, rule-based result kept" with the reason.

Accessibility: h1 page. The data table's expandable rows use a button with `aria-expanded`. Keyboard entry is the first row toggle.

## Screen 8: Data Safety

```
+--------------------------------------------------------------------------+
| h1 Data Safety                                                           |
| h2 What is masked                                                        |
| Name        Ravi Kumar      -> Ravi K...       (in UI, AI and MCP)       |
| Phone       +91 9812345210  -> +91 98.....210                            |
| Account     ACC00912345     -> ACC-...2345                               |
| h2 Where masking applies                                                 |
| Screens: masked by default   AI calls: always masked   MCP: always masked|
| h2 Recent reveals (Supervisor only)                                      |
| 11:55 Supervisor revealed customer name on case C-0007                   |
+--------------------------------------------------------------------------+
```

The examples on this screen use synthetic values only.

Accessibility: h1 page, h2 sections, and a definition list for the before and after values. Keyboard entry is the first section heading link.

## Assumptions & Open Questions

- [assumption] The mint accent `#55FFBE` is too light for text on white, so it is used only for outlines, underlines and focus rings, never for text; final contrast is checked when the UI is built.
- [assumption] The extra scenario shown in the examples is suspicious loan applications; duplicate insurance claims may be added as well, which is decided in requirements.
