"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  defaultDateRange,
  defaultDateRangeLastMonth,
  defaultDateRangeYtd,
  runSnapshotQuery,
} from "@/lib/api";
import type { PremadeReport, QueryResponse, SnapshotMetadata } from "@/lib/types";
import {
  aggregationLabel,
  allowedAggsForMeasure,
  buildColumnLabels,
  chartTypeLabel,
  defaultMeasureSelection,
  prettifyFieldName,
  requiredDateLabel,
} from "@/lib/businessLabels";
import { getFavorite } from "@/lib/favorites";
import { getViewRemote, saveViewRemote } from "@/lib/savedViews";
import { applyDatePresetConfig, estimatePeriodDays, widenDateRange } from "@/lib/datePresets";
import { applyProcessGuide } from "@/lib/processGuide";
import { pinReportUrl } from "@/lib/pinReport";
import { useAuth } from "@/components/AuthProvider";
import { FavoritesPanel } from "./FavoritesPanel";
import { GlobalFilterBar } from "./GlobalFilterBar";
import { RawSqlPanel } from "./RawSqlPanel";
import { ResultsPanel } from "./ResultsPanel";
import { ScopeFilterSelect } from "./ScopeFilterSelect";
import { SnapshotDataModelPanel } from "./SnapshotDataModelPanel";

type DatePreset =
  | { kind: "days"; label: string; days: number }
  | { kind: "ytd"; label: string }
  | { kind: "last_month"; label: string };

const DATE_PRESETS: DatePreset[] = [
  { kind: "days", label: "Last 30 days", days: 30 },
  { kind: "days", label: "Last quarter", days: 90 },
  { kind: "last_month", label: "Prior month" },
  { kind: "ytd", label: "Year to date" },
  { kind: "days", label: "Last 12 months", days: 365 },
];

type Tab = "reports" | "builder" | "model" | "sql";

type ExplorerPanelProps = {
  metadata: SnapshotMetadata;
};

