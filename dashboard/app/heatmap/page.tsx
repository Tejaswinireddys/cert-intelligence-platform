'use client';

import { useEffect } from 'react';
import { Grid3x3 } from 'lucide-react';
import { api } from '@/lib/api';
import { usePoll } from '@/lib/usePoll';
import { useApp } from '@/components/AppContext';
import { Card, Skeleton } from '@/components/primitives';
import HeatmapGrid, { HeatmapLegend } from '@/components/HeatmapGrid';
import Footer from '@/components/Footer';

export default function HeatmapPage() {
  const { setMode } = useApp();
  const heatmap = usePoll(api.heatmap);

  useEffect(() => {
    if (!heatmap.loading) setMode(heatmap.mode);
  }, [heatmap.mode, heatmap.loading, setMode]);

  const grand = heatmap.data?.rows.reduce((s, r) => s + r.total, 0) ?? 0;
  const soon =
    heatmap.data?.rows.reduce((s, r) => s + r.buckets[0] + r.buckets[1], 0) ?? 0;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <div className="text-[11px] uppercase tracking-wide text-slate-500">Total Mapped</div>
          <div className="mt-1 text-2xl font-bold text-white tabular-nums">{grand}</div>
        </Card>
        <Card>
          <div className="text-[11px] uppercase tracking-wide text-slate-500">Expiring ≤30d</div>
          <div className="mt-1 text-2xl font-bold text-tier-p2 tabular-nums">{soon}</div>
        </Card>
        <Card>
          <div className="text-[11px] uppercase tracking-wide text-slate-500">Owner Groups</div>
          <div className="mt-1 text-2xl font-bold text-teal-accent tabular-nums">
            {heatmap.data?.rows.length ?? 0}
          </div>
        </Card>
      </div>

      <Card
        title="Expiry Heatmap"
        subtitle="Owner group × expiry window · color intensity = certificate count"
        action={
          <div className="rounded-lg bg-teal-accent/12 p-2 text-teal-accent ring-1 ring-teal-accent/25">
            <Grid3x3 size={16} />
          </div>
        }
      >
        {heatmap.loading || !heatmap.data ? (
          <Skeleton className="h-80" />
        ) : (
          <>
            <HeatmapGrid data={heatmap.data} />
            <div className="mt-5 border-t hairline pt-4">
              <HeatmapLegend />
            </div>
          </>
        )}
      </Card>

      <Footer />
    </div>
  );
}
