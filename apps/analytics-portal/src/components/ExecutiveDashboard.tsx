"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { fetchExecutiveSummary } from "@/lib/api";
import { useBrand, usePortalConfig } from "@/components/PortalThemeProvider";
import type { ExecutiveSummary } from "@/lib/types";
import { DashboardWidget } from "./DashboardWidget";
import { DashboardControls } from "./DashboardControls";
import { CrossFilterProvider, useCrossFilter } from "./CrossFilterContext";
import { PresentationToolbar } from "./PresentationToolbar";

type ExecutiveDashboardProps = {
  variant?: "home" | "full";
  initialDays?: number;
};

function ExecutiveDashboardInner({ variant = "full", initialDays = 30 }: ExecutiveDashboardProps) {
  const brand = useBrand();
  const portal = usePortalConfig();
  const { filter, toggleFilter, clearFilter } = useCrossFilter();
  const [days, setDays] = useState(initialDays);
  const [compare, setCompare] = useState(false);
  const [summary, setSummary] = useState<ExecutiveSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchExecutiveSummary(
      days,
      compare,
      filter ? { field: filter.field, value: filter.value } : undefined,
    )
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false));
  }, [days, compare, filter]);

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
        toggleFilter(kpi.trend_dimension, label, label);
      }
    },
    [toggleFilter],
  );

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-400">
            Executive overview
          </p>
          <h2 className="mt-1 text-xl font-bold text-white md:text-2xl">
            {isHome ? "Key metrics at a glance" : `${portal.organization_name} performance`}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {summary?.period.label ?? `Last ${days} days`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {!isHome ? (
            <>
              <DashboardControls
                days={days}
                compare={compare}
                onDaysChange={setDays}
                onCompareChange={setCompare}
              />
              <PresentationToolbar
                title={`${portal.organization_name} Executive Dashboard`}
                exportSections={exportSections}
              />
              <Link href="/dashboard/custom" className="btn-ghost">
                Custom dashboards
              </Link>
            </>
          ) : null}
          {isHome ? (
            <Link href="/dashboard" className="btn-primary">
              Open full dashboard
            </Link>
          ) : null}
        </div>
      </div>

      {filter && !isHome ? (
        <div className="flex items-center justify-between rounded-xl border border-amber-400/25 bg-amber-500/10 px-4 py-2 text-sm text-amber-100">
          <span>
            Cross-filter active: <strong>{filter.label ?? filter.field}</strong> = {filter.value}
          </span>
          <button type="button" onClick={clearFilter} className="btn-ghost text-xs">
            Clear
          </button>
        </div>
      ) : null}

      {!summary?.db_configured && !loading ? (
        <div className="glass-panel border-amber-400/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
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
              />
            ))}
          </div>
        ) : (
          <div className="glass-panel px-4 py-8 text-center text-sm text-slate-500">
            Unable to load executive metrics.
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
