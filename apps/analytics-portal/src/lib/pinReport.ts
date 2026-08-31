/** Build URL to pin a report or snapshot on the custom dashboard builder. */
export function pinReportUrl(opts: {
  snapshotId: string;
  reportId?: string;
  title: string;
  chartType?: string;
  visual?: "chart" | "kpi";
  measureField?: string;
  measureAgg?: string;
  dimensions?: string[];
  days?: number;
}): string {
  const params = new URLSearchParams({
    pin_snapshot: opts.snapshotId,
    pin_title: opts.title,
  });
  if (opts.reportId) params.set("pin_report", opts.reportId);
  if (opts.chartType) params.set("pin_chart", opts.chartType);
  if (opts.visual) params.set("pin_visual", opts.visual);
  if (opts.measureField) params.set("pin_measure", opts.measureField);
  if (opts.measureAgg) params.set("pin_agg", opts.measureAgg);
  if (opts.dimensions?.length) params.set("pin_dims", opts.dimensions.join(","));
  if (opts.days) params.set("pin_days", String(opts.days));
  return `/dashboards/new?${params.toString()}`;
}
