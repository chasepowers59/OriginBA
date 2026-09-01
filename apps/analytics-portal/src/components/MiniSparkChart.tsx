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
import { valueRampColors } from "@/lib/chartEmphasis";
import { tickLabels } from "@/lib/axisLabels";
import { formatTooltipCurrency, formatTooltipNumber } from "@/lib/format";

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
  // App-wide value ramp: blue = highest, shifting toward red as values drop; the
  // cross-filter selection overrides its bar to the selection hue.
  const fills = valueRampColors(points.map((p) => p.value));
  const ticks = tickLabels(points.map((p) => p.label), 9);
  const data = points.map((p, i) => ({
    name: ticks[i],
    fullName: p.label,
    value: p.value,
    fill: selectedLabel === p.label ? "var(--chart-selected)" : fills[i],
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
          interval="preserveStartEnd"
          minTickGap={8}
          height={20}
          tickLine={false}
          axisLine={false}
        />
        <YAxis hide domain={["auto", "auto"]} />
        <Tooltip
          content={<SparkTooltip isCurrency={format === "currency"} />}
          wrapperStyle={{ zIndex: 50, outline: "none" }}
          cursor={{ fill: "var(--chip-bg)" }}
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
