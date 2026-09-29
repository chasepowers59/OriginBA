"use client";

import { categoryLabel } from "@/lib/chartLabels";
import { useCallback, useMemo, useState, type ReactNode } from "react";
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
import { emphasisFills } from "@/lib/chartEmphasis";
import { isOrderedAxis, orderChartRows } from "@/lib/chartOrder";
import { BUILDER_AXIS, chartLayout, piePlan, tickLineHeight } from "@/lib/chartLayout";
import { formatTimeBucket } from "@/lib/timeBucketLabel";

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

/** Container width in px, 0 until measured: the charts lay out from it. */
export function useElementWidth() {
  const [width, setWidth] = useState(0);
  const ref = useCallback((node: HTMLElement | null) => {
    if (!node) return undefined;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)));
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
}

export type TickText = Map<string, { lines: string[]; title: string }>;

/** A flat tick of one or two lines (chartLayout decides them); hover shows the full label. */
export function AxisTick({
  x = 0,
  y = 0,
  payload,
  textAnchor,
  verticalAnchor,
  ticks,
  fontSize,
}: {
  x?: number;
  y?: number;
  payload?: { value?: unknown };
  textAnchor?: "start" | "middle" | "end" | "inherit";
  verticalAnchor?: string;
  ticks: TickText;
  fontSize: number;
}) {
  const value = String(payload?.value ?? "");
  const { lines, title } = ticks.get(value) ?? { lines: [value], title: value };
  const lineHeight = tickLineHeight(fontSize);
  // Row labels centre on their bar; column labels hang below the axis.
  const firstDy =
    verticalAnchor === "middle" ? fontSize * 0.35 - ((lines.length - 1) * lineHeight) / 2 : fontSize;
  return (
    <text x={x} y={y} textAnchor={textAnchor} fontSize={fontSize} fill="var(--foreground-subtle)">
      <title>{title}</title>
      {lines.map((line, i) => (
        <tspan key={i} x={x} dy={i === 0 ? firstDy : lineHeight}>
          {line}
        </tspan>
      ))}
    </text>
  );
}

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
  const [measureRef, width] = useElementWidth();

  const config = useMemo<ChartConfig>(() => {
    const c: ChartConfig = {};
    series.forEach((s, i) => {
      c[s.key] = { label: s.label, color: SERIES_VARS[i % SERIES_VARS.length] };
    });
    return c;
  }, [series]);

  // An ordered axis (dates, aging bands) keeps its order and its columns: a reader
  // infers a thinned tick from its neighbours. A categorical one never hides a label.
  const ordered = sortTimeSeries || isOrderedAxis(xLabel);
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
      ordered,
    );
  }, [rows, xKey, series, ordered]);

  // A time bucket is a timestamp; naming its period beats truncating its first instant.
  const labels = useMemo(
    () => data.map((d) => (sortTimeSeries ? formatTimeBucket(String(d[xKey]), xGrain) : String(d[xKey]))),
    [data, xKey, sortTimeSeries, xGrain],
  );
  const layout = chartLayout({
    ...BUILDER_AXIS,
    labels,
    values: rows.flatMap((r) => series.map((s) => r[s.key])),
    width,
    horizontal: visual === "horizontal",
  });
  const pie =
    visual === "pie" && series.length
      ? piePlan(data.map((d) => String(d[xKey])), data.map((d) => Number(d[series[0].key])))
      : null;
  const shown: BuilderVisual = visual === "pie" && !pie?.slices ? "bar" : visual;
  const asRows =
    shown === "horizontal" ||
    ((shown === "bar" || shown === "stacked-bar") && !ordered && layout.orientation === "horizontal");
  const ticks: TickText = new Map(
    data.map((d, i) => [String(d[xKey]), { lines: layout.tickLines[i], title: labels[i] }]),
  );
  const categoryTick = <AxisTick ticks={ticks} fontSize={BUILDER_AXIS.fontSize} />;

  const anyCurrency = series.some((s) => s.currency);
  // Axis ticks COMPACT ($12.3M) so they fit the axis width; tooltips show the full
  // value. formatCurrency never compacts, which clipped revenue axes at width 56.
  const fmt = (v: number) => (anyCurrency ? `$${formatNumber(v)}` : formatNumber(v));
  const tipFormatter = anyCurrency
    ? (value: unknown) => formatCurrency(Number(value))
    : (value: unknown) => formatTooltipNumber(Number(value));

  // Single-measure bars: one hue, the leader emphasised by strength, red only for
  // negatives (lib/chartEmphasis); a cross-filter selection takes the selection hue.
  const singleSeries = series.length === 1;
  const barFills = useMemo(() => {
    if (!singleSeries) return [];
    const key = series[0].key;
    return emphasisFills(
      data.map((d) => Number(d[key] ?? 0)),
      (i) => selectedCategory != null && String(data[i][xKey]) === selectedCategory,
    );
  }, [singleSeries, data, series, selectedCategory, xKey]);

  // Screen readers get a description of what the chart encodes; the data itself
  // is available through the result table, so a summary is the right depth here.
  const a11yLabel = `${asRows ? "horizontal bar" : shown.replace("-", " ")} chart: ${series.map((s) => s.label).join(", ")} by ${xLabel ?? xKey}, ${data.length} categories`;

  const handleSelect = (category: unknown) => {
    if (onCategorySelect && category != null) onCategorySelect(String(category));
  };
  const clickCursor = onCategorySelect ? "pointer" : "default";

  const xTickLabel = (v: string) => {
    const label = ticks.get(String(v))?.title ?? String(v);
    return label.length > 16 ? `${label.slice(0, 15)}…` : label;
  };

  const grid = <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border-subtle)" />;
  const tip = <ChartTooltip content={<ChartTooltipContent valueFormatter={tipFormatter} />} />;
  const legend = series.length > 1 ? <ChartLegend content={<ChartLegendContent />} /> : null;
  const xAxis = ordered ? (
    <XAxis
      dataKey={xKey}
      tickLine={false}
      axisLine={false}
      tick={{ fontSize: BUILDER_AXIS.fontSize, fill: "var(--foreground-subtle)" }}
      tickFormatter={xTickLabel}
      interval="preserveStartEnd"
      minTickGap={12}
    />
  ) : (
    <XAxis
      dataKey={xKey}
      tickLine={false}
      axisLine={false}
      tick={categoryTick}
      interval={0}
      height={layout.axisSize}
    />
  );

  // Every outcome renders in the one measured frame, so the layout knows its width.
  const frame = (node: ReactNode) => (
    <div ref={measureRef} className="w-full min-w-0">
      {pie?.note && layout.showChart ? <p className="mb-2 text-xs text-fg-muted">{pie.note}</p> : null}
      {node}
    </div>
  );

  if (!data.length || !series.length) {
    return frame(
      <div
        className="flex items-center justify-center rounded-xl border border-dashed"
        style={{ height, borderColor: "var(--border)", color: "var(--foreground-subtle)" }}
      >
        {emptyMessage}
      </div>,
    );
  }

  if (!layout.showChart) {
    return frame(<p className="px-4 py-10 text-center text-sm text-fg-muted">{layout.note}</p>);
  }

  if (shown === "pie" && pie?.slices) {
    const key = series[0].key;
    // Legend config keyed by CATEGORY so names actually render.
    const pieData = pie.slices.map((s) => ({ [xKey]: s.label, [key]: s.value }));
    const pieConfig: ChartConfig = { ...config };
    pieData.forEach((d, i) => {
      pieConfig[String(d[xKey])] = {
        label: String(d[xKey]),
        color: SERIES_VARS[i % SERIES_VARS.length],
      };
    });
    return frame(
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
      </ChartContainer>,
    );
  }

  if (asRows) {
    const stackId = shown === "stacked-bar" ? "a" : undefined;
    // Rows drive the chart's own height, but the VIEWPORT is capped and scrolls: a
    // 200-row result no longer produces a 7,000px page (or blows out a dashboard tile).
    const chartHeight = Math.max(height, data.length * 34);
    return frame(
      <div style={{ maxHeight: Math.max(height, 560), overflowY: chartHeight > Math.max(height, 560) ? "auto" : "visible" }}>
      <ChartContainer config={config} style={{ height: chartHeight }} className="w-full" role="img" aria-label={a11yLabel}>
        <BarChart data={data} layout="vertical" margin={{ left: 8 }} maxBarSize={40}>
          <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="var(--border-subtle)" />
          <XAxis type="number" tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }} tickFormatter={fmt} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey={xKey} width={layout.axisSize} tick={categoryTick} interval={0} axisLine={false} tickLine={false} />
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
                <Cell key={i} fill={barFills[i]} />
              ))}
            </Bar>
          ) : (
            series.map((s) => (
              <Bar key={s.key} dataKey={s.key} fill={`var(--color-${s.key})`} radius={stackId ? 0 : [0, 4, 4, 0]} stackId={stackId} />
            ))
          )}
        </BarChart>
      </ChartContainer>
      </div>,
    );
  }

  if (shown === "line") {
    return frame(
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
      </ChartContainer>,
    );
  }

  if (shown === "area" || shown === "stacked-area") {
    const stackId = shown === "stacked-area" ? "a" : undefined;
    return frame(
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
      </ChartContainer>,
    );
  }

  // bar / stacked-bar
  const stackId = shown === "stacked-bar" ? "a" : undefined;
  return frame(
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
              <Cell key={i} fill={barFills[i]} />
            ))}
          </Bar>
        ) : (
          series.map((s) => (
            <Bar key={s.key} dataKey={s.key} fill={`var(--color-${s.key})`} radius={stackId ? 0 : [4, 4, 0, 0]} stackId={stackId} />
          ))
        )}
      </BarChart>
    </ChartContainer>,
  );
}
