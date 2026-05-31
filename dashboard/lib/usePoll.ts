'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { Mode } from './api';

interface PollState<T> {
  data: T | null;
  mode: Mode;
  loading: boolean;
  lastUpdated: Date | null;
  refresh: () => void;
}

// Lightweight polling hook. Fetches once on mount, then on `intervalMs`.
export function usePoll<T>(
  fetcher: () => Promise<{ data: T; mode: Mode }>,
  intervalMs?: number,
  deps: unknown[] = [],
): PollState<T> {
  const [data, setData] = useState<T | null>(null);
  const [mode, setMode] = useState<Mode>('MOCK');
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const run = useCallback(async () => {
    const res = await fetcherRef.current();
    setData(res.data);
    setMode(res.mode);
    setLastUpdated(new Date());
    setLoading(false);
  }, []);

  useEffect(() => {
    setLoading(true);
    run();
    if (!intervalMs) return;
    const id = setInterval(run, intervalMs);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, mode, loading, lastUpdated, refresh: run };
}
