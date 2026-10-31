# Practices Discovery Evidence

> By the lead (`aidlc-pipeline-deploy-agent`), working alone (collaborators off
> for `mvp` scope, so no support reviews). Final after the interview.

## What was inspected

| Source | What it gave |
|---|---|
| Repository root | Greenfield: only `.gitignore` (empty) and `aidlc/`; no commits, no code, no CI or deploy config, no lint or test config. Nothing to infer team habits from. |
| `aidlc/spaces/default/memory/org.md` | The five suggested defaults: trunk-based with squash-merge to `main`; walking skeleton when scope enables it; test-after with an 80% line-coverage floor and CI before merge for `mvp`; deploy on merge to staging with a manual production approval; formatter and linter decide code style. |
| `aidlc/spaces/default/memory/team.md`, `project.md` | No affirmed practice sections yet (only one Corrections line in `team.md`), so this is a first run, not a re-run. |
| `ideation/intent-capture/intent-statement.md` | `mvp` scope; hybrid AI with a human final decision; visible PII masking; in-app AI logs. |
| `ideation/feasibility/constraint-register.md` | Stack (TC-03), same Dockerfile local and deployed (TC-06), 3-hour Level 1 and 18:00 deadline (OC-01), pre-written code checked at check-in (OC-03), $10 AI cap (OC-04), public jury URL required (OC-05), synthetic data only (RC-01), PII masked before AI (RC-03). |
| `ideation/scope-definition/scope-document.md` | Sequencing step 1 is a thin deployed slice that accepts an upload. |
| `aidlc-state.md` | Greenfield, `mvp`, Test Strategy Standard, Operation phase skipped, Construction is unit-major and serial with checkpoints enabled. |

## What was inferred (before the interview)

- A small team deciding jointly under a 3-hour clock fits trunk-based work with very short branches better than pull-request review queues.
- One hosted environment exists (the jury URL), so "staging" and "production" collapse into one; the manual production approval becomes a human check of the live URL before submission.
- The 80% coverage floor is a real time cost inside 3 hours and cannot be lowered for `mvp`.

## Interview decisions

| Q | Answer | What it settled |
|---|---|---|
| Q1 | A | Short-lived branches squash-merged into `main`; no formal PR review; the team agrees each merge together. |
| Q2 | A | Before 11:00 only planning documents are committed; application code starts at 11:00. |
| Q3 | B | No walking-skeleton ceremony or dedicated end-to-end check. |
| Q4 | C | Tests first for everything: Methodology `tdd`, failing tests first for each layer, then implementation. Replaces the draft's test-after default. |
| Q5 | A | 80% line coverage, tests in CI before every merge, plus one acceptance test per planted fraud scenario. |
| Q6 | A | `pytest` + `pytest-cov` for the backend, Vitest for the frontend. |
| Q7 | A | Every merge to `main` auto-deploys the one Dockerfile to the managed host; one named team member checks the live URL before 18:00; rollback = redeploy the previous image. |
| Q8 | A | Ruff (lint and format) for Python; Vite+'s built-in lint and format for TypeScript; lint failure blocks the merge; no extra naming rules. |
| Q9 | A, C, D | Hard rules: mask PII before any AI call or MCP response; never commit real customer data, production credentials or real payment details; never commit secrets. |
| Q10 | A | Resolves the Q3 vs scope-order conflict: keep the approved scope order (deploy and upload first) as an ordinary first step, with no separate end-to-end check. |

Two proposed rules were not chosen in Q9 and are not hard rules: "ALWAYS build
local and deployed runs from the same Dockerfile" (TC-06) and "NEVER let the AI
make the final case decision" (TC-05). Both remain recorded as constraints in
the ideation constraint register; they are just not promoted to `## Mandated` /
`## Forbidden`.

## Risk accepted by the team

TDD for every layer, plus an 80% line-coverage floor, CI before every merge and
one acceptance test per planted scenario, competes directly with the 3-hour
Level 1 milestone. Q5's context stated this cost and that the floor cannot be
lowered; the team chose it anyway (Q4 C, Q5 A) and confirmed the summary. Build
and Test will hold the floor; it will not be weakened to make a step pass.

## Remaining uncertainty

- Which managed host (Render, Railway or Fly.io) is still open; the team picks before the first deploy (Q7).
- The named team member who signs off the live URL is not yet named (Q7).
- Vite+'s built-in lint/format tooling and its coverage reporting with Vitest have not been tried in this repo yet; if they fall short, the team decides a replacement at that point.
