import { describe, expect, it } from "vitest";
import { defaultDateRange, defaultDateRangeLastMonth, defaultDateRangeYtd } from "./api";
import { anchoredLabel, applyDatePresetConfig, widenDateRange } from "./datePresets";

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
    expect(anchoredLabel("Last 6 months", asOf)).toBe("Last 6 months, as of 18 Jun 2026");
    expect(anchoredLabel("Last 6 months", null)).toBe("Last 6 months");
    expect(anchoredLabel("Custom range", asOf)).toBe("Custom range");
  });

  it("widening keeps the anchor", () => {
    expect(widenDateRange(90, asOf).range).toEqual(["2025-12-20", "2026-06-18"]);
  });
});
