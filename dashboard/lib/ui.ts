import type { Tier, Routing } from './types';

export const TIER_META: Record<Tier, { label: string; color: string; bg: string; ring: string; text: string }> = {
  P1: { label: 'P1', color: '#ef4444', bg: 'bg-tier-p1/15', ring: 'ring-tier-p1/40', text: 'text-tier-p1' },
  P2: { label: 'P2', color: '#f59e0b', bg: 'bg-tier-p2/15', ring: 'ring-tier-p2/40', text: 'text-tier-p2' },
  P3: { label: 'P3', color: '#22c55e', bg: 'bg-tier-p3/15', ring: 'ring-tier-p3/40', text: 'text-tier-p3' },
  OK: { label: 'OK', color: '#64748b', bg: 'bg-slate-500/15', ring: 'ring-slate-500/40', text: 'text-slate-400' },
};

export const ROUTING_META: Record<Routing, { label: string; cls: string }> = {
  AUTO: { label: 'Auto', cls: 'bg-teal-accent/15 text-teal-accent ring-1 ring-teal-accent/30' },
  AI_SUGGEST: { label: 'AI Suggest', cls: 'bg-cyan-accent/15 text-cyan-accent ring-1 ring-cyan-accent/30' },
  STEWARD_TRIAGE: { label: 'Steward Triage', cls: 'bg-amber-400/15 text-amber-300 ring-1 ring-amber-400/30' },
};

export function daysColor(days: number): string {
  if (days <= 7) return 'text-tier-p1';
  if (days <= 30) return 'text-tier-p2';
  if (days <= 60) return 'text-tier-p3';
  return 'text-slate-300';
}

export function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return iso;
  }
}

export function fmtDay(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return iso;
  }
}

export function pct(n: number): string {
  return `${n.toFixed(1)}%`;
}

export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ');
}
