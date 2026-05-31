'use client';

import { useEffect, useState } from 'react';
import { UserSearch, UserCheck, Loader2, Inbox, Sparkles } from 'lucide-react';
import { api } from '@/lib/api';
import { usePoll } from '@/lib/usePoll';
import { useApp } from '@/components/AppContext';
import { TierBadge, ConfidenceBar, Card, Skeleton, EmptyState } from '@/components/primitives';
import Footer from '@/components/Footer';
import { daysColor, cn } from '@/lib/ui';
import { OWNER_GROUPS } from '@/lib/mockData';

export default function OrphansPage() {
  const { setMode } = useApp();
  const orphans = usePoll(api.orphans);
  const [assigning, setAssigning] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [assigned, setAssigned] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!orphans.loading) setMode(orphans.mode);
  }, [orphans.mode, orphans.loading, setMode]);

  async function assign(serial: string) {
    const owner = draft[serial];
    if (!owner) return;
    setAssigning(serial);
    const res = await api.assign(serial, owner);
    setAssigning(null);
    setAssigned((p) => ({ ...p, [serial]: res.data.owner_group }));
  }

  const items = (orphans.data?.items ?? []).filter((o) => !assigned[o.serial]);

  return (
    <div className="space-y-5">
      <Card className="border-amber-400/15">
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-amber-400/12 p-2.5 text-amber-300 ring-1 ring-amber-400/25 shrink-0">
            <Sparkles size={18} />
          </div>
          <div>
            <h2 className="text-[13px] font-semibold text-white">The accuracy loop</h2>
            <p className="mt-1 text-[12px] leading-relaxed text-slate-400">
              Certs with owner confidence below 0.50, or no CMDB match, land here for steward triage. Each manual
              assignment is logged as <span className="text-cyan-accent">AI-suggested vs human-final</span>, feeding
              the attribution model so future scans route more certificates automatically.
            </p>
          </div>
        </div>
      </Card>

      <div className="glass-card overflow-hidden p-0">
        <div className="scroll-area max-h-[calc(100dvh-320px)] overflow-x-auto">
          <table className="w-full min-w-[820px] text-left">
            <thead className="sticky top-0 z-10 bg-navy-800/95 backdrop-blur">
              <tr className="text-[11px] uppercase tracking-wide text-slate-500">
                <th className="px-4 py-3 font-semibold">Common Name</th>
                <th className="px-3 py-3 font-semibold">Tier</th>
                <th className="px-3 py-3 font-semibold">Days</th>
                <th className="px-3 py-3 font-semibold">Confidence</th>
                <th className="px-3 py-3 font-semibold">Reason</th>
                <th className="px-3 py-3 font-semibold">Assign Owner</th>
              </tr>
            </thead>
            <tbody>
              {orphans.loading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i} className="border-t border-white/[0.04]">
                      <td colSpan={6} className="px-4 py-2.5">
                        <Skeleton className="h-6 w-full" />
                      </td>
                    </tr>
                  ))
                : items.map((o) => (
                    <tr key={o.serial} className="border-t border-white/[0.04] hover:bg-white/[0.02]">
                      <td className="px-4 py-3">
                        <div className="text-[12.5px] font-medium text-slate-100">{o.common_name}</div>
                        <div className="font-mono text-[10.5px] text-slate-600">{o.serial.slice(0, 12)}…</div>
                      </td>
                      <td className="px-3 py-3">
                        <TierBadge tier={o.tier} />
                      </td>
                      <td className={cn('px-3 py-3 text-[12.5px] font-semibold tabular-nums', daysColor(o.days_left))}>
                        {o.days_left}d
                      </td>
                      <td className="px-3 py-3">
                        <ConfidenceBar value={o.owner_confidence} />
                      </td>
                      <td className="px-3 py-3 text-[12px] text-slate-400">{o.reason}</td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <select
                            value={draft[o.serial] ?? ''}
                            onChange={(e) => setDraft((p) => ({ ...p, [o.serial]: e.target.value }))}
                            data-testid={`select-owner-${o.serial}`}
                            className="rounded-lg border border-white/10 bg-navy-800 px-2.5 py-1.5 text-[12px] text-slate-200 outline-none hover:border-teal-accent/30 focus:border-teal-accent/50"
                          >
                            <option value="">Select…</option>
                            {OWNER_GROUPS.filter((g) => g !== 'Unassigned').map((g) => (
                              <option key={g} value={g} className="bg-navy-800">
                                {g}
                              </option>
                            ))}
                          </select>
                          <button
                            onClick={() => assign(o.serial)}
                            disabled={!draft[o.serial] || assigning === o.serial}
                            data-testid={`button-assign-${o.serial}`}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-teal-accent/15 px-2.5 py-1.5 text-[12px] font-semibold text-teal-accent ring-1 ring-teal-accent/30 transition-all hover:bg-teal-accent/25 disabled:opacity-40"
                          >
                            {assigning === o.serial ? (
                              <Loader2 size={13} className="animate-spin" />
                            ) : (
                              <UserCheck size={13} />
                            )}
                            Assign
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
          {!orphans.loading && items.length === 0 && (
            <EmptyState
              icon={<Inbox size={32} />}
              title="Queue clear"
              sub="Every discovered certificate has a confident owner. Nice."
            />
          )}
        </div>
      </div>

      <Footer />
    </div>
  );
}
