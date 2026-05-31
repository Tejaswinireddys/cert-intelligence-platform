// Realistic mock dataset that mirrors every endpoint shape in API_CONTRACT.md.
// Used as a fallback when the backend is unreachable, and forced on when
// NEXT_PUBLIC_USE_MOCK=true. The fleet totals 142 certs with tier mix
// P1:6 / P2:18 / P3:41 / OK:77.

import type {
  Summary,
  Certificate,
  CertList,
  CertDetail,
  CertEvent,
  Heatmap,
  Trend,
  OrphanList,
  DlqList,
  AuditList,
  AuditEntry,
  ScanResult,
  ApproveResult,
  RenewResult,
  AssignResult,
  Health,
  Tier,
  Routing,
  Environment,
  Criticality,
} from './types';

export const OWNER_GROUPS = [
  'Payments Platform',
  'Identity',
  'Edge & CDN',
  'Data Platform',
  'Core Banking',
  'Customer API',
  'Internal Tools',
  'Unassigned',
];

const CAS = ['DigiCert', 'Let\u2019s Encrypt', 'Sectigo', 'Internal PKI', 'GlobalSign'];
const ENVS: Environment[] = ['prod', 'staging', 'dev', 'test'];
const CRITS: Criticality[] = ['critical', 'high', 'medium', 'low'];

const DOMAINS = [
  'api', 'auth', 'gateway', 'checkout', 'ledger', 'identity', 'cdn', 'assets',
  'reports', 'admin', 'vault', 'broker', 'stream', 'metrics', 'login', 'pay',
  'wallet', 'kyc', 'risk', 'notify', 'webhook', 'edge', 'static', 'media',
];

// Deterministic PRNG so the demo is stable across reloads.
function makeRng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 0xffffffff;
  };
}
const rng = makeRng(20260530);

function pick<T>(arr: T[]): T {
  return arr[Math.floor(rng() * arr.length)];
}

function hex(n: number): string {
  let out = '';
  for (let i = 0; i < n; i++) out += Math.floor(rng() * 16).toString(16).toUpperCase();
  return out;
}

function isoFromNow(days: number): string {
  const d = new Date('2026-05-30T20:00:00Z');
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString();
}

function tierFromDays(days: number, crit: Criticality): Tier {
  if (days <= 7 && (crit === 'critical' || crit === 'high')) return 'P1';
  if (days <= 30) return 'P2';
  if (days <= 60) return 'P3';
  return 'OK';
}

// Build a fleet whose tier distribution matches the contract exactly.
function buildFleet(): Certificate[] {
  const plan: { tier: Tier; count: number; daysRange: [number, number] }[] = [
    { tier: 'P1', count: 6, daysRange: [-1, 7] },
    { tier: 'P2', count: 18, daysRange: [8, 30] },
    { tier: 'P3', count: 41, daysRange: [31, 60] },
    { tier: 'OK', count: 77, daysRange: [61, 300] },
  ];

  const certs: Certificate[] = [];
  let idx = 0;

  for (const group of plan) {
    for (let i = 0; i < group.count; i++) {
      idx++;
      const [lo, hi] = group.daysRange;
      const daysLeft = Math.floor(lo + rng() * (hi - lo));
      const sub = pick(DOMAINS);
      const root = pick(['example.com', 'acme-bank.io', 'fintrust.net', 'corp.internal']);
      const cn = `${sub}.${root}`;
      const sanCount = 1 + Math.floor(rng() * 3);
      const sans = [cn];
      for (let s = 1; s < sanCount; s++) sans.push(`${pick(DOMAINS)}.${root}`);

      const crit = group.tier === 'P1' ? pick(['critical', 'high'] as Criticality[]) : pick(CRITS);
      const env = group.tier === 'P1' ? 'prod' : pick(ENVS);

      // Owner confidence drives routing.
      let confidence: number;
      let routing: Routing;
      let ownerGroup: string;
      const roll = rng();
      if (roll < 0.12) {
        confidence = 0.18 + rng() * 0.3; // < 0.5 -> steward triage / orphan
        routing = 'STEWARD_TRIAGE';
        ownerGroup = rng() < 0.5 ? 'Unassigned' : pick(OWNER_GROUPS);
      } else if (roll < 0.32) {
        confidence = 0.5 + rng() * 0.2;
        routing = 'AI_SUGGEST';
        ownerGroup = pick(OWNER_GROUPS.slice(0, 7));
      } else {
        confidence = 0.78 + rng() * 0.21;
        routing = 'AUTO';
        ownerGroup = pick(OWNER_GROUPS.slice(0, 7));
      }

      const riskBase =
        group.tier === 'P1' ? 8.5 : group.tier === 'P2' ? 6 : group.tier === 'P3' ? 3.5 : 1.5;

      certs.push({
        serial: hex(16),
        thumbprint: `sha1:${hex(40).toLowerCase()}`,
        common_name: cn,
        sans,
        ca: pick(CAS),
        template: env === 'prod' ? 'prod-tls' : `${env}-tls`,
        valid_from: isoFromNow(daysLeft - 365),
        valid_to: isoFromNow(daysLeft),
        days_left: daysLeft,
        environment: env,
        criticality: crit,
        application_ci: `APP-${1000 + Math.floor(rng() * 900)}`,
        server_ci: `SRV-${3000 + Math.floor(rng() * 900)}`,
        owner_group: ownerGroup,
        escalation_path: `${ownerGroup.toLowerCase().replace(/[^a-z]+/g, '-')}-oncall`,
        renewal_method: pick(['venafi-driver', 'acme-client', 'manual-csr']),
        deploy_method: pick(['venafi-driver', 'k8s-cert-manager', 'f5-irule']),
        key_handling_policy: pick(['venafi', 'hsm-backed', 'sealed-secret']),
        last_verified_endpoint: cn,
        last_verified_port: pick([443, 8443, 9443]),
        risk_score: Math.round((riskBase + rng() * 1.4) * 10) / 10,
        tier: group.tier,
        owner_confidence: Math.round(confidence * 100) / 100,
        routing,
        status: pick(['open', 'in_progress', 'open', 'resolved']),
        jira_key: `CERT-${300 + idx}`,
      });
    }
  }
  return certs;
}

