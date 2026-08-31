"use client";

import { useMemo } from "react";
import { BuilderChart } from "@/components/builder/BuilderChart";
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
          <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-muted">
            Chart view
          </p>
          <p className="text-xs text-fg-muted">
            {prettifyFieldName(suggestion.dimensionKey)} vs{" "}
            {prettifyFieldName(suggestion.measureKey)}
            {chartRows.length < rows.length
              ? ` · showing first ${chartRows.length} rows`
              : ""}
          </p>
        </div>
      </div>
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-solid)] p-2">
        <BuilderChart
          visual={suggestion.chartType}
          rows={chartRows}
          xKey={suggestion.dimensionKey}
          xLabel={prettifyFieldName(suggestion.dimensionKey)}
          series={[
            {
              key: suggestion.measureKey,
              label: prettifyFieldName(suggestion.measureKey),
              currency: suggestion.isCurrency,
            },
          ]}
          sortTimeSeries={suggestion.sortTimeSeries}
          height={272}
          emptyMessage="No chart data for this result"
        />
      </div>
    </div>
  );
}
