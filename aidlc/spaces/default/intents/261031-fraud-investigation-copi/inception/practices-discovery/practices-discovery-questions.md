# Practices Discovery — Questions

Draft under review: `team-practices.md`, `discovered-rules.md`, `evidence.md` (same folder). Suggested answers come from the organisation's default practices and this project's approved ideation decisions.

## Q1. [Release engineer] How do changes reach the main branch, and does a merge need someone's approval?

A. Short-lived branches squash-merged into `main`; no formal pull-request review, the team agrees each merge together
B. Commit straight to `main`
C. Pull requests with one reviewer's approval before merge
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. [Release engineer] Does the check-in rule on pre-written code limit what we commit before 11:00?

A. Yes: before 11:00 commit only the planning documents (requirements, designs, rules); application code starts at 11:00
B. No limit: code may be prepared in advance
C. Not known yet; confirm at check-in and decide then
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. [Developer] Build a thin end-to-end slice first? A walking skeleton is a minimal version that runs the whole way through, built first to prove the pieces connect before the real features go in.

A. Yes: first the deployed URL works, one file uploads, and its records are stored and shown
B. No: build features one by one and connect them at the end
C. Not yet defined
X. Other (please specify)

[Answer]: B

## Q4. [Quality engineer] When are tests written?

A. After each layer is built (implement a layer, then write and run its tests)
B. Tests first for the detection and risk-scoring logic, after for everything else
C. Tests first for everything
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q5. [Quality engineer] Coverage and CI: keep the 80% line-coverage floor and run tests in CI before every merge?

Context: for this kind of plan, the organisation's defaults set an 80% line-coverage floor and require tests to pass in CI before a merge. That costs real time in a 3-hour milestone, and the defaults do not allow lowering it.

A. Yes: 80% line coverage, tests in CI before merge, plus an acceptance test for each planted fraud scenario
B. Yes to 80% and CI, without per-scenario acceptance tests
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q6. [Quality engineer] Which test tools?

A. pytest with pytest-cov for the backend, Vitest for the frontend
B. pytest only; no frontend tests
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q7. [Release engineer] How does a change reach the jury URL, and who signs it off?

A. Every merge to `main` auto-deploys the one Dockerfile to the managed host (Render, Railway or Fly.io; the team picks); one named team member checks the live URL by hand before 18:00; rollback means redeploying the previous image
B. Deploy by hand only when the team decides
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q8. [Developer] Which formatter and linter, and any naming rules beyond language defaults?

A. Ruff (lint and format) for Python; Vite+'s built-in lint and format for TypeScript; lint failure blocks the merge in CI; no extra naming rules
B. Ruff for Python; Prettier and ESLint for TypeScript
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q9. [Product owner] Which of these should be hard rules for the project? (select all that apply)

A. ALWAYS mask PII (names, phones, emails, account numbers) before any AI model call or MCP response
B. ALWAYS build local and deployed runs from the same Dockerfile
C. NEVER commit real customer data, production credentials or real payment details; demo data is synthetic only
D. NEVER commit API keys or other secrets to the repository
E. NEVER let the AI make the final case decision; a person decides, and the rule-based result stands if AI is unavailable
F. None of these
X. Other (please specify)

[Answer]: A, C, D

## Q10. [Developer] Should the first thing built still be a deployed slice that accepts an upload?

Context: you answered "No" to building a thin end-to-end slice first (Q3), but the approved scope's sequencing starts with "a thin end-to-end slice that is deployed and accepts an upload" (Scope Definition, Q4). This settles which one holds.

A. Keep the approved scope order: deploy and upload come first, but treat it as an ordinary first step, with no separate end-to-end check before the other features
B. Change the scope order: build features one by one and deploy near the end
C. Yes after all: run a proper walking skeleton with an end-to-end check before the other features
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Consolidated Summary Confirmation

- Way of working: short-lived branches squash-merged into `main`; no formal pull-request review, the team agrees each merge together (Q1). Before 11:00 only planning documents are committed; application code starts at 11:00 (Q2).
- Walking skeleton: no separate walking-skeleton check (Q3), but the approved scope order stands, so deploy and upload come first as an ordinary first step (Q10).
- Testing: tests first for everything (Q4); 80% line coverage, tests in CI before every merge, and an acceptance test for each planted fraud scenario (Q5); pytest with pytest-cov for the backend and Vitest for the frontend (Q6).
- Deployment: every merge to `main` auto-deploys the one Dockerfile to the managed host; one named team member checks the live URL before 18:00; rollback means redeploying the previous image (Q7).
- Code style: Ruff (lint and format) for Python; Vite+'s built-in lint and format for TypeScript; lint failure blocks the merge; no extra naming rules (Q8).
- Hard rules: ALWAYS mask PII before any AI model call or MCP response; NEVER commit real customer data, production credentials or real payment details; NEVER commit API keys or other secrets (Q9).

Does this all look correct?

- Looks correct
- Request changes

[Answer]: Looks correct
