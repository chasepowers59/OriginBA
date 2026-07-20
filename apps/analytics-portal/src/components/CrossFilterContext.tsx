"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export type CrossFilter = {
  field: string;
  value: string;
  label?: string;
} | null;

type CrossFilterContextValue = {
  filter: CrossFilter;
  setFilter: (field: string, value: string, label?: string) => void;
  toggleFilter: (field: string, value: string, label?: string) => void;
  clearFilter: () => void;
};

const CrossFilterContext = createContext<CrossFilterContextValue | null>(null);

export function CrossFilterProvider({ children }: { children: ReactNode }) {
  const [filter, setFilterState] = useState<CrossFilter>(null);

  const setFilter = useCallback((field: string, value: string, label?: string) => {
    setFilterState({ field, value, label });
  }, []);

  const toggleFilter = useCallback((field: string, value: string, label?: string) => {
    setFilterState((prev) =>
      prev?.field === field && prev?.value === value ? null : { field, value, label },
    );
  }, []);

  const clearFilter = useCallback(() => setFilterState(null), []);

  const value = useMemo(
    () => ({ filter, setFilter, toggleFilter, clearFilter }),
    [filter, setFilter, toggleFilter, clearFilter],
  );

  return <CrossFilterContext.Provider value={value}>{children}</CrossFilterContext.Provider>;
}

export function useCrossFilter() {
  const ctx = useContext(CrossFilterContext);
  if (!ctx) {
    return {
      filter: null as CrossFilter,
      setFilter: (_f: string, _v: string) => {},
      toggleFilter: (_f: string, _v: string) => {},
      clearFilter: () => {},
    };
  }
  return ctx;
}
