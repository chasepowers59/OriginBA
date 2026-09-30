"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  defaultDateRange,
  defaultDateRangeLastMonth,
  defaultDateRangeYtd,
  runSnapshotQuery,
} from "@/lib/api";
import type { PremadeReport, QueryResponse, SnapshotMetadata } from "@/lib/types";
import {
  allowedAggsForMeasure,
  buildColumnLabels,
  defaultMeasureSelection,
  withoutRepeatedLeadingWord,
} from "@/lib/businessLabels";
import { getFavorite } from "@/lib/favorites";
import { getViewRemote, saveViewRemote } from "@/lib/savedViews";
import {
  ALL_DATES,
  applyDatePresetConfig,
  canvasOpensOnAllDates,
  canWidenDateRange,
  estimatePeriodDays,
  explorerPeriodLabel,
  fallBackToAllDates,
  opensOnAllDates,
  widenDateRange,
} from "@/lib/datePresets";
import { explorerQuery, reportToRun } from "@/lib/explorerFilters";
import { runningLabel } from "@/lib/queryProgress";
import { applyProcessGuide } from "@/lib/processGuide";
import { resolveDateField } from "@/lib/tileDateField";
import { setPageContext } from "@/lib/assistantContext";
import { PinMenu } from "@/components/PinMenu";
import { useAuth } from "@/components/AuthProvider";
import { POPOVER_PANEL, usePopover } from "@/lib/popover";
import { FavoritesPanel } from "./FavoritesPanel";
import { GlobalFilterBar } from "./GlobalFilterBar";
import { ResultsPanel } from "./ResultsPanel";
import { ScopeFilterSelect } from "./ScopeFilterSelect";
import { SnapshotDataModelPanel } from "./SnapshotDataModelPanel";
import { VisibilityToggle } from "./VisibilityToggle";
import { FolderInput } from "./FolderInput";

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

type Tab = "reports" | "model";

type ChartType = "bar" | "line" | "pie" | "horizontal" | "table";

