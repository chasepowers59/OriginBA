"use client";

import type { TooltipProps } from "recharts";
import { formatTooltipCurrency, formatTooltipNumber } from "@/lib/format";

type ChartTooltipProps = TooltipProps<number, string> & {
  measureLabel?: string;
  isCurrency?: boolean;
};

export function ChartTooltipContent({
  active,
  payload,
  measureLabel = "Value",
  isCurrency = false,
}: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  const point = payload[0];
  const n = Number(point?.value);
  const display = isCurrency ? formatTooltipCurrency(n) : formatTooltipNumber(n);
  const category =
    (point?.payload as { fullName?: string } | undefined)?.fullName ??
    String(point?.name ?? "");

  return (
    <div className="chart-tooltip pointer-events-none z-50 min-w-[140px] max-w-[280px] rounded-xl px-4 py-3 ring-1 ring-black/5 dark:ring-white/10">
      <p className="truncate text-xs font-medium leading-snug text-[var(--tooltip-muted)]" title={category}>
        {category}
      </p>
      <p className="mt-2 text-2xl font-bold tabular-nums leading-none tracking-tight text-[var(--tooltip-text)]">
        {display}
      </p>
      <p className="mt-2 text-[10px] font-semibold uppercase tracking-wider text-sky-600 dark:text-sky-400/90">
        {measureLabel}
      </p>
    </div>
  );
}

export const chartTooltipWrapperStyle = {
  zIndex: 50,
  outline: "none",
};
