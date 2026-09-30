import type { DashboardTemplate } from "@/lib/dashboardTemplates";
import type { ReportLibraryFolder } from "@/lib/types";
import { MAX_TILES } from "@/lib/dashboardSlots";
import { splitFolder } from "@/lib/libraryLayout";

/** A folder too thin on essentials still opens as a board worth reading. */
const MIN_TILES = 4;

/**
 * A Library folder as a starter dashboard: one tile per report the folder says to start
 * with, topped up from the rest of the folder to four, and never past the grid. Each
 * tile runs its report (report_id), so it carries the report's own filters and money
 * rules rather than a copy of them.
 */
export function folderDashboard(folder: ReportLibraryFolder): Omit<DashboardTemplate, "id" | "workstream"> {
  const { essentials, more } = splitFolder(folder);
  const reports = [...essentials, ...more.slice(0, Math.max(0, MIN_TILES - essentials.length))]
    .slice(0, MAX_TILES);
  return {
    title: folder.title,
    description: folder.description,
    days: 180,
    tiles: reports.map((r, slot) => ({
      slot,
      title: r.title,
      visual: "chart",
      snapshot_id: r.snapshot_id,
      report_id: r.report_id,
      chart_type: r.chart_type || "bar",
    })),
  };
}
