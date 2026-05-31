'use client';

import { ReactNode } from 'react';
import { TIER_META, ROUTING_META, cn } from '@/lib/ui';
import type { Tier, Routing } from '@/lib/types';

export function TierBadge({ tier, size = 'sm' }: { tier: Tier; size?: 'sm' | 'xs' }) {
  const m = TIER_META[tier];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md font-bold ring-1 tabular-nums',
        m.bg,
        m.ring,
        m.text,
        size === 'xs' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-[11px]',
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: m.color }} />
      {m.label}
    </span>
  );
}

export function RoutingBadge({ routing }: { routing: Routing }) {
  const m = ROUTING_META[routing];
  return (
    <span className={cn('inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold', m.cls)}>
      {m.label}
    </span>
  );
}

export function Chip({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md bg-white/[0.05] px-1.5 py-0.5 text-[10.5px] font-medium text-slate-300 ring-1 ring-white/[0.06]',
        className,
      )}
    >
      {children}
    </span>
  );
}

export function ConfidenceBar({ value }: { value: number }) {
  const v = Math.round(value * 100);
  const color = v >= 78 ? '#2dd4bf' : v >= 50 ? '#22d3ee' : '#f59e0b';
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/[0.08]">
        <div className="h-full rounded-full transition-all" style={{ width: `${v}%`, background: color }} />
      </div>
      <span className="tabular-nums text-[11px] text-slate-400">{v}%</span>
    </div>
  );
}

export function Card({
  children,
  className,
  title,
  subtitle,
  action,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <section className={cn('glass-card p-5 animate-fade-in', className)}>
      {(title || action) && (
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-[13px] font-semibold text-white">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-[11px] text-slate-500">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse-soft rounded-md bg-white/[0.06]', className)} />;
}

export function EmptyState({ icon, title, sub }: { icon: ReactNode; title: string; sub?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-14 text-center">
      <div className="text-slate-600">{icon}</div>
      <div className="text-sm font-medium text-slate-300">{title}</div>
      {sub && <div className="max-w-sm text-[12px] text-slate-500">{sub}</div>}
    </div>
  );
}
