"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

/**
 * `field` is already the business name a reader recognises -- reporting columns are
 * Title Case ("Customer Class", "SA Type"). An optional `label` used to ride along, and
 * both call sites passed the VALUE into it, so the banner read "Commercial = Commercial"
 * instead of "Customer Class = Commercial".
 */
export type CrossFilter = {
  field: string;
  value: string;
} | null;

type CrossFilterContextValue = {
  filter: CrossFilter;
  setFilter: (field: string, value: string) => void;
  toggleFilter: (field: string, value: string) => void;
  clearFilter: () => void;
};

const CrossFilterContext = createContext<CrossFilterContextValue | null>(null);

export function CrossFilterProvider({ children }: { children: ReactNode }) {
  const [filter, setFilterState] = useState<CrossFilter>(null);

  const setFilter = useCallback((field: string, value: string) => {
    setFilterState({ field, value });
  }, []);

  const toggleFilter = useCallback((field: string, value: string) => {
    setFilterState((prev) =>
      prev?.field === field && prev?.value === value ? null : { field, value },
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
