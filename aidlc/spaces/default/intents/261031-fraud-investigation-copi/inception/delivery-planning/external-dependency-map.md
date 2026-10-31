# External Dependency Map

Inputs: `inception/domain-design/components.md` (external dependencies), `inception/requirements-analysis/requirements.md`.

## External Dependencies

| Dependency | Used by | Bolt | Type | Needed by | Risk | Action before that Bolt |
|---|---|---|---|---|---|---|
| Supabase Postgres | ActivityStore | B1 | Cloud database | B1 start | Medium — free tier, requires account | Create free Supabase project; copy `DATABASE_URL` to `.env.local` (gitignored) |
| Chosen container host (Render / Railway / Fly.io) | Dockerfile | B1 | Hosting | B1 done | Medium — deployment key required | Create account and project; set `DEPLOY_URL` secret in CI |
| OpenRouter API | AiReview | B3 | Third-party AI | B3 start | Low — free credits; $10 cap in code | Create account; add `OPENROUTER_API_KEY` to `.env.local` and to CI secrets |
| NetworkX | LinkGraph | B2 | Python package | B2 start | Low — public PyPI; pinned version | Listed in `pyproject.toml`; installed via `pip install` |

## Notes

- **No dependency blocks B1 construction** — NetworkX and OpenRouter are not needed until B2 and B3; Supabase is needed at B1 but setup is a 5-minute self-service task.
- **All credentials flow through environment variables** — never committed to the repository (project rule: `NEVER commit API keys or other secrets`).
- **CI fake model for OpenRouter** — the `OPENROUTER_API_KEY` is not required in CI; a `FAKE_LLM=1` env flag switches the AI client to the deterministic stub.

## Sources

- [desc] Digital Fraud Investigation System — hackathon MVP
- [scope] mvp
- `inception/domain-design/components.md`
