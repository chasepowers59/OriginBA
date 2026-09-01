import type { DatabaseQueryTemplate } from "./databaseQueryTemplates";
import { isIdentifierColumn } from "./format";

export type ChartSuggestion = {
  dimensionKey: string;
  measureKey: string;
  chartType: "bar" | "line" | "horizontal";
  isCurrency: boolean;
  sortTimeSeries: boolean;
  label: string;
};

const DATE_HINTS = /(_dt|_dttm|_date|month|period|week|year)/i;
const CURRENCY_HINTS = /(amt|amount|revenue|dollar|cur_amt|calc_amt|gl_amt|billed)/i;
const COUNT_HINTS = /(count|rows|segments|quantity|qty|sq)/i;

function isNumericValue(value: unknown): boolean {
  if (value == null || value === "") return false;
  const n = Number(value);
  return Number.isFinite(n);
}

function looksLikeDateColumn(name: string, sample: unknown): boolean {
  if (DATE_HINTS.test(name)) return true;
  if (typeof sample === "string" && /^\d{4}-\d{2}-\d{2}/.test(sample)) return true;
  return false;
}

export function suggestChart(
  columns: string[],
  rows: Record<string, unknown>[],
  template?: DatabaseQueryTemplate | null,
): ChartSuggestion | null {
  if (rows.length < 2 || columns.length < 2) return null;

  if (template?.chartDimension && template.chartMeasure) {
    const dim = columns.find(
      (c) => c.toUpperCase() === template.chartDimension!.toUpperCase(),
    );
    const measure = columns.find(
      (c) => c.toUpperCase() === template.chartMeasure!.toUpperCase(),
    );
    if (dim && measure) {
      return {
        dimensionKey: dim,
        measureKey: measure,
        chartType: template.chartType ?? "bar",
        isCurrency: template.isCurrency ?? CURRENCY_HINTS.test(measure),
        sortTimeSeries: template.sortTimeSeries ?? looksLikeDateColumn(dim, rows[0]?.[dim]),
        label: measure,
      };
    }
  }

  // Identifier columns (ACCT_ID, BSEG_ID…) are never measures — a bar of summed
  // account ids is nonsense — and only dimension-of-last-resort. Sample several
  // rows: the first row alone misclassifies a column whose first value is null.
  const sampleRows = rows.slice(0, 20);
  const isMostlyNumeric = (col: string) => {
    const numericCount = sampleRows.filter((r) => isNumericValue(r[col])).length;
    return numericCount >= Math.max(2, Math.floor(sampleRows.length * 0.6));
  };
  const hasCategoryValues = (col: string) =>
    sampleRows.some((r) => r[col] != null && r[col] !== "" && !isNumericValue(r[col]));

  const categoricalCols = columns.filter(hasCategoryValues);
  const dimensionKey =
    categoricalCols.find((c) => !isIdentifierColumn(c)) ?? categoricalCols[0] ?? null;

  const measureKey =
    columns.find(
      (col) => col !== dimensionKey && !isIdentifierColumn(col) && isMostlyNumeric(col),
    ) ?? null;

  if (!dimensionKey || !measureKey) return null;

  const sortTimeSeries = looksLikeDateColumn(dimensionKey, rows[0]?.[dimensionKey]);
  return {
    dimensionKey,
    measureKey,
    chartType: sortTimeSeries ? "line" : rows.length > 8 ? "horizontal" : "bar",
    isCurrency: CURRENCY_HINTS.test(measureKey) && !COUNT_HINTS.test(measureKey),
    sortTimeSeries,
    label: measureKey,
  };
}
