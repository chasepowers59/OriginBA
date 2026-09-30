import { describe, expect, it } from "vitest";
import { chartedMeasureColumn, kpiHeadline, tileIsUnset } from "./dashboardTileMath";

/**
 * UX-backlog fixes, tests first:
 * - DashboardTile charted the LAST result column but labeled it with measures[0];
 *   a 2-measure premade report labeled one measure with the other's name. The
 *   charted column must be the FIRST measure's column (dimensions come first in
 *   the result, then measures in request order).
 * - The KPI headline summed group values regardless of agg — the SUM of averages
 *   is not an average. Sum only sum/count; a single ungrouped row passes through;
 *   anything else is honestly blank.
 */
describe("chartedMeasureColumn", () => {
  it("picks the first measure's column, not the last column", () => {
    expect(chartedMeasureColumn(["Division", "Billed Amount", "Segment Count"], 2)).toBe(
      "Billed Amount",
    );
  });

  it("handles the single-measure case", () => {
    expect(chartedMeasureColumn(["Division", "Count"], 1)).toBe("Count");
  });

  it("falls back to the last column when the shape is unexpected", () => {
    expect(chartedMeasureColumn(["OnlyColumn"], 3)).toBe("OnlyColumn");
  });
});

describe("kpiHeadline", () => {
  const rows = [
    { Division: "Water", Amount: 10 },
    { Division: "Electric", Amount: 30 },
  ];

  it("sums grouped rows for sum and count aggs", () => {
    expect(kpiHeadline(rows, "Amount", "sum")).toBe(40);
    expect(kpiHeadline(rows, "Amount", "count")).toBe(40);
  });

  it("passes a single ungrouped row through for any agg", () => {
    expect(kpiHeadline([{ Amount: 12.5 }], "Amount", "avg")).toBe(12.5);
    expect(kpiHeadline([{ Amount: 7 }], "Amount", "max")).toBe(7);
  });

  it("refuses to sum grouped avg/min/max", () => {
    expect(kpiHeadline(rows, "Amount", "avg")).toBeNull();
    expect(kpiHeadline(rows, "Amount", "min")).toBeNull();
  });

  it("handles empty results", () => {
    expect(kpiHeadline([], "Amount", "sum")).toBeNull();
  });
});

describe("a tile nobody has set up yet", () => {
  // design review 2026-09-30: a new dashboard opened on a tile reading "Nothing to compare:
  // one group (91114)" -- a chart with no breakdown, drawing its own row count as a category
  const base = { id: "t", slot: 0, title: "New tile", snapshot_id: "rpt_financial_txn" };
  it("is a chart or table with no ready-to-run report and no breakdown", () => {
    expect(tileIsUnset({ ...base, visual: "chart" })).toBe(true);
    expect(tileIsUnset({ ...base, visual: "table", dimensions: [] })).toBe(true);
  });
  it("is set up once it has a breakdown or a report", () => {
    expect(tileIsUnset({ ...base, visual: "chart", dimensions: ["FT Type"] })).toBe(false);
    expect(tileIsUnset({ ...base, visual: "chart", report_id: "by_type" })).toBe(false);
    expect(tileIsUnset({ ...base, visual: "chart", time_grain: "month" })).toBe(false);   // a trend over time
  });
  it("a KPI needs no breakdown: it is one number", () => {
    expect(tileIsUnset({ ...base, visual: "kpi" })).toBe(false);
  });
});
