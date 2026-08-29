"use client";

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  XAxis,
  YAxis,
} from "recharts";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { formatCurrency, formatNumber } from "@/lib/format";

export type BuilderVisual =
  | "bar"
  | "stacked-bar"
  | "horizontal"
  | "line"
  | "area"
  | "stacked-area"
  | "pie";

export type ChartSeries = { key: string; label: string; currency?: boolean };

type BuilderChartProps = {
  rows: Record<string, unknown>[];
  xKey: string;
  xLabel: string;
  series: ChartSeries[];
  visual: BuilderVisual;
  height?: number;
};

// Series colors come from the theme's --chart-1..5 (light + dark aware, defined in
// globals.css). A single series keeps one accent; multiple series each take the next.
const SERIES_VARS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

export function BuilderChart({
  rows,
  xKey,
  xLabel,
  series,
  visual,
  height = 340,
}: BuilderChartProps) {
  const config = useMemo<ChartConfig>(() => {
    const c: ChartConfig = {};
    series.forEach((s, i) => {
      c[s.key] = { label: s.label, color: SERIES_VARS[i % SERIES_VARS.length] };
    });
    return c;
  }, [series]);

  const data = useMemo(
    () =>
      rows.map((r) => {
        const row: Record<string, unknown> = {
          [xKey]: String(r[xKey] ?? "—"),
        };
        for (const s of series) row[s.key] = Number(r[s.key] ?? 0);
        return row;
      }),
    [rows, xKey, series],
  );

  const anyCurrency = series.some((s) => s.currency);
  const fmt = (v: number) => (anyCurrency ? formatCurrency(v) : formatNumber(v));

  if (!data.length || !series.length) {
    return (
      <div
        className="flex items-center justify-center rounded-xl border border-dashed"
        style={{ height, borderColor: "var(--border)", color: "var(--foreground-subtle)" }}
      >
        Drop a dimension and a measure to see a chart
      </div>
    );
  }

  const grid = <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border-subtle)" />;
  const tip = <ChartTooltip content={<ChartTooltipContent />} />;
  const legend = series.length > 1 ? <ChartLegend content={<ChartLegendContent />} /> : null;
  const xAxis = (
    <XAxis
      dataKey={xKey}
      tickLine={false}
      axisLine={false}
      tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }}
      tickFormatter={(v: string) => (v.length > 16 ? v.slice(0, 15) + "…" : v)}
      interval="preserveStartEnd"
      minTickGap={12}
    />
  );

  if (visual === "pie") {
    const key = series[0].key;
    return (
      <ChartContainer config={config} style={{ height }} className="w-full">
        <PieChart>
          {tip}
          <Pie data={data} dataKey={key} nameKey={xKey} innerRadius={64} outerRadius={120} paddingAngle={2}>
            {data.map((_, i) => (
              <Cell key={i} fill={SERIES_VARS[i % SERIES_VARS.length]} />
            ))}
          </Pie>
          <ChartLegend content={<ChartLegendContent nameKey={xKey} />} />
        </PieChart>
      </ChartContainer>
    );
  }

  if (visual === "horizontal") {
    return (
      <ChartContainer config={config} style={{ height: Math.max(height, data.length * 34) }} className="w-full">
        <BarChart data={data} layout="vertical" margin={{ left: 8 }}>
          <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="var(--border-subtle)" />
          <XAxis type="number" tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }} tickFormatter={fmt} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey={xKey} width={130} tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }} axisLine={false} tickLine={false} />
          {tip}
          {legend}
          {series.map((s) => (
            <Bar key={s.key} dataKey={s.key} fill={`var(--color-${s.key})`} radius={[0, 4, 4, 0]} />
          ))}
        </BarChart>
      </ChartContainer>
    );
  }

  if (visual === "line") {
    return (
      <ChartContainer config={config} style={{ height }} className="w-full">
        <LineChart data={data} margin={{ left: 4, right: 8 }}>
          {grid}
          {xAxis}
          <YAxis tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }} tickFormatter={fmt} axisLine={false} tickLine={false} width={56} />
          {tip}
          {legend}
          {series.map((s) => (
            <Line key={s.key} type="monotone" dataKey={s.key} stroke={`var(--color-${s.key})`} strokeWidth={2} dot={false} />
          ))}
        </LineChart>
      </ChartContainer>
    );
  }

  if (visual === "area" || visual === "stacked-area") {
    const stackId = visual === "stacked-area" ? "a" : undefined;
    return (
      <ChartContainer config={config} style={{ height }} className="w-full">
        <AreaChart data={data} margin={{ left: 4, right: 8 }}>
          <defs>
            {series.map((s) => (
              <linearGradient key={s.key} id={`fill-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={`var(--color-${s.key})`} stopOpacity={0.35} />
                <stop offset="95%" stopColor={`var(--color-${s.key})`} stopOpacity={0.04} />
              </linearGradient>
            ))}
          </defs>
          {grid}
          {xAxis}
          <YAxis tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }} tickFormatter={fmt} axisLine={false} tickLine={false} width={56} />
          {tip}
          {legend}
          {series.map((s) => (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              stroke={`var(--color-${s.key})`}
              strokeWidth={2}
              fill={`url(#fill-${s.key})`}
              stackId={stackId}
            />
          ))}
        </AreaChart>
      </ChartContainer>
    );
  }

  // bar / stacked-bar
  const stackId = visual === "stacked-bar" ? "a" : undefined;
  return (
    <ChartContainer config={config} style={{ height }} className="w-full">
      <BarChart data={data} margin={{ left: 4, right: 8 }}>
        {grid}
        {xAxis}
        <YAxis tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }} tickFormatter={fmt} axisLine={false} tickLine={false} width={56} />
        {tip}
        {legend}
        {series.map((s) => (
          <Bar key={s.key} dataKey={s.key} fill={`var(--color-${s.key})`} radius={stackId ? 0 : [4, 4, 0, 0]} stackId={stackId} />
        ))}
      </BarChart>
    </ChartContainer>
  );
}
