// API client. Fetches from the FastAPI backend defined in API_CONTRACT.md and
// FALLS BACK to mock data when the backend is unreachable (try/catch). Set
// NEXT_PUBLIC_USE_MOCK=true to force mock mode (e.g. for a static demo build).

import type {
  Summary,
  CertList,
  CertDetail,
  Heatmap,
  Trend,
  OrphanList,
  DlqList,
  AuditList,
  ScanResult,
  ApproveResult,
  RenewResult,
  AssignResult,
  Health,
} from './types';
import * as mock from './mockData';

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export const FORCE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === 'true';

// Tracks whether the most recent network call fell back to mock data.
export type Mode = 'LIVE' | 'MOCK';

const TIMEOUT_MS = 4000;

async function getJSON<T>(path: string, fallback: () => T): Promise<{ data: T; mode: Mode }> {
  if (FORCE_MOCK) return { data: fallback(), mode: 'MOCK' };
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    const res = await fetch(`${API_BASE}/api${path}`, { signal: ctrl.signal });
    clearTimeout(t);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as T;
    return { data, mode: 'LIVE' };
  } catch {
    return { data: fallback(), mode: 'MOCK' };
  }
}

async function postJSON<T>(
  path: string,
  body: unknown,
  fallback: () => T,
): Promise<{ data: T; mode: Mode }> {
  if (FORCE_MOCK) return { data: fallback(), mode: 'MOCK' };
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    const res = await fetch(`${API_BASE}/api${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body ?? {}),
      signal: ctrl.signal,
    });
    clearTimeout(t);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as T;
    return { data, mode: 'LIVE' };
  } catch {
    return { data: fallback(), mode: 'MOCK' };
  }
}

function qs(params?: Record<string, string | undefined>): string {
  if (!params) return '';
  const clean = Object.entries(params).filter(([, v]) => v != null && v !== '') as [
    string,
    string,
  ][];
  if (!clean.length) return '';
  return '?' + new URLSearchParams(clean).toString();
}

export const api = {
  health: () => getJSON<Health>('/health', () => mock.mockHealth),
  summary: () => getJSON<Summary>('/summary', () => mock.mockSummary),
  certificates: (params?: Record<string, string | undefined>) =>
    getJSON<CertList>(`/certificates${qs(params)}`, () =>
      mock.mockCertificates(cleanParams(params)),
    ),
  certificate: (serial: string) =>
    getJSON<CertDetail>(`/certificates/${serial}`, () => mock.mockCertDetail(serial)),
  heatmap: () => getJSON<Heatmap>('/heatmap', () => mock.mockHeatmap),
  trend: () => getJSON<Trend>('/trend', () => mock.mockTrend),
  orphans: () => getJSON<OrphanList>('/orphans', () => mock.mockOrphans),
  dlq: () => getJSON<DlqList>('/dlq', () => mock.mockDlq),
  audit: (params?: Record<string, string | undefined>) =>
    getJSON<AuditList>(`/audit${qs(params)}`, () => mock.mockAudit(cleanParams(params))),
  scan: (body?: unknown) => postJSON<ScanResult>('/scan', body, () => mock.mockScan()),
  approve: (serial: string) =>
    postJSON<ApproveResult>(`/certificates/${serial}/approve`, {}, () =>
      mock.mockApprove(serial),
    ),
  renew: (serial: string) =>
    postJSON<RenewResult>(`/certificates/${serial}/renew`, {}, () => mock.mockRenew(serial)),
  assign: (serial: string, owner_group: string) =>
    postJSON<AssignResult>(`/orphans/${serial}/assign`, { owner_group }, () =>
      mock.mockAssign(serial, owner_group),
    ),
};

function cleanParams(params?: Record<string, string | undefined>): Record<string, string> {
  const out: Record<string, string> = {};
  if (!params) return out;
  for (const [k, v] of Object.entries(params)) if (v != null && v !== '') out[k] = v;
  return out;
}
