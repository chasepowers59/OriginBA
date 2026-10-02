import { describe, expect, it } from "vitest";
import { exportAbout, exportNote } from "./exportAbout";

/**
 * An export says what it holds (2026-10-01). The screen says "This shows: ..." and "top 500
 * rows"; the Excel file carried only the rows and the PDF only the period, so a number pasted
 * from either could not be traced to its filters, and a cut breakdown read as complete.
 */
const base = {
  title: "Which service points are switched on and off most?",
  dataSet: "On/Off History",
  period: "Last 12 months, as of Jul 17, 2026",
  disclosure: ["Event Date/Time from Jul 17, 2025 to Jul 17, 2026"],
  rowCount: 500,
  total: "4,457",
  truncated: true,
  exportedAt: "Oct 1, 2026, 5:00 PM",
};

describe("an export says what it holds", () => {
  it("the workbook's About sheet names the report, its filters, and that the list is cut", () => {
    const rows = exportAbout(base);
    const get = (k: string) => rows.find((r) => r.Field === k)?.Value;
    expect(get("Report")).toBe(base.title);
    expect(get("This shows")).toBe("Event Date/Time from Jul 17, 2025 to Jul 17, 2026");
    expect(get("Rows")).toBe("top 500 (more groups than are listed)");
    expect(get("Total across every group")).toBe("4,457");
  });

  it("a whole result says how many rows, with no cut note", () => {
    const rows = exportAbout({ ...base, truncated: false, rowCount: 37 });
    expect(rows.find((r) => r.Field === "Rows")?.Value).toBe("37");
  });

  it("the PDF note carries the period, the filters and the cut, within the API's 400 characters", () => {
    const note = exportNote(base);
    expect(note).toContain("Last 12 months, as of Jul 17, 2026");
    expect(note).toContain("This shows: Event Date/Time from Jul 17, 2025 to Jul 17, 2026");
    expect(note).toContain("top 500 rows");
    expect(exportNote({ ...base, disclosure: ["x".repeat(600)] }).length).toBeLessThanOrEqual(400);
  });
});
