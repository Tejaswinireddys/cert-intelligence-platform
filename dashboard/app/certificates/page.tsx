'use client';

import { useEffect, useMemo, useState } from 'react';
import { Search, SlidersHorizontal, FileSearch, X } from 'lucide-react';
import { api } from '@/lib/api';
import { usePoll } from '@/lib/usePoll';
import { useApp } from '@/components/AppContext';
import { TierBadge, RoutingBadge, Chip, ConfidenceBar, Skeleton, EmptyState } from '@/components/primitives';
import CertDrawer from '@/components/CertDrawer';
import Footer from '@/components/Footer';
import { daysColor, cn } from '@/lib/ui';
import type { Tier, Routing } from '@/lib/types';

const TIERS: (Tier | '')[] = ['', 'P1', 'P2', 'P3', 'OK'];
const ENVS = ['', 'prod', 'staging', 'dev', 'test'];
const ROUTINGS: (Routing | '')[] = ['', 'AUTO', 'AI_SUGGEST', 'STEWARD_TRIAGE'];

function Select({
  value,
  onChange,
  options,
  label,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  label: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      data-testid={`filter-${label.toLowerCase()}`}
      className="rounded-lg border border-white/10 bg-navy-800 px-3 py-2 text-[12.5px] text-slate-200 outline-none transition-colors hover:border-teal-accent/30 focus:border-teal-accent/50"
    >
      {options.map((o) => (
        <option key={o} value={o} className="bg-navy-800">
          {o === '' ? `All ${label}` : o}
        </option>
      ))}
    </select>
  );
}

export default function CertificatesPage() {
  const { setMode } = useApp();
  const [tier, setTier] = useState('');
  const [environment, setEnvironment] = useState('');
  const [routing, setRouting] = useState('');
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 250);
    return () => clearTimeout(t);
  }, [search]);

  const params = useMemo(
    () => ({ tier, environment, routing, search: debounced }),
    [tier, environment, routing, debounced],
  );

  const certs = usePoll(
    () => api.certificates(params),
    undefined,
    [tier, environment, routing, debounced],
  );

  useEffect(() => {
    if (!certs.loading) setMode(certs.mode);
  }, [certs.mode, certs.loading, setMode]);

  const items = certs.data?.items ?? [];
  const total = certs.data?.total ?? 0;
  const hasFilter = tier || environment || routing || debounced;

  function clearAll() {
    setTier('');
    setEnvironment('');
    setRouting('');
    setSearch('');
  }

  return (
    <div className="space-y-5">
      {/* Filter bar */}
      <div className="glass-card flex flex-wrap items-center gap-3 p-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search CN, SAN or serial…"
            data-testid="input-search"
            className="w-full rounded-lg border border-white/10 bg-navy-800 py-2 pl-9 pr-3 text-[12.5px] text-slate-200 outline-none transition-colors placeholder:text-slate-600 hover:border-teal-accent/30 focus:border-teal-accent/50"
          />
        </div>
        <div className="flex items-center gap-2 text-slate-500">
          <SlidersHorizontal size={15} />
        </div>
        <Select value={tier} onChange={setTier} options={TIERS} label="Tiers" />
        <Select value={environment} onChange={setEnvironment} options={ENVS} label="Envs" />
        <Select value={routing} onChange={setRouting} options={ROUTINGS} label="Routing" />
        {hasFilter && (
          <button
            onClick={clearAll}
            data-testid="button-clear-filters"
            className="inline-flex items-center gap-1 rounded-lg px-2.5 py-2 text-[12px] text-slate-400 hover:bg-white/[0.05] hover:text-white"
          >
            <X size={13} /> Clear
          </button>
        )}
        <span className="ml-auto text-[12px] text-slate-500 tabular-nums">
          {certs.loading ? '…' : `${items.length} of ${total}`} certificates
        </span>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden p-0">
        <div className="scroll-area max-h-[calc(100dvh-260px)] overflow-x-auto">
          <table className="w-full min-w-[1000px] text-left">
            <thead className="sticky top-0 z-10 bg-navy-800/95 backdrop-blur">
              <tr className="text-[11px] uppercase tracking-wide text-slate-500">
                <th className="px-4 py-3 font-semibold">Common Name</th>
                <th className="px-3 py-3 font-semibold">SANs</th>
                <th className="px-3 py-3 font-semibold">Tier</th>
                <th className="px-3 py-3 font-semibold">Days</th>
                <th className="px-3 py-3 font-semibold">Env</th>
                <th className="px-3 py-3 font-semibold">Crit</th>
                <th className="px-3 py-3 font-semibold">Owner</th>
                <th className="px-3 py-3 font-semibold">Routing</th>
                <th className="px-3 py-3 font-semibold">Confidence</th>
                <th className="px-3 py-3 font-semibold">CA</th>
                <th className="px-3 py-3 font-semibold">Jira</th>
                <th className="px-3 py-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {certs.loading
                ? Array.from({ length: 12 }).map((_, i) => (
                    <tr key={i} className="border-t border-white/[0.04]">
                      <td colSpan={12} className="px-4 py-2.5">
                        <Skeleton className="h-5 w-full" />
                      </td>
                    </tr>
                  ))
                : items.map((c) => (
                    <tr
                      key={c.serial}
                      onClick={() => setSelected(c.serial)}
                      data-testid={`row-cert-${c.serial}`}
                      className="cursor-pointer border-t border-white/[0.04] transition-colors hover:bg-teal-accent/[0.05]"
                    >
                      <td className="px-4 py-2.5">
                        <div className="text-[12.5px] font-medium text-slate-100">{c.common_name}</div>
                        <div className="text-[10.5px] text-slate-600 font-mono">{c.serial.slice(0, 12)}…</div>
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex max-w-[180px] flex-wrap gap-1">
                          {c.sans.slice(0, 2).map((s) => (
                            <Chip key={s}>{s.length > 18 ? s.slice(0, 16) + '…' : s}</Chip>
                          ))}
                          {c.sans.length > 2 && <Chip>+{c.sans.length - 2}</Chip>}
                        </div>
                      </td>
                      <td className="px-3 py-2.5">
                        <TierBadge tier={c.tier} />
                      </td>
                      <td className={cn('px-3 py-2.5 text-[12.5px] font-semibold tabular-nums', daysColor(c.days_left))}>
                        {c.days_left}d
                      </td>
                      <td className="px-3 py-2.5 text-[12px] text-slate-300">{c.environment}</td>
                      <td className="px-3 py-2.5 text-[12px] text-slate-400 capitalize">{c.criticality}</td>
                      <td className="px-3 py-2.5 text-[12px] text-slate-300 whitespace-nowrap">
                        {c.owner_group || <span className="text-amber-300">Unassigned</span>}
                      </td>
                      <td className="px-3 py-2.5">
                        <RoutingBadge routing={c.routing} />
                      </td>
                      <td className="px-3 py-2.5">
                        <ConfidenceBar value={c.owner_confidence} />
                      </td>
                      <td className="px-3 py-2.5 text-[12px] text-slate-400">{c.ca}</td>
                      <td className="px-3 py-2.5">
                        <Chip>{c.jira_key}</Chip>
                      </td>
                      <td className="px-3 py-2.5 text-[12px] capitalize text-slate-400">{c.status.replace('_', ' ')}</td>
                    </tr>
                  ))}
            </tbody>
          </table>
          {!certs.loading && items.length === 0 && (
            <EmptyState
              icon={<FileSearch size={32} />}
              title="No certificates match"
              sub="Adjust filters or clear the search to see the full fleet."
            />
          )}
        </div>
      </div>

      <Footer />
      <CertDrawer serial={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
