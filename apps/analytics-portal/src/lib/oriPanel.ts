import type { OriAnomaly, OriFinding, OriForecast, OriRead, OriTrends } from "@/lib/api";
import type { AskRequest, OriItem } from "@/lib/assistantContext";

export type Investigation = { key: string; headline: string; detail: string; ask: AskRequest };

/** The moves against the prior period first, then the unusual months: one list, one follow-up each. */
export function investigations(findings: OriFinding[], anomalies: OriAnomaly[]): Investigation[] {
  return [
    // a move's question carries its own figures; an unusual month is restated by the server
    ...findings.map((f) => ({ ...f, key: `move:${f.kpi_id}`, ask: { question: f.question, context: null } })),
    ...anomalies.map((a) => ({ ...a, key: `month:${a.kpi_id}:${a.month}`, ask: oriAsk(a, "anomaly") })),
  ];
}

export type ForecastRow = { month: string; actual?: number; projected?: number; range?: [number, number] };

/**
 * One row per month: the actual months, then the projected ones. The last actual month also
 * starts the projection, with a range of no width, so the dashed line and the band grow out of
 * the last real point rather than floating beside it.
 */
export function forecastRows({ history, forecast }: Pick<OriForecast, "history" | "forecast">): ForecastRow[] {
  const rows: ForecastRow[] = history.map((p) => ({ month: p.month, actual: p.value }));
  const last = rows[rows.length - 1];
  if (last && forecast.length) Object.assign(last, { projected: last.actual, range: [last.actual, last.actual] });
  return [...rows, ...forecast.map((p): ForecastRow => ({ month: p.month, projected: p.value, range: [p.low, p.high] }))];
}

/**
 * Nothing to say, no panel. The findings are fast, so nothing shows before them; the trends can
 * take half a minute cold, so while they come the panel stays up and says Ori is looking.
 */
export function oriPanelShows(read: OriRead | null, trends: OriTrends | null): boolean {
  if (!read) return false;
  if (!trends) return true;
  return Boolean(read.brief?.trim()) || read.findings.length + trends.anomalies.length + trends.forecasts.length > 0;
}

/** The forecast chart's frame: margins round the plot, and room under the lowest value tick. */
export const FORECAST_FRAME = {
  margin: { top: 6, right: 12, bottom: 4, left: 0 },
  valuePadding: { top: 0, bottom: 8 },
} as const;

/** Asking about one of Ori's items names it, so the server can restate what Ori showed. */
export function oriAsk(
  item: { kpi_id: string; question: string; snapshot_id?: string | null; headline: string },
  kind: OriItem["kind"],
): AskRequest {
  return {
    question: item.question,
    context: item.snapshot_id
      ? { canvas_id: item.snapshot_id, label: item.headline, ori_item: { kind, kpi_id: item.kpi_id } }
      : null,
  };
}
