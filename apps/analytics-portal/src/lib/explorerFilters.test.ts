import { describe, expect, it } from "vitest";
import { canWidenDateRange, explorerPeriodLabel } from "./datePresets";
import { explorerFilters } from "./explorerFilters";

const range = { dateField: "Snapshot Date", dateStart: "2025-06-18", dateEnd: "2026-06-18" };

describe("explorerFilters: the filters the explorer's query sends", () => {
  it("sends no date window at all under All dates", () => {
    const filters = explorerFilters({ ...range, allDates: true });
    expect(filters.some((f) => f.op === "between")).toBe(false);
    expect(filters).toEqual([]);
  });

  it("sends the window otherwise, then the report's, scope and cross-filters", () => {
    expect(explorerFilters({
      ...range, allDates: false,
      reportFilters: [{ field: "SA Status", op: "eq", value: "Active" }],
      scope: { field: "Customer Class", value: "Residential" },
      drill: { field: "SA Type", value: "Electric" },
    })).toEqual([
      { field: "Snapshot Date", op: "between", value: ["2025-06-18", "2026-06-18"] },
      { field: "SA Status", op: "eq", value: "Active" },
      { field: "Customer Class", op: "eq", value: "Residential" },
      { field: "SA Type", op: "eq", value: "Electric" },
    ]);
  });

  it("keeps a report's own filters and the cross-filter under All dates", () => {
    expect(explorerFilters({
      ...range, allDates: true, scope: { field: "Customer Class", value: "" },
      drill: { field: "SA Type", value: "Electric" },
    })).toEqual([{ field: "SA Type", op: "eq", value: "Electric" }]);
  });
});

describe("canWidenDateRange", () => {
  it("offers a wider window only when there is one to widen", () => {
    expect(canWidenDateRange({ allDates: false, dateField: "Bill Date", currentDays: 90 })).toBe(true);
    expect(canWidenDateRange({ allDates: false, dateField: "Bill Date", currentDays: 365 })).toBe(true);
  });

  it("does not offer it under All dates, on a canvas with no date, or at the widest step", () => {
    expect(canWidenDateRange({ allDates: true, dateField: "Bill Date", currentDays: 180 })).toBe(false);
    expect(canWidenDateRange({ allDates: false, dateField: null, currentDays: 180 })).toBe(false);
    expect(canWidenDateRange({ allDates: false, dateField: "Bill Date", currentDays: 730 })).toBe(false);
    // "Widening" a three-year custom range would narrow it to two.
    expect(canWidenDateRange({ allDates: false, dateField: "Bill Date", currentDays: 1095 })).toBe(false);
  });
});

describe("explorerPeriodLabel", () => {
  const asOf = "2026-06-18";

  it("says All dates when no window applied", () => {
    expect(explorerPeriodLabel({ allDates: true, activePreset: "All dates", asOf })).toBe("All dates");
    expect(explorerPeriodLabel({ allDates: true, activePreset: "All dates", fellBackFrom: "Last 12 months", asOf }))
      .toBe("All dates (nothing in last 12 months, as of 18 Jun 2026)");
  });

  it("names the window the server applied instead of claiming All dates", () => {
    expect(explorerPeriodLabel({
      allDates: true, activePreset: "All dates", asOf, appliedWindow: { days: 90 },
    })).toBe("Last 90 days");
  });

  it("names the reader's own window as before", () => {
    expect(explorerPeriodLabel({ allDates: false, activePreset: "Last 12 months", asOf }))
      .toBe("Last 12 months, as of 18 Jun 2026");
  });
});

