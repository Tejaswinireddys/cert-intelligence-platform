'use client';

import { useEffect } from 'react';
import {
  Shield,
  AlertOctagon,
  Clock,
  Activity,
  Users,
  RefreshCw,
  Inbox,
  AlertTriangle,
  Timer,
} from 'lucide-react';
import { api } from '@/lib/api';
import { usePoll } from '@/lib/usePoll';
import { useApp } from '@/components/AppContext';
import { KpiCard } from '@/components/KpiCard';
import { Card, Skeleton } from '@/components/primitives';
import { TrendChart, TierDonut } from '@/components/Charts';
import HeatmapGrid, { HeatmapLegend } from '@/components/HeatmapGrid';
import Footer from '@/components/Footer';
import { pct } from '@/lib/ui';

export default function OverviewPage() {
  const { setMode, lastScan } = useApp();
  const summary = usePoll(api.summary, 10000);
  const heatmap = usePoll(api.heatmap);
  const trend = usePoll(api.trend);

  useEffect(() => {
    if (!summary.loading) setMode(summary.mode);
  }, [summary.mode, summary.loading, setMode]);

  const s = summary.data;

  return (
    <div className="space-y-6">
      {/* Status line */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[12px] text-slate-500">
          {summary.lastUpdated
            ? `Updated ${summary.lastUpdated.toLocaleTimeString('en-US', { hour12: false })} · auto-refresh 10s`
            : 'Loading fleet…'}
          {lastScan && (
            <span className="ml-2 text-teal-accent">
              · last scan: {lastScan.scanned} certs, {lastScan.new_events} new events
            </span>
          )}
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {summary.loading || !s ? (
          Array.from({ length: 10 }).map((_, i) => <Skeleton key={i} className="h-[92px]" />)
        ) : (
          <>
            <KpiCard label="Total Certs" value={s.total_certs} icon={<Shield size={16} />} accent="teal" />
            <KpiCard label="P1 Critical" value={s.tier_counts.P1} icon={<AlertOctagon size={16} />} accent="p1" hint="≤7d, critical" />
            <KpiCard label="P2 Urgent" value={s.tier_counts.P2} icon={<AlertTriangle size={16} />} accent="p2" hint="8–30 days" />
            <KpiCard label="P3 Planned" value={s.tier_counts.P3} icon={<Clock size={16} />} accent="p3" hint="31–60 days" />
            <KpiCard label="OK" value={s.tier_counts.OK} icon={<Shield size={16} />} accent="slate" hint=">60 days" />
            <KpiCard label="SLA Compliance" value={pct(s.sla_compliance_pct)} icon={<Activity size={16} />} accent="cyan" />
            <KpiCard label="Owner Coverage" value={pct(s.coverage_pct)} icon={<Users size={16} />} accent="teal" />
            <KpiCard label="Renewed / Week" value={s.renewed_this_week} icon={<RefreshCw size={16} />} accent="p3" hint={`${s.renewed_this_month} this month`} />
            <KpiCard label="Orphans" value={s.orphan_count} icon={<Inbox size={16} />} accent="amber" />
            <KpiCard label="DLQ" value={s.dlq_count} icon={<AlertTriangle size={16} />} accent="p1" />
          </>
        )}
      </div>

      {/* Heatmap */}
      <Card
        title="Expiry Heatmap"
        subtitle="Certificates by owner group × expiry window"
        action={<span className="hidden sm:block"><HeatmapLegend /></span>}
      >
        {heatmap.loading || !heatmap.data ? (
          <Skeleton className="h-64" />
        ) : (
          <HeatmapGrid data={heatmap.data} />
        )}
      </Card>

      {/* Trend + Donut */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card title="Renewal & Expiry Trend" subtitle="Weekly renewed, expiring and SLA %" className="lg:col-span-2">
          {trend.loading || !trend.data ? <Skeleton className="h-[280px]" /> : <TrendChart data={trend.data} />}
        </Card>
        <Card title="Risk Tier Distribution" subtitle="Current fleet by priority tier">
          {summary.loading || !s ? <Skeleton className="h-[280px]" /> : <TierDonut counts={s.tier_counts} />}
        </Card>
      </div>

      {/* Avg days to renew callout */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="sm:col-span-1">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-teal-accent/12 p-2.5 text-teal-accent ring-1 ring-teal-accent/25">
              <Timer size={18} />
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-wide text-slate-500">Avg Days to Renew</div>
              <div className="text-xl font-bold text-white tabular-nums">{s ? s.avg_days_to_renew : '—'}</div>
            </div>
          </div>
        </Card>
        <div className="glass-card flex items-center gap-3 p-5 sm:col-span-2">
          <Shield size={18} className="shrink-0 text-teal-deep" />
          <p className="text-[12px] leading-relaxed text-slate-400">
            The control plane scores and routes every certificate. Renewals run as idempotent sagas with human
            approval required for production. AI enriches ownership and risk — it never holds keys or touches servers.
          </p>
        </div>
      </div>

      <Footer />
    </div>
  );
}
