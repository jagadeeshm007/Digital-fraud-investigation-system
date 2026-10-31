# Rough Mockups — Questions

Inputs: `ideation/intent-capture/intent-statement.md`, `ideation/scope-definition/scope-document.md`, `ideation/scope-definition/intent-backlog.md`.

## Q1. [Designer] What are the primary entry points and key screens?

Context: one screen per Must in the intent backlog, plus places to show AI activity and data safety.

A. A side-navigation app with these screens: Data Upload (with validation report), Dashboard, Alerts list, Alert Detail (factors, supporting records, AI recommendation, related-entity graph), Case Queue, Case Detail (decision and history), AI Activity Log, and Data Safety (what is masked and why)
B. Fewer screens: Upload, Alerts and Cases only, with everything else folded in
C. A single long page with sections
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. [Product owner] What is the core happy path?

A. The investigator uploads or selects sample files, sees the validation report, runs detection, lands on the dashboard, opens a high-risk alert, reads its factors, supporting records and AI recommendation, opens the case, records a decision, and sees the decision history with the original alert unchanged.
B. Detection runs automatically on upload; the investigator starts from the case queue
C. The investigator starts from the dashboard, with data preloaded
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. [Designer] What should the alert detail show first?

Context: this is the screen judges will look at most, because it is where "explain why it was flagged" becomes visible.

A. Top: risk score and band, fraud category, and the AI recommendation in one line. Then the contributing factors with their points. Then supporting records as a timeline. Then the related-entity graph. Actions (open case) at the top right.
B. Supporting records first, factors after
C. The related-entity graph first, as the main view
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. [Designer] Are there brand guidelines or a design system to follow?

A. No brand guidelines. Use coss ui components and React Flow. Aim for a neutral, dense investigator console with light and dark themes.
B. Follow Azentio's brand look (please share guidelines)
C. A custom visual style (please describe)
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q5. [Designer] Which devices and screen sizes must be supported?

A. Desktop and laptop first (1280 px and wider), for investigators and judges; usable on a tablet; phones not targeted
B. Fully responsive, including phones
C. Desktop only
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q6. [Designer] What accessibility level is needed?

A. WCAG 2.1 AA basics: every action works by keyboard, text meets contrast ratios, risk level is never shown by colour alone, every input has a label
B. A full WCAG 2.1 AA audit
C. No specific requirement
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q7. [Product owner] How should the app visibly show that data is kept safe?

Context: the intent statement makes visible PII protection a success metric.

A. PII appears masked by default everywhere (for example a name shown as "Ravi K•••" and a phone number as "+91 98•••••210"), marked with a "Masked" badge. A supervisor can reveal a value, which is recorded in the audit trail. The AI Activity Log shows the masked text that was sent to the model.
B. Mask only in AI calls; show full values in the app
C. Mask everything, with no reveal at all
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q8. [Designer] Where do the Azentio brand guidelines come from?

Context: you chose Azentio's brand look (Q4), but no guidelines have been shared yet.

A. I approximate Azentio's look from its public website (colour palette and typography feel) on top of coss ui, without using its logo or trademarks
B. You will share Azentio's brand guidelines, and I wait for them
C. Use the neutral console look for now and switch to the brand later
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Consolidated Summary Confirmation

- Screens: a side-navigation app with Data Upload (with validation report), Dashboard, Alerts, Alert Detail (factors, supporting records, AI recommendation, related-entity graph), Case Queue, Case Detail (decision and history), AI Activity Log and Data Safety (Q1).
- Happy path: upload or select files, see the validation report, run detection, land on the dashboard, open a high-risk alert, read its factors, records and AI recommendation, open the case, record a decision, and see the history with the original alert unchanged (Q2).
- Alert detail order: risk score and band, category and one-line AI recommendation at the top; then factors with points; then supporting records as a timeline; then the related-entity graph; Open case at the top right (Q3).
- Look: Azentio's brand look (Q4), approximated from its public website's colour palette and typography on top of coss ui, with no logo or trademarks (Q8).
- Devices: desktop and laptop first (1280 px and wider), usable on a tablet, phones not targeted (Q5).
- Accessibility: WCAG 2.1 AA basics, meaning keyboard for every action, contrast ratios met, risk never shown by colour alone, and every input labelled (Q6).
- Data safety: PII masked by default with a Masked badge; a supervisor can reveal a value and the reveal is audited; the AI Activity Log shows the masked text sent to the model (Q7).

Does this all look correct?

- Looks correct
- Request changes

[Answer]: Looks correct
