"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { fetchExecutiveSummary } from "@/lib/api";
import { KpiAlertsDialog } from "@/components/KpiAlertsDialog";
import { useBrand, usePortalConfig } from "@/components/PortalThemeProvider";
import type { ExecutiveSummary } from "@/lib/types";
import { DashboardWidget } from "./DashboardWidget";
import { DashboardControls, type CompareMode } from "./DashboardControls";
import { CrossFilterProvider, useCrossFilter } from "./CrossFilterContext";
import { PresentationToolbar } from "./PresentationToolbar";
import { formatDateTime } from "@/lib/format";
import { CrossFilterBanner } from "@/components/CrossFilterBanner";

type ExecutiveDashboardProps = {
  variant?: "home" | "full";
  initialDays?: number;
};

function ExecutiveDashboardInner({ variant = "full", initialDays = 30 }: ExecutiveDashboardProps) {
  const brand = useBrand();
  const portal = usePortalConfig();
  const { filter, toggleFilter, clearFilter } = useCrossFilter();
  const [days, setDays] = useState(initialDays);
  // Deltas are one toggle away, not on by default: the in-database Oracle path
  // runs a prior-period query per KPI, and doubling ~9 KPIs' queries over the VPN
  // left the grid blank for 20s+ (measured 2026-08-28). The KPIs load fast without
  // it; the polished delta chips render the moment Compare is on. The Postgres
  // shape could default this on -- revisit per-engine if it becomes worthwhile.
  const [compare, setCompare] = useState(false);
  const [compareMode, setCompareMode] = useState<CompareMode>("prior_period");
  const [summary, setSummary] = useState<ExecutiveSummary | null>(null);
  const [showAlerts, setShowAlerts] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [loading, setLoading] = useState(true);
  // Which lens each card is showing, by kpi id. Empty means every card keeps its
  // default, so the URL stays clean until the reader actually switches one.
  const [lenses, setLenses] = useState<Record<string, string>>({});

  useEffect(() => {
    setLoading(true);
    fetchExecutiveSummary(
      days,
      compare,
      filter ? { field: filter.field, value: filter.value } : undefined,
      compareMode,
      lenses,
    )
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false));
  }, [days, compare, compareMode, filter, reloadKey, lenses]);

  const handleLensChange = useCallback((kpiId: string, lensId: string) => {
    setLenses((prev) => (prev[kpiId] === lensId ? prev : { ...prev, [kpiId]: lensId }));
  }, []);

  const isHome = variant === "home";

  const exportSections = useMemo(
    () =>
      (summary?.kpis ?? []).map((kpi) => ({
        name: kpi.label,
        headers: ["Category", "Value"],
        rows: kpi.trend.map((t) => ({ Category: t.label, Value: t.value })),
      })),
    [summary],
  );

  const handleTrendClick = useCallback(
    (kpi: { trend_dimension?: string | null }, label: string) => {
      if (kpi.trend_dimension) {
        toggleFilter(kpi.trend_dimension, label);
      }
    },
    [toggleFilter],
  );

  return (
    <section className="space-y-4">
      {showAlerts ? <KpiAlertsDialog onClose={() => setShowAlerts(false)} /> : null}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-heading-accent">
            Executive overview
          </p>
          <h2 className="mt-1 text-xl font-bold text-heading md:text-2xl">
            {isHome ? "Key metrics at a glance" : `${portal.organization_name} performance`}
          </h2>
          <p className="mt-1 text-sm text-fg-muted">
            {summary?.period.label ?? `Last ${days} days`}
            {summary?.refresh?.last_refresh ? (
              <span className="ml-2 text-xs text-fg-muted">
                · data refreshed {formatDateTime(summary.refresh.last_refresh)} (
                {summary.refresh.tables.reduce((a, t) => a + t.batch_rows, 0).toLocaleString()}{" "}
                rows in latest batch)
              </span>
            ) : null}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {!isHome ? (
            <>
              <DashboardControls
                days={days}
                compare={compare}
                compareMode={compareMode}
                onDaysChange={setDays}
                onCompareChange={setCompare}
                onCompareModeChange={setCompareMode}
              />
              <PresentationToolbar
                title={`${portal.organization_name} Executive Dashboard`}
                exportSections={exportSections}
              />
              <button type="button" onClick={() => setShowAlerts(true)} className="btn-ghost">
                Alerts
              </button>
              <Link href="/dashboards" className="btn-ghost">
                Custom dashboards
              </Link>
            </>
          ) : null}
          {isHome ? (
            <Link href="/" className="btn-primary">
              Open full dashboard
            </Link>
          ) : null}
        </div>
      </div>

      {filter && !isHome ? (
        <CrossFilterBanner field={filter.field} value={filter.value} onClear={clearFilter} />
      ) : null}

      {!summary?.db_configured && !loading ? (
        <div className="glass-panel border-warn bg-warn-bg px-4 py-3 text-sm text-warn">
          Connect your database in Settings to load live KPIs and trend charts.
        </div>
      ) : null}

      <div id="dashboard-export-root">
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: isHome ? 3 : 6 }).map((_, i) => (
              <div key={i} className="glass-panel loading-shimmer h-40 rounded-2xl" />
            ))}
          </div>
        ) : summary?.kpis.length ? (
          <div
            className={`grid gap-4 ${
 isHome ? "sm:grid-cols-2 lg:grid-cols-3" : "sm:grid-cols-2 xl:grid-cols-3"
 }`}
          >
            {(isHome ? summary.kpis.slice(0, 3) : summary.kpis).map((kpi) => (
              <DashboardWidget
                key={kpi.id}
                kpi={kpi}
                compact={isHome}
                showCompare={compare && !isHome}
                selectedTrendLabel={
                  filter && filter.field === kpi.trend_dimension ? filter.value : null
                }
                onTrendClick={isHome ? undefined : handleTrendClick}
                onLensChange={handleLensChange}
              />
            ))}
          </div>
        ) : summary?.catalog_note ? (
          // A legacy-catalog org has none of the governed canvases the KPIs read — one
          // clear explanation instead of a grid of per-KPI errors.
          <div className="glass-panel px-6 py-8 text-center">
            <p className="text-sm font-medium text-heading">
              Executive KPIs aren&apos;t available for this organization
            </p>
            <p className="mx-auto mt-2 max-w-xl text-sm text-fg-muted">{summary.catalog_note}</p>
          </div>
        ) : (
          <div className="glass-panel px-4 py-8 text-center text-sm text-fg-muted">
            <p>Unable to load executive metrics.</p>
            <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="btn-ghost mt-3">
              Try again
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

export function ExecutiveDashboard(props: ExecutiveDashboardProps) {
  return (
    <CrossFilterProvider>
      <ExecutiveDashboardInner {...props} />
    </CrossFilterProvider>
  );
}
