import { describe, expect, it } from "vitest";
import { isOrderedAxis, orderChartRows } from "./chartOrder";

/**
 * Categorical charts used to render in whatever order the query happened to return,
 * so the same question drew a different-looking chart on Home, in a dashboard tile and
 * in the builder. Ranked largest-first is the convention for categorical bars; a time
 * axis is the one thing that must NOT be ranked, because reordering a date axis
 * destroys the trend the chart exists to show.
 */
describe("orderChartRows", () => {
  const rows = [
    { name: "Res", amt: 30, other: 1 },
    { name: "Comm", amt: 90, other: 2 },
    { name: "Ind", amt: 60, other: 3 },
  ];

  it("ranks categories largest first", () => {
    const out = orderChartRows(rows, "name", ["amt"], false);
    expect(out.map((r) => r.name)).toEqual(["Comm", "Ind", "Res"]);
  });

  it("leaves a time axis in chronological order", () => {
    const dates = [
      { name: "2026-03", amt: 5 },
      { name: "2026-01", amt: 90 },
      { name: "2026-02", amt: 50 },
    ];
    const out = orderChartRows(dates, "name", ["amt"], true);
    expect(out.map((r) => r.name)).toEqual(["2026-01", "2026-02", "2026-03"]);
  });

  it("ranks a stacked chart by the total of every series, not the first one", () => {
    // 'a' leads on the first measure but 'b' is the taller bar once stacked.
    const stacked = [
      { name: "a", one: 10, two: 1 },
      { name: "b", one: 9, two: 40 },
    ];
    const out = orderChartRows(stacked, "name", ["one", "two"], false);
    expect(out.map((r) => r.name)).toEqual(["b", "a"]);
  });

  it("treats missing and non-numeric values as zero rather than dropping the row", () => {
    const messy = [{ name: "x" }, { name: "y", amt: 4 }, { name: "z", amt: "nope" }];
    const out = orderChartRows(messy, "name", ["amt"], false);
    expect(out[0].name).toBe("y");
    expect(out).toHaveLength(3);
  });

  it("is stable for equal values, so equal bars keep the query's order", () => {
    const tied = [
      { name: "first", amt: 5 },
      { name: "second", amt: 5 },
      { name: "third", amt: 5 },
    ];
    expect(orderChartRows(tied, "name", ["amt"], false).map((r) => r.name)).toEqual([
      "first",
      "second",
      "third",
    ]);
  });

  it("does not mutate the caller's array", () => {
    const original = [...rows];
    orderChartRows(rows, "name", ["amt"], false);
    expect(rows).toEqual(original);
  });

  it("orders an aging band by the band, not by size", () => {
    // Real shape from rpt_sa_aged_balance. Ranked by size this reads
    // None, 0-30, 121+, 31-60 -- the aging story is gone.
    const bands = [
      { name: "None", amt: 153 },
      { name: "0-30", amt: 71 },
      { name: "121+", amt: 59 },
      { name: "31-60", amt: 4 },
    ];
    const out = orderChartRows(bands, "name", ["amt"], true);
    expect(out.map((r) => r.name)).toEqual(["0-30", "31-60", "121+", "None"]);
  });

  it("recognises the axes that carry their own order", () => {
    expect(isOrderedAxis("Oldest Debt Band")).toBe(true);
    expect(isOrderedAxis("Accounting Date")).toBe(true);
    expect(isOrderedAxis("Age Bucket")).toBe(true);
    expect(isOrderedAxis("Bill Month")).toBe(true);
    expect(isOrderedAxis("Customer Class")).toBe(false);
    expect(isOrderedAxis("SA Type")).toBe(false);
    expect(isOrderedAxis(null)).toBe(false);
  });

  it("handles an empty result and a chart with no measures", () => {
    expect(orderChartRows([], "name", ["amt"], false)).toEqual([]);
    expect(orderChartRows(rows, "name", [], false).map((r) => r.name)).toEqual([
      "Res",
      "Comm",
      "Ind",
    ]);
  });
});
