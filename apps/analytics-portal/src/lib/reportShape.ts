import { AGGREGATION_LABELS } from "./businessLabels";

type Measure = { field?: string; agg?: string; [k: string]: unknown };
// Only `field` is read; op/value ride along from the catalog and are allowed through.
type Filter = { field?: string; [k: string]: unknown };

/**
 * One line saying what a premade report RETURNS: "Total Current Amount by SA Type,
 * filtered on Is Frozen".
 *
 * The library used to show a title and a paragraph of why-it-matters, and nothing about
 * the shape — so a reader had to open a report to find out whether it counted rows or
 * summed money, what it grouped by, and whether it was already scoped. The catalog
 * carries measures, dimensions and filters per report; only the API was dropping them.
 *
 * Deliberately not a full sentence of every detail: past one measure it says "and N
 * more" rather than growing a list nobody reads on a card.
 */
export function reportShape(report: {
  measures?: Measure[] | null;
  dimensions?: string[] | null;
  filters?: Filter[] | null;
}): string {
  const measures = report.measures ?? [];
  if (!measures.length) return "";

  const [first, ...rest] = measures;
  const agg = AGGREGATION_LABELS[String(first.agg ?? "count").toLowerCase()] ?? first.agg ?? "";
  // "*" is the row count, and "Count of records *" reads like a typo.
  const head = first.field && first.field !== "*" ? `${agg} ${first.field}` : agg;
  const measurePart = rest.length ? `${head} and ${rest.length} more` : head;

  const dims = (report.dimensions ?? []).filter(Boolean);
  const byPart = dims.length ? ` by ${joinReadable(dims)}` : "";

  const filterFields = (report.filters ?? []).map((f) => f.field).filter(Boolean) as string[];
  const filterPart = filterFields.length
    ? `, filtered on ${joinReadable(filterFields)}`
    : "";

  return `${measurePart}${byPart}${filterPart}`;
}

/** "A", "A and B", "A, B and C" — the way a person would say the list aloud. */
function joinReadable(items: string[]): string {
  if (items.length <= 1) return items[0] ?? "";
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}
