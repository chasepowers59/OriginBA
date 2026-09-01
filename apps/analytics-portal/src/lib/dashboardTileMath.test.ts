import { describe, expect, it } from "vitest";
import { chartedMeasureColumn, kpiHeadline } from "./dashboardTileMath";

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
