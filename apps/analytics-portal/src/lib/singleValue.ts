import { formatCurrency, formatNumber } from "@/lib/format";
import type { ChartSeries } from "@/components/builder/BuilderChart";

export type SingleValue = { values: { label: string; text: string }[] };

/**
 * A one-row result with no category is a number, not a chart: "See where this number comes
 * from" on a Home card opens exactly this. Null whenever there is a category, more than one
 * row, or no value to show, and the chart layer decides as before.
 */
export function singleValue({ xKey, rows, series }: {
  xKey: string; rows: Record<string, unknown>[]; series: ChartSeries[];
}): SingleValue | null {
  if (xKey || rows.length !== 1 || !series.length) return null;
  const row = rows[0];
  const present = series.filter((s) => row[s.key] != null && row[s.key] !== "");
  if (!present.length) return null;
  return {
    values: present.map((s) => ({
      label: s.label,
      text: s.currency ? formatCurrency(row[s.key]) : formatNumber(row[s.key]),
    })),
  };
}
