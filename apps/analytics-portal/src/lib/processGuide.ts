import type { PremadeReport, ProcessFieldGuide, ScopeFilterDef, SnapshotMetadata } from "@/lib/types";

export type ProcessScopedMetadata = SnapshotMetadata & {
  activeProcessId: string | null;
  processGuide: ProcessFieldGuide | null;
  guidedDimensions: SnapshotMetadata["dimensions"];
  guidedMeasures: SnapshotMetadata["measures"];
  guidedScopeFilters: ScopeFilterDef[];
  guidedPremadeReports: PremadeReport[];
};

function pickById<T extends { id: string }>(items: T[], allowed: string[]): T[] {
  const order = new Map(allowed.map((id, idx) => [id.toUpperCase(), idx]));
  return items
    .filter((item) => order.has(item.id.toUpperCase()))
    .sort((a, b) => (order.get(a.id.toUpperCase()) ?? 99) - (order.get(b.id.toUpperCase()) ?? 99));
}

export function applyProcessGuide(
  metadata: SnapshotMetadata,
  processId: string | null,
): ProcessScopedMetadata {
  const guide = processId ? metadata.process_guides?.[processId] ?? null : null;

  if (!guide) {
    return {
      ...metadata,
      activeProcessId: null,
      processGuide: null,
      guidedDimensions: metadata.dimensions,
      guidedMeasures: metadata.measures,
      guidedScopeFilters: metadata.scope_filters ?? [],
      guidedPremadeReports: metadata.premade_reports,
    };
  }

  const dimIds = guide.dimensions.length ? guide.dimensions : metadata.dimensions.map((d) => d.id);
  const measureIds = guide.measures.length ? guide.measures : metadata.measures.map((m) => m.id);
  const scopeIds = guide.scope_fields ?? [];

  const guidedScopeFilters = (metadata.scope_filters ?? []).filter((f) =>
    scopeIds.length ? scopeIds.includes(f.field) : true,
  );

  let guidedPremadeReports = metadata.premade_reports;
  if (guide.report_ids?.length) {
    const allowed = new Set(guide.report_ids);
    guidedPremadeReports = metadata.premade_reports.filter((r) => allowed.has(r.id));
  }

  return {
    ...metadata,
    activeProcessId: processId,
    processGuide: guide,
    guidedDimensions: pickById(metadata.dimensions, dimIds),
    guidedMeasures: pickById(metadata.measures, measureIds),
    guidedScopeFilters,
    guidedPremadeReports,
  };
}

export function exploreUrl(
  snapshotId: string,
  opts?: { reportId?: string | null; processId?: string | null; tab?: string },
): string {
  const params = new URLSearchParams();
  if (opts?.processId) params.set("process", opts.processId);
  if (opts?.reportId) params.set("report", opts.reportId);
  if (opts?.tab && opts.tab !== "reports") params.set("tab", opts.tab);
  const qs = params.toString();
  return qs ? `/explore/${snapshotId}?${qs}` : `/explore/${snapshotId}`;
}
