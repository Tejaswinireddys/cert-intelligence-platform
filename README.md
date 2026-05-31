# Certificate Intelligence Platform

A production-grade, agentic platform for discovering, scoring, renewing, and deploying TLS/SSL certificates across an enterprise fleet — with a deterministic control plane, scoped AI agents that **never touch keys or servers**, and a rich Next.js operations dashboard.

> Runs **out of the box in MOCK mode** with a simulated 140+ certificate fleet, seeded data, mock Venafi/Jira/Teams/CMDB/Vault adapters, and a live dashboard. Add real credentials later to flip individual integrations to **LIVE**.

---

## Why this design

This platform enforces a hard separation between *deciding* and *doing*:

| Plane | Responsibility | Touches keys/servers? | AI involved? |
| --- | --- | --- | --- |
| **Control plane** | Scan, score, route, decide | No | No (deterministic) |
| **Intelligence engine** | Scorer, dedup, resolver, bus | No | No (plain Python) |
| **AI agents** | Enrich, draft tickets/messages, suggest ambiguous owners | No (signed, scoped tools only) | Yes |
| **Execution plane** | Renew → deploy → verify (with rollback) | Yes (and only here) | No |

Core invariants (also in `CLAUDE.md`):

- The Intelligence Engine (scanner, scorer, dedup, renew) is **plain Python — no LLM calls**.
- LLM agents may only **enrich, draft messages, and suggest** ambiguous owners. They call **signed, scoped tools** and can never reach a forbidden tool.
- **Private keys never enter** Jira, Teams, logs, prompts, or agent memory. Agents see cert serial / thumbprint only.
- Every state change is **idempotent** — key = `cert_serial + renewal_window`.
- **Production** renewal/deploy requires a **human approval** (Jira transition). Dev/test may auto-approve.
- **Freeze windows** (Friday evening + weekends) block production deploys.
- **Append-only audit** event for every renewal, deploy, and close.

---

## Architecture

```
                 ┌──────────────────────── Control Plane (deterministic) ────────────────────────┐
                 │                                                                                │
  Venafi  ──────▶│  Scanner ──▶ Dedup ──▶ Scorer ──▶ Resolver ──▶ Event Bus (per-tier + DLQ)      │
  (TPP/VCP)      │     │                     │           │                  │                      │
                 │  search_all          P1/P2/P3/OK  CMDB joins        retry + backoff             │
                 └─────┼─────────────────────┼───────────┼──────────────────┼──────────────────────┘
                       │                      │           │                  │
                       ▼                      ▼           ▼                  ▼
             ┌─────────────────── AI Agents (scoped, signed tools — never hold keys) ──────────────┐
             │  Orchestrator ─▶ Jira Agent · Renewal Agent · Notify Agent · CMDB Agent             │
             └────────────────────────────────────┬───────────────────────────────────────────────┘
                                                   │  signed, time-boxed deploy request
                                                   ▼
             ┌──────────────── Execution Plane (the ONLY place keys/servers are touched) ──────────┐
             │  Trigger ─▶ Venafi Driver (renew) ─▶ Ansible Runner (deploy) ─▶ Verify (SSL probe)   │
             │                              Saga with compensation / rollback · freeze windows      │
             └──────────────────────────────────────────────────────────────────────────────────────┘

   Integrations: Jira · Microsoft Teams · CMDB · Vault     |     API: FastAPI (webhooks + dashboard)
   Storage: SQLite (default) / Postgres-ready              |     UI: Next.js 14 + React 18 + Recharts
```

---

## Risk scoring (deterministic, 100% test-covered)

`score = weight × 1 / max(days_to_expiry, 1)` where `weight = environment_multiplier`:

| Environment | Multiplier |
| --- | --- |
| prod | ×3 |
| staging | ×2 |
| dev / test | ×1 |

Tiers by days-to-expiry: **P1** `< 7d` · **P2** `7–30d` · **P3** `31–90d` · **OK** `> 90d`.

Owner routing by resolver confidence: `≥ 0.80 → AUTO` · `≥ 0.50 → AI_SUGGEST` · else `STEWARD_TRIAGE`.

---

## Repository layout

```
cert-intelligence-platform/
├── CLAUDE.md                 # Architectural invariants (read every session)
├── API_CONTRACT.md           # Full REST contract the dashboard consumes
├── README.md                 # This file
├── pyproject.toml            # Python package + deps
├── docker-compose.yml        # api + dashboard (+ commented Postgres/Redis/Vault for LIVE)
├── Dockerfile
├── .env.example              # All CIP_* settings, MOCK/LIVE toggles
├── playbooks/
│   └── deploy_cert.yml       # Signed Ansible playbook (execution plane)
├── scripts/
│   └── run_api.sh            # PYTHONPATH=src uvicorn launcher
├── src/cip/
│   ├── config.py             # Settings + SecretResolver (env / vault backends)
│   ├── db.py                 # SQLAlchemy ORM, SQLite default, Postgres-ready
│   ├── app.py                # FastAPI factory (lifespan seeds initial scan)
│   ├── scheduler.py          # APScheduler daily scan
│   ├── audit/log.py          # Append-only audit (scrubs key material)
│   ├── models/               # Pydantic: certificate, owner, event
│   ├── venafi/               # client (TPP/VCP) + mock simulated fleet
│   ├── engine/               # scanner, scorer, dedup, resolver, bus, renew
│   ├── agents/               # orchestrator + jira/renewal/notify/cmdb + tools, llm
│   ├── execution/            # trigger, venafi_driver, ansible_runner, verify, saga
│   ├── integrations/         # jira, teams, cmdb, vault (MOCK + LIVE)
│   └── api/                  # dashboard.py (REST), webhooks.py
├── tests/                    # scorer (100%), dedup (100%), idempotency, tool scopes
└── dashboard/                # Next.js 14 App Router + Tailwind + Recharts
    ├── app/                  # /, /certificates, /heatmap, /orphans, /dlq, /audit
    ├── components/
    └── lib/                  # api.ts (LIVE w/ mock fallback), mockData.ts, types.ts
```

