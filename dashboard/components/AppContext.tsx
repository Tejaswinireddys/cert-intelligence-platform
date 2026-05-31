'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { Mode } from '@/lib/api';

interface AppCtx {
  mode: Mode;
  setMode: (m: Mode) => void;
  lastScan: { scanned: number; new_events: number } | null;
  setLastScan: (v: { scanned: number; new_events: number } | null) => void;
}

const Ctx = createContext<AppCtx | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<Mode>('MOCK');
  const [lastScan, setLastScan] = useState<{ scanned: number; new_events: number } | null>(null);

  // Once any call reports LIVE, prefer LIVE; if a later call reports MOCK, downgrade.
  const setMode = useCallback((m: Mode) => setModeState(m), []);

  return (
    <Ctx.Provider value={{ mode, setMode, lastScan, setLastScan }}>{children}</Ctx.Provider>
  );
}

export function useApp(): AppCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
