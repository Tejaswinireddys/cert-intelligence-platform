'use client';

import { ReactNode } from 'react';
import { cn } from '@/lib/ui';

export function KpiCard({
  label,
  value,
  unit,
  icon,
  accent = 'teal',
  hint,
}: {
  label: string;
  value: string | number;
  unit?: string;
  icon: ReactNode;
  accent?: 'teal' | 'cyan' | 'p1' | 'p2' | 'p3' | 'slate' | 'amber';
  hint?: string;
}) {
  const accents: Record<string, string> = {
    teal: 'text-teal-accent',
    cyan: 'text-cyan-accent',
    p1: 'text-tier-p1',
    p2: 'text-tier-p2',
    p3: 'text-tier-p3',
    slate: 'text-slate-300',
    amber: 'text-amber-300',
  };
  const glow: Record<string, string> = {
    teal: 'shadow-[inset_0_0_0_1px_rgba(45,212,191,0.12)]',
    cyan: 'shadow-[inset_0_0_0_1px_rgba(34,211,238,0.12)]',
    p1: 'shadow-[inset_0_0_0_1px_rgba(239,68,68,0.18)]',
    p2: 'shadow-[inset_0_0_0_1px_rgba(245,158,11,0.18)]',
    p3: 'shadow-[inset_0_0_0_1px_rgba(34,197,94,0.16)]',
    slate: 'shadow-[inset_0_0_0_1px_rgba(148,163,184,0.12)]',
    amber: 'shadow-[inset_0_0_0_1px_rgba(245,158,11,0.16)]',
  };

  return (
    <div className={cn('glass-card p-4 transition-transform hover:-translate-y-0.5', glow[accent])}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</span>
        <span className={cn('opacity-80', accents[accent])}>{icon}</span>
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className={cn('text-2xl font-bold tabular-nums', accents[accent])}>{value}</span>
        {unit && <span className="text-sm font-medium text-slate-500">{unit}</span>}
      </div>
      {hint && <div className="mt-1 text-[11px] text-slate-500">{hint}</div>}
    </div>
  );
}
