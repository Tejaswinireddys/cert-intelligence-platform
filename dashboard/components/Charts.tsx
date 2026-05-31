'use client';

import {
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import type { Trend, TierCounts } from '@/lib/types';
import { TIER_META } from '@/lib/ui';

export function TrendChart({ data }: { data: Trend }) {
  return (
    <div style={{ width: '100%', height: 280 }}>
      <ResponsiveContainer>
        <AreaChart data={data.points} margin={{ top: 10, right: 8, left: -16, bottom: 0 }}>
          <defs>
            <linearGradient id="gRenewed" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2dd4bf" stopOpacity={0.5} />
              <stop offset="100%" stopColor="#2dd4bf" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gExpiring" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis
            dataKey="week"
            tickFormatter={(w: string) => w.replace('2026-', '')}
            tick={{ fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={36} />
          <YAxis
            yAxisId="sla"
            orientation="right"
            domain={[80, 100]}
            tick={{ fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={36}
            tickFormatter={(v: number) => `${v}%`}
          />
          <Tooltip />
          <Area
            type="monotone"
            dataKey="renewed"
            name="Renewed"
            stroke="#2dd4bf"
            strokeWidth={2}
            fill="url(#gRenewed)"
          />
          <Area
            type="monotone"
            dataKey="expiring"
            name="Expiring"
            stroke="#f59e0b"
            strokeWidth={2}
            fill="url(#gExpiring)"
          />
          <Line
            yAxisId="sla"
            type="monotone"
            dataKey="sla_pct"
            name="SLA %"
            stroke="#22d3ee"
            strokeWidth={2}
            dot={{ r: 2.5, fill: '#22d3ee' }}
          />
        </AreaChart>
      </ResponsiveContainer>
      <div className="mt-1 flex items-center justify-center gap-5 text-[11px] text-slate-400">
        {[
          { l: 'Renewed', c: '#2dd4bf' },
          { l: 'Expiring', c: '#f59e0b' },
          { l: 'SLA %', c: '#22d3ee' },
        ].map((x) => (
          <span key={x.l} className="inline-flex items-center gap-1.5">
            <span className="h-0.5 w-4 rounded" style={{ background: x.c }} />
            {x.l}
          </span>
        ))}
      </div>
    </div>
  );
}

export function TierDonut({ counts }: { counts: TierCounts }) {
  const data = (['P1', 'P2', 'P3', 'OK'] as const).map((t) => ({
    name: t,
    value: counts[t],
    color: TIER_META[t].color,
  }));
  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <div className="relative" style={{ width: '100%', height: 280 }}>
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={68}
            outerRadius={100}
            paddingAngle={2}
            stroke="none"
          >
            {data.map((d) => (
              <Cell key={d.name} fill={d.color} />
            ))}
          </Pie>
          <Tooltip />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
            formatter={(v) => <span style={{ color: '#94a3b8' }}>{v}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center" style={{ marginTop: -18 }}>
        <span className="text-2xl font-bold text-white tabular-nums">{total}</span>
        <span className="text-[11px] text-slate-500">total certs</span>
      </div>
    </div>
  );
}
