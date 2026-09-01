"use client";

import { useMemo, useState } from "react";
import type { QueryResponse } from "@/lib/types";
import {
  formatBoolean,
  formatCellValue,
  formatCurrency,
  formatNumber,
  formatPercent,
} from "@/lib/format";
import { EmptyStateIcon } from "@/components/EmptyStateIcon";
import {
  kpiLabelsForMeasure,
  measureDisplaysAsCurrency,
  prettifyFieldName,
} from "@/lib/businessLabels";
import { BuilderChart } from "./builder/BuilderChart";
import { downloadWorkbook } from "@/lib/exportXlsx";
import { printCouncilPack } from "@/lib/councilPack";
import { useBrand } from "@/components/PortalThemeProvider";

type SortDir = "asc" | "desc";

type ResultsPanelProps = {
  result: QueryResponse | null;
  dimensionKey: string;
  measureKey: string;
  chartType: "bar" | "line" | "pie" | "horizontal" | "table";
  totalMeasure: number | null;
  loading: boolean;
  snapshotId: string;
  snapshotLabel?: string;
  reportTitle?: string | null;
  columnLabels?: Record<string, string>;
  booleanColumns?: Set<string>;
  measureField?: string;
  measureAgg?: string;
  periodLabel?: string;
  scopeLabel?: string;
  dateRange?: [string, string];
  drillFilter?: { field: string; value: string } | null;
  onDrillSelect?: (category: string) => void;
  onClearDrill?: () => void;
  sortTimeSeries?: boolean;
  emptyContext?: {
    periodLabel?: string;
    dateRange?: [string, string];
    scopeLabel?: string;
    drillFilter?: { field: string; value: string } | null;
  };
  onWidenPeriod?: () => void;
};

