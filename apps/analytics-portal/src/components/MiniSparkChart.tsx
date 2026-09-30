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
import { emphasisFills } from "@/lib/chartEmphasis";
import { AxisTick, useElementWidth, type TickText } from "@/components/builder/BuilderChart";
import { SPARK_AXIS, chartLayout, minBarPx } from "@/lib/chartLayout";
import { formatCurrency, formatNumber } from "@/lib/format";

type MiniSparkChartProps = {
  points: ExecutiveTrendPoint[];
  format: "currency" | "number";
  height?: number;
  /** The breakdown has an inherent order (aging bands, months): keep it in columns. */
  ordered?: boolean;
  selectedLabel?: string | null;
  onBarClick?: (label: string) => void;
};

/** Horizontal rows stay at least this tall, so one-line labels never touch. */
const MIN_ROW_PX = 16;

function SparkTooltip({
  active,
  payload,
  formatValue,
}: TooltipProps<number, string> & { formatValue: (n: number) => string }) {
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
        {formatValue(n)}
      </p>
    </div>
  );
}

export function MiniSparkChart({
  points,
  format,
  height = 120,
  ordered = false,
  selectedLabel,
  onBarClick,
}: MiniSparkChartProps) {
  const [measureRef, width] = useElementWidth();
  const fills = emphasisFills(
    points.map((p) => p.value),
    (i) => selectedLabel === points[i].label,
  );
  const data = points.map((p, i) => ({
    name: p.label,
    fullName: p.label,
    value: p.value,
    fill: fills[i],
  }));

  const labels = points.map((p) => p.label);
  const layout = chartLayout({ ...SPARK_AXIS, labels, values: points.map((p) => p.value), width, ordered });
  const ticks: TickText = new Map(labels.map((label, i) => [label, { lines: layout.tickLines[i], title: label }]));
  const tick = <AxisTick ticks={ticks} fontSize={SPARK_AXIS.fontSize} />;
  const rows = layout.orientation === "horizontal";
  const formatValue = format === "currency" ? formatCurrency : formatNumber;

  if (!layout.showChart) {
    return (
      <p ref={measureRef} className="flex items-center justify-center px-2 text-center text-xs text-fg-muted" style={{ height }}>
        {layout.note}
      </p>
    );
  }

  // Axis labels stay FLAT and every bar keeps its label: columns wrap to two lines,
  // and above five categories each gets its own row (chartLayout decides).
  return (
    <div
      ref={measureRef}
      className="w-full min-w-0"
      role="img"
      aria-label={`${rows ? "Horizontal bar" : "Bar"} chart: ${points.map((p) => `${p.label} ${formatValue(p.value)}`).join(", ")}`}
    >
      <ResponsiveContainer width="100%" height={rows ? Math.max(height, points.length * MIN_ROW_PX) : height}>
        <BarChart
          data={data}
          layout={rows ? "vertical" : "horizontal"}
          barCategoryGap="18%"
          margin={{ top: 4, right: 2, left: 2, bottom: 0 }}
        >
          {rows ? (
            <XAxis type="number" hide domain={["auto", "auto"]} />
          ) : (
            <XAxis dataKey="name" tick={tick} interval={0} height={layout.axisSize} tickLine={false} axisLine={false} />
          )}
          {rows ? (
            <YAxis type="category" dataKey="name" width={layout.axisSize} tick={tick} interval={0} tickLine={false} axisLine={false} />
          ) : (
            <YAxis hide domain={["auto", "auto"]} />
          )}
          <Tooltip
            content={<SparkTooltip formatValue={formatValue} />}
            wrapperStyle={{ zIndex: 50, outline: "none" }}
            cursor={{ fill: "var(--chip-bg)" }}
          />
          <Bar
            dataKey="value"
            radius={rows ? [0, 3, 3, 0] : [3, 3, 0, 0]}
            minPointSize={minBarPx}
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
    </div>
  );
}
