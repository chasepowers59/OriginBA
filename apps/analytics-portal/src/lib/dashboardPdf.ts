/** A dashboard's tiles as the server PDF's sections (POST /portal/export/dashboard-pdf). */
import { formatCompact, formatNumber } from "./format";
import type { ExecutiveKpi } from "./types";

export type ExportSection = { name: string; headers: string[]; rows: Record<string, unknown>[]; note?: string; failed?: boolean };

// api/export_routes.py refuses more than these
const MAX_SECTIONS = 12;
const MAX_ROWS = 5000;

export function dashboardPdfSections(sections: ExportSection[]) {
  let budget = MAX_ROWS;
  return sections
    .filter((s) => s.headers.length)
    .slice(0, MAX_SECTIONS)
    .map((s) => {
      const rows = s.rows.slice(0, budget);
      budget -= rows.length;
      const cut = rows.length < s.rows.length
        ? `Showing the first ${formatNumber(rows.length)} of ${formatNumber(s.rows.length)} rows (truncated)`
        : "";
      return { title: s.name, note: [s.note, cut].filter(Boolean).join(" · "), columns: s.headers, rows, failed: Boolean(s.failed) };
    });
}

/** The first line of an error, short: a PDF note, not a stack. */
function briefError(error: string) {
  const line = error.trim().split("\n")[0].trim();
  return line.length > 120 ? `${line.slice(0, 119)}…` : line;
}

/** KPI cards as export sections: the headline value and what it counts, then its breakdown. */
export function kpiSections(kpis: ExecutiveKpi[]): ExportSection[] {
  return kpis.map((kpi) => {
    const value = kpi.value == null ? "No value" : formatCompact(kpi.value, { currency: kpi.format === "currency" });
    const change = kpi.change_pct == null
      ? []
      : [`${kpi.change_pct > 0 ? "+" : ""}${kpi.change_pct}%${kpi.compare_label ? ` ${kpi.compare_label}` : ""}`];
    return {
      name: kpi.label,
      note: kpi.error ? `This card could not load: ${briefError(kpi.error)}` : [value, kpi.subtitle, ...change].join(" · "),
      headers: ["Category", "Value"],
      rows: kpi.trend.map((t) => ({ Category: t.label, Value: t.value })),
      failed: Boolean(kpi.error),
    };
  });
}
