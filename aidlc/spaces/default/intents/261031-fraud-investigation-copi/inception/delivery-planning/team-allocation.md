# Team Allocation

Inputs: `inception/practices-discovery/team-practices.md`, `inception/units-generation/unit-of-work.md`, `delivery-planning-questions.md`.

## Team Structure

Single team, all Bolts. No separate mobs — the full team builds each Bolt together in dependency order. Roles rotate per session.

| Role | Responsibility |
|---|---|
| Driver | Writes the code in the active session |
| Navigator | Reviews each line as it is written; watches for contract violations and test gaps |
| Researcher | Looks ahead: reads the next Bolt's dependencies, clears blockers early |

## Bolt Assignments

| Bolt | Assigned to | Notes |
|---|---|---|
| B1 — platform | Full team | First Bolt — establishes container, schema, and CI; everyone should be present |
| B2 — detection-cases | Full team | Largest Bolt (XL complexity); pair on the 7 detection rules |
| B3 — ai-review | Full team | Requires OpenRouter key in env; CI uses the fake model |
| B4 — web-console | Full team (or split with B5) | Frontend-heavy; pair on the React Flow graph |
| B5 — mcp-gateway | Full team (or split with B4) | Can run in parallel with B4 once B3 is merged |

## Skill Notes

- Python / FastAPI: needed for B1–B3 and B5
- React / Vite+ / coss ui: needed for B4
- MCP protocol: needed for B5 — one team member should read the MCP spec before B5 starts
- OpenRouter API: needed for B3 — set `OPENROUTER_API_KEY` in `.env.local` (gitignored)

## Parallel Construction (B4 + B5)

If two or more people are available simultaneously after B3 merges, split the team: one person takes B4, another takes B5. Both branches are opened from `main` at the same commit. Merge order does not matter — there is no dependency between them. If running solo, build B4 first (more user-visible value), then B5.

## Sources

- [desc] Digital Fraud Investigation System — hackathon MVP
- [scope] mvp
- `inception/practices-discovery/team-practices.md`
- `inception/units-generation/unit-of-work.md`
