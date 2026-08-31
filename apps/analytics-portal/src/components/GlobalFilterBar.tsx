"use client";

import { prettifyFieldName } from "@/lib/businessLabels";

type GlobalFilterBarProps = {
  periodLabel?: string;
  dateRange?: [string, string];
  scopeLabel?: string | null;
  drillFilter?: { field: string; value: string } | null;
  onClearDrill?: () => void;
  onClearScope?: () => void;
};

export function GlobalFilterBar({
  periodLabel,
  dateRange,
  scopeLabel,
  drillFilter,
  onClearDrill,
  onClearScope,
}: GlobalFilterBarProps) {
  const hasFilters = Boolean(scopeLabel || drillFilter);
  if (!periodLabel && !hasFilters) return null;

  return (
    <div className="no-print flex flex-wrap items-center gap-2 rounded-xl border border-edge-subtle bg-surface-subtle px-3 py-2 text-xs">
      <span className="font-medium uppercase tracking-wide text-fg-muted">Active filters</span>
      {periodLabel ? (
        <span className="chip chip-active">
          {periodLabel}
          {dateRange ? ` · ${dateRange[0]} → ${dateRange[1]}` : ""}
        </span>
      ) : null}
      {scopeLabel ? (
        <span className="chip">
          {scopeLabel}
          {onClearScope ? (
            <button
              type="button"
              onClick={onClearScope}
              className="ml-1 text-fg-muted hover:text-heading"
              aria-label="Clear scope filter"
            >
              ×
            </button>
          ) : null}
        </span>
      ) : null}
      {drillFilter ? (
        <span className="chip border-amber-400/30 bg-amber-500/10 text-amber-800 dark:text-amber-100">
          {prettifyFieldName(drillFilter.field)} = {drillFilter.value}
          {onClearDrill ? (
            <button
              type="button"
              onClick={onClearDrill}
              className="ml-1 text-amber-700 dark:text-amber-200/80 hover:text-heading"
              aria-label="Clear cross-filter"
            >
              ×
            </button>
          ) : null}
        </span>
      ) : null}
    </div>
  );
}
