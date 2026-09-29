"use client";

import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import type { QueryResponse } from "@/lib/types";
import {
  formatBoolean,
  formatCellValue,
  formatCurrency,
  formatNumber,
  formatPercent,
  formatDateTime,
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
import { AppliedWindowNote } from "@/components/AppliedWindowNote";
import { downloadPdf } from "@/lib/api";
import { isMeasureColumn, summarizeResult } from "@/lib/resultSummary";
import { POPOVER_PANEL, menuFocusIndex, usePopover } from "@/lib/popover";

type SortDir = "asc" | "desc";

type ResultsPanelProps = {
  result: QueryResponse | null;
  dimensionKey: string;
  measureKey: string;
  chartType: "bar" | "line" | "pie" | "horizontal" | "table";
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
  onShowAllDates?: () => void;
  /** Beside Export in the result toolbar (the explorer's Save menu). */
  actions?: ReactNode;
};

export function ResultsPanel({
  result,
  dimensionKey,
  measureKey,
  chartType,
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
  onShowAllDates,
  actions,
}: ResultsPanelProps) {
  const brand = useBrand();
  const [pdfState, setPdfState] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const kpi = kpiLabelsForMeasure(measureField, measureAgg);
  const isCurrency = measureDisplaysAsCurrency(measureField, measureAgg);

  const summary = useMemo(
    () =>
      result
        ? summarizeResult({
            columns: result.columns,
            rows: result.rows,
            measureKey,
            dimensionKey,
            measureField,
            measureAgg,
            labels: columnLabels,
          })
        : null,
    [result, measureKey, dimensionKey, measureField, measureAgg, columnLabels],
  );
  const insight = summary?.leader;

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
          {result.applied_window ? (
            // The window is the server's, so neither "your current filters" nor the
            // reader's own period (under All dates) is what matched nothing.
            <>{result.applied_window.note}</>
          ) : ctx?.periodLabel ? (
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
        <div className="relative mt-5 flex flex-wrap justify-center gap-2">
          {onShowAllDates ? (
            <button type="button" onClick={onShowAllDates} className="btn-primary text-xs">
              Show all dates
            </button>
          ) : null}
          {onWidenPeriod ? (
            <button type="button" onClick={onWidenPeriod} className={`${onShowAllDates ? "btn-ghost" : "btn-primary"} text-xs`}>
              Widen date range
            </button>
          ) : null}
          {onClearDrill && ctx?.drillFilter ? (
            <button type="button" onClick={onClearDrill} className="btn-ghost text-xs">
              Clear cross-filter
            </button>
          ) : null}
          {actions}
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

  const handlePdf = async () => {
    setPdfState("Preparing…");
    try {
      await downloadPdf({
        title: reportTitle ?? snapshotLabel ?? snapshotId,
        note: [periodLabel, dateRange ? `${dateRange[0]} to ${dateRange[1]}` : null].filter(Boolean).join(" · "),
        columns: result.columns,
        labels: Object.fromEntries(result.columns.map((c) => [c, columnLabels[c] ?? prettifyFieldName(c)])),
        rows: result.rows,
      });
      setPdfState(null);
    } catch (err) {
      setPdfState(err instanceof Error ? err.message : "The PDF could not be made.");
    }
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
          Generated {formatDateTime(new Date())} · {brand.connection_label}
        </p>
        <hr className="my-4 border-slate-300" />
      </div>

      <div className="no-print flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-lg font-semibold text-heading">
            {reportTitle ?? "Analysis results"}
          </h3>
          <p className="text-sm text-fg-muted">
            {periodLabel ? `${periodLabel} · ` : ""}
            {result.row_count} field values
            {loading ? " · updating…" : ""}
          </p>
          <AppliedWindowNote result={result} />
        </div>
        {/* relative: below sm a toolbar popup spans this row, not its button. */}
        <div className="relative flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setSortDir((d) => (d === "desc" ? "asc" : "desc"))}
            className="btn-ghost whitespace-nowrap"
          >
            Sort {sortDir === "desc" ? "high → low" : "low → high"}
          </button>
          <ExportMenu
            items={[
              { label: "Excel workbook", onSelect: handleExport },
              {
                label: pdfState === "Preparing…" ? "Preparing PDF…" : "Download PDF",
                onSelect: () => void handlePdf(),
                disabled: pdfState === "Preparing…",
              },
              {
                label: "Council pack (PDF)",
                onSelect: () => printCouncilPack(reportTitle ?? snapshotLabel ?? snapshotId),
              },
            ]}
          />
          {actions}
        </div>
      </div>
      {pdfState ? (
        <p role="status" className="no-print text-xs text-fg-muted">
          {pdfState === "Preparing…" ? "Preparing the PDF…" : pdfState}
        </p>
      ) : null}

      {onDrillSelect && !drillFilter ? (
        <p className="no-print text-xs text-fg-muted">
          Click a chart bar or table row to cross-filter this view.
        </p>
      ) : null}

      {insight ? (
        <div className="rounded-xl border border-edge tint-panel px-4 py-3 text-sm text-heading">
          <span className="font-medium text-heading">{insight.label}</span> leads this view at{" "}
          <span className="font-semibold text-primary">{formatPercent(insight.share)}</span> of the
          total ({formatMeasure(insight.value)}).
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-3">
        <KpiCard label={kpi.groups} value={formatNumber(result.row_count)} />
        <KpiCard
          label={kpi.total}
          value={summary?.total != null ? formatMeasure(summary.total) : "—"}
          note={summary?.notTotalled}
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
                  <th key={col} className={`px-4 py-3 font-medium text-fg-muted ${isMeasureColumn(col) ? "text-right" : ""}`}>
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
                  className={`border-b border-edge-subtle transition ${
 onDrillSelect ? "cursor-pointer" : ""
 } ${
 drillFilter?.value === String(row[dimensionKey])
 ? "bg-warn-bg"
 : "hover:bg-chip"
 }`}
                >
                  {result.columns.map((col) => (
                    <td key={col} className={`px-4 py-2.5 text-heading ${isMeasureColumn(col) ? "text-right tabular-nums" : ""}`}>
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
        <summary className="cursor-pointer font-medium text-fg-muted group-open:text-primary">
          Technical query details (for IT review)
        </summary>
        <pre className="mt-3 overflow-x-auto whitespace-pre-wrap rounded-lg bg-black/30 p-3 text-fg-muted">
          {result.sql}
        </pre>
      </details>
    </div>
  );
}

type ExportItem = { label: string; onSelect: () => void; disabled?: boolean };

function ExportMenu({ items }: { items: ExportItem[] }) {
  const { open, setOpen, rootRef, triggerRef } = usePopover();
  const menuId = useId();
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    if (open) itemRefs.current[0]?.focus();
  }, [open]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Tab") {
      setOpen(false);
      return;
    }
    const current = itemRefs.current.findIndex((el) => el === document.activeElement);
    const next = menuFocusIndex(e.key, current, items.length);
    if (next == null) return;
    e.preventDefault();
    itemRefs.current[next]?.focus();
  };

  return (
    <div ref={rootRef} className="sm:relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="btn-ghost whitespace-nowrap"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
      >
        Export <span aria-hidden="true">▾</span>
      </button>
      {open ? (
        <div id={menuId} role="menu" aria-label="Export" onKeyDown={onKeyDown} className={`${POPOVER_PANEL} p-1.5 sm:w-56`}>
          {items.map((item, i) => (
            <button
              key={i}
              ref={(el) => {
                itemRefs.current[i] = el;
              }}
              type="button"
              role="menuitem"
              disabled={item.disabled}
              onClick={() => {
                setOpen(false);
                item.onSelect();
              }}
              className="block w-full rounded-lg px-3 py-2 text-left text-sm text-heading hover:bg-chip disabled:opacity-60"
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function KpiCard({
  label,
  value,
  note,
  highlight,
  small,
}: {
  label: string;
  value: string;
  note?: string | null;
  highlight?: boolean;
  small?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border px-4 py-3 ${
 highlight
 ? "border-edge tint-panel-br"
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
      {note ? <p className="mt-1 text-xs text-fg-muted">{note}</p> : null}
    </div>
  );
}
