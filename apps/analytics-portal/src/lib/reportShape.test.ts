import { describe, expect, it } from "vitest";
import { reportShape } from "./reportShape";

/**
 * A library card showed a title and a paragraph and never said what the report actually
 * RETURNS. "How many accounts, by customer class?" reads well, but the reader still has
 * to open it to learn whether it counts accounts or sums a balance, what it groups by,
 * and whether a filter is already applied. The catalog knows all three — the library API
 * was dropping them.
 */
describe("reportShape", () => {
  it("describes a count with one grouping", () => {
    expect(
      reportShape({
        measures: [{ field: "*", agg: "count" }],
        dimensions: ["Customer Class"],
      }),
    ).toBe("Count of records by Customer Class");
  });

  it("names the measure when it is not a plain row count", () => {
    expect(
      reportShape({
        measures: [{ field: "Current Amount", agg: "sum" }],
        dimensions: ["SA Type"],
      }),
    ).toBe("Total Current Amount by SA Type");
  });

  it("joins two groupings readably and keeps their order", () => {
    expect(
      reportShape({
        measures: [{ field: "*", agg: "count" }],
        dimensions: ["Bill Cycle", "Customer Class"],
      }),
    ).toBe("Count of records by Bill Cycle and Customer Class");
  });

  it("lists three or more groupings with commas", () => {
    const out = reportShape({
      measures: [{ field: "*", agg: "count" }],
      dimensions: ["A", "B", "C"],
    });
    expect(out).toBe("Count of records by A, B and C");
  });

  it("says so when the report is already filtered", () => {
    expect(
      reportShape({
        measures: [{ field: "*", agg: "count" }],
        dimensions: ["SA Type"],
        filters: [{ field: "SA Status Code", op: "in", value: ["20"] }],
      }),
    ).toBe("Count of records by SA Type, filtered on SA Status Code");
  });

  it("names both filters when there are two", () => {
    const out = reportShape({
      measures: [{ field: "*", agg: "count" }],
      dimensions: [],
      filters: [
        { field: "Is Frozen", op: "eq", value: true },
        { field: "Is Bill Segment", op: "eq", value: true },
      ],
    });
    expect(out).toBe("Count of records, filtered on Is Frozen and Is Bill Segment");
  });

  it("handles a measure with no grouping", () => {
    expect(reportShape({ measures: [{ field: "*", agg: "count" }], dimensions: [] })).toBe(
      "Count of records",
    );
  });

  it("summarises several measures without listing all of them", () => {
    expect(
      reportShape({
        measures: [
          { field: "Current Amount", agg: "sum" },
          { field: "*", agg: "count" },
        ],
        dimensions: ["SA Type"],
      }),
    ).toBe("Total Current Amount and 1 more by SA Type");
  });

  it("returns empty rather than a broken sentence when the catalog says nothing", () => {
    expect(reportShape({})).toBe("");
    expect(reportShape({ measures: [], dimensions: [] })).toBe("");
  });
});