export function ResultsPanel({
  result,
  dimensionKey,
  measureKey,
  chartType,
  totalMeasure,
  loading,
  snapshotId,
  snapshotLabel,
  reportTitle,
  columnLabels = {},
  booleanColumns,
  measureField = "*",
  measureAgg = "count",
  periodLabel,
  scopeLabel,
  dateRange,
  drillFilter,
  onDrillSelect,
  onClearDrill,
  sortTimeSeries,
  emptyContext,
  onWidenPeriod,
}: ResultsPanelProps) {
  const brand = useBrand();
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const kpi = kpiLabelsForMeasure(measureField, measureAgg);
  const isCurrency = measureDisplaysAsCurrency(measureField, measureAgg);

  const insight = useMemo(() => {
    if (!result || !measureKey || !dimensionKey || !result.rows.length) return null;
    const sorted = [...result.rows].sort(
      (a, b) => Number(b[measureKey] ?? 0) - Number(a[measureKey] ?? 0),
    );
    const top = sorted[0];
    if (!top) return null;
    const topValue = Number(top[measureKey] ?? 0);
    const total = sorted.reduce((s, r) => s + Number(r[measureKey] ?? 0), 0);
    if (total <= 0) return null; // "leads at 0.0% of total" is noise, not an insight
    const label = String(top[dimensionKey] ?? "Top value");
    return { label, share: (topValue / total) * 100, topValue };
  }, [result, measureKey, dimensionKey]);

  const sortedRows = useMemo(() => {
    if (!result || !measureKey) return [];
    return [...result.rows].sort((a, b) => {
      const av = Number(a[measureKey] ?? 0);
      const bv = Number(b[measureKey] ?? 0);
      return sortDir === "desc" ? bv - av : av - bv;
    });
  }, [result, measureKey, sortDir]);

  if (!result && !loading) {
    return (
      <div className="glass-panel flex min-h-[320px] flex-col items-center justify-center p-12 text-center">
        <EmptyStateIcon variant="chart" />
        <p className="text-lg font-medium text-fg">Choose a standard report to get started</p>
        <p className="mt-2 max-w-sm text-sm text-fg-muted">
          Your chart, key metrics, and exportable detail table will appear here.
        </p>
      </div>
    );
  }

  if (!result) return null;

  if (result.row_count === 0 && !loading) {
    const ctx = emptyContext;
    return (
      <div className="glass-panel flex min-h-[320px] flex-col items-center justify-center p-10 text-center">
        <EmptyStateIcon variant="search" />
        <h3 className="text-lg font-semibold text-heading">No data for this view</h3>
        <p className="mt-3 max-w-md text-sm text-fg-muted">
          {ctx?.periodLabel ? (
            <>
              Nothing matched <strong className="text-heading">{ctx.periodLabel}</strong>
              {ctx.dateRange ? ` (${ctx.dateRange[0]} to ${ctx.dateRange[1]})` : ""}.
            </>
          ) : (
            "Nothing matched your current filters."
          )}
          {ctx?.scopeLabel ? <> Scope filter: {ctx.scopeLabel}.</> : null}
          {ctx?.drillFilter ? (
            <> Cross-filter: {ctx.drillFilter.value}.</>
          ) : null}
        </p>
        <p className="mt-2 text-xs text-fg-muted">
          Try widening the reporting period, clearing scope or cross-filters, or pick a different
          field.
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {onWidenPeriod ? (
            <button type="button" onClick={onWidenPeriod} className="btn-primary text-xs">
              Widen date range
            </button>
          ) : null}
          {onClearDrill && ctx?.drillFilter ? (
            <button type="button" onClick={onClearDrill} className="btn-ghost text-xs">
              Clear cross-filter
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  const handleExport = () => {
    // A REAL .xlsx (typed numbers survive) — this button said Excel while writing CSV.
    const friendlyHeaders = result.columns.map((c) => columnLabels[c] ?? prettifyFieldName(c));
    const labeledRows = result.rows.map((row) => {
      const out: Record<string, unknown> = {};
      result.columns.forEach((col, i) => {
        const v = row[col];
        out[friendlyHeaders[i]] =
          booleanColumns?.has(col) || typeof v === "boolean" ? formatBoolean(v) : v;
      });
      return out;
    });
    downloadWorkbook(
      [{ name: reportTitle ?? snapshotLabel ?? snapshotId, columns: friendlyHeaders, rows: labeledRows }],
      `${snapshotId}_analysis.xlsx`,
    );
  };

  const formatMeasure = (value: unknown) =>
    isCurrency ? formatCurrency(value) : formatNumber(value);

  const breakdownLabel =
    columnLabels[dimensionKey] ??
    columnLabels[result.columns[0] ?? ""] ??
    prettifyFieldName(dimensionKey);

  return (
    <div id="council-pack-export" className="council-pack space-y-4 animate-slide-up">
      <div className="council-pack-header hidden print:block">
        <p className="text-xs uppercase tracking-widest text-fg-muted">{brand.name}</p>
        <h1 className="text-2xl font-bold text-slate-900">{reportTitle ?? snapshotLabel}</h1>
        <p className="mt-1 text-sm text-fg-muted">{snapshotLabel}</p>
        <p className="mt-2 text-xs text-fg-muted">
          {periodLabel ?? "Reporting period"}
          {dateRange ? ` · ${dateRange[0]} to ${dateRange[1]}` : ""}
          {scopeLabel ? ` · ${scopeLabel}` : ""}
        </p>
        <p className="mt-1 text-xs text-fg-muted">
          Generated {new Date().toLocaleString()} · {brand.connection_label}
        </p>
        <hr className="my-4 border-slate-300" />
      </div>

      <div className="no-print flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-heading">
            {reportTitle ?? "Analysis results"}
          </h3>
          <p className="text-sm text-fg-muted">
            {periodLabel ? `${periodLabel} · ` : ""}
            {result.row_count} field values
            {loading ? " · updating…" : ""}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setSortDir((d) => (d === "desc" ? "asc" : "desc"))}
            className="btn-ghost"
          >
            Sort {sortDir === "desc" ? "high → low" : "low → high"}
          </button>
          <button type="button" onClick={handleExport} className="btn-ghost">
            Export to Excel
          </button>
          <button
            type="button"
            onClick={() => printCouncilPack(reportTitle ?? snapshotLabel ?? snapshotId)}
            className="btn-primary"
          >
            Council pack (PDF)
          </button>
        </div>
      </div>

      {onDrillSelect && !drillFilter ? (
        <p className="no-print text-xs text-fg-muted">
          Click a chart bar or table row to cross-filter this view.
        </p>
      ) : null}

      {insight ? (
        <div className="rounded-xl border border-sky-400/20 bg-gradient-to-r from-sky-500/10 to-indigo-500/10 px-4 py-3 text-sm text-heading">
          <span className="font-medium text-heading">{insight.label}</span> leads this view at{" "}
          <span className="font-semibold text-sky-600 dark:text-sky-300">{formatPercent(insight.share)}</span> of the
          total ({formatMeasure(insight.topValue)}).
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-3">
        <KpiCard label={kpi.groups} value={formatNumber(result.row_count)} />
        <KpiCard
          label={kpi.total}
          value={totalMeasure != null ? formatMeasure(totalMeasure) : "—"}
          highlight
        />
        <KpiCard label={kpi.breakdown} value={breakdownLabel} small />
      </div>

      {dimensionKey && measureKey && chartType !== "table" ? (
        <div className="glass-panel p-5">
          <BuilderChart
            visual={chartType as "bar" | "line" | "pie" | "horizontal"}
            rows={sortedRows}
            xKey={dimensionKey}
            xLabel={columnLabels[dimensionKey] ?? dimensionKey}
            series={[
              {
                key: measureKey,
                label: columnLabels[measureKey] ?? "Value",
                currency: isCurrency,
              },
            ]}
            selectedCategory={drillFilter?.value ?? null}
            onCategorySelect={onDrillSelect}
            sortTimeSeries={sortTimeSeries}
            emptyMessage="No chart data for this selection"
          />
        </div>
      ) : null}

      <div className="glass-panel overflow-hidden">
        <div className="border-b border-edge-subtle px-4 py-2 text-xs text-fg-muted">
          {chartType === "table"
            ? "Results table — click a row to cross-filter"
            : "Detail table — click a row to cross-filter"}
        </div>
        <div className={chartType === "table" ? "max-h-[560px] overflow-auto" : "max-h-[420px] overflow-auto"}>
          <table className="min-w-full text-left text-sm">
            <thead className="sticky top-0 border-b border-edge-subtle bg-surface-solid backdrop-blur">
              <tr>
                {result.columns.map((col) => (
                  <th key={col} className="px-4 py-3 font-medium text-fg-muted">
                    {columnLabels[col] ?? prettifyFieldName(col)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((row, idx) => (
                <tr
                  key={idx}
                  onClick={() =>
                    onDrillSelect?.(String(row[dimensionKey] ?? ""))
                  }
                  className={`border-b border-edge-subtle transition hover:bg-white/[0.03] ${
                    onDrillSelect ? "cursor-pointer" : ""
                  } ${
                    drillFilter?.value === String(row[dimensionKey])
                      ? "bg-amber-500/10"
                      : ""
                  }`}
                >
                  {result.columns.map((col) => (
                    <td key={col} className="px-4 py-2.5 text-heading">
                      {formatCellValue(row[col], {
                        columnId: col,
                        isMeasure: col === measureKey,
                        asCurrency: col === measureKey && isCurrency,
                        isBoolean: booleanColumns?.has(col),
                      })}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <details className="no-print glass-panel-subtle group p-4 text-xs text-fg-muted">
        <summary className="cursor-pointer font-medium text-fg-muted group-open:text-sky-400">
          Technical query details (for IT review)
        </summary>
        <pre className="mt-3 overflow-x-auto whitespace-pre-wrap rounded-lg bg-black/30 p-3 text-fg-muted">
          {result.sql}
        </pre>
      </details>
    </div>
  );
}

function KpiCard({
  label,
  value,
  highlight,
  small,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  small?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border px-4 py-3 ${
        highlight
          ? "border-sky-400/20 bg-gradient-to-br from-sky-500/10 to-indigo-500/10"
          : "border-edge-subtle bg-surface-subtle"
      }`}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted">{label}</p>
      <p
        className={`mt-1 font-semibold text-heading ${small ? "truncate text-sm" : "text-xl"}`}
        title={value}
      >
        {value}
      </p>
    </div>
  );
}
