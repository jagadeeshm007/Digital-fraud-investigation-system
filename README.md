# Digital Fraud Investigation System (DFIS)

**Team Ozys · Azentio.ai Build Labs 2026** · Live: https://dfis-gray.vercel.app

## What it is

DFIS is a fraud investigation console for a bank that runs lending, insurance and core banking.

- It loads customer profiles, accounts, transactions, device and login logs, loan applications and
  insurance claims from CSV, Excel or JSON. Every rejected row is reported with the reason.
- It detects suspicious transfers, shared devices, account takeover, loan rings, duplicate claims
  and synthetic identities.
- Every alert gets a 0 to 100 risk score, and each point is explained by a factor that cites its
  evidence.
- Legitimate lookalikes, such as regular rent payments or a household sharing a phone, are cleared
  with a stated reason.
- An AI second opinion (Groq) adjusts a score by at most ±10 and may only cite real evidence.
- Analysts work alerts and cases from a role-based console:
  - Roles: Analyst, Investigator, Supervisor.
  - Personal data is masked; only a Supervisor can reveal it, and every reveal is audited.
  - Every action goes to the audit trail.
- An MCP server lets Claude and other AI assistants read cases and, with the user's consent, record
  decisions.

Stack: FastAPI + PostgreSQL + React (Vite+, coss ui, React Flow).

## Run it with Docker (recommended)

You need Docker. This runs the app and its own Postgres entirely on your machine.

```bash
cp .env.example .env     # set MASKING_HMAC_KEY (openssl rand -hex 32); optional GROQ_API_KEY
docker compose up -d --build
```

Open http://localhost:8000.

**Load demo data:** on **Data Upload**, press **Load sample data**. Then switch the role to
**Investigator** and press **Run detection** on **Alerts**.

Useful commands:

| Command | What it does |
|---|---|
| `docker compose logs -f app` | Follow the app logs |
| `FAKE_LLM=1 docker compose up -d` | Run without real AI calls (an offline stub) |
| `docker compose down` | Stop and keep the data |
| `docker compose down -v` | Stop and delete the data |

## Run it without Docker

You need Python 3.11+, Node 22+ and a PostgreSQL database. Set `DATABASE_URL` in `.env`.

```bash
cp .env.example .env
pip install -e .
cd frontend && npm ci && npm run build && cd ..
SERVE_FRONTEND=1 uvicorn app.main:app --port 8000
```

For frontend development with hot reload, run `npm run dev` in `frontend/`. It serves on :5173 and
sends API requests to :8000.

## Connect Claude (MCP)

With the app running:

```bash
claude mcp add --transport http dfis http://localhost:8000/mcp --header "X-Role: investigator"
```

Start a new Claude Code session and ask, for example, "use dfis to show the dashboard". Writes
always ask you to confirm first.

## Tests

```bash
pytest
```
