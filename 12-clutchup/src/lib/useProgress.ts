"use client";

import { useCallback, useEffect, useState } from "react";

const KEY = "clutchup.cleared.v1";

/**
 * Tracks which spots the learner has marked "practiced", persisted to
 * localStorage. No accounts, no server — your progress lives on your device.
 */
export function useProgress() {
  const [cleared, setCleared] = useState<Set<string>>(new Set());
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) setCleared(new Set(JSON.parse(raw) as string[]));
    } catch {
      /* ignore corrupt storage */
    }
    setHydrated(true);
  }, []);

  const persist = useCallback((next: Set<string>) => {
    try {
      localStorage.setItem(KEY, JSON.stringify([...next]));
    } catch {
      /* storage full / disabled — progress just won't persist */
    }
  }, []);

  const toggle = useCallback(
    (id: string) => {
      setCleared((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        persist(next);
        return next;
      });
    },
    [persist]
  );

  const reset = useCallback(() => {
    setCleared(new Set());
    persist(new Set());
  }, [persist]);

  const has = useCallback((id: string) => cleared.has(id), [cleared]);

  return { cleared, has, toggle, reset, hydrated, count: cleared.size };
}
