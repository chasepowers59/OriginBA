import { exportRowsCsv } from "./format";
import { downloadWorkbook } from "./exportXlsx";
import { brandTitle } from "./brand";
import { exportFilename } from "./exportFilename";

export function printDashboardPack(title: string, targetId = "dashboard-export-root"): void {
  const previous = document.title;
  document.title = brandTitle(title);
  const el = document.getElementById(targetId);
  if (el) el.classList.add("printing-dashboard");
  window.print();
  window.setTimeout(() => {
    document.title = previous;
    if (el) el.classList.remove("printing-dashboard");
  }, 500);
}

export function exportDashboardXlsx(
  title: string,
  sections: { name: string; headers: string[]; rows: Record<string, unknown>[] }[],
): void {
  downloadWorkbook(
    sections.map((s) => ({ name: s.name, columns: s.headers, rows: s.rows })),
    exportFilename(title, "dashboard", "xlsx"),
  );
}