export const FLEET: Certificate[] = buildFleet();

export const mockHealth: Health = {
  status: 'ok',
  mode: 'MOCK',
  version: '1.0.0',
  time: isoFromNow(0),
};

export const mockSummary: Summary = {
  total_certs: 142,
  tier_counts: { P1: 6, P2: 18, P3: 41, OK: 77 },
  sla_compliance_pct: 94.3,
  renewed_this_week: 12,
  renewed_this_month: 38,
  orphan_count: 9,
  dlq_count: 2,
  coverage_pct: 96.1,
  avg_days_to_renew: 3.4,
};

export function mockCertificates(params?: Record<string, string>): CertList {
  let items = [...FLEET];
  if (params) {
    if (params.tier) items = items.filter((c) => c.tier === params.tier);
    if (params.environment) items = items.filter((c) => c.environment === params.environment);
    if (params.owner_group) items = items.filter((c) => c.owner_group === params.owner_group);
    if (params.routing) items = items.filter((c) => c.routing === params.routing);
    if (params.search) {
      const q = params.search.toLowerCase();
      items = items.filter(
        (c) =>
          c.common_name.toLowerCase().includes(q) ||
          c.serial.toLowerCase().includes(q) ||
          c.sans.some((s) => s.toLowerCase().includes(q)),
      );
    }
  }
  const total = items.length;
  const offset = params?.offset ? parseInt(params.offset, 10) : 0;
  const limit = params?.limit ? parseInt(params.limit, 10) : items.length;
  return { total, items: items.slice(offset, offset + limit) };
}

const EVENT_FLOW: { type: CertEvent['type']; actor: CertEvent['actor']; detail: string }[] = [
  { type: 'scanned', actor: 'engine', detail: 'Discovered via network scan on :443' },
  { type: 'scored', actor: 'engine', detail: 'Risk scored against expiry + criticality model' },
  { type: 'ticket_created', actor: 'jira_agent', detail: 'Jira issue opened and linked to CMDB CI' },
  { type: 'notified', actor: 'notify_agent', detail: 'Owner group paged via escalation path' },
  { type: 'renewal_requested', actor: 'renewal_agent', detail: 'Renewal saga kicked (idempotent)' },
  { type: 'renewed', actor: 'execution', detail: 'New certificate issued by CA' },
  { type: 'deployed', actor: 'execution', detail: 'Deployed by execution plane (driver-managed)' },
  { type: 'verified', actor: 'engine', detail: 'TLS handshake verified on live endpoint' },
  { type: 'closed', actor: 'jira_agent', detail: 'Jira issue transitioned to Done' },
];

export function mockCertDetail(serial: string): CertDetail {
  const cert = FLEET.find((c) => c.serial === serial) ?? FLEET[0];
  const steps = cert.tier === 'OK' ? 4 : cert.tier === 'P3' ? 6 : EVENT_FLOW.length;
  const events: CertEvent[] = EVENT_FLOW.slice(0, steps).map((e, i) => ({
    id: `${cert.serial}-ev-${i}`,
    type: e.type,
    tier: cert.tier,
    ts: isoFromNow(-steps + i),
    detail: e.detail,
    actor: e.actor,
  }));

  const ai = cert.owner_confidence;
  return {
    certificate: cert,
    events,
    jira_key: cert.jira_key,
    ai_suggestions: [
      {
        suggested_owner: cert.owner_group === 'Unassigned' ? 'Identity' : cert.owner_group,
        confidence: Math.max(0.4, ai - 0.1),
        human_final: cert.owner_group === 'Unassigned' ? '' : cert.owner_group,
        ts: isoFromNow(-2),
      },
    ],
  };
}

