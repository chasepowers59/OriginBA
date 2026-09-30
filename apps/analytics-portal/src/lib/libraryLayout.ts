import { aggregationLabel } from "./businessLabels";
import type { ReportLibraryEntry, ReportLibraryFolder } from "./types";

/**
 * The Library is a folder tree (catalog `report_library`): each folder names a few reports
 * to start with and keeps the rest one click away. These decide what is on screen; the
 * component only draws it.
 */

/** The reader's own saved views: a folder at the top of the rail, not in the catalog. */
export const SAVED_VIEWS = "saved";

export function showsSavedViews(requested: string | null, savedCount: number): boolean {
  return requested === SAVED_VIEWS && savedCount > 0;
}

/** The folder the URL asks for, or the first one with reports in it; never an empty folder. */
export function folderToShow(folders: ReportLibraryFolder[], requested: string | null): ReportLibraryFolder | null {
  const withReports = folders.filter((f) => f.reports.length > 0);
  return withReports.find((f) => f.id === requested) ?? withReports[0] ?? null;
}

/** "Start here" and "More in this folder", each in catalog order. */
export function splitFolder(folder: ReportLibraryFolder): { essentials: ReportLibraryEntry[]; more: ReportLibraryEntry[] } {
  return {
    essentials: folder.reports.filter((r) => r.essential),
    more: folder.reports.filter((r) => !r.essential),
  };
}

export type SearchGroup = { folder: ReportLibraryFolder; reports: ReportLibraryEntry[] };

/**
 * Every report whose question, why, data set or dimensions carry every word of the query,
 * grouped under its folder in folder order. A blank query is the folder view, not a search.
 */
export function searchLibrary(folders: ReportLibraryFolder[], query: string): SearchGroup[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  const matches = (r: ReportLibraryEntry) => {
    const haystack = [r.title, r.description, r.snapshot_label, ...(r.dimensions ?? [])].join(" ").toLowerCase();
    return words.every((w) => haystack.includes(w));
  };
  return folders
    .map((folder) => {
      const { essentials, more } = splitFolder(folder);
      return { folder, reports: [...essentials, ...more].filter(matches) };
    })
    .filter((g) => g.reports.length > 0);
}

/** One quiet line under a card's title: what it groups by, then what it measures. */
export function shapeLine(report: Pick<ReportLibraryEntry, "dimensions" | "measures">): string {
  const dims = (report.dimensions ?? []).filter(Boolean);
  const [first, ...rest] = report.measures ?? [];
  const parts: string[] = [];
  if (dims.length) {
    parts.push(`By ${dims.length > 1 ? `${dims.slice(0, -1).join(", ")} and ${dims[dims.length - 1]}` : dims[0]}`);
  }
  if (first) {
    const agg = aggregationLabel(String(first.agg ?? "count"));
    // "*" is the row count ("Count of records *" reads like a typo), and a field that
    // already names its aggregation reads "Total Total Balance" with it prefixed.
    const field = first.field && first.field !== "*" ? first.field : "";
    const namesItsAgg = field.toLowerCase().startsWith(`${agg.toLowerCase()} `);
    const head = !field ? agg : namesItsAgg ? field : `${agg} ${field}`;
    parts.push(rest.length ? `${head} and ${rest.length} more` : head);
  }
  return parts.join(" · ");
}

/** The Library URL for a folder and a search; both ride in the query so links and Back work. */
export function libraryHref({ folder, q }: { folder?: string | null; q?: string | null }): string {
  const params = new URLSearchParams();
  if (folder) params.set("folder", folder);
  if (q?.trim()) params.set("q", q.trim());
  const qs = params.toString();
  return qs ? `/reports?${qs}` : "/reports";
}
