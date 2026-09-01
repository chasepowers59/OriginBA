import { exportRowsCsv } from "./format";
import { downloadWorkbook } from "./exportXlsx";
import { brandTitle } from "./brand";

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

export function exportDashboardCsv(
  title: string,
  sections: { name: string; headers: string[]; rows: Record<string, unknown>[] }[],
): void {
  const allHeaders = ["Section", ...sections[0]?.headers ?? ["Value"]];
  const rows: Record<string, unknown>[] = [];
  for (const section of sections) {
    for (const row of section.rows) {
      const out: Record<string, unknown> = { Section: section.name };
      section.headers.forEach((h) => {
        out[h] = row[h] ?? row[Object.keys(row).find((k) => k === h) ?? ""] ?? "";
      });
      rows.push(out);
    }
    rows.push({ Section: "" });
  }
  exportRowsCsv(allHeaders, rows, `${title.replace(/\s+/g, "_")}_dashboard.csv`);
}

/** The Excel pack is a REAL workbook: one sheet per dashboard section, typed values. */
export function exportDashboardXlsx(
  title: string,
  sections: { name: string; headers: string[]; rows: Record<string, unknown>[] }[],
): void {
  downloadWorkbook(
    sections.map((s) => ({ name: s.name, columns: s.headers, rows: s.rows })),
    `${title.replace(/\s+/g, "_")}_dashboard.xlsx`,
  );
}
