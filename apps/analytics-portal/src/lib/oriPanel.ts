import type { OriAnomaly, OriFinding, OriForecast, OriRead, OriTrends } from "@/lib/api";

export type Investigation = { key: string; headline: string; detail: string; question: string };

/** The moves against the prior period first, then the unusual months: one list, one follow-up each. */
export function investigations(findings: OriFinding[], anomalies: OriAnomaly[]): Investigation[] {
  return [
    ...findings.map((f) => ({ ...f, key: `move:${f.kpi_id}` })),
    ...anomalies.map((a) => ({ ...a, key: `month:${a.kpi_id}:${a.month}` })),
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
