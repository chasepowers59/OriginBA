import { downloadWorkbook } from "./exportXlsx";
import { exportFilename } from "./exportFilename";
import type { ExportSection } from "./dashboardPdf";

export function exportDashboardXlsx(title: string, sections: ExportSection[]): void {
  downloadWorkbook(
    sections.map((s) => ({ name: s.name, columns: s.headers, rows: s.rows })),
    exportFilename(title, "dashboard", "xlsx"),
  );
}
