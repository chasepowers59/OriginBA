"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ExecutiveTrendPoint } from "@/lib/types";
import { ChartTooltipContent, chartTooltipWrapperStyle } from "./ChartTooltip";

// Single-accent treatment (Power BI / Tableau convention): one hue carries the
// series, the leading value is emphasized and the rest recede, so the eye lands
// on what matters instead of decoding a rainbow. Selection overrides to amber.
const ACCENT = "#38bdf8";
const ACCENT_MUTED = "rgba(56, 189, 248, 0.32)";
const SELECTED = "#fbbf24";

type MiniSparkChartProps = {
  points: ExecutiveTrendPoint[];
  format: "currency" | "number";
  height?: number;
  selectedLabel?: string | null;
  onBarClick?: (label: string) => void;
};

export function MiniSparkChart({
  points,
  format,
  height = 120,
  selectedLabel,
  onBarClick,
}: MiniSparkChartProps) {
  const maxValue = points.reduce((m, p) => Math.max(m, p.value), 0);
  const data = points.map((p) => ({
    name: p.label.slice(0, 14),
    fullName: p.label,
    value: p.value,
    fill:
      selectedLabel === p.label
        ? SELECTED
        : p.value >= maxValue && maxValue > 0
          ? ACCENT
          : ACCENT_MUTED,
  }));

  if (!data.length) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-white/10 text-xs text-slate-500"
        style={{ height }}
      >
        No trend data
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} barCategoryGap="18%" margin={{ top: 4, right: 2, left: 2, bottom: 0 }}>
        <XAxis
          dataKey="name"
          tick={{ fontSize: 9, fill: "#64748b" }}
          interval={0}
          angle={-25}
          textAnchor="end"
          height={42}
          tickLine={false}
          axisLine={false}
        />
        <YAxis hide domain={[0, "auto"]} />
        <Tooltip
          content={<ChartTooltipContent measureLabel="Value" isCurrency={format === "currency"} />}
          wrapperStyle={chartTooltipWrapperStyle}
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
