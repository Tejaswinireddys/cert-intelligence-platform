'use client';

import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, ScrollText } from 'lucide-react';
import { api } from '@/lib/api';
import { usePoll } from '@/lib/usePoll';
import { useApp } from '@/components/AppContext';
import { Chip, Skeleton } from '@/components/primitives';
import Footer from '@/components/Footer';
import { fmtDate, cn } from '@/lib/ui';

const PAGE = 25;

function OutcomeBadge({ outcome }: { outcome: string }) {
  const ok = outcome === 'ok';
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10.5px] font-semibold ring-1',
        ok ? 'bg-tier-p3/12 text-tier-p3 ring-tier-p3/25' : 'bg-tier-p2/12 text-tier-p2 ring-tier-p2/25',
      )}
    >
      {outcome}
    </span>
  );
}

export default function AuditPage() {
  const { setMode } = useApp();
  const [page, setPage] = useState(0);
  const audit = usePoll(
    () => api.audit({ limit: String(PAGE), offset: String(page * PAGE) }),
    undefined,
    [page],
  );

  useEffect(() => {
    if (!audit.loading) setMode(audit.mode);
  }, [audit.mode, audit.loading, setMode]);

  const items = audit.data?.items ?? [];
  const total = audit.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE));

  return (
    <div className="space-y-5">
      <div className="glass-card flex items-center justify-between gap-3 p-4">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-teal-accent/12 p-2.5 text-teal-accent ring-1 ring-teal-accent/25">
            <ScrollText size={18} />
          </div>
          <div>
            <h2 className="text-[13px] font-semibold text-white">Append-only audit log</h2>
            <p className="text-[12px] text-slate-500 tabular-nums">{total} immutable entries</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            data-testid="button-prev-page"
            className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-2.5 py-1.5 text-[12px] text-slate-300 hover:bg-white/[0.05] disabled:opacity-40"
          >
            <ChevronLeft size={14} /> Prev
          </button>
          <span className="text-[12px] text-slate-500 tabular-nums">
            {page + 1} / {pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(pages - 1, p + 1))}
            disabled={page >= pages - 1}
            data-testid="button-next-page"
            className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-2.5 py-1.5 text-[12px] text-slate-300 hover:bg-white/[0.05] disabled:opacity-40"
          >
            Next <ChevronRight size={14} />
          </button>
        </div>
      </div>

      <div className="glass-card overflow-hidden p-0">
        <div className="scroll-area max-h-[calc(100dvh-300px)] overflow-x-auto">
          <table className="w-full min-w-[960px] text-left">
            <thead className="sticky top-0 z-10 bg-navy-800/95 backdrop-blur">
              <tr className="text-[11px] uppercase tracking-wide text-slate-500">
                <th className="px-4 py-3 font-semibold">Timestamp</th>
                <th className="px-3 py-3 font-semibold">Actor</th>
                <th className="px-3 py-3 font-semibold">Action</th>
                <th className="px-3 py-3 font-semibold">Serial</th>
                <th className="px-3 py-3 font-semibold">Idempotency Key</th>
                <th className="px-3 py-3 font-semibold">Outcome</th>
                <th className="px-3 py-3 font-semibold">Detail</th>
              </tr>
            </thead>
            <tbody>
              {audit.loading
                ? Array.from({ length: PAGE }).map((_, i) => (
                    <tr key={i} className="border-t border-white/[0.04]">
                      <td colSpan={7} className="px-4 py-2">
                        <Skeleton className="h-5 w-full" />
                      </td>
                    </tr>
                  ))
                : items.map((a) => (
                    <tr key={a.id} className="border-t border-white/[0.04] hover:bg-white/[0.02]">
                      <td className="px-4 py-2.5 text-[12px] text-slate-400 tabular-nums whitespace-nowrap">
                        {fmtDate(a.ts)}
                      </td>
                      <td className="px-3 py-2.5">
                        <Chip>{a.actor}</Chip>
                      </td>
                      <td className="px-3 py-2.5 text-[12px] font-medium text-slate-200">{a.action}</td>
                      <td className="px-3 py-2.5 font-mono text-[11px] text-slate-500">{a.serial.slice(0, 10)}…</td>
                      <td className="px-3 py-2.5 font-mono text-[11px] text-cyan-accent/80">{a.idempotency_key}</td>
                      <td className="px-3 py-2.5">
                        <OutcomeBadge outcome={a.outcome} />
                      </td>
                      <td className="px-3 py-2.5 text-[12px] text-slate-400">{a.detail}</td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      </div>

      <Footer />
    </div>
  );
}
