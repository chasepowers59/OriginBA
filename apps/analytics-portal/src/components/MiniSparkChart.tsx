"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  type TooltipProps,
  XAxis,
  YAxis,
} from "recharts";
import type { ExecutiveTrendPoint } from "@/lib/types";
import { barEmphasisRoles, type BarEmphasis } from "@/lib/chartEmphasis";
import { formatTooltipCurrency, formatTooltipNumber } from "@/lib/format";

// Single-accent treatment (Power BI / Tableau convention): one hue carries the series,
// the leading value is emphasized and the rest recede, so the eye lands on what matters.
// Selection overrides to the shared cross-filter highlight. Colours are theme tokens.
const ROLE_FILL: Record<BarEmphasis, string> = {
  selected: "var(--chart-selected)",
  emphasis: "var(--chart-1)",
  base: "color-mix(in srgb, var(--chart-1) 32%, transparent)",
};

type MiniSparkChartProps = {
  points: ExecutiveTrendPoint[];
  format: "currency" | "number";
  height?: number;
  selectedLabel?: string | null;
  onBarClick?: (label: string) => void;
};

function SparkTooltip({
  active,
  payload,
  isCurrency,
}: TooltipProps<number, string> & { isCurrency: boolean }) {
  if (!active || !payload?.length) return null;
  const point = payload[0];
  const category =
    (point?.payload as { fullName?: string } | undefined)?.fullName ?? String(point?.name ?? "");
  const n = Number(point?.value);
  return (
    <div className="chart-tooltip pointer-events-none z-50 min-w-[120px] rounded-xl px-3 py-2 ring-1 ring-black/5 dark:ring-white/10">
      <p className="truncate text-xs font-medium text-[var(--tooltip-muted)]" title={category}>
        {category}
      </p>
      <p className="mt-1 text-lg font-bold tabular-nums leading-none text-[var(--tooltip-text)]">
        {isCurrency ? formatTooltipCurrency(n) : formatTooltipNumber(n)}
      </p>
    </div>
  );
}

export function MiniSparkChart({
  points,
  format,
  height = 120,
  selectedLabel,
  onBarClick,
}: MiniSparkChartProps) {
  const roles = barEmphasisRoles(
    points.map((p) => p.label),
    points.map((p) => p.value),
    selectedLabel,
  );
  const data = points.map((p, i) => ({
    name: p.label.slice(0, 14),
    fullName: p.label,
    value: p.value,
    fill: ROLE_FILL[roles[i]],
  }));

  if (!data.length) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-edge-subtle text-xs text-fg-muted"
        style={{ height }}
      >
        No trend data
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} barCategoryGap="18%" margin={{ top: 4, right: 2, left: 2, bottom: 0 }}>
        {/* Axis labels stay FLAT (design standard): truncate + skip ticks rather than
            rotate — angled text is harder to scan. */}
        <XAxis
          dataKey="name"
          tick={{ fontSize: 9, fill: "var(--foreground-subtle)" }}
          tickFormatter={(v: string) => (v.length > 9 ? v.slice(0, 8) + "…" : v)}
          interval="preserveStartEnd"
          minTickGap={8}
          height={20}
          tickLine={false}
          axisLine={false}
        />
        <YAxis hide domain={[0, "auto"]} />
        <Tooltip
          content={<SparkTooltip isCurrency={format === "currency"} />}
          wrapperStyle={{ zIndex: 50, outline: "none" }}
          cursor={{ fill: "rgba(255,255,255,0.05)" }}
        />
        <Bar
          dataKey="value"
          radius={[3, 3, 0, 0]}
          onClick={(payload) => onBarClick?.(String((payload as { fullName?: string }).fullName ?? ""))}
          style={{ cursor: onBarClick ? "pointer" : "default" }}
          isAnimationActive={false}
        >
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
