import { isUnitOfMeasureField, measureDisplaysAsCurrency } from "./businessLabels";

export const MIXED_UNITS_NOTE = "Not totalled: the rows are in different units.";

export type ResultSummary = {
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
}): ResultSummary {
  const none: ResultSummary = { total: null, leader: null, notTotalled: null };
  if (!r.measureKey) return none;

  const isQuantity = r.measureField !== "*" && r.measureAgg !== "count" && r.measureAgg !== "count_distinct"
    && !measureDisplaysAsCurrency(r.measureField, r.measureAgg);
  const mixesUnits = isQuantity && r.columns.some((col) =>
    col !== r.measureKey
    && (isUnitOfMeasureField(col) || isUnitOfMeasureField(r.labels?.[col] ?? ""))
    && new Set(r.rows.map((row) => String(row[col] ?? ""))).size > 1);
  if (mixesUnits) return { ...none, notTotalled: MIXED_UNITS_NOTE };

  const value = (row: Record<string, unknown>) => Number(row[r.measureKey] ?? 0);
  const total = r.rows.reduce((sum, row) => sum + value(row), 0);
  if (!r.dimensionKey || total <= 0) return { ...none, total }; // "leads at 0.0%" is noise

  const top = r.rows.reduce((best, row) => (value(row) > value(best) ? row : best));
  return {
    total,
    leader: { label: String(top[r.dimensionKey] ?? "Top value"), share: (value(top) / total) * 100, value: value(top) },
    notTotalled: null,
  };
}
