import type { BuilderQuestion, FilterDef } from "./types";

/** The question a KPI card asked (api/kpi_runner.py `explore_question`). */
export type CardQuestion = {
  snapshot_id: string;
  dimensions?: string[];
  measures: { field: string; agg: string }[];
  filters?: FilterDef[];
  chart_type?: string;
  all_dates?: boolean;
};

/** Where a card's number can be seen again: its ready-to-run report when it has one, else the
 *  builder opened on the card's own question; the data set page only for an older API. */
export function kpiExploreHref(kpi: { snapshot_id: string; explore_report_id?: string | null; explore_question?: CardQuestion | null }): string {
  if (kpi.explore_report_id) return `/explore/${kpi.snapshot_id}?report=${kpi.explore_report_id}`;
  if (kpi.explore_question) return `/build?question=${encodeURIComponent(JSON.stringify(kpi.explore_question))}`;
  return `/explore/${kpi.snapshot_id}`;
}

/** The builder's `?question=`; anything malformed is ignored (the server validates fields anyway). */
export function parseCardQuestion(raw: string | null | undefined): BuilderQuestion | null {
  if (!raw) return null;
  let q: Partial<CardQuestion>;
  try {
    q = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!q || typeof q.snapshot_id !== "string" || !Array.isArray(q.measures)) return null;
  return {
    id: "card", report_id: "", snapshot_label: "", workstream: "", workstream_label: "", title: "", description: "",
    snapshot_id: q.snapshot_id,
    dimensions: Array.isArray(q.dimensions) ? q.dimensions : [],
    measures: q.measures,
    filters: Array.isArray(q.filters) ? q.filters : [],
    chart_type: typeof q.chart_type === "string" ? q.chart_type : "bar",
    all_dates: Boolean(q.all_dates),
  };
}
