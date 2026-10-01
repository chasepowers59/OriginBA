import { describe, expect, it } from "vitest";
import { describeFilter, filterDisclosure } from "./filterDisclosure";

describe("describeFilter", () => {
  it("reads a true/false filter as a plain yes or no", () => {
    expect(describeFilter({ field: "Is Frozen", op: "eq", value: true })).toBe("Is Frozen: yes");
    expect(describeFilter({ field: "Is Cancelled", op: "eq", value: false })).toBe("Is Cancelled: no");
  });

  it("reads values, lists and ranges", () => {
    expect(describeFilter({ field: "Payment Status Code", op: "eq", value: "50" })).toBe("Payment Status Code is 50");
    expect(describeFilter({ field: "Service Type", op: "in", value: ["Water", "Sewer"] })).toBe("Service Type is Water or Sewer");
    expect(describeFilter({ field: "Bill Date", op: "between", value: ["2025-06-18", "2026-06-18"] }))
      .toBe("Bill Date from Jun 18, 2025 to Jun 18, 2026");
    expect(describeFilter({ field: "Days Open", op: "gt", value: 90 })).toBe("Days Open over 90");
  });
});

describe("filterDisclosure", () => {
  it("names the window, then the report's own filters, then scope, click-through and row limits", () => {
    expect(filterDisclosure({
      window: { field: "Bill Date", start: "2025-06-18", end: "2026-06-18" },
      reportFilters: [{ field: "Is Frozen", op: "eq", value: true }, { field: "Is Cancelled", op: "eq", value: false }],
      scope: { field: "Service Type", value: "Water" },
      drill: { field: "Bill Cycle", value: "Cycle 5" },
      rowRules: [{ field: "Division", values: ["North"] }],
    })).toEqual([
      "Bill Date from Jun 18, 2025 to Jun 18, 2026",
      "Is Frozen: yes",
      "Is Cancelled: no",
      "Service Type is Water",
      "Bill Cycle is Cycle 5",
      "your access: Division is North",
    ]);
  });

  it("says all dates outright, and nothing at all when nothing is filtered", () => {
    expect(filterDisclosure({ allDates: true })).toEqual(["all dates"]);
    expect(filterDisclosure({})).toEqual([]);
  });
});
