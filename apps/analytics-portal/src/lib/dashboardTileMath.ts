/**
 * Pure tile math, split out of DashboardTile so the two bug-prone decisions are
 * unit-tested: WHICH column a tile charts, and WHAT its KPI headline may claim.
 */
import { measureColumnLabel, measureDisplaysAsCurrency } from "./businessLabels";
import { formatCompact, formatPercent } from "./format";
import type { DashboardTileDef } from "./types";

/**
 * The query result orders columns as [dimensions…, measures in request order].
 * The tile charts (and labels) the FIRST measure — charting the last column
 * while labeling with measures[0] mislabeled 2-measure premade reports.
 */
export function chartedMeasureColumn(columns: string[], measureCount: number): string {
  const idx = columns.length - Math.max(1, measureCount);
  return columns[idx >= 0 ? idx : columns.length - 1] ?? "";
}

/**
 * A KPI headline over grouped rows is only honest for additive aggs: the sum of
 * group sums (or counts) is the total, but the sum of averages is nothing. A
 * single ungrouped row is the value itself for any agg; otherwise show nothing
 * rather than a wrong number.
 */
export function kpiHeadline(
  rows: Record<string, unknown>[],
  measureKey: string,
  agg: string,
): number | null {
  if (!rows.length || !measureKey) return null;
  if (rows.length === 1) {
    const v = Number(rows[0][measureKey]);
    return Number.isFinite(v) ? v : null;
  }
  if (agg === "sum" || agg === "count") {
    return rows.reduce((s, r) => s + Number(r[measureKey] ?? 0), 0);
  }
  return null;
}

/** A chart or table with no ready-to-run report and no breakdown is not set up yet: running it
 *  draws the row count as a lone "group". A KPI with no breakdown is one number, and is fine. */
export function tileIsUnset(tile: Pick<DashboardTileDef, "visual" | "report_id" | "dimensions" | "time_grain">): boolean {
  return tile.visual !== "kpi" && !tile.report_id && !tile.time_grain && !(tile.dimensions ?? []).length;
}

/** The charted series' name, as the builder names it: the server's column label, else its wording. */
export function tileSeriesLabel(
  columnLabels: Record<string, string> | undefined,
  measureKey: string,
  measureField: string,
  measureAgg: string,
): string {
  return columnLabels?.[measureKey] ?? measureColumnLabel(measureField, measureAgg);
}

/** A KPI tile's number: a share is a percentage, money is money, and nothing is a dash. */
export function tileHeadline(value: number | null, measureField: string, measureAgg: string): string {
  if (value === null) return "—";
  if (measureAgg === "share") return formatPercent(value);
  return formatCompact(value, { currency: measureDisplaysAsCurrency(measureField, measureAgg) });
}
