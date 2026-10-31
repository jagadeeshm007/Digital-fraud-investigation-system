# Refined Mockups — Questions

Inputs: `ideation/rough-mockups/wireframes.md`, `ideation/rough-mockups/user-flow.md`, `inception/user-stories/stories.md`, `inception/requirements-analysis/requirements.md`, `inception/practices-discovery/team-practices.md`.

The person left this stage's questions to the designer ("don't ask, assume with what you have"). Each answer below is the designer's choice, drawn from the approved upstream artifacts.

## Q1. [Designer] How is each user story represented in the UI?

A. One screen per epic as in the wireframes (8 screens). Story-level behaviour lives inside those screens: rejected records as a tab on Data Upload, rule settings as a drawer on the Dashboard, MCP with no screen of its own (its calls appear in the audit trail and AI log).
B. A separate screen per story
C. Not yet defined
X. Other (please specify)

[Answer]: A (designer's choice, left to the designer)

## Q2. [Designer] Which interaction patterns are needed?

A. Side drawer for rule settings and record details; inline expand for AI log rows; confirmation dialog only for Escalate (irreversible in this version); toasts for upload and decision results; no wizards
B. Modals for everything
C. Not yet defined
X. Other (please specify)

[Answer]: A (designer's choice, left to the designer)

## Q3. [Designer] Which states must each screen handle?

A. Loading (skeletons), empty, error, success and partial, per the wireframes, plus "AI pending" and "AI unavailable" on alerts and cases
B. Success only
C. Not yet defined
X. Other (please specify)

[Answer]: A (designer's choice, left to the designer)

## Q4. [Designer] Which design system and accessibility level apply?

A. coss ui components with the Azentio brand tokens from the wireframes, React Flow for the related-entity graph; WCAG 2.1 AA basics (NFR10)
B. Custom components
C. Not yet defined
X. Other (please specify)

[Answer]: A (designer's choice, left to the designer)

## Q5. [Designer] Which responsive breakpoints are needed?

A. Desktop at 1280 px and wider (full layout); tablet from 768 to 1279 px (side navigation collapses to icons, wide tables scroll horizontally with the first column pinned); phones not targeted (NFR11)
B. Desktop only
C. Not yet defined
X. Other (please specify)

[Answer]: A (designer's choice, left to the designer)
