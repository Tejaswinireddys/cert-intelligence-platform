# Certificate Intelligence Platform — Dashboard (Layer 4)

Production-grade operations dashboard for an automated TLS certificate lifecycle
management system. Built with **Next.js 14 (App Router) + React 18 + TypeScript +
Tailwind CSS + Recharts + lucide-react**.

## Requirements

- Node 20 (tested on v20.20.1)

## Install & Run

```bash
cd cert-intelligence-platform/dashboard
npm install

# Development server (http://localhost:3000, hot reload)
npm run dev

# Production static export -> ./out  (output: 'export' in next.config.js)
npm run build
```

The build is statically exported to `./out`. Serve it with any static file server:

```bash
npx serve out          # or: python3 -m http.server -d out 8099
```

Because `next.config.js` sets `output: 'export'`, the same codebase runs as a
normal dev server (`npm run dev`) **and** exports to a static bundle for hosting.

## Backend connection

All data is fetched from the FastAPI backend defined in `API_CONTRACT.md`.

- Base URL is configurable via `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`).
- All endpoints live under `/api` (e.g. `GET ${NEXT_PUBLIC_API_BASE}/api/summary`).
- Copy `.env.example` to `.env.local` to override.

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000   # backend base URL
NEXT_PUBLIC_USE_MOCK=false                    # set true to force mock mode
```

## Mock fallback — works with NO backend

The dashboard is designed to look fully populated even when no backend is running:

- **`lib/mockData.ts`** generates a realistic, deterministic dataset matching every
  endpoint's exact JSON shape from the contract: a fleet of **142 certificates** with
  tier mix **P1:6 / P2:18 / P3:41 / OK:77**, an owner-group × expiry-window heatmap, a
  9-week renewal/expiry/SLA trend, a 9-entry orphan queue, a 2-entry DLQ, and a 540-row
  paginated audit log. Cert detail includes an event timeline and AI ownership
  suggestions (suggested vs human-final).
- **`lib/api.ts`** is the API client. Every call `fetch`es the real backend, and on
  any failure (connection refused, CORS, timeout, non-2xx) it `catch`es and returns the
  matching mock payload. A 4s `AbortController` timeout prevents hanging.
- The global **MOCK / LIVE badge** (top-right) reflects the actual result of the most
  recent fetch — `LIVE` when the backend answered, `MOCK` when it fell back.
- Set **`NEXT_PUBLIC_USE_MOCK=true`** to skip all network calls and force mock mode
  (ideal for a fully static, backend-free demo deployment).

This means the static `./out` bundle can be deployed on its own and will render a
complete, believable dashboard out of the box.

## Auto-refresh

The Overview page polls `GET /api/summary` every **10s** via the `usePoll` hook
(`lib/usePoll.ts`), showing a "Updated HH:MM:SS · auto-refresh 10s" status line.

## Pages

| Route           | Contents                                                                 |
| --------------- | ------------------------------------------------------------------------ |
| `/`             | KPI cards, expiry heatmap, renewal/expiry+SLA trend, risk-tier donut     |
| `/certificates` | Searchable/filterable table (tier, env, routing, search) + detail drawer |
| `/heatmap`      | Full-width expiry heatmap with legend and totals                         |
| `/orphans`      | Low-confidence queue with "Assign Owner" action + accuracy-loop note     |
| `/dlq`          | Dead-letter queue table                                                  |
| `/audit`        | Paginated append-only audit log                                          |

The certificate **detail drawer** (row click → `GET /api/certificates/{serial}`)
shows full metadata, an event timeline (icon per event type), AI ownership
suggestions (suggested vs human-final), and **Approve** (prod only) / **Renew**
action buttons, with an explicit note that agents never touch keys or servers.

The top bar has an on-demand **Run Scan** button (`POST /api/scan`).

## Architecture principle (footer banner)

> Control plane decides · Execution plane deploys · AI enriches, never touches keys or servers.

## Project structure

```
app/                  App Router pages (layout + 6 routes)
components/           Sidebar, Topbar, Footer, Charts, HeatmapGrid, CertDrawer, KpiCard, primitives, AppContext
lib/types.ts          Types mirroring API_CONTRACT.md exactly
lib/mockData.ts       Deterministic mock dataset for every endpoint
lib/api.ts            Fetch-with-mock-fallback client (NEXT_PUBLIC_API_BASE / NEXT_PUBLIC_USE_MOCK)
lib/usePoll.ts        Polling hook (10s auto-refresh on Overview)
lib/ui.ts             Tier/routing metadata, color + formatting helpers
next.config.js        output: 'export', images.unoptimized, trailingSlash
```

## Notes / deviations from the contract

- **No deviations from the JSON shapes.** All types in `lib/types.ts` and all mock
  payloads match the contract field-for-field.
- The **WebSocket** channel (`WS /api/ws`, marked optional in the contract) is not
  implemented; the contract's documented fallback — polling `/api/summary` every 10s —
  is used instead.
- `trailingSlash: true` is set so the static export produces directory-style routes
  (`/audit/index.html`) that work correctly when served from static hosting.
- Next.js pinned to **14.2.35** (patched) rather than 14.2.5 to clear a known security
  advisory; still Next.js 14 App Router as specified.
