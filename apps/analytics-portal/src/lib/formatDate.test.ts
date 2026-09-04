import { describe, expect, it } from "vitest";
import { formatCellValue, formatDateTime, isoDateTimeString } from "@/lib/format";

/**
 * A date-only value is a CALENDAR DATE, not an instant at UTC midnight.
 *
 * `new Date("2026-09-02")` is specified to parse as UTC midnight, while
 * `new Date("2026-09-02T00:00:00")` (no zone) parses as LOCAL midnight. formatDateTime
 * fed the first form straight to toLocaleString, so west of UTC every date-only value
 * rendered as THE PREVIOUS DAY plus a time nobody supplied:
 *
 *     "2026-09-02"  ->  "Sep 1, 2026, 06:00 PM"     (TZ=America/Denver)
 *
 * Found by running real Ellensburg values through the live formatters:
 * RPT_CHARACTERISTICS."Ad Hoc Value" = "2001-02-26" rendered "Feb 25, 2001, 05:00 PM".
 * It reaches every canvas, not just that column — `formatCellValue` routes any
 * /^\d{4}-\d{2}-\d{2}/ string here, and the API serializes a Postgres DATE column with
 * `date.isoformat()`, which is exactly this form. A bill dated the 1st showed the 31st.
 *
 * This is bug class 12 (a calendar date derived in UTC) a third time, after
 * report_schedules and the frontend date-range builders. Same rule as always: these
 * are business dates in the utility's own calendar, never UTC instants.
 *
 * A date-only value also has no time, so inventing "06:00 PM" is its own small lie.
 */

describe("a date-only value keeps its calendar day", () => {
  it("does not shift a plain date backwards", () => {
    expect(formatDateTime("2026-09-02")).toBe("Sep 2, 2026");
    expect(formatDateTime("2001-02-26")).toBe("Feb 26, 2001");
  });

  it("does not invent a time for a value that has none", () => {
    expect(formatDateTime("2026-09-02")).not.toMatch(/AM|PM|:/);
  });

  it("still renders a real timestamp with its time", () => {
    const out = formatDateTime("2026-09-02T14:30:00");
    expect(out).toContain("Sep 2, 2026");
    expect(out).toMatch(/02:30|14:30/);
  });

  it("a timestamp carrying an explicit zone is still honoured", () => {
    // Z means an instant; converting it to the viewer's clock is correct here.
    expect(formatDateTime("2026-09-02T00:00:00Z")).toContain("2026");
  });

  it("reaches the table cell, which is where a reader sees it", () => {
    expect(formatCellValue("2026-09-02")).toBe("Sep 2, 2026");
  });

  it("reads a space-separated timestamp the way it reads the ISO form", () => {
    // The Data Quality worklist sends str(value) from Python: "2026-09-20 00:00:00".
    // `new Date("2026-09-20 00:00:00")` is implementation-defined -- Chrome parses it,
    // Safari returns Invalid Date -- so it rendered raw on one browser and formatted on
    // another. Normalised to the ISO form before parsing.
    // V8 parses the space form too, so the observable fact under test is the
    // normalisation itself, not the browser's parser.
    expect(isoDateTimeString("2026-09-20 00:00:00")).toBe("2026-09-20T00:00:00");
    expect(isoDateTimeString("2026-09-20T13:05:00")).toBe("2026-09-20T13:05:00");
    expect(isoDateTimeString("not a date")).toBe("not a date");
    expect(formatDateTime("2026-09-20 00:00:00")).toBe(formatDateTime("2026-09-20T00:00:00"));
  });

  it("leaves a non-date string alone", () => {
    expect(formatDateTime("not a date")).toBe("not a date");
    expect(formatDateTime(null)).toBe("—");
  });
});
