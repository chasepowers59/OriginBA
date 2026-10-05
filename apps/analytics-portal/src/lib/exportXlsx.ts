import * as XLSX from "xlsx";
import { noteExport } from "./exportAudit";
import { formatBoolean, saveBlob } from "./format";

/** The sheet that describes an export (lib/exportAbout), not part of its rows. */
export const ABOUT_SHEET = "About this export";

export type WorkbookSection = {
  name: string;
  columns: string[];
  rows: Record<string, unknown>[];
};

/** Excel sheet names: ≤31 chars, no []:*?/\ and unique within the workbook. */
function sanitizeSheetName(name: string, taken: Set<string>): string {
  let base = name.replace(/[[\]:*?/\\]/g, " ").replace(/\s+/g, " ").trim() || "Sheet";
  base = base.slice(0, 31);
  let candidate = base;
  let n = 2;
  while (taken.has(candidate)) {
    const suffix = ` (${n++})`;
    candidate = base.slice(0, 31 - suffix.length) + suffix;
  }
  taken.add(candidate);
  return candidate;
}

/**
 * Build a real .xlsx workbook (one sheet per section) as an ArrayBuffer.
 *
 * Types survive: numbers stay numeric (utility finance lives in Excel — a CSV string
 * column defeats the point), booleans render as the app-wide True/False, null/undefined
 * are empty cells. Pure and unit-tested; the browser download lives in downloadWorkbook.
 */
export function buildWorkbook(sections: WorkbookSection[]): ArrayBuffer {
  const wb = XLSX.utils.book_new();
  const taken = new Set<string>();
  for (const section of sections) {
    const aoa: unknown[][] = [section.columns];
    for (const row of section.rows) {
      aoa.push(
        section.columns.map((c) => {
          const v = row[c];
          if (v === null || v === undefined) return null;
          if (typeof v === "boolean") return formatBoolean(v);
          return v;
        }),
      );
    }
    const sheet = XLSX.utils.aoa_to_sheet(aoa);
    XLSX.utils.book_append_sheet(wb, sheet, sanitizeSheetName(section.name, taken));
  }
  return XLSX.write(wb, { type: "array", bookType: "xlsx" }) as ArrayBuffer;
}

/** Browser-side download of a built workbook. */
export function downloadWorkbook(sections: WorkbookSection[], filename: string): void {
  const buf = buildWorkbook(sections);
  const blob = new Blob([buf], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const name = filename.endsWith(".xlsx") ? filename : `${filename}.xlsx`;
  saveBlob(blob, name);
  // the rows that left, not the "About this export" sheet describing them
  noteExport("xlsx", name, sections.filter((s) => s.name !== ABOUT_SHEET).reduce((n, s) => n + s.rows.length, 0));
}
