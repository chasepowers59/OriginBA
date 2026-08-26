"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { fetchWorkstreamSummary } from "@/lib/api";
import {
  WORKSTREAM_DESCRIPTIONS,
  workstreamDisplayName,
} from "@/lib/businessLabels";
import type { WorkstreamSummary } from "@/lib/types";
import { DashboardWidget } from "./DashboardWidget";
import { DashboardControls, type CompareMode } from "./DashboardControls";
import { CrossFilterProvider, useCrossFilter } from "./CrossFilterContext";
import { PresentationToolbar } from "./PresentationToolbar";
import { WorkstreamHeroLinks } from "./WorkstreamHeroLinks";
import type { WorkstreamGroup } from "@/lib/types";

function WorkstreamDashboardInner({
  workstreamId,
  snapshotCount,
  workstreams,
}: {
  workstreamId: string;
  snapshotCount?: number;
  workstreams: WorkstreamGroup[];
}) {
  const { filter, toggleFilter, clearFilter } = useCrossFilter();
  const [days, setDays] = useState(30);
  const [compare, setCompare] = useState(false);
  const [compareMode, setCompareMode] = useState<CompareMode>("prior_period");
  const [summary, setSummary] = useState<WorkstreamSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchWorkstreamSummary(
      workstreamId,
      days,
      compare,
      filter ? { field: filter.field, value: filter.value } : undefined,
      compareMode,
    )
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false));
  }, [workstreamId, days, compare, compareMode, filter]);

  const label = summary?.workstream_label ?? workstreamDisplayName(workstreamId);

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
    (kpi: { trend_dimension?: string | null }, trendLabel: string) => {
      if (kpi.trend_dimension) toggleFilter(kpi.trend_dimension, trendLabel, trendLabel);
    },
    [toggleFilter],
  );

  return (
    <section className="space-y-6">
      <div className="glass-panel relative overflow-hidden p-6 md:p-8">
        <div className="relative flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link href="/" className="text-xs text-sky-400 hover:text-sky-300">
              ← All workstreams
            </Link>
            <h1 className="mt-2 text-3xl font-bold text-white">{label}</h1>
            <p className="mt-2 max-w-2xl text-slate-400">
              {WORKSTREAM_DESCRIPTIONS[workstreamId] ?? "Governed analytics for this business area."}
            </p>
            {snapshotCount != null ? (
              <p className="mt-2 text-xs text-slate-500">{snapshotCount} snapshot domains</p>
            ) : null}
          </div>
          <PresentationToolbar title={`${label} Dashboard`} exportSections={exportSections} />
        </div>
      </div>

      <DashboardControls
        days={days}
        compare={compare}
        compareMode={compareMode}
        onDaysChange={setDays}
        onCompareChange={setCompare}
        onCompareModeChange={setCompareMode}
      />

      <WorkstreamHeroLinks workstreamId={workstreamId} workstreams={workstreams} />

      {filter ? (
        <div className="flex items-center justify-between rounded-xl border border-amber-400/25 bg-amber-500/10 px-4 py-2 text-sm text-amber-100">
          <span>
            Cross-filter: <strong>{filter.label ?? filter.field}</strong> = {filter.value}
          </span>
          <button type="button" onClick={clearFilter} className="btn-ghost text-xs">
            Clear
          </button>
        </div>
      ) : (
        <p className="text-xs text-slate-500">Click spark chart bars to cross-filter all tiles.</p>
      )}

      <div id="dashboard-export-root">
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="glass-panel loading-shimmer h-48 rounded-2xl" />
            ))}
          </div>
        ) : summary?.kpis.length ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {summary.kpis.map((kpi) => (
              <DashboardWidget
                key={kpi.id}
                kpi={kpi}
                showCompare={compare}
                selectedTrendLabel={
                  filter && filter.field === kpi.trend_dimension ? filter.value : null
                }
                onTrendClick={handleTrendClick}
              />
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

export function WorkstreamDashboard(props: {
  workstreamId: string;
  snapshotCount?: number;
  workstreams: WorkstreamGroup[];
}) {
  return (
    <CrossFilterProvider>
      <WorkstreamDashboardInner {...props} />
    </CrossFilterProvider>
  );
}
