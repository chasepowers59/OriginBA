"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { fetchWorkstreamAbout, fetchWorkstreamSummary } from "@/lib/api";
import {
  WORKSTREAM_DESCRIPTIONS,
  workstreamDisplayName,
} from "@/lib/businessLabels";
import type { WorkstreamAbout, WorkstreamSummary } from "@/lib/types";
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
  const [about, setAbout] = useState<WorkstreamAbout | null>(null);
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

  useEffect(() => {
    fetchWorkstreamAbout(workstreamId).then(setAbout).catch(() => setAbout(null));
  }, [workstreamId]);

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
            <Link href="/reports" className="text-xs text-primary hover:text-primary">
              ← All workstreams
            </Link>
            <h1 className="mt-2 text-3xl font-bold text-heading">{label}</h1>
            <p className="mt-2 max-w-2xl text-fg-muted">
              {WORKSTREAM_DESCRIPTIONS[workstreamId] ?? "Governed analytics for this business area."}
            </p>
            {snapshotCount != null ? (
              <p className="mt-2 text-xs text-fg-muted">{snapshotCount} reporting canvases</p>
            ) : null}
          </div>
          <PresentationToolbar title={`${label} Dashboard`} exportSections={exportSections} />
        </div>
      </div>

      {about ? (
        <details className="glass-panel-subtle px-5 py-4">
          <summary className="cursor-pointer text-sm font-semibold text-heading">
            About this workstream
            <span className="ml-2 text-xs font-normal text-fg-muted">
              what it includes, what it deliberately does not, and where it connects
            </span>
          </summary>
          <div className="mt-4 grid gap-6 md:grid-cols-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-primary">
                Included ({about.canvases.length} canvases · {about.kpis.length} KPIs)
              </p>
              {about.summary ? (
                <p className="mt-2 text-xs leading-relaxed text-fg-muted">{about.summary}</p>
              ) : null}
              <ul className="mt-2 space-y-1">
                {about.canvases.map((c) => (
                  <li key={c.id}>
                    <Link href={`/explore/${c.id}`} className="text-xs text-primary hover:text-primary">
                      {c.label}
                    </Link>
                    {c.grain ? <span className="ml-1 text-[10px] text-fg-muted">— {c.grain}</span> : null}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-warn">
                Deliberately not included
              </p>
              <ul className="mt-2 space-y-2">
                {about.not_included.map((n) => (
                  <li key={n} className="text-xs leading-relaxed text-fg-muted">
                    {n}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-ok">
                Connects to
              </p>
              <ul className="mt-2 space-y-2">
                {about.related.map((r) => (
                  <li key={r.workstream} className="text-xs leading-relaxed text-fg-muted">
                    <Link href={`/workstream/${r.workstream}`} className="font-medium text-ok hover:text-ok">
                      {r.label}
                    </Link>{" "}
                    — {r.via}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </details>
      ) : null}

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
        <div className="flex items-center justify-between rounded-xl border border-warn bg-warn-bg px-4 py-2 text-sm text-warn">
          <span>
            Cross-filter: <strong>{filter.label ?? filter.field}</strong> = {filter.value}
          </span>
          <button type="button" onClick={clearFilter} className="btn-ghost text-xs">
            Clear
          </button>
        </div>
      ) : (
        <p className="text-xs text-fg-muted">Click spark chart bars to cross-filter all tiles.</p>
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
