'use client';

import { useEffect, useState } from 'react';
import {
  X,
  ScanLine,
  Sparkles,
  Ticket,
  Bell,
  RefreshCw,
  CheckCircle2,
  Server,
  ShieldCheck,
  Lock,
  FileBadge,
  CircleDot,
  Loader2,
  ShieldAlert,
} from 'lucide-react';
import type { CertDetail, CertEvent, EventType } from '@/lib/types';
import { api } from '@/lib/api';
import { TierBadge, RoutingBadge, Chip, ConfidenceBar, Skeleton } from './primitives';
import { fmtDate, fmtDay, daysColor, cn } from '@/lib/ui';

const EVENT_ICON: Record<EventType, typeof ScanLine> = {
  scanned: ScanLine,
  scored: Sparkles,
  ticket_created: Ticket,
  notified: Bell,
  renewal_requested: RefreshCw,
  renewed: FileBadge,
  deployed: Server,
  verified: ShieldCheck,
  closed: CheckCircle2,
  dlq: ShieldAlert,
};

function Timeline({ events }: { events: CertEvent[] }) {
  return (
    <ol className="relative ml-2 space-y-4 border-l border-teal-accent/15 pl-5">
      {events.map((e) => {
        const Icon = EVENT_ICON[e.type] ?? CircleDot;
        return (
          <li key={e.id} className="relative">
            <span className="absolute -left-[27px] flex h-5 w-5 items-center justify-center rounded-full bg-navy-850 ring-1 ring-teal-accent/30">
              <Icon size={11} className="text-teal-accent" />
            </span>
            <div className="flex items-center gap-2">
              <span className="text-[12px] font-semibold capitalize text-slate-200">
                {e.type.replace(/_/g, ' ')}
              </span>
              <Chip className="text-[9.5px]">{e.actor}</Chip>
            </div>
            <p className="mt-0.5 text-[11.5px] text-slate-400">{e.detail}</p>
            <span className="text-[10.5px] text-slate-600">{fmtDate(e.ts)}</span>
          </li>
        );
      })}
    </ol>
  );
}

function MetaRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5 border-b border-white/[0.04]">
      <span className="text-[11px] text-slate-500">{label}</span>
      <span className="text-[12px] font-medium text-slate-200 text-right tabular-nums">{children}</span>
    </div>
  );
}

