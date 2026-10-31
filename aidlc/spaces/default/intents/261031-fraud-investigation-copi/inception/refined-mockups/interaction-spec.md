# Interaction Specification

Inputs: `ideation/rough-mockups/wireframes.md`, `ideation/rough-mockups/user-flow.md`, `inception/user-stories/stories.md`, `inception/requirements-analysis/requirements.md`, `inception/practices-discovery/team-practices.md`, `mockups.md`. Format: component-spec template.

## RiskBadge

| Field | Value |
|---|---|
| Component | RiskBadge |
| Description | Shows the risk band and score (US3.1) |
| Category | display |

| State | Description | Trigger |
|---|---|---|
| default | Letter and score, e.g. "H 92" | render |
| empty | "–" when no score yet | no data |

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| score | number | yes | — | 0–100 |
| band | "Low" \| "Medium" \| "High" | yes | — | from score: below 40, 40–69, 70 and above |

| Requirement | Implementation |
|---|---|
| ARIA role | none (text) |
| Label | `aria-label="Risk High, 92 of 100"` |
| Contrast | text on band colour meets 4.5:1; never colour alone (letter and number shown) |

## FileUploader

| Field | Value |
|---|---|
| Component | FileUploader |
| Description | Picks source type and file, starts validation (US1.1, US1.2) |
| Category | input |

| State | Description | Trigger |
|---|---|---|
| default | Source select, file input, Validate disabled | page load |
| ready | Validate enabled | file chosen |
| loading | Progress "Validating N rows"; Validate disabled | submit |
| error | "Could not read this file as CSV, Excel or JSON"; file name kept | parse failure |
| too-large | "File exceeds the N MB limit" | size check |

| Requirement | Implementation |
|---|---|
| Keyboard | Tab to source, file and Validate; Enter submits |
| Label | visible labels on every control |
| Screen reader | `aria-live="polite"` announces the result counts |

## ValidationReport

| State | Description | Trigger |
|---|---|---|
| success | Counts plus a problems table | validation done |
| all-rejected | Counts; Run detection disabled with the reason | zero accepted |
| empty-file | "This file has no records" | zero rows |

Accessibility: a real `<table>` with `<th scope="col">`.

## AlertFilters

| Prop | Type | Description |
|---|---|---|
| customer, transaction | string | free text |
| product | enum | All, Lending, Insurance, Core banking |
| risk | enum | All, Low, Medium, High |
| from, to | date | IST day boundaries |
| type | enum | detection types |

Behaviour:
- Filters apply on change, debounced at 300 ms.
- Reset clears all filters.
- Filter state is kept in the URL query (masked identifiers only, never raw PII).

Accessibility: a `form` landmark labelled "Alert filters".

## DecisionForm

| State | Description | Trigger |
|---|---|---|
| default | Radios by role; reason empty; button enabled | open case |
| invalid | "A reason is required"; selection kept | submit without reason |
| saving | Button disabled with "Saving" | submit |
| error | Message; reason text kept | server error |
| final | Form hidden; "Case is Escalated / Closed" | status final |

Escalate opens ConfirmDialog. Focus is trapped while it is open, Escape cancels, and focus returns to the Escalate radio afterwards.

Accessibility: a `fieldset` with `legend` "Decision"; the radio group uses arrow keys.

## AiRecommendationPanel

| State | Description |
|---|---|
| pending | Skeleton plus "AI reviewing masked evidence" |
| ready | Recommendation, category, citations (links), base, adjustment, final |
| unavailable | "AI review unavailable; rule-based score shown" plus the reason (error, timeout, budget reached, invalid citation) |

Screen reader: `aria-live="polite"` announces when the panel becomes ready.

## EntityGraph (React Flow)

- **Nodes:** customer, account, device, application, claim. Each node shows an icon and a masked label.
- **Edges:** shared identifiers.
- **Layout:** d3-force.
- **Text alternative:** a list of links beside the graph, reachable by keyboard.

## RevealButton

- Supervisor only.
- Clicking it shows the value in place and appends a history line.
- No undo is needed, because the reveal is shown for this view only.

## Toasts

- Shown for upload results, decisions and rule saves.
- Close after 5 s, with `aria-live`.
- Errors stay until dismissed.
