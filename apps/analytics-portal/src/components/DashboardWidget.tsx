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

  const workstreamName = workstreamDisplayName(kpi.workstream);
  // Reference-dashboard panel headers lead with a small rounded icon chip, coloured per
  // category. Chip hue cycles through the chart palette keyed by the workstream name.
  const CHIP_VARS = ["--chart-1", "--chart-2", "--chart-3", "--chart-4", "--chart-5"];
  const chipVar =
    CHIP_VARS[
      Math.abs([...kpi.workstream].reduce((h, c) => h * 31 + c.charCodeAt(0), 7)) % CHIP_VARS.length
    ];

  const inner = (
    <>
      <div className="border-b border-edge-subtle px-4 py-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-2.5">
            <span
              aria-hidden
              className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[11px] font-bold text-white"
              style={{ background: `var(${chipVar})` }}
            >
              {workstreamName.charAt(0)}
            </span>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">
                {workstreamName}
              </p>
              <h3 className="mt-0.5 font-semibold text-heading group-hover:text-primary dark:group-hover:text-primary">{kpi.label}</h3>
              <p className="mt-0.5 text-xs text-fg-muted">{kpi.subtitle}</p>
            </div>
          </div>
          <span className="shrink-0 text-fg-muted transition group-hover:text-primary dark:group-hover:text-primary">→</span>
        </div>
        <p className={`mt-3 font-bold tracking-tight tabular-nums text-heading ${compact ? "text-2xl" : "text-3xl"}`}>
          {formatted}
        </p>
        {showCompare ? (
          <div className="mt-2">
            <KpiCompareBadge changePct={kpi.change_pct} priorLabel={kpi.compare_label ?? undefined} />
          </div>
        ) : null}
        {kpi.error ? (
          <p className="mt-1 text-xs text-warn">{kpi.error}</p>
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
      <div className="group glass-panel block overflow-hidden transition hover:border-edge">
        {inner}
        <Link href={exploreHref} className="block border-t border-edge-subtle px-4 py-2 text-xs text-primary">
          Open full report →
        </Link>
      </div>
    );
  }

  return (
    <Link
      href={exploreHref}
      className="group glass-panel block overflow-hidden transition hover:border-edge hover:shadow-lg hover:shadow-sky-500/5"
    >
      {inner}
    </Link>
  );
}