/** The report behind the result on screen, restored when a newer run is cancelled. */
type ShownReport = {
  id: string;
  title: string;
  dimensions: string[];
  measureField: string;
  measureAgg: string;
  chartType: ChartType;
};

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
  const measures = scoped.guidedMeasures;
  const processGuide = scoped.processGuide;
  const { can } = useAuth();
  // Ad-hoc building and SQL now live at the single /build and /database surfaces (see the
  // CTAs + the ?tab redirects below); the canvas page keeps only Reports + Data model.
  const tabOptions = (
    [
      ["reports", "Reports", true],
      ["model", "Data model", can("portal:read")],
    ] as const
  ).filter(([, , allowed]) => allowed);

  const tabFromUrl = searchParams.get("tab");
  const initialTab: Tab = tabFromUrl === "model" ? "model" : "reports";

  const [tab, setTab] = useState<Tab>(initialTab);
  const [activeReportId, setActiveReportId] = useState<string | null>(null);
  const [activeReportTitle, setActiveReportTitle] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState<string[]>([]);
  const [measureField, setMeasureField] = useState("*");
  const [measureAgg, setMeasureAgg] = useState("count");
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [activePreset, setActivePreset] = useState("Last 6 months");
  const [allDates, setAllDates] = useState(false);
  const [privateOnly, setPrivateOnly] = useState(false);
  const [folder, setFolder] = useState("");
  // The opening window the page fell back from, said beside "All dates" so the reader knows why.
  const [fellBackFrom, setFellBackFrom] = useState<string | null>(null);
  const firstRun = useRef(true);
  const [scopeField, setScopeField] = useState(scopeFilters[0]?.field ?? "");
  const [scopeValue, setScopeValue] = useState("");
  const [chartType, setChartType] = useState<ChartType>("bar");
  const [drillFilter, setDrillFilter] = useState<{ field: string; value: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [favoriteApplied, setFavoriteApplied] = useState(false);
  const [openAbout, setOpenAbout] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [cancelNote, setCancelNote] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const shownRef = useRef<ShownReport | null>(null);
  const aboutIdPrefix = useId();

  const allowedTabs = new Set<Tab>(tabOptions.map(([key]) => key));

  // Old deep links route to the single surfaces: ?tab=sql -> /database, ?tab=builder -> /build.
  useEffect(() => {
    if (tabFromUrl === "sql") {
      router.replace(`/database?table=${encodeURIComponent(metadata.table_name)}`);
    } else if (tabFromUrl === "builder") {
      router.replace(`/build?canvas=${encodeURIComponent(metadata.id)}`);
    }
  }, [tabFromUrl, router, metadata.table_name, metadata.id]);

  useEffect(() => {
    const next = tabFromUrl === "model" ? "model" : tabFromUrl === "reports" ? "reports" : null;
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
    if (preset.kind === "ytd") range = defaultDateRangeYtd(metadata.data_as_of);
    else if (preset.kind === "last_month") range = defaultDateRangeLastMonth(metadata.data_as_of);
    else range = defaultDateRange(preset.days, metadata.data_as_of);
    setDateStart(range[0]);
    setDateEnd(range[1]);
    setActivePreset(preset.label);
    setAllDates(false);
    setFellBackFrom(null);
  }, [metadata.data_as_of]);

  const showAllDates = useCallback(() => {
    setAllDates(true);
    setActivePreset(ALL_DATES);
    setFellBackFrom(null);
  }, []);

  const buildQuery = useCallback(
    // The presets window on the canvas's MEASURED date. They used to key off a
    // mandatory-window field no canvas sets, so "Prior month" changed state and sent
    // nothing -- the query ran unwindowed and the reader had no way to tell. A canvas
    // with no date at all (the price list, asset locations) gets no window, which is
    // correct: a transaction window means nothing on a dimension table.
    (report: PremadeReport) =>
      explorerQuery({
        dateField: resolveDateField(metadata),
        allDates,
        dateStart,
        dateEnd,
        reportFilters: report.filters,
        scope: { field: scopeField, value: scopeValue },
        drill: drillFilter,
        dimensions: report.dimensions,
        measures: report.measures,
      }),
    [metadata, allDates, dateStart, dateEnd, scopeField, scopeValue, drillFilter],
  );

  const showReport = useCallback((shown: ShownReport | null) => {
    setActiveReportId(shown?.id ?? null);
    setActiveReportTitle(shown?.title ?? null);
    setDimensions(shown?.dimensions ?? []);
    if (!shown) return;
    setMeasureField(shown.measureField);
    setMeasureAgg(shown.measureAgg);
    setChartType(shown.chartType);
  }, []);

  const runPremade = useCallback(
    async (report: PremadeReport) => {
      const shown: ShownReport = {
        id: report.id,
        title: report.title,
        dimensions: report.dimensions,
        measureField: report.measures[0]?.field ?? "*",
        measureAgg: report.measures[0]?.agg ?? "count",
        chartType: report.chart_type,
      };
      showReport(shown);
      setTab("reports");
      if (opensOnAllDates({ report, activeReportId, allDates, hasDateField: Boolean(resolveDateField(metadata)) })) {
        // the auto-run effect follows allDates and re-runs this report unwindowed
        setFellBackFrom(null);
        setActivePreset(ALL_DATES);
        setAllDates(true);
        return;
      }
      setLoading(true);
      setError(null);
      setCancelNote(null);
      // A newer run supersedes an older one, so a slow response can no longer land on top.
      abortRef.current?.abort();
      const run = new AbortController();
      abortRef.current = run;
      try {
        const response = await runSnapshotQuery(metadata.id, buildQuery(report), run.signal);
        const fallBack = fallBackToAllDates({
          rowCount: response.row_count,
          windowed: Boolean(resolveDateField(metadata)) && !allDates,
          firstRun: firstRun.current,
        });
        firstRun.current = false;
        if (fallBack) {
          // Re-run without the window (the auto-run effect follows allDates).
          setFellBackFrom(activePreset);
          setActivePreset(ALL_DATES);
          setAllDates(true);
          return;
        }
        setResult(response);
        shownRef.current = shown;
      } catch (err) {
        if (run.signal.aborted) return;
        setError(err instanceof Error ? err.message : "Unable to run this report");
        setResult(null);
      } finally {
        if (abortRef.current === run) {
          abortRef.current = null;
          setLoading(false);
        }
      }
    },
    [metadata, allDates, activePreset, activeReportId, buildQuery, showReport],
  );

  const cancelRun = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
    showReport(shownRef.current);
    setCancelNote(result ? "Cancelled. Showing the previous result." : "Cancelled.");
  };

  useEffect(() => {
    if (!loading) return;
    const started = Date.now();
    const timer = window.setInterval(() => setElapsedMs(Date.now() - started), 1000);
    return () => {
      window.clearInterval(timer);
      setElapsedMs(0);
    };
  }, [loading]);

  useEffect(() => () => abortRef.current?.abort(), []);

  useEffect(() => {
    const { range, label } = applyDatePresetConfig(metadata.default_date_preset, metadata.data_as_of);
    const defaultMeasure = defaultMeasureSelection({
      measures,
      trusted_measures: metadata.trusted_measures,
    });
    const allByDefault = canvasOpensOnAllDates(metadata.default_date_preset);
    setDateStart(range[0]);
    setDateEnd(range[1]);
    setActivePreset(allByDefault ? ALL_DATES : label);
    setAllDates(allByDefault);
    setFellBackFrom(null);
    firstRun.current = true;
    setActiveReportId(null);
    setActiveReportTitle(null);
    setMeasureField(defaultMeasure.field);
    setMeasureAgg(defaultMeasure.agg);
    setScopeField(scopeFilters[0]?.field ?? "");
    setScopeValue("");
    setDrillFilter(null);
    abortRef.current?.abort();
    shownRef.current = null;
    setCancelNote(null);
    setResult(null);
    setFavoriteApplied(false);
  }, [
    metadata.id,
    processId,
    scopeFilters,
    metadata.default_date_preset,
    metadata.data_as_of,
    metadata.trusted_measures,
    measures,
  ]);

  useEffect(() => {
    // a report's own aggregation stands, e.g. a share of a true/false field, which is not a measure
    const own = premadeReports.find((r) => r.id === activeReportId)?.measures[0];
    if (own?.field === measureField && own.agg === measureAgg) return;
    const aggs = allowedAggsForMeasure({ measures }, measureField);
    if (!aggs.includes(measureAgg)) {
      setMeasureAgg(aggs[0] ?? "count");
    }
  }, [measureField, measureAgg, metadata, activeReportId, premadeReports]);

  useEffect(() => {
    const field = searchParams.get("cross_field");
    const value = searchParams.get("cross_value");
    if (field && value) {
      setDrillFilter({ field, value });
    }
  }, [searchParams]);

  useEffect(() => {
    const favId = searchParams.get("favorite");
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
      setAllDates(fav.datePreset === ALL_DATES);
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
        // A custom (dimensions-based) saved view opens in the single builder surface,
        // WITH its saved definition (the view id hydrates the shelves there).
        router.replace(`/build?view=${encodeURIComponent(fav.id)}`);
      }
    }
  }, [searchParams, metadata, favoriteApplied, runPremade, dateStart, dateEnd, router]);

  useEffect(() => {
    if (!dateStart || !dateEnd) return;
    if (searchParams.get("favorite") && !favoriteApplied) return;
    if (tab === "model") return;

    // a ?report= link is applied here and only here: running it anywhere else raced this run
    const linked = favoriteApplied ? null : searchParams.get("report");
    const report = reportToRun(premadeReports, activeReportId, linked);
    if (!report) return;
    if (linked) setFavoriteApplied(true);
    runPremade(report);
  }, [allDates, dateStart, dateEnd, scopeField, scopeValue, drillFilter, metadata.id, tab]); // eslint-disable-line react-hooks/exhaustive-deps

  const activeReport = premadeReports.find((r) => r.id === activeReportId) ?? null;

  const drillDimension =
    dimensions[0] ??
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

  const periodLabel = explorerPeriodLabel({
    allDates,
    activePreset,
    asOf: metadata.data_as_of,
    fellBackFrom,
    appliedWindow: result?.applied_window,
  });

  // Tell the assistant which canvas and window the reader is looking at.
  useEffect(() => {
    setPageContext({
      canvas_id: metadata.id,
      label: metadata.label,
      period: periodLabel,
      filters: [
        ...(scopeField && scopeValue ? [`${scopeField} = ${scopeValue}`] : []),
        ...(drillFilter ? [`${drillFilter.field} = ${drillFilter.value}`] : []),
      ],
    });
  }, [metadata.id, metadata.label, periodLabel, scopeField, scopeValue, drillFilter]);
  useEffect(() => () => setPageContext(null), []);

  const handleWidenPeriod = () => {
    const currentDays = estimatePeriodDays(dateStart, dateEnd);
    const wider = widenDateRange(currentDays, metadata.data_as_of);
    setDateStart(wider.range[0]);
    setDateEnd(wider.range[1]);
    setActivePreset(wider.label);
    setAllDates(false);
  };

  const dimensionKey = drillDimension || dimensions[0] || "";
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
    const server = Object.entries(result.column_labels ?? {}).map(([c, l]) => [c, withoutRepeatedLeadingWord(l)]);
    return { ...local, ...Object.fromEntries(server) };
  }, [result, metadata, dimensions, measureField, measureAgg]);

  // Flag columns keyed by declared type, so the detail table renders True/False rather
  // than a raw 1/0 (Oracle NUMBER(1)) or bare boolean.
  const booleanColumns = useMemo(
    () => new Set((metadata.fields ?? []).filter((f) => f.type === "boolean").map((f) => f.id)),
    [metadata.fields],
  );

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
    visibility: (privateOnly ? "private" : "organization") as "private" | "organization",
    folder: folder.trim() || null,
  });

  const handleSaveFavorite = async () => {
    await saveViewRemote(viewPayload());
    setSavedMsg(privateOnly ? "Saved for you only" : "Saved to workspace");
    window.setTimeout(() => setSavedMsg(null), 2500);
  };

  const handleSaveCopy = async () => {
    const base = viewPayload();
    await saveViewRemote({ ...base, title: `${base.title} (copy)` });
    setSavedMsg("Saved copy to workspace");
    window.setTimeout(() => setSavedMsg(null), 2500);
  };

  const running = loading ? runningLabel(elapsedMs) : null;
  const resolvedDateField = resolveDateField(metadata);
  const dateFieldLabel =
    metadata.date_fields.find((d) => d.id === resolvedDateField)?.label ??
    resolvedDateField ??
    "";

  return (
    <div className="space-y-6">
      {processGuide ? (
        <div className="glass-panel-subtle border-edge px-4 py-3">
          <p className="text-sm font-semibold portal-heading">{processGuide.label}</p>
          <p className="mt-1 text-sm portal-text-muted">{processGuide.description}</p>
          <p className="mt-2 text-xs portal-text-subtle">
            Fields and reports are limited to what is relevant for this business process.
          </p>
        </div>
      ) : null}
      {tab !== "model" ? (
        <GlobalFilterBar
          periodLabel={periodLabel}
          dateRange={allDates ? undefined : [dateStart, dateEnd]}
          scopeLabel={scopeLabel && scopeValue ? `${scopeLabel}: ${scopeValue}` : null}
          drillFilter={drillFilter}
          onClearDrill={clearDrill}
          onClearScope={() => setScopeValue("")}
        />
      ) : null}
      <div className="no-print flex flex-wrap items-center justify-between gap-2">
        {/* basis-full until sm: `flex-1` alone means flex-basis:0, so on a narrow screen
            this collapsed to 43px beside its siblings instead of wrapping onto its own
            line, and the tab labels rendered 16px wide and unreadable. */}
        <div className="glass-panel basis-full p-2 sm:basis-0 sm:flex-1">
          <div className="grid grid-cols-2 gap-1 sm:grid-cols-3">
            {tabOptions.map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => selectTab(key)}
                className={`rounded-xl px-2 py-2.5 text-xs font-medium transition sm:text-sm ${
 tab === key
 ? "tint-active text-heading ring-1 ring-edge"
 : "text-fg-muted hover:bg-chip hover:text-heading"
 }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        {/* Route to the single full-featured surfaces for deeper work. */}
        <div className="flex gap-2">
          {can("explorer:builder") ? (
            <Link href={`/build?canvas=${encodeURIComponent(metadata.id)}`} className="btn-ghost whitespace-nowrap text-xs">
              Build a custom view →
            </Link>
          ) : null}
          {can("snapshots:raw_sql") ? (
            <Link
              href={`/database?table=${encodeURIComponent(metadata.table_name)}`}
              className="btn-ghost whitespace-nowrap text-xs"
            >
              Open in SQL →
            </Link>
          ) : null}
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
      ) : (
        // Stacked (below xl), the results come straight after the filters and before the
        // report list; side by side, the filters and the list share the left column.
        <div className="grid gap-6 xl:grid-cols-[340px_1fr] xl:grid-rows-[auto_1fr]">
      {/* min-w-0 on every item: a grid item defaults to min-width:auto, so one wide child
          sized this column to 860px in a 375px viewport and scrolled the whole PAGE sideways. */}
      <div className="no-print min-w-0 space-y-4 xl:col-start-1 xl:row-start-1">
        <div className="glass-panel p-4">
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-widest text-fg-muted">
            Reporting period
          </p>
          <p className="mb-3 text-xs text-fg-muted">
            {resolvedDateField
              ? `Filtered by ${dateFieldLabel.toLowerCase()}`
              : "This report has no date to filter on."}
          </p>
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
            {dateFieldLabel ? (
              <button
                type="button"
                onClick={showAllDates}
                className={`chip ${allDates ? "chip-active" : ""}`}
              >
                {ALL_DATES}
              </button>
            ) : null}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <label className="block text-xs text-fg-muted">
              Start date
              <input
                type="date"
                value={allDates ? "" : dateStart}
                disabled={allDates}
                onChange={(e) => {
                  setDateStart(e.target.value);
                  setActivePreset("Custom range");
                  setAllDates(false);
                }}
                className="input-modern mt-1"
              />
            </label>
            <label className="block text-xs text-fg-muted">
              End date
              <input
                type="date"
                value={allDates ? "" : dateEnd}
                disabled={allDates}
                onChange={(e) => {
                  setDateEnd(e.target.value);
                  setActivePreset("Custom range");
                  setAllDates(false);
                }}
                className="input-modern mt-1"
              />
            </label>
          </div>
          {allDates ? (
            <p className="mt-2 text-xs text-fg-muted">Pick a period above to choose dates.</p>
          ) : null}
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
      </div>

      <main className="min-w-0 space-y-4 xl:col-start-2 xl:row-span-2 xl:row-start-1">
        {error ? (
          <div className="glass-panel border-over bg-over-bg px-4 py-3 text-sm text-over">
            {error}
          </div>
        ) : null}
        {running ? (
          <div className="glass-panel-subtle flex items-center justify-between gap-3 px-4 py-2 text-sm text-heading">
            {/* Read out by the status line at the end of this column. */}
            <span aria-hidden="true">{running}</span>
            <button type="button" onClick={cancelRun} className="btn-ghost text-xs">
              Cancel
            </button>
          </div>
        ) : cancelNote ? (
          <p className="text-xs text-fg-muted">{cancelNote}</p>
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
            chartType={chartType}
            loading={loading}
            snapshotId={metadata.id}
            snapshotLabel={metadata.label}
            reportTitle={activeReportTitle}
            columnLabels={columnLabels}
            booleanColumns={booleanColumns}
            measureField={measureField}
            measureAgg={measureAgg}
            periodLabel={periodLabel}
            scopeLabel={scopeLabel ? `${scopeLabel}: ${scopeValue}` : undefined}
            dateRange={allDates ? undefined : [dateStart, dateEnd]}
            drillFilter={drillFilter}
            onDrillSelect={drillDimension ? handleDrill : undefined}
            onClearDrill={clearDrill}
            sortTimeSeries={false}
            emptyContext={{
              periodLabel,
              dateRange: allDates ? undefined : [dateStart, dateEnd],
              scopeLabel: scopeLabel ? `${scopeLabel}: ${scopeValue}` : undefined,
              drillFilter,
            }}
            onWidenPeriod={
              canWidenDateRange({
                allDates,
                dateField: resolvedDateField,
                currentDays: estimatePeriodDays(dateStart, dateEnd),
              })
                ? handleWidenPeriod
                : undefined
            }
            onShowAllDates={allDates || !dateFieldLabel ? undefined : showAllDates}
            actions={
              <SaveMenu message={savedMsg}>
                <div className="flex flex-wrap items-center gap-2">
                  <FolderInput kind="views" value={folder} onChange={setFolder} />
                  <VisibilityToggle privateOnly={privateOnly} onChange={setPrivateOnly} />
                </div>
                <button type="button" onClick={() => void handleSaveFavorite()} className="btn-ghost w-full">
                  Save view
                </button>
                <button type="button" onClick={() => void handleSaveCopy()} className="btn-ghost w-full text-xs">
                  Save a copy
                </button>
                {activeReportId ? (
                  <PinMenu
                    target={{
                      snapshotId: metadata.id,
                      reportId: activeReportId,
                      title: activeReportTitle ?? metadata.label,
                      chartType,
                      days: estimatePeriodDays(dateStart, dateEnd),
                    }}
                  />
                ) : null}
              </SaveMenu>
            }
          />
        )}
        {/* Always mounted, so a screen reader hears the running count and a cancel. */}
        <p role="status" aria-live="polite" className="sr-only">
          {running ?? cancelNote ?? ""}
        </p>
      </main>

      <aside className="no-print min-w-0 space-y-4 self-start xl:col-start-1 xl:row-start-2">
        <div className="glass-panel p-4">
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-fg-muted">
            Ready-to-run reports
          </p>
          <ul className="space-y-2">
            {premadeReports.map((report) => {
              const aboutId = `${aboutIdPrefix}-${report.id}`;
              const aboutOpen = openAbout === report.id;
              return (
                <li
                  key={report.id}
                  className={`rounded-xl border transition ${
 activeReportId === report.id
 ? "border-edge bg-band ring-1 ring-edge"
 : "border-edge-subtle bg-surface-subtle hover:bg-chip"
 }`}
                >
                  <div className="flex items-start">
                    <button
                      type="button"
                      onClick={() => runPremade(report)}
                      disabled={loading}
                      aria-current={activeReportId === report.id ? "true" : undefined}
                      className="min-w-0 flex-1 px-4 py-3 text-left font-medium text-heading disabled:opacity-60"
                    >
                      {report.title}
                    </button>
                    {report.description ? (
                      <button
                        type="button"
                        onClick={() => setOpenAbout(aboutOpen ? null : report.id)}
                        aria-expanded={aboutOpen}
                        aria-controls={aboutId}
                        aria-label={`About ${report.title}`}
                        className="shrink-0 rounded-xl px-3 py-3 text-fg-muted hover:text-heading"
                      >
                        <span aria-hidden="true">{aboutOpen ? "▴" : "▾"}</span>
                      </button>
                    ) : null}
                  </div>
                  {aboutOpen ? (
                    <p id={aboutId} className="px-4 pb-3 text-xs text-fg-muted">
                      {report.description}
                    </p>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
        <FavoritesPanel compact />
      </aside>
        </div>
      )}
    </div>
  );
}

/** Save and pin, behind one toolbar button; the panel stays open to confirm a save. */
function SaveMenu({ message, children }: { message: string | null; children: ReactNode }) {
  const { open, setOpen, rootRef, triggerRef } = usePopover();
  const panelId = useId();
  return (
    <div ref={rootRef} className="sm:relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="btn-ghost whitespace-nowrap"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
      >
        Save <span aria-hidden="true">▾</span>
      </button>
      {open ? (
        <div id={panelId} role="group" aria-label="Save or pin this view" className={`${POPOVER_PANEL} space-y-2 p-3 sm:w-72`}>
          {children}
          {message ? <p role="status" className="text-center text-xs text-ok">{message}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
