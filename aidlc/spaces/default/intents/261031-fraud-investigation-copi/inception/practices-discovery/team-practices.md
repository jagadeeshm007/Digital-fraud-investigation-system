# Team Practices

> Agreed in the practices interview (`practices-discovery-questions.md`, Q1–Q10,
> summary confirmed "Looks correct"). The repository has no code and no commits
> yet (greenfield).

## Way of Working

We work trunk-based on `main`. Every piece of work goes on a short-lived branch
(hours, not days) that is squash-merged back into `main` as one commit. There
are no long-lived `develop` or release branches. We do not use formal
pull-request reviews: the team agrees each merge together (Q1). Before 11:00 we
commit only planning documents (requirements, designs, rules); application code
starts at 11:00, so nothing pre-written trips the check-in rule (Q2).

## Walking Skeleton

We do not run a separate walking-skeleton ceremony and there is no dedicated
end-to-end check before the other features (Q3). We still keep the approved
scope order: the first step is getting the app deployed at its public URL and
accepting an upload, treated as an ordinary first step like any other, before
we add detection, risk scoring, the dashboard and the case queue (Q10).

## Testing Posture

- **Methodology**: tdd
- **Methodology evidence**: Q4, the team chose "Tests first for everything" over test-after and over tests-first only for detection and risk scoring.
- **Ordering**: For each layer, we write its failing tests first, then implement until they pass, before moving to the next layer.
- Coverage: at least 80% line coverage; the floor is not lowered to make a step pass (Q5).
- CI: the full test suite runs in CI before every merge to `main`, and a failure blocks the merge (Q5).
- Acceptance: every planted synthetic fraud scenario has its own acceptance test proving it is flagged, and that legitimate lookalikes are not (Q5).
- Tooling: `pytest` with `pytest-cov` for the Python backend; Vitest for the React frontend (Q6).

## Deployment

Every merge to `main` builds the one Dockerfile and deploys it automatically to
the managed container host (Render, Railway or Fly.io; the team picks one),
which serves the public jury URL. That single hosted environment is our only
environment. One named team member checks the live URL by hand before 18:00 and
signs it off as the version the jury sees. Rollback means redeploying the
previous image (Q7).

## Code Style

We let the tools decide formatting and lint rules, configured in the repo root:

- Python: Ruff for linting and formatting (configured in `pyproject.toml`).
- TypeScript / React: Vite+'s built-in lint and format.
- Lint runs in CI; a lint failure blocks the merge.
- No naming rules beyond each language's usual style (Q8).
