"use client";

import { useMemo } from "react";
import { ChartView } from "@/components/ChartView";
import type { ChartSuggestion } from "@/lib/databaseChartUtils";
import { prettifyFieldName } from "@/lib/businessLabels";

export function DatabaseResultChart({
  rows,
  suggestion,
}: {
  rows: Record<string, unknown>[];
  suggestion: ChartSuggestion;
}) {
  const chartRows = useMemo(() => rows.slice(0, 100), [rows]);

  return (
    <div className="border-b border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            Chart view
          </p>
          <p className="text-xs text-slate-400">
            {prettifyFieldName(suggestion.dimensionKey)} vs{" "}
            {prettifyFieldName(suggestion.measureKey)}
            {chartRows.length < rows.length
              ? ` · showing first ${chartRows.length} rows`
              : ""}
          </p>
        </div>
      </div>
      <div className="h-72 rounded-xl border border-[var(--border)] bg-[var(--surface-solid)] p-2">
        <ChartView
          chartType={suggestion.chartType === "horizontal" ? "horizontal" : suggestion.chartType}
          rows={chartRows}
          dimensionKey={suggestion.dimensionKey}
          measureKey={suggestion.measureKey}
          measureLabel={prettifyFieldName(suggestion.measureKey)}
          isCurrency={suggestion.isCurrency}
          sortTimeSeries={suggestion.sortTimeSeries}
        />
      </div>
    </div>
  );
}
