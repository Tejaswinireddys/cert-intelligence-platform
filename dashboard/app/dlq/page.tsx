'use client';

import { useEffect } from 'react';
import { AlertTriangle, ShieldCheck } from 'lucide-react';
import { api } from '@/lib/api';
import { usePoll } from '@/lib/usePoll';
import { useApp } from '@/components/AppContext';
import { Chip, Skeleton, EmptyState } from '@/components/primitives';
import Footer from '@/components/Footer';
import { fmtDate } from '@/lib/ui';

export default function DlqPage() {
  const { setMode } = useApp();
  const dlq = usePoll(api.dlq);

  useEffect(() => {
    if (!dlq.loading) setMode(dlq.mode);
  }, [dlq.mode, dlq.loading, setMode]);

  const items = dlq.data?.items ?? [];

  return (
    <div className="space-y-5">
      <div className="glass-card flex items-start gap-3 p-4 ring-1 ring-tier-p1/15">
        <div className="rounded-lg bg-tier-p1/12 p-2.5 text-tier-p1 ring-1 ring-tier-p1/25 shrink-0">
          <AlertTriangle size={18} />
        </div>
        <div>
          <h2 className="text-[13px] font-semibold text-white">Dead-letter queue</h2>
          <p className="mt-1 text-[12px] leading-relaxed text-slate-400">
            Events that exhausted their retry budget. Each entry is safe to replay — the saga is idempotent, keyed by
            serial and ISO week. Resolve the upstream cause, then re-enqueue.
          </p>
        </div>
      </div>

      <div className="glass-card overflow-hidden p-0">
        <div className="scroll-area overflow-x-auto">
          <table className="w-full min-w-[760px] text-left">
            <thead className="bg-navy-800/95">
              <tr className="text-[11px] uppercase tracking-wide text-slate-500">
                <th className="px-4 py-3 font-semibold">Event Type</th>
                <th className="px-3 py-3 font-semibold">Serial</th>
                <th className="px-3 py-3 font-semibold">Attempts</th>
                <th className="px-3 py-3 font-semibold">Last Error</th>
                <th className="px-3 py-3 font-semibold">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {dlq.loading
                ? Array.from({ length: 2 }).map((_, i) => (
                    <tr key={i} className="border-t border-white/[0.04]">
                      <td colSpan={5} className="px-4 py-2.5">
                        <Skeleton className="h-6 w-full" />
                      </td>
                    </tr>
                  ))
                : items.map((d) => (
                    <tr key={d.id} className="border-t border-white/[0.04] hover:bg-white/[0.02]">
                      <td className="px-4 py-3">
                        <Chip className="text-tier-p2">{d.event_type}</Chip>
                      </td>
                      <td className="px-3 py-3 font-mono text-[11.5px] text-slate-300">{d.serial.slice(0, 14)}…</td>
                      <td className="px-3 py-3">
                        <span className="inline-flex items-center rounded-md bg-tier-p1/12 px-2 py-0.5 text-[12px] font-bold text-tier-p1 tabular-nums ring-1 ring-tier-p1/25">
                          {d.attempts}×
                        </span>
                      </td>
                      <td className="px-3 py-3 text-[12.5px] text-slate-300">{d.last_error}</td>
                      <td className="px-3 py-3 text-[12px] text-slate-500 tabular-nums">{fmtDate(d.ts)}</td>
                    </tr>
                  ))}
            </tbody>
          </table>
          {!dlq.loading && items.length === 0 && (
            <EmptyState
              icon={<ShieldCheck size={32} />}
              title="Queue empty"
              sub="No failed events. Every saga completed within its retry budget."
            />
          )}
        </div>
      </div>

      <Footer />
    </div>
  );
}
