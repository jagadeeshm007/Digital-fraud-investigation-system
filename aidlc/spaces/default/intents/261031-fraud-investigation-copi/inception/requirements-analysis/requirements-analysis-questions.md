# Requirements Analysis — Questions

Inputs: `ideation/intent-capture/intent-statement.md`, `ideation/scope-definition/scope-document.md`, `inception/practices-discovery/team-practices.md`, plus the other approved ideation artifacts (feasibility, rough mockups). Only questions those artifacts do not already settle are asked here.

## Q1. [Product owner] Which extra fraud scenario does this version detect?

Context: the challenge requires at least one extra scenario beyond the four required ones; the scope named suspicious loan applications or duplicate insurance claims.

A. Both: suspicious loan applications (several applications under different identities from the same device, phone or address, disbursed into linked accounts and then moved out) and duplicate insurance claims (the same incident, amount or documents claimed more than once, or across linked customers)
B. Suspicious loan applications only
C. Duplicate insurance claims only
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. [Product owner] Does this version also detect identity fraud and synthetic profiles?

Context: the challenge lists identity fraud as scenario 1, but Level 1's minimum list does not require it. Detecting it means flagging repeated contact details, identity numbers reused across customers, and suspiciously similar profiles.

A. Yes: repeated phone, email, address or identity number across "independent" customers, and near-duplicate profiles (similar names and dates of birth), as one detection type
B. No: leave it for a later version
C. Only exact repeats of phone, email or identity number, without similar-profile matching
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. [Product owner] How is risk scored and banded, and how far may AI move it?

A. A 0–100 score from weighted factors. Bands: Low below 40, Medium 40–69, High 70 and above. AI may adjust the rule-based score by at most 10 points either way. Every factor, and the AI adjustment, is listed with its points.
B. Bands only (Low, Medium, High), no numeric score
C. 0–100 score with AI allowed up to 20 points either way
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. [Product owner] What data volumes must the app handle?

A. Demo data of about 2,000 customers, 2,500 accounts and 50,000 transactions over 60 days, plus logins, loan applications and claims. Organiser files up to about 100,000 rows each.
B. Small: a few thousand rows in total
C. Large: a million rows or more
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. [Product owner] Which roles exist, and what can each do?

Context: the wireframes use a role switcher with three roles, and a supervisor-only reveal.

A. Three roles chosen with a role switcher, with no real login for the hackathon. Analyst: view everything (masked) and record an initial decision. Investigator: the same, plus escalate. Supervisor: the same, plus reveal masked values and change rule settings. The server enforces each permission, and every action is recorded.
B. Real sign-in with user accounts
C. One role that can do everything
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q6. [Product owner] Which case decisions and statuses are there?

A. Decisions: Requires Investigation, False Positive, Escalate. Each needs a written reason. Status moves New, then Under Investigation, then Escalated or Closed (false positive). Every change is kept in the case history, and the original alert never changes.
B. Only Requires Investigation and False Positive
C. Free-text decisions with no fixed statuses
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q7. [Product owner] How configurable are the detection rules?

Context: the challenge asks for configurable rules.

A. Thresholds and factor weights live in one settings file. A supervisor can change them in the app, the change applies on the next detection run, and every change is recorded.
B. Settings file only; no editing in the app
C. Fixed in the code
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q8. [Product owner] What can be done through the MCP server?

A. Read: dashboard figures, list and filter alerts, open an alert, open a case, read the AI activity log. Write, each only after the user's consent: record a case decision, run detection. Everything is masked and checked against the same role permissions as the app.
B. As A, plus uploading data files through MCP
C. Read only
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q9. [Product owner] What speed is good enough?

A. Dashboard and lists load in under 2 seconds with the demo data. A detection run over 50,000 transactions finishes in under 60 seconds. Each AI review finishes in under 15 seconds and runs in the background, so alerts appear before AI finishes.
B. No specific targets
C. Everything, including AI, in under 5 seconds
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Consolidated Summary Confirmation

- Extra scenarios: both suspicious loan applications and duplicate insurance claims (Q1).
- Identity fraud: also detected, as repeated phone, email, address or identity number across customers plus near-duplicate profiles (Q2).
- Risk: 0–100 from weighted factors; Low below 40, Medium 40–69, High 70 and above; AI adjusts at most 10 points either way; every factor and the AI adjustment listed with points (Q3).
- Volumes: demo data of about 2,000 customers, 2,500 accounts and 50,000 transactions over 60 days, plus logins, loans and claims; organiser files up to about 100,000 rows each (Q4).
- Roles: Analyst, Investigator and Supervisor through a role switcher with no real login; server-enforced permissions; every action recorded (Q5).
- Cases: decisions Requires Investigation, False Positive and Escalate, each with a reason; status New, Under Investigation, then Escalated or Closed; history kept and the original alert never changes (Q6).
- Rules: thresholds and weights in one settings file, editable by a supervisor in the app, applied on the next detection run, every change recorded (Q7).
- MCP: reads of figures, alerts, cases and the AI log; with consent, record a case decision and run detection; masked and role-checked (Q8).
- Speed: dashboard and lists under 2 seconds; detection over 50,000 transactions under 60 seconds; each AI review under 15 seconds in the background (Q9).

Does this all look correct before I generate the requirements artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
