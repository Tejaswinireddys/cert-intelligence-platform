# API Contract — Backend ⇄ Dashboard

The FastAPI backend exposes these endpoints under `/api`. The Next.js dashboard
consumes them. This contract is frozen — both sides build against it.

Base URL (dev): `http://localhost:8000`

All list endpoints return JSON. All timestamps are ISO-8601 UTC strings.

---

## GET /api/health
```json
{ "status": "ok", "mode": "MOCK", "version": "1.0.0", "time": "2026-05-30T20:00:00Z" }
```

## GET /api/summary
Top-line dashboard KPIs.
```json
{
  "total_certs": 142,
  "tier_counts": { "P1": 6, "P2": 18, "P3": 41, "OK": 77 },
  "sla_compliance_pct": 94.3,
  "renewed_this_week": 12,
  "renewed_this_month": 38,
  "orphan_count": 9,
  "dlq_count": 2,
  "coverage_pct": 96.1,
  "avg_days_to_renew": 3.4
}
```

## GET /api/certificates
Query params: `tier` (P1|P2|P3|OK), `environment`, `owner_group`, `routing`
(AUTO|AI_SUGGEST|STEWARD_TRIAGE), `search` (CN/SAN/serial), `limit`, `offset`.
```json
{
  "total": 142,
  "items": [
    {
      "serial": "0A1B2C...",
      "thumbprint": "sha1:...",
      "common_name": "api.example.com",
      "sans": ["api.example.com", "auth.example.com"],
      "ca": "DigiCert",
      "template": "prod-tls",
      "valid_from": "2025-06-01T00:00:00Z",
      "valid_to": "2026-06-05T00:00:00Z",
      "days_left": 6,
      "environment": "prod",
      "criticality": "critical",
      "application_ci": "APP-1042",
      "server_ci": "SRV-3310",
      "owner_group": "Payments Platform",
      "escalation_path": "payments-oncall",
      "renewal_method": "venafi-driver",
      "deploy_method": "venafi-driver",
      "key_handling_policy": "venafi",
      "last_verified_endpoint": "api.example.com",
      "last_verified_port": 443,
      "risk_score": 9.0,
      "tier": "P1",
      "owner_confidence": 0.93,
      "routing": "AUTO",
      "status": "open",
      "jira_key": "CERT-318"
    }
  ]
}
```

## GET /api/certificates/{serial}
Single cert + its event timeline + linked Jira/CMDB refs.
```json
{ "certificate": { ...as above... },
  "events": [ { "id": "...", "type": "scanned|scored|ticket_created|notified|renewal_requested|renewed|deployed|verified|closed|dlq", "tier": "P1", "ts": "...", "detail": "...", "actor": "engine|jira_agent|renewal_agent|notify_agent|cmdb_agent|execution" } ],
  "jira_key": "CERT-318",
  "ai_suggestions": [ { "suggested_owner": "Payments Platform", "confidence": 0.62, "human_final": "Payments Platform", "ts": "..." } ]
}
```

## GET /api/heatmap
Expiry heatmap: certs bucketed by owner_group × expiry window.
```json
{
  "windows": ["<7d", "8-30d", "31-60d", "61-90d", ">90d"],
  "rows": [
    { "owner_group": "Payments Platform", "buckets": [2, 3, 1, 4, 10], "total": 20 },
    { "owner_group": "Identity", "buckets": [0, 1, 5, 2, 14], "total": 22 }
  ]
}
```

## GET /api/trend
Renewal & expiry trend over time (for line chart).
```json
{
  "points": [
    { "week": "2026-W18", "renewed": 8, "expiring": 12, "sla_pct": 91.0 },
    { "week": "2026-W19", "renewed": 11, "expiring": 9, "sla_pct": 95.0 }
  ]
}
```

## GET /api/orphans
Certs in steward-triage (confidence < 0.50) or unresolved owner.
```json
{ "items": [ { "serial": "...", "common_name": "...", "owner_confidence": 0.31, "reason": "no CMDB CI match", "tier": "P2", "days_left": 22 } ] }
```

## GET /api/dlq
Dead-letter queue entries (failed events after N retries).
```json
{ "items": [ { "id": "...", "event_type": "...", "serial": "...", "attempts": 5, "last_error": "Venafi 429 rate limit", "ts": "..." } ] }
```

## GET /api/audit
Append-only audit log (paginated). `?limit=&offset=&serial=`
```json
{ "total": 540, "items": [ { "id": "...", "ts": "...", "actor": "...", "action": "renewal_requested", "serial": "...", "idempotency_key": "...:2026-W23", "outcome": "ok", "detail": "..." } ] }
```

## POST /api/scan
Trigger an on-demand scan (returns counts). Body: `{}` or `{ "windows": [7,30,60,90] }`.
```json
{ "scanned": 142, "new_events": 23, "tier_counts": { "P1": 6, "P2": 18, "P3": 41 } }
```

## POST /api/certificates/{serial}/approve
Human approval transition for a production renewal (simulates Jira transition).
```json
{ "serial": "...", "approved": true, "by": "user", "jira_key": "CERT-318", "next": "renewal_requested" }
```

## POST /api/certificates/{serial}/renew
Kick the renew→deploy→verify saga for one cert (dev/test auto, prod requires prior approve).
```json
{ "serial": "...", "saga": "renewed|deployed|verified|renewed-not-deployed|rollback", "events": [ ... ] }
```

## POST /api/orphans/{serial}/assign
Steward assigns an owner (logs AI-suggestion vs human-final for accuracy loop).
Body: `{ "owner_group": "Payments Platform" }`
```json
{ "serial": "...", "owner_group": "Payments Platform", "routing": "AUTO" }
```

## WS /api/ws  (optional live updates)
Pushes `{ "type": "event", "payload": {...} }` on new engine events. Dashboard
may poll `/api/summary` every 10s as a fallback if WS is unavailable.
