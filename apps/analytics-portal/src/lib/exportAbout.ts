/** What an export holds, said in the file itself: the screen's "This shows: ..." and its
 *  "top N rows" note travel with the Excel workbook (an About sheet) and the PDF (its note). */
export type ExportContext = {
  title: string;
  dataSet: string;
  period?: string | null;
  disclosure?: string[];
  rowCount: number;
  /** the formatted total over every group (the unbroken answer when the list is cut) */
  total?: string | null;
  truncated?: boolean;
  exportedAt: string;
};

const rowsText = (c: ExportContext) =>
  c.truncated ? `top ${c.rowCount} (more groups than are listed)` : String(c.rowCount);

export function exportAbout(c: ExportContext): { Field: string; Value: string }[] {
  const rows: [string, string | null | undefined][] = [
    ["Report", c.title],
    ["Data set", c.dataSet],
    ["Period", c.period],
    ["This shows", c.disclosure?.length ? c.disclosure.join(" · ") : null],
    ["Rows", rowsText(c)],
    [c.truncated ? "Total across every group" : "Total", c.total],
    ["Exported", c.exportedAt],
  ];
  return rows.filter(([, v]) => v != null && v !== "").map(([Field, Value]) => ({ Field, Value: String(Value) }));
}

const NOTE_MAX = 400; // PdfExportRequest.note (api/export_routes.py)

export function exportNote(c: ExportContext): string {
  const parts = [
    c.period,
    c.disclosure?.length ? `This shows: ${c.disclosure.join(" · ")}` : null,
    c.truncated ? `top ${c.rowCount} rows; the total${c.total ? ` (${c.total})` : ""} counts every group` : null,
  ].filter(Boolean) as string[];
  const note = parts.join(" — ");
  return note.length > NOTE_MAX ? `${note.slice(0, NOTE_MAX - 1)}…` : note;
}
