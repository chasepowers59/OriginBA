/**
 * Pure tile math, split out of DashboardTile so the two bug-prone decisions are
 * unit-tested: WHICH column a tile charts, and WHAT its KPI headline may claim.
 */

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
