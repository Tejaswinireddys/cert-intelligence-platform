'use client';

import type { Heatmap } from '@/lib/types';
import { cn } from '@/lib/ui';

// Color intensity by count, with window-aware urgency tint (left = sooner = warmer).
function cellStyle(count: number, max: number, colIdx: number, total: number) {
  if (count === 0) return { background: 'rgba(255,255,255,0.025)', color: '#475569' };
  const t = Math.min(1, count / Math.max(1, max));
  // Urgency hue: <7d red, 8-30 amber, 31-60 teal-green, else teal.
  const hue =
    colIdx === 0 ? '239,68,68' : colIdx === 1 ? '245,158,11' : colIdx === 2 ? '34,197,94' : '45,212,191';
  const alpha = 0.14 + t * 0.62;
  return {
    background: `rgba(${hue},${alpha})`,
    color: t > 0.55 ? '#0a1622' : '#e6edf6',
    borderColor: `rgba(${hue},${Math.min(0.8, alpha + 0.15)})`,
  };
}

export default function HeatmapGrid({ data, dense = false }: { data: Heatmap; dense?: boolean }) {
  const max = Math.max(
    1,
    ...data.rows.flatMap((r) => r.buckets),
  );
  const colTotals = data.windows.map((_, i) => data.rows.reduce((s, r) => s + r.buckets[i], 0));
  const grand = data.rows.reduce((s, r) => s + r.total, 0);

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate" style={{ borderSpacing: dense ? '4px' : '6px' }}>
        <thead>
          <tr>
            <th className="text-left text-[11px] font-semibold text-slate-500 pr-2 min-w-[150px]">
              Owner Group
            </th>
            {data.windows.map((w) => (
              <th key={w} className="text-center text-[11px] font-semibold text-slate-400 px-1 min-w-[68px]">
                {w}
              </th>
            ))}
            <th className="text-center text-[11px] font-semibold text-slate-500 pl-2 min-w-[56px]">
              Total
            </th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr key={row.owner_group}>
              <td className="pr-2 text-[12px] font-medium text-slate-200 whitespace-nowrap">
                {row.owner_group}
              </td>
              {row.buckets.map((count, i) => (
                <td key={i}>
                  <div
                    className={cn(
                      'flex items-center justify-center rounded-md border border-transparent tabular-nums font-semibold transition-transform hover:scale-[1.06] hover:z-10 relative',
                      dense ? 'h-9 text-[12px]' : 'h-11 text-[13px]',
                    )}
                    style={cellStyle(count, max, i, row.total)}
                    title={`${row.owner_group} · ${data.windows[i]} · ${count} certs`}
                  >
                    {count}
                  </div>
                </td>
              ))}
              <td className="pl-2 text-center text-[12px] font-bold text-teal-accent tabular-nums">
                {row.total}
              </td>
            </tr>
          ))}
          <tr>
            <td className="pr-2 pt-1 text-[11px] font-semibold text-slate-500">Column total</td>
            {colTotals.map((t, i) => (
              <td key={i} className="pt-1 text-center text-[11px] font-semibold text-slate-400 tabular-nums">
                {t}
              </td>
            ))}
            <td className="pl-2 pt-1 text-center text-[12px] font-bold text-white tabular-nums">{grand}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export function HeatmapLegend() {
  return (
    <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-400">
      <span className="font-semibold text-slate-300">Urgency</span>
      {[
        { c: '239,68,68', l: '<7d critical' },
        { c: '245,158,11', l: '8–30d soon' },
        { c: '34,197,94', l: '31–60d planned' },
        { c: '45,212,191', l: '>60d healthy' },
      ].map((x) => (
        <span key={x.l} className="inline-flex items-center gap-1.5">
          <span className="h-3 w-3 rounded" style={{ background: `rgba(${x.c},0.7)` }} />
          {x.l}
        </span>
      ))}
      <span className="text-slate-600">· darker = more certs</span>
    </div>
  );
}
