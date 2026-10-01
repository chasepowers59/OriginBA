import { isUnitOfMeasureField, measureDisplaysAsCurrency } from "./businessLabels";

/** The query names its aggregates m0, m1... (api/query_builder.py): the number columns. */
export function isMeasureColumn(column: string): boolean {
  return /^m\d+$/.test(column);
}

export const MIXED_UNITS_NOTE = "Not totalled: the rows are in different units.";
export const TRUNCATED_NOTE = "Not totalled: only the top groups are listed, and their sum is not the total.";
export const NOT_ADDITIVE_NOTE = "Not totalled: averages, percentages, distinct counts and highest or lowest values do not add up across groups.";

type ResultSummary = {
  total: number | null;
  leader: { label: string; share: number; value: number } | null;
  notTotalled: string | null;
};

/**
 * The results panel's total and "X leads this view at N%" line. A quantity broken down by
 * unit of measure has no total: kWh + therms + gallons is not a number, so neither is a
 * share of it. Counts and money add whatever the unit, and rows that all carry one unit
 * (a unit cross-filter) add too.
 */
export function summarizeResult(r: {
  columns: string[];
  rows: Record<string, unknown>[];
  measureKey: string;
  dimensionKey: string;
  measureField: string;
  measureAgg: string;
  labels?: Record<string, string>;
  /** The API cut the breakdown to its top groups (`truncated`)... */
  truncated?: boolean;
  /** ...and answered the same question unbroken: the true total (`totals[measureKey]`). */
  grandTotal?: number | null;
}): ResultSummary {
  const none: ResultSummary = { total: null, leader: null, notTotalled: null };
  if (!r.measureKey) return none;
  if (r.measureAgg !== "sum" && r.measureAgg !== "count") return { ...none, notTotalled: NOT_ADDITIVE_NOTE };

  const isQuantity = r.measureField !== "*" && r.measureAgg === "sum"
    && !measureDisplaysAsCurrency(r.measureField, r.measureAgg);
  const mixesUnits = isQuantity && r.columns.some((col) =>
    col !== r.measureKey
    && (isUnitOfMeasureField(col) || isUnitOfMeasureField(r.labels?.[col] ?? ""))
    && new Set(r.rows.map((row) => String(row[col] ?? ""))).size > 1);
  if (mixesUnits) return { ...none, notTotalled: MIXED_UNITS_NOTE };

  const value = (row: Record<string, unknown>) => Number(row[r.measureKey] ?? 0);
  // a cut breakdown's rows do not add up to the total (CityCorp on/off churn, 2026-10-01:
  // 1,971 shown of 3,591); the unbroken answer is the total, or there is none
  if (r.truncated && r.grandTotal == null) return { ...none, notTotalled: TRUNCATED_NOTE };
  const total = r.grandTotal ?? r.rows.reduce((sum, row) => sum + value(row), 0);
  // "leads at 0.0%" is noise, and so is "leads at 100%": one group (a cross-filtered bar) leads nothing
  if (!r.dimensionKey || total <= 0 || r.rows.length < 2) return { ...none, total };

  const top = r.rows.reduce((best, row) => (value(row) > value(best) ? row : best));
  return {
    total,
    leader: { label: String(top[r.dimensionKey] ?? "Top value"), share: (value(top) / total) * 100, value: value(top) },
    notTotalled: null,
  };
}

/** The detail table's footer: "Total" in the first non-measure column, the total under the
 *  measure, blanks elsewhere. Null when the result is not totalled (see summarizeResult). */
export function totalRow(columns: string[], measureKey: string, total: number | null): (string | number | null)[] | null {
  if (!measureKey || total == null) return null;
  const labelAt = columns.findIndex((c) => c !== measureKey);
  return columns.map((c, i) => (c === measureKey ? total : i === labelAt ? "Total" : null));
}

/** The leader line's parts: "<label> leads this view with <value>, <share> of the <total>
 *  total." Both amounts are named, so the leader's amount never reads as the total. */
export function leaderParts(
  leader: { label: string; share: number; value: number },
  total: number,
  formatMeasure: (n: number) => string,
  formatPercent: (n: number) => string,
): { label: string; value: string; share: string; total: string } {
  return { label: leader.label, value: formatMeasure(leader.value), share: formatPercent(leader.share), total: formatMeasure(total) };
}
