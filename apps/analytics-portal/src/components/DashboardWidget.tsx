"use client";

import Link from "next/link";
import { MiniSparkChart } from "./MiniSparkChart";
import { KpiCompareBadge } from "./KpiCompareBadge";
import { formatCurrency, formatNumber } from "@/lib/format";
import { workstreamDisplayName } from "@/lib/businessLabels";
import type { ExecutiveKpi } from "@/lib/types";

type DashboardWidgetProps = {
  kpi: ExecutiveKpi;
  compact?: boolean;
  showCompare?: boolean;
  selectedTrendLabel?: string | null;
  onTrendClick?: (kpi: ExecutiveKpi, label: string) => void;
};

export function DashboardWidget({
  kpi,
  compact,
  showCompare,
  selectedTrendLabel,
  onTrendClick,
}: DashboardWidgetProps) {
  const formatted =
    kpi.value == null
      ? "—"
      : kpi.format === "currency"
        ? formatCurrency(kpi.value)
        : formatNumber(kpi.value);

  const exploreHref = kpi.explore_report_id
    ? `/explore/${kpi.snapshot_id}?report=${kpi.explore_report_id}`
    : `/explore/${kpi.snapshot_id}`;

  const inner = (
    <>
      <div className="border-b border-white/5 px-4 py-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sky-400/80">
              {workstreamDisplayName(kpi.workstream)}
            </p>
            <h3 className="mt-0.5 font-semibold text-white group-hover:text-sky-100">{kpi.label}</h3>
            <p className="mt-0.5 text-xs text-slate-500">{kpi.subtitle}</p>
          </div>
          <span className="shrink-0 text-slate-600 transition group-hover:text-sky-400">→</span>
        </div>
        <p className={`mt-3 font-bold tracking-tight tabular-nums text-white ${compact ? "text-2xl" : "text-3xl"}`}>
          {formatted}
        </p>
        {showCompare ? (
          <div className="mt-2">
            <KpiCompareBadge changePct={kpi.change_pct} priorLabel={kpi.compare_label ?? undefined} />
          </div>
        ) : null}
        {kpi.error ? (
          <p className="mt-1 text-xs text-amber-400/90">{kpi.error}</p>
        ) : null}
      </div>
      {!compact ? (
        <div className="px-2 pb-2 pt-1">
          <MiniSparkChart
            points={kpi.trend}
            format={kpi.format}
            height={130}
            selectedLabel={selectedTrendLabel}
            onBarClick={
              onTrendClick && kpi.trend_dimension
                ? (label) => onTrendClick(kpi, label)
                : undefined
            }
          />
        </div>
      ) : null}
    </>
  );

  if (onTrendClick) {
    return (
      <div className="group glass-panel block overflow-hidden transition hover:border-sky-400/30">
        {inner}
        <Link href={exploreHref} className="block border-t border-white/5 px-4 py-2 text-xs text-sky-400">
          Open full report →
        </Link>
      </div>
    );
  }

  return (
    <Link
      href={exploreHref}
      className="group glass-panel block overflow-hidden transition hover:border-sky-400/30 hover:shadow-lg hover:shadow-sky-500/5"
    >
      {inner}
    </Link>
  );
}
