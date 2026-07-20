import type { DatabaseQueryTemplate } from "./databaseQueryTemplates";

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

  let dimensionKey: string | null = null;
  let measureKey: string | null = null;

  for (const col of columns) {
    const sample = rows[0]?.[col];
    if (!dimensionKey && !isNumericValue(sample)) {
      dimensionKey = col;
    }
  }

  for (const col of columns) {
    if (col === dimensionKey) continue;
    const numericCount = rows.slice(0, 20).filter((r) => isNumericValue(r[col])).length;
    if (numericCount >= Math.max(2, Math.floor(rows.slice(0, 20).length * 0.6))) {
      measureKey = col;
      break;
    }
  }

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
