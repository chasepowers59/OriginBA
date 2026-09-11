"use client";

import { categoryLabel } from "@/lib/chartLabels";
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
import { formatCurrency, formatNumber, formatTooltipNumber } from "@/lib/format";
import { valueRampColors } from "@/lib/chartEmphasis";
import { isOrderedAxis, orderChartRows } from "@/lib/chartOrder";
import { formatTimeBucket } from "@/lib/timeBucketLabel";
import { useColorMode } from "@/components/PortalThemeProvider";

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
  // Cross-filter: highlight one category and report clicks (single-measure surfaces).
  selectedCategory?: string | null;
  onCategorySelect?: (category: string) => void;
  emptyMessage?: string;
  sortTimeSeries?: boolean;
  /** Grain of the time bucket on the x axis, so its ticks can name the period. */
  xGrain?: string | null;
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
  height = 460,
  selectedCategory = null,
  onCategorySelect,
  emptyMessage = "Drop a dimension and a measure to see a chart",
  sortTimeSeries = false,
  xGrain = null,
}: BuilderChartProps) {
  const { colorMode } = useColorMode();

  const config = useMemo<ChartConfig>(() => {
    const c: ChartConfig = {};
    series.forEach((s, i) => {
      c[s.key] = { label: s.label, color: SERIES_VARS[i % SERIES_VARS.length] };
    });
    return c;
  }, [series]);

  const data = useMemo(() => {
    const mapped = rows.map((r) => {
      const row: Record<string, unknown> = { [xKey]: categoryLabel(r[xKey]) };
      for (const s of series) row[s.key] = Number(r[s.key] ?? 0);
      return row;
    });
    return orderChartRows(
      mapped,
      xKey,
      series.map((s) => s.key),
      sortTimeSeries || isOrderedAxis(xLabel),
    );
  }, [rows, xKey, xLabel, series, sortTimeSeries]);

  const anyCurrency = series.some((s) => s.currency);
  // Axis ticks COMPACT ($12.3M) so they fit the axis width; tooltips show the full
  // value. formatCurrency never compacts, which clipped revenue axes at width 56.
  const fmt = (v: number) => (anyCurrency ? `$${formatNumber(v)}` : formatNumber(v));
  const tipFormatter = anyCurrency
    ? (value: unknown) => formatCurrency(Number(value))
    : (value: unknown) => formatTooltipNumber(Number(value));

  // Single-measure bars use the app-wide value ramp: blue = highest, shifting toward
  // red as values drop. A cross-filter selection overrides its bar to the selection hue.
  const singleSeries = series.length === 1;
  const rampFills = useMemo<string[] | null>(() => {
    if (!singleSeries) return null;
    const key = series[0].key;
    return valueRampColors(data.map((d) => Number(d[key] ?? 0)), { dark: colorMode === "dark" });
  }, [singleSeries, data, series, colorMode]);

  const cellFill = (i: number, fallback: string) => {
    if (selectedCategory != null && String(data[i]?.[xKey]) === selectedCategory) {
      return "var(--chart-selected)";
    }
    return rampFills ? rampFills[i] : fallback;
  };

  // Screen readers get a description of what the chart encodes; the data itself
  // is available through the result table, so a summary is the right depth here.
  const a11yLabel = `${visual} chart: ${series.map((s) => s.label).join(", ")} by ${xLabel ?? xKey}, ${data.length} categories`;

  const handleSelect = (category: unknown) => {
    if (onCategorySelect && category != null) onCategorySelect(String(category));
  };
  const clickCursor = onCategorySelect ? "pointer" : "default";

  if (!data.length || !series.length) {
    return (
      <div
        className="flex items-center justify-center rounded-xl border border-dashed"
        style={{ height, borderColor: "var(--border)", color: "var(--foreground-subtle)" }}
      >
        {emptyMessage}
      </div>
    );
  }

  // A time bucket is a timestamp; naming its period beats truncating its first instant.
  const xTickLabel = (v: string) => {
    const label = sortTimeSeries ? formatTimeBucket(String(v), xGrain) : String(v);
    return label.length > 16 ? `${label.slice(0, 15)}…` : label;
  };

  const grid = <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border-subtle)" />;
  const tip = <ChartTooltip content={<ChartTooltipContent valueFormatter={tipFormatter} />} />;
  const legend = series.length > 1 ? <ChartLegend content={<ChartLegendContent />} /> : null;
  const xAxis = (
    <XAxis
      dataKey={xKey}
      tickLine={false}
      axisLine={false}
      tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }}
      tickFormatter={xTickLabel}
      interval="preserveStartEnd"
      minTickGap={12}
    />
  );

  if (visual === "pie") {
    const key = series[0].key;
    // A readable pie: positive slices only (negative arcs are broken by definition —
    // adjustments/refunds go negative routinely), capped at 7 + an "Other" bucket, and
    // a legend config keyed by CATEGORY so names actually render.
    const positive = data.filter((d) => Number(d[key]) > 0);
    if (!positive.length) {
      return (
        <div
          className="flex items-center justify-center rounded-xl border border-dashed px-6 text-center text-sm"
          style={{ height, borderColor: "var(--border)", color: "var(--foreground-subtle)" }}
        >
          A pie needs positive values — switch to a bar for this result.
        </div>
      );
    }
    const sorted = [...positive].sort((a, b) => Number(b[key]) - Number(a[key]));
    const MAX_SLICES = 7;
    const head = sorted.slice(0, MAX_SLICES);
    const tail = sorted.slice(MAX_SLICES);
    const pieData = tail.length
      ? [...head, { [xKey]: `Other (${tail.length})`, [key]: tail.reduce((a, d) => a + Number(d[key]), 0) }]
      : head;
    const pieConfig: ChartConfig = { ...config };
    pieData.forEach((d, i) => {
      pieConfig[String(d[xKey])] = {
        label: String(d[xKey]),
        color: SERIES_VARS[i % SERIES_VARS.length],
      };
    });
    return (
      <ChartContainer config={pieConfig} style={{ height }} className="w-full" role="img" aria-label={a11yLabel}>
        <PieChart>
          {tip}
          <Pie
            data={pieData}
            dataKey={key}
            nameKey={xKey}
            innerRadius="45%"
            outerRadius="78%"
            paddingAngle={2}
            onClick={(d: Record<string, unknown>) => handleSelect(d?.[xKey] ?? (d?.payload as Record<string, unknown>)?.[xKey])}
            style={{ cursor: clickCursor }}
          >
            {pieData.map((d, i) => {
              const isSelected = selectedCategory != null && String(d[xKey]) === selectedCategory;
              return (
                <Cell
                  key={i}
                  fill={isSelected ? "var(--chart-selected)" : SERIES_VARS[i % SERIES_VARS.length]}
                  stroke={isSelected ? "var(--chart-selected)" : "transparent"}
                  strokeWidth={2}
                />
              );
            })}
          </Pie>
          <ChartLegend content={<ChartLegendContent nameKey={xKey} />} />
        </PieChart>
      </ChartContainer>
    );
  }

  if (visual === "horizontal") {
    // Rows drive the chart's own height, but the VIEWPORT is capped and scrolls: a
    // 200-row result no longer produces a 7,000px page (or blows out a dashboard tile).
    const chartHeight = Math.max(height, data.length * 34);
    return (
      <div style={{ maxHeight: Math.max(height, 560), overflowY: chartHeight > Math.max(height, 560) ? "auto" : "visible" }}>
      <ChartContainer config={config} style={{ height: chartHeight }} className="w-full" role="img" aria-label={a11yLabel}>
        <BarChart data={data} layout="vertical" margin={{ left: 8 }} maxBarSize={40}>
          <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="var(--border-subtle)" />
          <XAxis type="number" tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }} tickFormatter={fmt} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey={xKey} width={130} tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }} tickFormatter={(v: string) => (v.length > 18 ? v.slice(0, 17) + "…" : v)} axisLine={false} tickLine={false} />
          {tip}
          {legend}
          {singleSeries ? (
            <Bar
              dataKey={series[0].key}
              radius={[0, 4, 4, 0]}
              onClick={(d: Record<string, unknown>) => handleSelect(d?.[xKey])}
              style={{ cursor: clickCursor }}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={cellFill(i, `var(--color-${series[0].key})`)} />
              ))}
            </Bar>
          ) : (
            series.map((s) => (
              <Bar key={s.key} dataKey={s.key} fill={`var(--color-${s.key})`} radius={[0, 4, 4, 0]} />
            ))
          )}
        </BarChart>
      </ChartContainer>
      </div>
    );
  }

  if (visual === "line") {
    return (
      <ChartContainer config={config} style={{ height }} className="w-full" role="img" aria-label={a11yLabel}>
        <LineChart data={data} margin={{ left: 4, right: 8 }}>
          {grid}
          {xAxis}
          <YAxis tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }} tickFormatter={fmt} axisLine={false} tickLine={false} width={56} />
          {tip}
          {legend}
          {series.map((s) => (
            <Line key={s.key} type="monotone" dataKey={s.key} stroke={`var(--color-${s.key})`} strokeWidth={2} dot={data.length < 3} />
          ))}
        </LineChart>
      </ChartContainer>
    );
  }

  if (visual === "area" || visual === "stacked-area") {
    const stackId = visual === "stacked-area" ? "a" : undefined;
    return (
      <ChartContainer config={config} style={{ height }} className="w-full" role="img" aria-label={a11yLabel}>
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
    <ChartContainer config={config} style={{ height }} className="w-full" role="img" aria-label={a11yLabel}>
      <BarChart data={data} margin={{ left: 4, right: 8 }} maxBarSize={64}>
        {grid}
        {xAxis}
        <YAxis tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }} tickFormatter={fmt} axisLine={false} tickLine={false} width={56} />
        {tip}
        {legend}
        {singleSeries ? (
          <Bar
            dataKey={series[0].key}
            radius={stackId ? 0 : [4, 4, 0, 0]}
            stackId={stackId}
            onClick={(d: Record<string, unknown>) => handleSelect(d?.[xKey])}
            style={{ cursor: clickCursor }}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={cellFill(i, `var(--color-${series[0].key})`)} />
            ))}
          </Bar>
        ) : (
          series.map((s) => (
            <Bar key={s.key} dataKey={s.key} fill={`var(--color-${s.key})`} radius={stackId ? 0 : [4, 4, 0, 0]} stackId={stackId} />
          ))
        )}
      </BarChart>
    </ChartContainer>
  );
}
