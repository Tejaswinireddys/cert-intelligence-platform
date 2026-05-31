'use client';

import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { RadioTower, ScanLine, Loader2, CheckCircle2 } from 'lucide-react';
import { api } from '@/lib/api';
import { useApp } from './AppContext';
import { cn } from '@/lib/ui';

const TITLES: Record<string, { title: string; sub: string }> = {
  '/': { title: 'Operations Overview', sub: 'Fleet health, expiry risk and renewal velocity' },
  '/certificates': { title: 'Certificates', sub: 'Searchable inventory across the managed fleet' },
  '/heatmap': { title: 'Expiry Heatmap', sub: 'Certificates by owner group and expiry window' },
  '/orphans': { title: 'Orphan Queue', sub: 'Low-confidence certs awaiting steward triage' },
  '/dlq': { title: 'Dead-Letter Queue', sub: 'Failed events after retry exhaustion' },
  '/audit': { title: 'Audit Log', sub: 'Append-only record of every action' },
};

function ModeBadge({ mode }: { mode: 'LIVE' | 'MOCK' }) {
  const live = mode === 'LIVE';
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide ring-1',
        live
          ? 'bg-tier-p3/12 text-tier-p3 ring-tier-p3/30'
          : 'bg-amber-400/12 text-amber-300 ring-amber-400/30',
      )}
      title={live ? 'Connected to backend' : 'Backend unreachable — showing sample data'}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', live ? 'bg-tier-p3 animate-pulse-soft' : 'bg-amber-300')} />
      {live ? 'LIVE' : 'MOCK'}
    </span>
  );
}

export default function Topbar() {
  const pathname = usePathname();
  const { mode, setMode, setLastScan } = useApp();
  const [scanning, setScanning] = useState(false);
  const [done, setDone] = useState(false);

  // trailingSlash:true yields paths like "/audit/" — normalize before lookup.
  const key = pathname !== '/' ? pathname.replace(/\/+$/, '') : '/';
  const meta = TITLES[key] ?? TITLES['/'];

  async function runScan() {
    setScanning(true);
    setDone(false);
    const res = await api.scan({ windows: [7, 30, 60, 90] });
    setMode(res.mode);
    setLastScan({ scanned: res.data.scanned, new_events: res.data.new_events });
    setScanning(false);
    setDone(true);
    setTimeout(() => setDone(false), 2500);
  }

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-4 border-b hairline bg-navy-850/70 px-5 backdrop-blur-md">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h1 className="truncate text-[15px] font-semibold text-white">{meta.title}</h1>
          <span className="hidden sm:inline text-slate-600">·</span>
          <p className="hidden sm:block truncate text-[12px] text-slate-500">{meta.sub}</p>
        </div>
        <div className="md:hidden text-[11px] font-semibold text-teal-accent">
          Certificate Intelligence Platform
        </div>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <ModeBadge mode={mode} />
        <button
          onClick={runScan}
          disabled={scanning}
          data-testid="button-run-scan"
          className={cn(
            'inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-[13px] font-semibold transition-all',
            'bg-gradient-to-b from-teal-accent to-teal-deep text-navy-900 shadow-[0_8px_24px_-10px_rgba(45,212,191,0.7)]',
            'hover:brightness-110 active:scale-[0.98] disabled:opacity-70 disabled:cursor-wait',
          )}
        >
          {scanning ? (
            <Loader2 size={15} className="animate-spin" />
          ) : done ? (
            <CheckCircle2 size={15} />
          ) : (
            <ScanLine size={15} />
          )}
          {scanning ? 'Scanning…' : done ? 'Scan complete' : 'Run Scan'}
        </button>
        <div className="hidden lg:flex items-center gap-1.5 text-[11px] text-slate-500">
          <RadioTower size={13} className="text-teal-deep" />
          poll 10s
        </div>
      </div>
    </header>
  );
}
