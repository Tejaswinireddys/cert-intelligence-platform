'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  ShieldCheck,
  FileBadge,
  Grid3x3,
  UserSearch,
  AlertTriangle,
  ScrollText,
} from 'lucide-react';
import { cn } from '@/lib/ui';

const NAV = [
  { href: '/', label: 'Overview', icon: LayoutDashboard },
  { href: '/certificates', label: 'Certificates', icon: FileBadge },
  { href: '/heatmap', label: 'Heatmap', icon: Grid3x3 },
  { href: '/orphans', label: 'Orphan Queue', icon: UserSearch },
  { href: '/dlq', label: 'DLQ', icon: AlertTriangle },
  { href: '/audit', label: 'Audit Log', icon: ScrollText },
];

function ShieldLogo() {
  return (
    <svg width="34" height="34" viewBox="0 0 32 32" fill="none" aria-label="Certificate Intelligence shield">
      <defs>
        <linearGradient id="shieldGrad" x1="0" y1="0" x2="32" y2="32">
          <stop offset="0" stopColor="#2dd4bf" />
          <stop offset="1" stopColor="#0e7490" />
        </linearGradient>
      </defs>
      <path
        d="M16 2.5 5 6.5v8.2c0 6.6 4.4 11.3 11 14.8 6.6-3.5 11-8.2 11-14.8V6.5L16 2.5Z"
        fill="url(#shieldGrad)"
        opacity="0.18"
      />
      <path
        d="M16 2.5 5 6.5v8.2c0 6.6 4.4 11.3 11 14.8 6.6-3.5 11-8.2 11-14.8V6.5L16 2.5Z"
        stroke="#2dd4bf"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="m10.5 16 3.6 3.6L21.5 12"
        stroke="#5eead4"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Sidebar() {
  const pathname = usePathname();
  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <aside className="hidden md:flex flex-col bg-navy-850/80 border-r hairline scroll-area">
      <div className="flex items-center gap-3 px-5 h-16 border-b hairline shrink-0">
        <ShieldLogo />
        <div className="leading-tight">
          <div className="text-[13px] font-bold tracking-tight text-white">Certificate</div>
          <div className="text-[13px] font-bold tracking-tight text-teal-accent -mt-0.5">
            Intelligence
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          Operations
        </div>
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
                active
                  ? 'bg-teal-accent/12 text-teal-accent ring-1 ring-teal-accent/25 shadow-[0_0_24px_-12px_rgba(45,212,191,0.6)]'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-white/[0.04]',
              )}
            >
              <Icon
                size={18}
                className={cn('shrink-0', active ? 'text-teal-accent' : 'text-slate-500 group-hover:text-slate-300')}
              />
              <span className="truncate">{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-4 py-4 border-t hairline shrink-0">
        <div className="flex items-center gap-2 text-[11px] text-slate-500">
          <ShieldCheck size={14} className="text-teal-deep shrink-0" />
          <span className="leading-snug">
            AI enriches, never touches keys or servers.
          </span>
        </div>
      </div>
    </aside>
  );
}
