"use client";

import { Area, CartesianGrid, ComposedChart, Line, XAxis, YAxis, type TooltipProps } from "recharts";
import { ChartContainer, ChartTooltip } from "@/components/ui/chart";
import type { OriForecast } from "@/lib/api";
import { formatCurrency, formatMonth, formatNumber, valueAxis } from "@/lib/format";
import { ORI } from "@/lib/ori";
import { FORECAST_FRAME, forecastRows, type ForecastRow } from "@/lib/oriPanel";

// One series, one hue: the actual line, its dashed forecast and the likely band are all --chart-1.
const HUE = "var(--chart-1)";

function ForecastTooltip({
  active,
  payload,
  formatValue,
}: TooltipProps<number, string> & { formatValue: (v: unknown) => string }) {
  const row = payload?.[0]?.payload as ForecastRow | undefined;
  if (!active || !row) return null;
  const actual = row.actual != null;
  return (
    <div className="chart-tooltip pointer-events-none min-w-[140px] rounded-xl px-3 py-2 ring-1 ring-black/5 dark:ring-white/10">
      <p className="text-xs font-medium text-[var(--tooltip-muted)]">
        {formatMonth(row.month)} · {actual ? ORI.actual : ORI.forecast}
      </p>
      <p className="mt-1 text-base font-bold tabular-nums leading-none text-[var(--tooltip-text)]">
        {formatValue(actual ? row.actual : row.projected)}
      </p>
      {!actual && row.range ? (
        <p className="mt-1 text-xs tabular-nums text-[var(--tooltip-muted)]">
          {ORI.likelyRange(formatValue(row.range[0]), formatValue(row.range[1]))}
        </p>
      ) : null}
    </div>
  );
}

/** The actual months as a solid line, the forecast dashed on from the last of them, its likely range a light band. */
export function OriForecastChart({ forecast, height = 140 }: { forecast: OriForecast; height?: number }) {
  const rows = forecastRows(forecast);
  const currency = forecast.format === "currency";
  const formatValue = currency ? formatCurrency : formatNumber;
  const axis = valueAxis(
    rows.flatMap((r) => [r.actual, r.projected, ...(r.range ?? [])]).filter((v): v is number => v != null),
    { currency, zero: false, maxTicks: 4 },
  );

  return (
    <ChartContainer config={{}} style={{ height }} className="w-full min-w-0" role="img" aria-label={ORI.forecastChart(forecast.label)}>
      <ComposedChart data={rows} margin={FORECAST_FRAME.margin}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border-subtle)" />
        <XAxis
          dataKey="month"
          tickFormatter={formatMonth}
          tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
          minTickGap={16}
        />
        <YAxis
          ticks={axis.ticks}
          domain={axis.domain}
          padding={FORECAST_FRAME.valuePadding}
          tickFormatter={axis.format}
          tick={{ fontSize: 11, fill: "var(--foreground-subtle)" }}
          tickLine={false}
          axisLine={false}
          width={48}
        />
        <ChartTooltip content={<ForecastTooltip formatValue={formatValue} />} wrapperStyle={{ outline: "none" }} />
        <Area dataKey="range" stroke="none" fill={HUE} fillOpacity={0.14} activeDot={false} isAnimationActive={false} />
        <Line dataKey="actual" stroke={HUE} strokeWidth={2} dot={false} isAnimationActive={false} />
        <Line dataKey="projected" stroke={HUE} strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
      </ComposedChart>
    </ChartContainer>
  );
}
