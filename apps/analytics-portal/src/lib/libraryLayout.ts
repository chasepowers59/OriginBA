import type { ReportLibraryEntry, ReportLibraryPack } from "./types";

export type LibrarySection = { workstream: string; label: string; reports: ReportLibraryEntry[] };

/**
 * The library's one grouping (UI-4): each report under its workstream, in the rail's order.
 * Packs are how the catalog curates reports; shown beside the rail they were a second
 * taxonomy with different counts. A workstream the rail does not list lands last.
 */
export function reportsByWorkstream(packs: ReportLibraryPack[], order: string[]): LibrarySection[] {
  const sections = new Map<string, LibrarySection>();
  const seen = new Set<string>();
  for (const report of packs.flatMap((p) => p.reports)) {
    const key = `${report.snapshot_id}:${report.report_id}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const section = sections.get(report.workstream)
      ?? { workstream: report.workstream, label: report.workstream_label, reports: [] };
    section.reports.push(report);
    sections.set(report.workstream, section);
  }
  const rank = (id: string) => (order.includes(id) ? order.indexOf(id) : order.length);
  return [...sections.values()].sort((a, b) => rank(a.workstream) - rank(b.workstream));
}

/** How the report library opens: folded while browsing everything, open once the reader narrows it. */
export function sectionsStartOpen(s: { query: string; workstream: string | null; sectionCount: number }): boolean {
  return Boolean(s.query.trim() || s.workstream || s.sectionCount <= 1);
}

/** The line under a folded section's title: its first reports by name, so it does not read as empty. */
export function sectionPreview(reports: Pick<ReportLibraryEntry, "title">[], shown = 3): string {
  const names = reports.slice(0, shown).map((r) => r.title);
  const more = reports.length - names.length;
  return names.join(" · ") + (more > 0 ? ` · and ${more} more` : "");
}
