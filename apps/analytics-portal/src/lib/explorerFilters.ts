import { windowFilter } from "./datePresets";
import type { FilterDef, QueryRequest } from "./types";

/**
 * The filters an explorer report runs with: the reporting window (none under All dates or
 * on a canvas with no date), the report's own, then the scope and the cross-filter.
 */
export function explorerFilters(p: {
  dateField: string | null;
  allDates: boolean;
  dateStart: string;
  dateEnd: string;
  reportFilters?: FilterDef[];
  scope?: { field: string; value: string } | null;
  drill?: { field: string; value: string } | null;
}): FilterDef[] {
  return [
    ...windowFilter(p.dateField, p.allDates, p.dateStart, p.dateEnd),
    ...(p.reportFilters ?? []),
    ...[p.scope, p.drill]
      .filter((f): f is { field: string; value: string } => Boolean(f?.field && f.value))
      .map((f) => ({ field: f.field, op: "eq", value: f.value })),
  ];
}

/** The explorer's request: the filters above, and "All dates" said explicitly so the server
 *  does not add its default window to an unfiltered query on a large canvas. */
export function explorerQuery(p: Parameters<typeof explorerFilters>[0] & {
  dimensions: string[];
  measures: QueryRequest["measures"];
}): QueryRequest {
  return {
    dimensions: p.dimensions,
    measures: p.measures,
    filters: explorerFilters(p),
    time_dimensions: [],
    limit: 500,
    all_dates: p.allDates,
  };
}

/** The report the explorer runs: a linked report until the link is applied, then the one the
 *  reader has open, else the canvas's first. The one place this is decided, so a link's run
 *  and the page's auto-run cannot race each other. */
export function reportToRun<R extends { id: string }>(
  reports: R[],
  activeReportId: string | null,
  linkedReportId: string | null,
): R | undefined {
  const find = (id: string | null) => (id ? reports.find((r) => r.id === id) : undefined);
  return find(linkedReportId) ?? find(activeReportId) ?? reports[0];
}