export function ExplorerPanel({ metadata }: ExplorerPanelProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const processId = searchParams.get("process");
  const scoped = useMemo(
    () => applyProcessGuide(metadata, processId),
    [metadata, processId],
  );
  const scopeFilters = scoped.guidedScopeFilters;
  const premadeReports = scoped.guidedPremadeReports;
  const builderDimensions = scoped.guidedDimensions;
  const builderMeasures = scoped.guidedMeasures;
  const processGuide = scoped.processGuide;
  const { can } = useAuth();
  const tabOptions = (
    [
      ["reports", "Reports", true],
      ["builder", "Ad Hoc Builder", can("explorer:builder")],
      ["model", "Data model", can("portal:read")],
      ["sql", "SQL", can("snapshots:raw_sql")],
    ] as const
  ).filter(([, , allowed]) => allowed);

  const tabFromUrl = searchParams.get("tab");
  const initialTab: Tab =
    tabFromUrl === "model" ||
    tabFromUrl === "sql" ||
    tabFromUrl === "builder" ||
    tabFromUrl === "reports"
      ? tabFromUrl
      : "reports";

  const [tab, setTab] = useState<Tab>(initialTab);
  const [activeReportId, setActiveReportId] = useState<string | null>(null);
  const [activeReportTitle, setActiveReportTitle] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState<string[]>([]);
  const [measureField, setMeasureField] = useState("*");
  const [measureAgg, setMeasureAgg] = useState("count");
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [activePreset, setActivePreset] = useState("Last 6 months");
  const [scopeField, setScopeField] = useState(scopeFilters[0]?.field ?? "");
  const [scopeValue, setScopeValue] = useState("");
  const [chartType, setChartType] = useState<"bar" | "line" | "pie" | "horizontal" | "table">("bar");
  const [timeGrain, setTimeGrain] = useState<"" | "month" | "quarter" | "year">("");
  const [drillFilter, setDrillFilter] = useState<{ field: string; value: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [favoriteApplied, setFavoriteApplied] = useState(false);

  const allowedTabs = new Set(tabOptions.map(([key]) => key));

  useEffect(() => {
    const next =
      tabFromUrl === "model" ||
      tabFromUrl === "sql" ||
      tabFromUrl === "builder" ||
      tabFromUrl === "reports"
        ? tabFromUrl
        : null;
    if (next && allowedTabs.has(next)) setTab(next);
  }, [tabFromUrl, allowedTabs]);

  const selectTab = useCallback(
    (next: Tab) => {
      setTab(next);
      const params = new URLSearchParams(searchParams.toString());
      if (next === "reports") params.delete("tab");
      else params.set("tab", next);
      if (next !== "model") params.delete("modelTab");
      const qs = params.toString();
      router.replace(qs ? `?${qs}` : `/explore/${metadata.id}`, { scroll: false });
    },
    [metadata.id, router, searchParams],
  );

  useEffect(() => {
    if (!allowedTabs.has(tab)) selectTab("reports");
  }, [allowedTabs, tab, selectTab]);

  const syncCrossFilterUrl = useCallback(
    (next: { field: string; value: string } | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (next) {
        params.set("cross_field", next.field);
        params.set("cross_value", next.value);
      } else {
        params.delete("cross_field");
        params.delete("cross_value");
      }
      const qs = params.toString();
      router.replace(qs ? `?${qs}` : `/explore/${metadata.id}`, { scroll: false });
    },
    [metadata.id, router, searchParams],
  );

  const modelSubTab = searchParams.get("modelTab");

  const applyDatePreset = useCallback((preset: DatePreset) => {
    let range: [string, string];
    if (preset.kind === "ytd") range = defaultDateRangeYtd();
    else if (preset.kind === "last_month") range = defaultDateRangeLastMonth();
    else range = defaultDateRange(preset.days);
    setDateStart(range[0]);
    setDateEnd(range[1]);
    setActivePreset(preset.label);
  }, []);

  const buildFilters = useCallback(
    (extra: PremadeReport["filters"] = []) => {
      // A snapshot need not HAVE a required date field. The dbt canvases do not: they
      // are contract-governed and row-capped, so a mandatory transaction window is both
      // unnecessary and meaningless on a dimension table like the price list. Building
      // the filter unconditionally sent {field: null} and the API rejected the whole
      // query -- "Input should be a valid string" -- so the explorer showed a validation
      // error instead of a chart.
      const filters: PremadeReport["filters"] = [
        ...(metadata.required_date_field
          ? [{
              field: metadata.required_date_field,
              op: "between" as const,
              value: [dateStart, dateEnd],
            }]
          : []),
        ...extra,
      ];
      if (scopeField && scopeValue) {
        filters.push({ field: scopeField, op: "eq", value: scopeValue });
      }
      if (drillFilter) {
        filters.push({ field: drillFilter.field, op: "eq", value: drillFilter.value });
      }
      return filters;
    },
    [metadata.required_date_field, dateStart, dateEnd, scopeField, scopeValue, drillFilter],
  );

  const runPremade = useCallback(
    async (report: PremadeReport) => {
      setActiveReportId(report.id);
      setActiveReportTitle(report.title);
      setDimensions(report.dimensions);
      setMeasureField(report.measures[0]?.field ?? "*");
      setMeasureAgg(report.measures[0]?.agg ?? "count");
      setChartType(report.chart_type);
      setTab("reports");
      setLoading(true);
      setError(null);
      try {
        const response = await runSnapshotQuery(metadata.id, {
          dimensions: report.dimensions,
          measures: report.measures,
          filters: buildFilters(report.filters),
          time_dimensions: [],
          limit: 500,
        });
        setResult(response);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to run this report");
        setResult(null);
      } finally {
        setLoading(false);
      }
    },
    [metadata.id, buildFilters],
  );

  const queryPayload = useCallback(
    (dims: string[], measures: { field: string; agg: string }[], extraFilters: PremadeReport["filters"] = []) => ({
      dimensions: timeGrain ? [] : dims,
      measures,
      filters: buildFilters(extraFilters),
      time_dimensions:
        timeGrain && metadata.required_date_field
          ? [{ field: metadata.required_date_field, grain: timeGrain }]
          : [],
      limit: 500,
    }),
    [timeGrain, metadata.required_date_field, buildFilters],
  );

  const runBuilder = useCallback(async () => {
    setLoading(true);
    setError(null);
    setActiveReportId(null);
    setActiveReportTitle("Custom analysis");
    setTab("builder");
    try {
      const response = await runSnapshotQuery(
        metadata.id,
        queryPayload(
          dimensions,
          [{ field: measureField, agg: measureAgg }],
        ),
      );
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to run this analysis");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [metadata.id, dimensions, measureField, measureAgg, queryPayload]);

  useEffect(() => {
    const { range, label } = applyDatePresetConfig(metadata.default_date_preset);
    const defaultMeasure = defaultMeasureSelection({
      measures: builderMeasures,
      trusted_measures: metadata.trusted_measures,
    });
    setDateStart(range[0]);
    setDateEnd(range[1]);
    setActivePreset(label);
    setActiveReportId(null);
    setActiveReportTitle(null);
    setMeasureField(defaultMeasure.field);
    setMeasureAgg(defaultMeasure.agg);
    setScopeField(scopeFilters[0]?.field ?? "");
    setScopeValue("");
    setDrillFilter(null);
    setResult(null);
    setFavoriteApplied(false);
  }, [
    metadata.id,
    processId,
    scopeFilters,
    metadata.default_date_preset,
    metadata.trusted_measures,
    builderMeasures,
  ]);

  useEffect(() => {
    const aggs = allowedAggsForMeasure({ measures: builderMeasures }, measureField);
    if (!aggs.includes(measureAgg)) {
      setMeasureAgg(aggs[0] ?? "count");
    }
  }, [measureField, measureAgg, metadata]);

  useEffect(() => {
    const field = searchParams.get("cross_field");
    const value = searchParams.get("cross_value");
    if (field && value) {
      setDrillFilter({ field, value });
    }
  }, [searchParams]);

  useEffect(() => {
    const favId = searchParams.get("favorite");
    const reportParam = searchParams.get("report");
    if (reportParam && !favoriteApplied && dateStart && dateEnd) {
      const report = premadeReports.find((r) => r.id === reportParam);
      if (report) {
        runPremade(report);
        setFavoriteApplied(true);
        return;
      }
    }
    if (favId && !favoriteApplied) {
      void getViewRemote(favId).then((fav) => {
        if (!fav || fav.snapshotId !== metadata.id) {
          const local = getFavorite(favId);
          if (local && local.snapshotId === metadata.id) applyFavorite(local);
          return;
        }
        applyFavorite(fav);
      });
    }

    function applyFavorite(fav: import("@/lib/favorites").SavedFavorite) {
      if (fav.dateStart) setDateStart(fav.dateStart);
      if (fav.dateEnd) setDateEnd(fav.dateEnd);
      if (fav.datePreset) setActivePreset(fav.datePreset);
      if (fav.scopeField) setScopeField(fav.scopeField);
      if (fav.scopeValue) setScopeValue(fav.scopeValue);
      if (fav.chartType) setChartType(fav.chartType);
      setFavoriteApplied(true);

      if (fav.kind === "premade" && fav.reportId) {
        const report = premadeReports.find((r) => r.id === fav.reportId);
        if (report) {
          window.setTimeout(() => runPremade(report), 0);
          return;
        }
      }
      if (fav.dimensions?.length) {
        setDimensions(fav.dimensions);
        setMeasureField(fav.measureField ?? "*");
        setMeasureAgg(fav.measureAgg ?? "count");
        setActiveReportTitle(fav.title);
        setTab("builder");
      }
    }
  }, [searchParams, metadata, favoriteApplied, runPremade, dateStart, dateEnd]);

  useEffect(() => {
    if (!dateStart || !dateEnd) return;
    if (searchParams.get("favorite") && !favoriteApplied) return;
    if (tab === "model" || tab === "sql") return;

    if (tab === "builder" && dimensions.length) {
      void runBuilder();
      return;
    }

    const report =
      premadeReports.find((r) => r.id === activeReportId) ?? premadeReports[0];
    if (!report) return;
    runPremade(report);
  }, [dateStart, dateEnd, scopeField, scopeValue, drillFilter, metadata.id, tab, dimensions.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const activeReport = premadeReports.find((r) => r.id === activeReportId) ?? null;

  const drillDimension = timeGrain
    ? null
    : dimensions[0] ??
      activeReport?.dimensions[0] ??
      (result && result.columns.length > 1 ? result.columns[0] : "");

  const handleDrill = useCallback(
    (category: string) => {
      const dim = drillDimension;
      if (!dim || dim.startsWith("TD")) return;
      const next =
        drillFilter?.field === dim && drillFilter.value === category
          ? null
          : { field: dim, value: category };
      setDrillFilter(next);
      syncCrossFilterUrl(next);
    },
    [drillDimension, drillFilter, syncCrossFilterUrl],
  );

  const clearDrill = () => {
    setDrillFilter(null);
    syncCrossFilterUrl(null);
  };

  const handleWidenPeriod = () => {
    const currentDays = estimatePeriodDays(dateStart, dateEnd);
    const wider = widenDateRange(currentDays);
    setDateStart(wider.range[0]);
    setDateEnd(wider.range[1]);
    setActivePreset(wider.label);
  };

  const trustedMeasures = metadata.trusted_measures ?? [];
  const showUntrustedSumWarning =
    measureAgg === "sum" &&
    measureField !== "*" &&
    !trustedMeasures.includes(measureField);

  const dimensionKey = timeGrain
    ? (result?.columns[0] ?? "")
    : drillDimension || dimensions[0] || "";
  const measureKey = useMemo(() => {
    if (!result?.columns.length) return "";
    return result.columns[result.columns.length - 1];
  }, [result]);

  const columnLabels = useMemo(() => {
    if (!result) return {};
    // The SERVER's labels first. It knows every alias it assigned; the client builder
    // only names the last measure column, so a two-measure report left the other as
    // "m0". Kept as the fallback for anything the server did not label.
    const local = buildColumnLabels(metadata, dimensions, measureField, measureAgg, result.columns);
    return { ...local, ...(result.column_labels ?? {}) };
  }, [result, metadata, dimensions, measureField, measureAgg]);

  const totalMeasure = useMemo(() => {
    if (!result || !measureKey) return null;
    return result.rows.reduce((sum, row) => sum + Number(row[measureKey] ?? 0), 0);
  }, [result, measureKey]);

  const scopeLabel =
    scopeValue && scopeFilters.find((f) => f.field === scopeField)?.label;

  const viewPayload = () => ({
    snapshotId: metadata.id,
    snapshotLabel: metadata.label,
    title: activeReportTitle ?? metadata.label,
    kind: (activeReportId ? "premade" : "custom") as "premade" | "custom",
    reportId: activeReportId ?? undefined,
    dimensions: dimensions.length ? dimensions : undefined,
    measureField,
    measureAgg,
    chartType,
    datePreset: activePreset,
    dateStart,
    dateEnd,
    scopeField: scopeField || undefined,
    scopeValue: scopeValue || undefined,
  });

  const handleSaveFavorite = async () => {
    await saveViewRemote(viewPayload());
    setSavedMsg("Saved to workspace");
    window.setTimeout(() => setSavedMsg(null), 2500);
  };

  const handleSaveCopy = async () => {
    const base = viewPayload();
    await saveViewRemote({ ...base, title: `${base.title} (copy)` });
    setSavedMsg("Saved copy to workspace");
    window.setTimeout(() => setSavedMsg(null), 2500);
  };

  const dateFieldLabel = requiredDateLabel(metadata);

  return (
    <div className="space-y-6">
      {processGuide ? (
        <div className="glass-panel-subtle border-sky-400/20 px-4 py-3">
          <p className="text-sm font-semibold portal-heading">{processGuide.label}</p>
          <p className="mt-1 text-sm portal-text-muted">{processGuide.description}</p>
          <p className="mt-2 text-xs portal-text-subtle">
            Fields and reports are limited to what is relevant for this business process.
          </p>
        </div>
      ) : null}
      {tab !== "model" && tab !== "sql" ? (
        <GlobalFilterBar
          periodLabel={activePreset}
          dateRange={[dateStart, dateEnd]}
          scopeLabel={scopeLabel && scopeValue ? `${scopeLabel}: ${scopeValue}` : null}
          drillFilter={drillFilter}
          onClearDrill={clearDrill}
          onClearScope={() => setScopeValue("")}
        />
      ) : null}
      <div className="no-print glass-panel p-2">
        <div className="grid grid-cols-2 gap-1 sm:grid-cols-4">
          {tabOptions.map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => selectTab(key)}
              className={`rounded-xl px-2 py-2.5 text-xs font-medium transition sm:text-sm ${
                tab === key
                  ? "bg-gradient-to-r from-sky-500/20 to-indigo-500/20 text-white ring-1 ring-sky-400/30"
                  : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {tab === "model" ? (
        <SnapshotDataModelPanel
          metadata={metadata}
          initialSubTab={
            modelSubTab === "tables" ||
            modelSubTab === "joins" ||
            modelSubTab === "fields" ||
            modelSubTab === "overview"
              ? modelSubTab
              : undefined
          }
        />
      ) : tab === "sql" ? (
        <RawSqlPanel snapshotId={metadata.id} tableName={metadata.table_name} />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[340px_1fr]">
      <aside className="no-print space-y-4">
        <FavoritesPanel compact />

        <div className="glass-panel p-4">
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-widest text-slate-500">
            Reporting period
          </p>
          <p className="mb-3 text-xs text-slate-600">Filtered by {dateFieldLabel.toLowerCase()}</p>
          <div className="mb-3 flex flex-wrap gap-2">
            {DATE_PRESETS.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => applyDatePreset(p)}
                className={`chip ${activePreset === p.label ? "chip-active" : ""}`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <label className="block text-xs text-slate-500">
              Start date
              <input
                type="date"
                value={dateStart}
                onChange={(e) => {
                  setDateStart(e.target.value);
                  setActivePreset("Custom range");
                }}
                className="input-modern mt-1"
              />
            </label>
            <label className="block text-xs text-slate-500">
              End date
              <input
                type="date"
                value={dateEnd}
                onChange={(e) => {
                  setDateEnd(e.target.value);
                  setActivePreset("Custom range");
                }}
                className="input-modern mt-1"
              />
            </label>
          </div>
        </div>

        {scopeFilters.length ? (
          <ScopeFilterSelect
            snapshotId={metadata.id}
            filters={scopeFilters}
            selectedField={scopeField}
            selectedValue={scopeValue}
            onFieldChange={setScopeField}
            onValueChange={setScopeValue}
          />
        ) : null}

        {tab === "reports" ? (
          <div className="glass-panel p-4">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-slate-500">
              Ready-to-run reports
            </p>
            <div className="space-y-2">
              {premadeReports.map((report) => (
                <button
                  key={report.id}
                  type="button"
                  onClick={() => runPremade(report)}
                  disabled={loading}
                  className={`w-full rounded-xl border px-4 py-3 text-left transition disabled:opacity-60 ${
                    activeReportId === report.id
                      ? "border-sky-400/40 bg-sky-500/10 ring-1 ring-sky-400/20"
                      : "border-white/5 bg-slate-950/30 hover:border-white/15 hover:bg-white/5"
                  }`}
                >
                  <div className="font-medium text-white">{report.title}</div>
                  <div className="mt-1 text-xs text-slate-500">{report.description}</div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="glass-panel space-y-3 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
              Build your view
            </p>
            <label className="block text-xs text-slate-500">
              Time trend (optional)
              <select
                value={timeGrain}
                onChange={(e) => {
                  const v = e.target.value as "" | "month" | "quarter" | "year";
                  setTimeGrain(v);
                  if (v && chartType !== "table") setChartType("line");
                }}
                className="input-modern mt-1"
              >
                <option value="">Group by field</option>
                <option value="month">Trend by month</option>
                <option value="quarter">Trend by quarter</option>
                <option value="year">Trend by year</option>
              </select>
            </label>
            <label className="block text-xs text-slate-500">
              Field
              <select
                value={dimensions[0] ?? ""}
                onChange={(e) => setDimensions(e.target.value ? [e.target.value] : [])}
                disabled={Boolean(timeGrain)}
                className="input-modern mt-1 disabled:opacity-50"
              >
                <option value="">Choose a field…</option>
                {builderDimensions.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs text-slate-500">
              Metric
              <select
                value={measureField}
                onChange={(e) => {
                  const next = e.target.value;
                  setMeasureField(next);
                  const aggs = allowedAggsForMeasure({ measures: builderMeasures }, next);
                  setMeasureAgg(aggs[0] ?? "count");
                }}
                className="input-modern mt-1"
              >
                {builderMeasures.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                    {trustedMeasures.includes(m.id) ? " · trusted" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs text-slate-500">
              Calculation
              <select
                value={measureAgg}
                onChange={(e) => setMeasureAgg(e.target.value)}
                className="input-modern mt-1"
              >
                {allowedAggsForMeasure({ measures: builderMeasures }, measureField).map(
                  (agg) => (
                    <option key={agg} value={agg}>
                      {aggregationLabel(agg)}
                    </option>
                  ),
                )}
              </select>
            </label>
            <label className="block text-xs text-slate-500">
              Chart style
              <div className="mt-2 flex flex-wrap gap-2">
                {(["bar", "horizontal", "line", "pie", "table"] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => {
                      setChartType(t);
                      if (t === "table") setTimeGrain("");
                    }}
                    className={`chip ${chartType === t ? "chip-active" : ""}`}
                  >
                    {chartTypeLabel(t)}
                  </button>
                ))}
              </div>
            </label>
            <button
              type="button"
              onClick={runBuilder}
              disabled={loading || (!dimensions.length && !timeGrain)}
              className="btn-primary w-full"
            >
              {loading ? "Running analysis…" : "Run analysis"}
            </button>
            {showUntrustedSumWarning ? (
              <p className="rounded-lg border border-amber-400/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                <strong className="text-amber-200">Not a trusted measure.</strong> Summing{" "}
                {measureField} may double-count at this grain. Prefer{" "}
                {trustedMeasures.join(", ") || "governed measures"} for dollar totals.
              </p>
            ) : null}
          </div>
        )}

        {result ? (
          <div className="space-y-2">
            <button type="button" onClick={() => void handleSaveFavorite()} className="btn-ghost w-full">
              Save to workspace
            </button>
            <button type="button" onClick={() => void handleSaveCopy()} className="btn-ghost w-full text-xs">
              Save a copy
            </button>
            {activeReportId ? (
              <Link
                href={pinReportUrl({
                  snapshotId: metadata.id,
                  reportId: activeReportId,
                  title: activeReportTitle ?? metadata.label,
                  chartType,
                  days: estimatePeriodDays(dateStart, dateEnd),
                })}
                className="btn-ghost block w-full text-center text-xs"
              >
                Pin to dashboard
              </Link>
            ) : null}
          </div>
        ) : null}
        {savedMsg ? (
          <p className="text-center text-xs text-emerald-400">{savedMsg}</p>
        ) : null}
      </aside>

      <main className="space-y-4">
        {error ? (
          <div className="glass-panel border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        ) : null}
        {loading && !result ? (
          <div className="glass-panel p-8">
            <div className="loading-shimmer mb-4 h-8 w-48 rounded-lg" />
            <div className="loading-shimmer h-64 rounded-xl" />
          </div>
        ) : (
          <ResultsPanel
            result={result}
            dimensionKey={dimensionKey}
            measureKey={measureKey}
            chartType={timeGrain && chartType !== "table" ? "line" : chartType}
            totalMeasure={totalMeasure}
            loading={loading}
            snapshotId={metadata.id}
            snapshotLabel={metadata.label}
            reportTitle={activeReportTitle}
            columnLabels={columnLabels}
            measureField={measureField}
            measureAgg={measureAgg}
            periodLabel={activePreset}
            scopeLabel={scopeLabel ? `${scopeLabel}: ${scopeValue}` : undefined}
            dateRange={[dateStart, dateEnd]}
            drillFilter={drillFilter}
            onDrillSelect={drillDimension && !timeGrain ? handleDrill : undefined}
            onClearDrill={clearDrill}
            sortTimeSeries={Boolean(timeGrain)}
            emptyContext={{
              periodLabel: activePreset,
              dateRange: [dateStart, dateEnd],
              scopeLabel: scopeLabel ? `${scopeLabel}: ${scopeValue}` : undefined,
              drillFilter,
            }}
            onWidenPeriod={handleWidenPeriod}
          />
        )}
      </main>
        </div>
      )}
    </div>
  );
}