export default function CertDrawer({
  serial,
  onClose,
}: {
  serial: string | null;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<CertDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<'approve' | 'renew' | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (!serial) return;
    setDetail(null);
    setLoading(true);
    api.certificate(serial).then((res) => {
      setDetail(res.data);
      setLoading(false);
    });
  }, [serial]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    if (serial) {
      document.addEventListener('keydown', onKey);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [serial, onClose]);

  async function doApprove() {
    if (!serial) return;
    setBusy('approve');
    const res = await api.approve(serial);
    setBusy(null);
    setToast(`Approved · next: ${res.data.next}`);
    setTimeout(() => setToast(null), 3000);
  }
  async function doRenew() {
    if (!serial) return;
    setBusy('renew');
    const res = await api.renew(serial);
    setBusy(null);
    setToast(`Renewal saga: ${res.data.saga}`);
    setTimeout(() => setToast(null), 3000);
    if (detail) setDetail({ ...detail, events: res.data.events.length ? res.data.events : detail.events });
  }

  if (!serial) return null;
  const c = detail?.certificate;
  const isProd = c?.environment === 'prod';

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/55 backdrop-blur-sm animate-fade-in" onClick={onClose} />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-[560px] flex-col bg-navy-850 shadow-2xl ring-1 ring-teal-accent/15 animate-fade-in">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 border-b hairline px-5 py-4">
          <div className="min-w-0">
            {loading || !c ? (
              <Skeleton className="h-5 w-48" />
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <FileBadge size={16} className="text-teal-accent shrink-0" />
                  <h2 className="truncate text-[15px] font-semibold text-white">{c.common_name}</h2>
                </div>
                <div className="mt-1.5 flex flex-wrap items-center gap-2">
                  <TierBadge tier={c.tier} />
                  <RoutingBadge routing={c.routing} />
                  <span className={cn('text-[12px] font-semibold tabular-nums', daysColor(c.days_left))}>
                    {c.days_left}d left
                  </span>
                  <Chip>{c.jira_key}</Chip>
                </div>
              </>
            )}
          </div>
          <button
            onClick={onClose}
            data-testid="button-close-drawer"
            className="rounded-md p-1.5 text-slate-400 hover:bg-white/[0.06] hover:text-white"
          >
            <X size={18} />
          </button>
        </div>

        <div className="scroll-area flex-1 px-5 py-4 space-y-6">
          {loading || !detail || !c ? (
            <div className="space-y-3">
              <Skeleton className="h-32" />
              <Skeleton className="h-40" />
            </div>
          ) : (
            <>
              {/* SANs */}
              <div>
                <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Subject Alternative Names
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {c.sans.map((s) => (
                    <Chip key={s}>{s}</Chip>
                  ))}
                </div>
              </div>

              {/* Metadata grid */}
              <div className="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
                <div>
                  <MetaRow label="Serial">{c.serial}</MetaRow>
                  <MetaRow label="CA">{c.ca}</MetaRow>
                  <MetaRow label="Template">{c.template}</MetaRow>
                  <MetaRow label="Environment">{c.environment}</MetaRow>
                  <MetaRow label="Criticality">{c.criticality}</MetaRow>
                  <MetaRow label="Risk Score">{c.risk_score}</MetaRow>
                </div>
                <div>
                  <MetaRow label="Owner Group">{c.owner_group || '—'}</MetaRow>
                  <MetaRow label="App CI">{c.application_ci}</MetaRow>
                  <MetaRow label="Server CI">{c.server_ci}</MetaRow>
                  <MetaRow label="Valid From">{fmtDay(c.valid_from)}</MetaRow>
                  <MetaRow label="Valid To">{fmtDay(c.valid_to)}</MetaRow>
                  <MetaRow label="Endpoint">
                    {c.last_verified_endpoint}:{c.last_verified_port}
                  </MetaRow>
                </div>
              </div>

              {/* Key handling note */}
              <div className="flex items-start gap-2 rounded-lg bg-teal-accent/[0.06] p-3 ring-1 ring-teal-accent/15">
                <Lock size={14} className="mt-0.5 shrink-0 text-teal-accent" />
                <p className="text-[11.5px] leading-relaxed text-slate-400">
                  Renewal <span className="text-slate-200">{c.renewal_method}</span> · deploy{' '}
                  <span className="text-slate-200">{c.deploy_method}</span> · keys{' '}
                  <span className="text-slate-200">{c.key_handling_policy}</span>. The control plane orchestrates;
                  the execution plane deploys. Agents never hold private keys or touch servers.
                </p>
              </div>

              {/* AI ownership suggestions */}
              <div>
                <div className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  <Sparkles size={12} className="text-cyan-accent" /> AI Ownership Suggestions
                </div>
                <div className="space-y-2">
                  {detail.ai_suggestions.map((a, i) => (
                    <div key={i} className="rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/[0.05]">
                      <div className="flex items-center justify-between">
                        <div className="text-[12px]">
                          <span className="text-slate-500">Suggested: </span>
                          <span className="font-medium text-cyan-accent">{a.suggested_owner}</span>
                        </div>
                        <ConfidenceBar value={a.confidence} />
                      </div>
                      <div className="mt-1.5 text-[12px]">
                        <span className="text-slate-500">Human final: </span>
                        <span className={cn('font-medium', a.human_final ? 'text-teal-accent' : 'text-amber-300')}>
                          {a.human_final || 'awaiting steward'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Timeline */}
              <div>
                <div className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Event Timeline
                </div>
                <Timeline events={detail.events} />
              </div>
            </>
          )}
        </div>

        {/* Action bar */}
        <div className="border-t hairline px-5 py-4">
          {toast && (
            <div className="mb-3 rounded-md bg-teal-accent/12 px-3 py-2 text-[12px] text-teal-accent ring-1 ring-teal-accent/25">
              {toast}
            </div>
          )}
          <div className="flex items-center gap-3">
            <button
              onClick={doApprove}
              disabled={!!busy || !isProd}
              data-testid="button-approve"
              title={isProd ? 'Approve production renewal' : 'Approval only required for production'}
              className={cn(
                'inline-flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-[13px] font-semibold transition-all',
                isProd
                  ? 'bg-white/[0.06] text-slate-100 ring-1 ring-white/10 hover:bg-white/[0.1]'
                  : 'cursor-not-allowed bg-white/[0.03] text-slate-600 ring-1 ring-white/[0.04]',
              )}
            >
              {busy === 'approve' ? <Loader2 size={15} className="animate-spin" /> : <CheckCircle2 size={15} />}
              Approve {isProd ? '(prod)' : ''}
            </button>
            <button
              onClick={doRenew}
              disabled={!!busy}
              data-testid="button-renew"
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-gradient-to-b from-teal-accent to-teal-deep px-3 py-2.5 text-[13px] font-semibold text-navy-900 shadow-[0_8px_24px_-10px_rgba(45,212,191,0.7)] transition-all hover:brightness-110 active:scale-[0.98] disabled:opacity-70"
            >
              {busy === 'renew' ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
              Renew
            </button>
          </div>
          <p className="mt-2 text-center text-[10.5px] text-slate-600">
            Agents orchestrate the saga — they never touch private keys or servers.
          </p>
        </div>
      </aside>
    </div>
  );
}
