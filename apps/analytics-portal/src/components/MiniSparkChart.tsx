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

const COLORS = ["#38bdf8", "#818cf8", "#22d3ee", "#34d399", "#a78bfa", "#fbbf24"];

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
  const data = points.map((p, i) => ({
    name: p.label.slice(0, 14),
    fullName: p.label,
    value: p.value,
    fill: selectedLabel === p.label ? "#fbbf24" : COLORS[i % COLORS.length],
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
      <BarChart data={data} barCategoryGap="12%">
        <XAxis
          dataKey="name"
          tick={{ fontSize: 9, fill: "#64748b" }}
          interval={0}
          angle={-25}
          textAnchor="end"
          height={42}
        />
        <YAxis hide domain={[0, "auto"]} />
        <Tooltip
          content={<ChartTooltipContent measureLabel="Value" isCurrency={format === "currency"} />}
          wrapperStyle={chartTooltipWrapperStyle}
          cursor={{ fill: "rgba(255,255,255,0.06)" }}
        />
        <Bar
          dataKey="value"
          radius={[4, 4, 0, 0]}
          onClick={(payload) => onBarClick?.(String((payload as { fullName?: string }).fullName ?? ""))}
          style={{ cursor: onBarClick ? "pointer" : "default" }}
        >
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
