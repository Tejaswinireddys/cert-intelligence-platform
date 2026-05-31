// Types mirror API_CONTRACT.md exactly.

export type Tier = 'P1' | 'P2' | 'P3' | 'OK';
export type Routing = 'AUTO' | 'AI_SUGGEST' | 'STEWARD_TRIAGE';
export type Environment = 'prod' | 'dev' | 'test' | 'staging';
export type Criticality = 'critical' | 'high' | 'medium' | 'low';

export interface Health {
  status: string;
  mode: 'MOCK' | 'LIVE';
  version: string;
  time: string;
}

export interface TierCounts {
  P1: number;
  P2: number;
  P3: number;
  OK: number;
}

export interface Summary {
  total_certs: number;
  tier_counts: TierCounts;
  sla_compliance_pct: number;
  renewed_this_week: number;
  renewed_this_month: number;
  orphan_count: number;
  dlq_count: number;
  coverage_pct: number;
  avg_days_to_renew: number;
}

export interface Certificate {
  serial: string;
  thumbprint: string;
  common_name: string;
  sans: string[];
  ca: string;
  template: string;
  valid_from: string;
  valid_to: string;
  days_left: number;
  environment: Environment;
  criticality: Criticality;
  application_ci: string;
  server_ci: string;
  owner_group: string;
  escalation_path: string;
  renewal_method: string;
  deploy_method: string;
  key_handling_policy: string;
  last_verified_endpoint: string;
  last_verified_port: number;
  risk_score: number;
  tier: Tier;
  owner_confidence: number;
  routing: Routing;
  status: string;
  jira_key: string;
}

export interface CertList {
  total: number;
  items: Certificate[];
}

export type EventType =
  | 'scanned'
  | 'scored'
  | 'ticket_created'
  | 'notified'
  | 'renewal_requested'
  | 'renewed'
  | 'deployed'
  | 'verified'
  | 'closed'
  | 'dlq';

export type Actor =
  | 'engine'
  | 'jira_agent'
  | 'renewal_agent'
  | 'notify_agent'
  | 'cmdb_agent'
  | 'execution';

export interface CertEvent {
  id: string;
  type: EventType;
  tier: Tier;
  ts: string;
  detail: string;
  actor: Actor;
}

export interface AiSuggestion {
  suggested_owner: string;
  confidence: number;
  human_final: string;
  ts: string;
}

export interface CertDetail {
  certificate: Certificate;
  events: CertEvent[];
  jira_key: string;
  ai_suggestions: AiSuggestion[];
}

export interface HeatmapRow {
  owner_group: string;
  buckets: number[];
  total: number;
}

export interface Heatmap {
  windows: string[];
  rows: HeatmapRow[];
}

export interface TrendPoint {
  week: string;
  renewed: number;
  expiring: number;
  sla_pct: number;
}

export interface Trend {
  points: TrendPoint[];
}

export interface Orphan {
  serial: string;
  common_name: string;
  owner_confidence: number;
  reason: string;
  tier: Tier;
  days_left: number;
}

export interface OrphanList {
  items: Orphan[];
}

export interface DlqEntry {
  id: string;
  event_type: string;
  serial: string;
  attempts: number;
  last_error: string;
  ts: string;
}

export interface DlqList {
  items: DlqEntry[];
}

export interface AuditEntry {
  id: string;
  ts: string;
  actor: string;
  action: string;
  serial: string;
  idempotency_key: string;
  outcome: string;
  detail: string;
}

export interface AuditList {
  total: number;
  items: AuditEntry[];
}

export interface ScanResult {
  scanned: number;
  new_events: number;
  tier_counts: { P1: number; P2: number; P3: number };
}

export interface ApproveResult {
  serial: string;
  approved: boolean;
  by: string;
  jira_key: string;
  next: string;
}

export interface RenewResult {
  serial: string;
  saga: string;
  events: CertEvent[];
}

export interface AssignResult {
  serial: string;
  owner_group: string;
  routing: Routing;
}
