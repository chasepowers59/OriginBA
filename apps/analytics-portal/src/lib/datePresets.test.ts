import { describe, expect, it } from "vitest";
import { defaultDateRange, defaultDateRangeLastMonth, defaultDateRangeYtd } from "./api";
import { anchoredLabel, applyDatePresetConfig, fallBackToAllDates, opensOnAllDates, widenDateRange, windowFilter } from "./datePresets";

// A frozen copy declares where its data ends (Ellensburg TEST: 18 Jun 2026). The explorer's
// presets were computed from the browser's today, so "Last 6 months" there read mostly the
// empty tail after the copy stopped. Every helper takes the org's anchor when there is one.

describe("anchored date ranges", () => {
  const asOf = "2026-06-18";

  it("a trailing range ends at the anchor", () => {
    expect(defaultDateRange(90, asOf)).toEqual(["2026-03-20", "2026-06-18"]);
  });

  it("year to date and last month read from the anchor's calendar", () => {
    expect(defaultDateRangeYtd(asOf)).toEqual(["2026-01-01", "2026-06-18"]);
    expect(defaultDateRangeLastMonth(asOf)).toEqual(["2026-05-01", "2026-05-31"]);
  });

  it("with no anchor, a range still ends today", () => {
    const [, end] = defaultDateRange(30);
    expect(end).toBe(defaultDateRange(30, null)[1]);
    expect(new Date(end).getFullYear()).toBe(new Date().getFullYear());
  });

  it("a preset ends at the anchor and keeps the chip's plain label", () => {
    const { range, label } = applyDatePresetConfig({ kind: "days", days: 180, label: "Last 6 months" }, asOf);
    expect(range).toEqual(["2025-12-20", "2026-06-18"]);
    expect(label).toBe("Last 6 months");
  });

  it("the period a reader sees names the date an anchored window is measured from", () => {
    expect(anchoredLabel("Last 6 months", asOf)).toBe("Last 6 months, as of Jun 18, 2026");
    expect(anchoredLabel("Last 6 months", null)).toBe("Last 6 months");
    expect(anchoredLabel("Custom range", asOf)).toBe("Custom range");
  });

  it("widening keeps the anchor", () => {
    expect(widenDateRange(90, asOf).range).toEqual(["2025-12-20", "2026-06-18"]);
  });
});

describe("all dates", () => {
  it("sends no window when the reader chose all dates", () => {
    expect(windowFilter("Bill Date", true, "2026-01-01", "2026-06-18")).toEqual([]);
  });

  it("sends the window otherwise, and none on a canvas with no date", () => {
    expect(windowFilter("Bill Date", false, "2026-01-01", "2026-06-18"))
      .toEqual([{ field: "Bill Date", op: "between", value: ["2026-01-01", "2026-06-18"] }]);
    expect(windowFilter(null, false, "2026-01-01", "2026-06-18")).toEqual([]);
  });

  // Rate Configuration dates each row by when its rate version took effect -- 2010 on
  // the demo org -- so a 180-day window showed "No data for this view" over 305 rows.
  it("falls back to all dates once, when the opening window is empty", () => {
    expect(fallBackToAllDates({ rowCount: 0, windowed: true, firstRun: true })).toBe(true);
    expect(fallBackToAllDates({ rowCount: 0, windowed: true, firstRun: false })).toBe(false);
    expect(fallBackToAllDates({ rowCount: 12, windowed: true, firstRun: true })).toBe(false);
    expect(fallBackToAllDates({ rowCount: 0, windowed: false, firstRun: true })).toBe(false);
  });
});

// A backlog question ("what has not yet reached the ledger?") asks about everything still
// open, however old; under the default 12 months Ellensburg showed $207.74 of $187,957.69
// pending. Such a report declares all_dates and opens on All dates when it is picked; the
// reader can still narrow it afterwards.
describe("opensOnAllDates", () => {
  const backlog = { id: "gl_not_extracted", all_dates: true };
  const base = { report: backlog, activeReportId: null, allDates: false, hasDateField: true };

  it("a backlog report opens on All dates when it is picked", () => {
    expect(opensOnAllDates(base)).toBe(true);
    expect(opensOnAllDates({ ...base, activeReportId: "gl_by_account" })).toBe(true);
  });

  it("re-running the open report keeps the reader's window", () => {
    expect(opensOnAllDates({ ...base, activeReportId: "gl_not_extracted" })).toBe(false);
  });

  it("nothing to do when already on All dates or the canvas has no date", () => {
    expect(opensOnAllDates({ ...base, allDates: true })).toBe(false);
    expect(opensOnAllDates({ ...base, hasDateField: false })).toBe(false);
  });

  it("an ordinary report keeps the window", () => {
    expect(opensOnAllDates({ ...base, report: { id: "gl_by_account" } })).toBe(false);
  });
});