---

## Quickstart

No Docker required. You only need **Python 3.11+** and **Node 18+**.

### Option A — Run locally without Docker (recommended)

**One-time setup** — creates the Python venv, installs the backend + dev deps, and installs the dashboard's npm packages:

```bash
cp .env.example .env           # defaults to MOCK mode (runs fully offline)
bash scripts/bootstrap.sh
```

Then open **two terminals**:

```bash
# Terminal 1 — backend
bash scripts/run_api.sh        # -> http://localhost:8000  (docs at /docs)

# Terminal 2 — dashboard
bash scripts/run_dashboard.sh  # -> http://localhost:3000
```

That's it. The dashboard shows a green **LIVE** badge when the backend is reachable and **falls back to bundled mock data** (with a **MOCK** badge) when it is not — so the UI always renders. If port 3000 is busy, Next.js uses 3001/3002, which the backend's default CORS already allows.

<details>
<summary>Prefer manual steps instead of the helper scripts?</summary>

```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
PYTHONPATH=src python -m uvicorn cip.app:app --port 8000

# Dashboard (separate terminal)
cd dashboard && npm install && npm run dev
```
</details>

### Option B — Docker Compose (optional)

```bash
cp .env.example .env
docker compose up --build
# API:        http://localhost:8000
# Dashboard:  http://localhost:3000
```

### Static demo build (self-contained, no backend)

```bash
cd dashboard
NEXT_PUBLIC_USE_MOCK=true NEXT_PUBLIC_ASSET_PREFIX=. npm run build   # → ./out
npx serve out
```

This is exactly how the hosted live demo is produced.

---

## MOCK vs LIVE

Everything is controlled by `CIP_MODE` and per-integration credentials in `.env` (see `.env.example`).

| Concern | MOCK (default) | LIVE |
| --- | --- | --- |
| Venafi | Simulated 140+ cert fleet | TPP / VCP REST with token auth |
| Jira / Teams / CMDB | In-memory adapters | Real REST clients (API tokens) |
| Vault | Env-backed secret resolver | HashiCorp Vault / KMS |
| LLM agent drafts | Deterministic templates | OpenAI (key from Vault) |
| Database | SQLite (`data/cip.db`) | Postgres via `CIP_DATABASE_URL` |

Flip the whole platform with `CIP_MODE=LIVE` and supply credentials; flip individual integrations by providing only their credentials. No code changes required.

---

## API surface

All endpoints are under `/api` (full schema in `API_CONTRACT.md`):

`GET /health` · `GET /summary` · `GET /certificates` · `GET /certificates/{serial}` ·
`GET /heatmap` · `GET /trend` · `GET /orphans` · `GET /dlq` · `GET /audit` ·
`POST /scan` · `POST /certificates/{serial}/approve` · `POST /certificates/{serial}/renew` ·
`POST /orphans/{serial}/assign`

Webhooks (Venafi / Jira callbacks) live under `src/cip/api/webhooks.py`.

---

## Testing

```bash
pytest                         # 30 tests
pytest --cov=cip --cov-report=term-missing
```

- **Scorer** and **dedup** carry **100% line coverage** (enforced invariant).
- Idempotency, tool-scope enforcement (forbidden tools rejected), and the certificate model are also covered.

---

## Dashboard pages

- **Overview** — 10 KPI cards (total, P1/P2/P3/OK, SLA %, owner coverage, renewed/week, orphans, DLQ), expiry heatmap (owner group × expiry window), renewal/expiry trend, and risk-tier distribution. Auto-refreshes every 10s.
- **Certificates** — searchable, filterable inventory (tier / env / routing); detail drawer with timeline, AI ownership suggestions, and Approve + Renew actions.
- **Heatmap** — full-screen expiry heatmap.
- **Orphan Queue** — low-confidence / unassigned certs with one-click owner assignment.
- **DLQ** — dead-lettered events with last error and attempt count.
- **Audit Log** — append-only event stream (actor, action, cert, timestamp).

---

## Security notes

- Keys live only in the execution plane and are pulled from Vault/KMS at runtime; they are scrubbed from all logs and audit entries.
- Agents operate through HMAC-signed, scoped tool calls; `FORBIDDEN_TOOLS` are hard-blocked regardless of scope.
- Deploy requests are signed and time-boxed; the saga rolls back on verification failure.
- Disable Venafi native auto-renew on any zone this platform controls (so the two don't race).