export const mockHeatmap: Heatmap = {
  windows: ['<7d', '8-30d', '31-60d', '61-90d', '>90d'],
  rows: [
    { owner_group: 'Payments Platform', buckets: [2, 4, 6, 4, 8], total: 24 },
    { owner_group: 'Identity', buckets: [1, 3, 7, 3, 9], total: 23 },
    { owner_group: 'Edge & CDN', buckets: [1, 2, 5, 3, 9], total: 20 },
    { owner_group: 'Data Platform', buckets: [0, 2, 4, 4, 7], total: 17 },
    { owner_group: 'Core Banking', buckets: [1, 3, 6, 2, 6], total: 18 },
    { owner_group: 'Customer API', buckets: [1, 2, 4, 3, 6], total: 16 },
    { owner_group: 'Internal Tools', buckets: [0, 1, 5, 2, 7], total: 15 },
    { owner_group: 'Unassigned', buckets: [0, 1, 4, 1, 3], total: 9 },
  ],
};

export const mockTrend: Trend = {
  points: [
    { week: '2026-W14', renewed: 6, expiring: 14, sla_pct: 88.0 },
    { week: '2026-W15', renewed: 9, expiring: 11, sla_pct: 90.5 },
    { week: '2026-W16', renewed: 7, expiring: 13, sla_pct: 89.2 },
    { week: '2026-W17', renewed: 10, expiring: 10, sla_pct: 92.0 },
    { week: '2026-W18', renewed: 8, expiring: 12, sla_pct: 91.0 },
    { week: '2026-W19', renewed: 11, expiring: 9, sla_pct: 95.0 },
    { week: '2026-W20', renewed: 13, expiring: 8, sla_pct: 95.8 },
    { week: '2026-W21', renewed: 12, expiring: 7, sla_pct: 96.4 },
    { week: '2026-W22', renewed: 12, expiring: 6, sla_pct: 94.3 },
  ],
};

export const mockOrphans: OrphanList = {
  items: FLEET.filter((c) => c.owner_confidence < 0.5 || c.owner_group === 'Unassigned')
    .slice(0, 9)
    .map((c) => ({
      serial: c.serial,
      common_name: c.common_name,
      owner_confidence: c.owner_confidence,
      reason: pick([
        'no CMDB CI match',
        'ambiguous owner group',
        'CI decommissioned',
        'multiple candidate owners',
        'low DNS attribution score',
      ]),
      tier: c.tier,
      days_left: c.days_left,
    })),
};

export const mockDlq: DlqList = {
  items: [
    {
      id: 'dlq-001',
      event_type: 'renewal_requested',
      serial: FLEET[0].serial,
      attempts: 5,
      last_error: 'Venafi 429 rate limit',
      ts: isoFromNow(-1),
    },
    {
      id: 'dlq-002',
      event_type: 'deployed',
      serial: FLEET[3].serial,
      attempts: 4,
      last_error: 'F5 iControl REST timeout after 30s',
      ts: isoFromNow(0),
    },
  ],
};

const AUDIT_ACTIONS = [
  'scan_triggered',
  'ticket_created',
  'renewal_requested',
  'renewed',
  'deployed',
  'verified',
  'owner_assigned',
  'approval_granted',
  'notify_sent',
];
const AUDIT_ACTORS = ['user', 'engine', 'jira_agent', 'renewal_agent', 'cmdb_agent', 'execution'];

function buildAudit(): AuditEntry[] {
  const out: AuditEntry[] = [];
  for (let i = 0; i < 540; i++) {
    const cert = FLEET[i % FLEET.length];
    const action = AUDIT_ACTIONS[i % AUDIT_ACTIONS.length];
    out.push({
      id: `aud-${String(540 - i).padStart(4, '0')}`,
      ts: isoFromNow(-Math.floor(i / 6)),
      actor: AUDIT_ACTORS[i % AUDIT_ACTORS.length],
      action,
      serial: cert.serial,
      idempotency_key: `${cert.serial.slice(0, 8)}:2026-W${22 - (i % 8)}`,
      outcome: i % 17 === 0 ? 'retry' : 'ok',
      detail: `${action} for ${cert.common_name}`,
    });
  }
  return out;
}
const AUDIT = buildAudit();

export function mockAudit(params?: Record<string, string>): AuditList {
  let items = AUDIT;
  if (params?.serial) items = items.filter((a) => a.serial === params.serial);
  const total = items.length;
  const offset = params?.offset ? parseInt(params.offset, 10) : 0;
  const limit = params?.limit ? parseInt(params.limit, 10) : 25;
  return { total, items: items.slice(offset, offset + limit) };
}

export function mockScan(): ScanResult {
  return { scanned: 142, new_events: 23, tier_counts: { P1: 6, P2: 18, P3: 41 } };
}

export function mockApprove(serial: string): ApproveResult {
  const cert = FLEET.find((c) => c.serial === serial) ?? FLEET[0];
  return {
    serial,
    approved: true,
    by: 'user',
    jira_key: cert.jira_key,
    next: 'renewal_requested',
  };
}

export function mockRenew(serial: string): RenewResult {
  const detail = mockCertDetail(serial);
  return { serial, saga: 'verified', events: detail.events };
}

export function mockAssign(serial: string, owner_group: string): AssignResult {
  return { serial, owner_group, routing: 'AUTO' };
}
