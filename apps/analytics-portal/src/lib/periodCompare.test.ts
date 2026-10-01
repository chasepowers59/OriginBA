import { describe, expect, it } from "vitest";
import { canCompare, comparePeriods, priorWindow } from "./periodCompare";

describe("priorWindow", () => {
  it("is the same number of days, ending the day before", () => {
    // 1 April to 30 June is 91 days, so the 91 before end on 31 March and start on 31 December
    expect(priorWindow("2026-04-01", "2026-06-30")).toEqual(["2025-12-31", "2026-03-31"]);
    expect(priorWindow("2026-06-18", "2026-06-18")).toEqual(["2026-06-17", "2026-06-17"]);
  });

  it("crosses a year boundary", () => {
    expect(priorWindow("2026-01-01", "2026-01-31")).toEqual(["2025-12-01", "2025-12-31"]);
  });
});

describe("canCompare", () => {
  const base = { allDates: false, dateField: "Bill Date", measures: [{ field: "Billed Amount", agg: "sum" }] };

  it("compares a windowed total or count", () => {
    expect(canCompare(base)).toBe(true);
    expect(canCompare({ ...base, measures: [{ field: "*", agg: "count" }] })).toBe(true);
  });

  it("never compares all dates, an undated canvas, or a rate or average", () => {
    expect(canCompare({ ...base, allDates: true })).toBe(false);
    expect(canCompare({ ...base, dateField: null })).toBe(false);
    expect(canCompare({ ...base, measures: [{ field: "Estimated Segment", agg: "share" }] })).toBe(false);
    expect(canCompare({ ...base, measures: [{ field: "Days Open", agg: "max" }] })).toBe(false);
  });
});

describe("comparePeriods", () => {
  const now = [{ Cycle: "C1", m0: 120 }, { Cycle: "C2", m0: 50 }, { Cycle: "C4", m0: 10 }];
  const before = [{ Cycle: "C1", m0: 100 }, { Cycle: "C2", m0: 80 }, { Cycle: "C3", m0: 5 }];

  it("totals both periods and their change", () => {
    const c = comparePeriods(now, before, "Cycle", "m0");
    expect(c.total).toEqual({ current: 180, prior: 185, change: -5, pct: (-5 / 185) * 100 });
  });

  it("matches groups across periods, counting a group absent from one as zero there", () => {
    const c = comparePeriods(now, before, "Cycle", "m0");
    const byKey = Object.fromEntries(c.groups.map((g) => [g.key, g]));
    expect(byKey.C3).toEqual({ key: "C3", current: 0, prior: 5, change: -5, pct: -100 });
    expect(byKey.C4).toEqual({ key: "C4", current: 10, prior: 0, change: 10, pct: null });
  });

  it("ranks the movers by the size of the change, either way", () => {
    expect(comparePeriods(now, before, "Cycle", "m0").movers.map((g) => g.key)).toEqual(["C2", "C1", "C4"]);
  });
});
