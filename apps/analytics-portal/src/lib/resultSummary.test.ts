import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { isUnitOfMeasureField } from "./businessLabels";
import { MIXED_UNITS_NOTE, summarizeResult, NOT_ADDITIVE_NOTE, totalRow } from "./resultSummary";

/**
 * "Billed usage by unit of measure" showed a Combined total of kWh + therms + gallons and
 * "kWh leads this view at 71% of the total". Neither number exists: quantities in
 * different units do not add. Counts and money still do, whatever the breakdown.
 */

const CATALOG = JSON.parse(
  readFileSync(resolve(__dirname, "../../../../output/catalog_dbt.json"), "utf8"),
).snapshots as Record<string, { dimensions: { id: string }[] }>;

describe("isUnitOfMeasureField", () => {
  it("matches exactly the unit columns the catalog offers as a breakdown", () => {
    const hits = new Set<string>();
    for (const canvas of Object.values(CATALOG)) {
      for (const d of canvas.dimensions) if (isUnitOfMeasureField(d.id)) hits.add(d.id);
    }
    expect([...hits].sort()).toEqual([
      "Billed Demand UOM", "Billed Demand UOM Code", "Billed Usage UOM", "Billed Usage UOM Code",
      "Read Quantity UOM", "Read Quantity UOM Code", "Sole UOM", "Sole UOM Code", "UOM Class",
      "Unit of Measure", "Unit of Measure Code",
    ]);
  });

  it("reads raw CISADM names and the other spellings of a unit", () => {
    for (const id of ["UOM_CD", "BILL_UOM_CD", "Measure Unit", "Unit", "Units"]) {
      expect(isUnitOfMeasureField(id), id).toBe(true);
    }
  });

  it("is not fooled by counts of units or money per unit", () => {
    for (const id of ["Distinct UOM Count", "Read UOM Count", "Average Price Per Unit",
                      "Unclassified Unit Charge Amount", "Customer Class"]) {
      expect(isUnitOfMeasureField(id), id).toBe(false);
    }
  });
});

const byUnit = [
  { "Unit of Measure": "kWh", m0: 700 },
  { "Unit of Measure": "Therms", m0: 200 },
  { "Unit of Measure": "Gallons", m0: 100 },
];
const base = { columns: ["Unit of Measure", "m0"], measureKey: "m0", dimensionKey: "Unit of Measure" };

describe("summarizeResult", () => {
  it("totals and ranks an ordinary breakdown", () => {
    const s = summarizeResult({
      ...base, columns: ["Customer Class", "m0"], dimensionKey: "Customer Class",
      rows: [{ "Customer Class": "Residential", m0: 75 }, { "Customer Class": "Commercial", m0: 25 }],
      measureField: "Billed Quantity", measureAgg: "sum",
    });
    expect(s.total).toBe(100);
    expect(s.leader).toEqual({ label: "Residential", share: 75, value: 75 });
    expect(s.notTotalled).toBeNull();
  });

  it("does not add quantities in different units, and says why", () => {
    const s = summarizeResult({ ...base, rows: byUnit, measureField: "Billed Quantity", measureAgg: "sum" });
    expect(s.total).toBeNull();
    expect(s.leader).toBeNull();
    expect(s.notTotalled).toBe(MIXED_UNITS_NOTE);
    expect(MIXED_UNITS_NOTE).toBe("Not totalled: the rows are in different units.");
  });

  it("finds the unit column by its label when the id is not a name", () => {
    const s = summarizeResult({
      ...base, columns: ["UOM_CD", "m0"], dimensionKey: "UOM_CD", labels: { UOM_CD: "Unit of Measure" },
      rows: byUnit.map((r) => ({ UOM_CD: r["Unit of Measure"], m0: r.m0 })),
      measureField: "Billed Quantity", measureAgg: "sum",
    });
    expect(s.notTotalled).toBe(MIXED_UNITS_NOTE);
  });

  it("still totals counts and money broken down by unit", () => {
    expect(summarizeResult({ ...base, rows: byUnit, measureField: "*", measureAgg: "count" }).total).toBe(1000);
    expect(summarizeResult({ ...base, rows: byUnit, measureField: "Billed Amount", measureAgg: "sum" }).total).toBe(1000);
  });

  it("totals when every row is in the same unit (a unit cross-filter)", () => {
    const s = summarizeResult({
      ...base, columns: ["Unit of Measure", "Customer Class", "m0"], dimensionKey: "Customer Class",
      rows: [
        { "Unit of Measure": "kWh", "Customer Class": "Residential", m0: 60 },
        { "Unit of Measure": "kWh", "Customer Class": "Commercial", m0: 40 },
      ],
      measureField: "Billed Quantity", measureAgg: "sum",
    });
    expect(s.total).toBe(100);
    expect(s.notTotalled).toBeNull();
  });

  it("names no leader when the total is not positive", () => {
    const s = summarizeResult({
      ...base, columns: ["Customer Class", "m0"], dimensionKey: "Customer Class",
      rows: [{ "Customer Class": "A", m0: 0 }], measureField: "*", measureAgg: "count",
    });
    expect(s.leader).toBeNull();
  });
});

describe("only sums and counts add across groups", () => {
  const rows = [{ d: "A", m0: 10 }, { d: "B", m0: 30 }];
  const base = { columns: ["d", "m0"], rows, measureKey: "m0", dimensionKey: "d", measureField: "Days Open" };

  it("a sum or count totals, with the leader's share", () => {
    expect(summarizeResult({ ...base, measureAgg: "sum" }).total).toBe(40);
    expect(summarizeResult({ ...base, measureField: "*", measureAgg: "count" }).leader?.share).toBe(75);
  });

  it("an average, distinct count, highest or lowest value is not totalled, and says why", () => {
    for (const agg of ["avg", "count_distinct", "max", "min"]) {
      const out = summarizeResult({ ...base, measureAgg: agg });
      expect(out.total).toBeNull();
      expect(out.leader).toBeNull();
      expect(out.notTotalled).toBe(NOT_ADDITIVE_NOTE);
    }
  });
});

describe("the detail table's total row", () => {
  // design review 2026-09-29: a finance lead reconciles to a total, and the table showed
  // 9 of 64 SA types with none
  it("labels the first column and totals the measure", () => {
    expect(totalRow(["d0", "d1", "m0"], "m0", 1234.5)).toEqual(["Total", null, 1234.5]);
  });
  it("puts the label in the first non-measure column even when the measure leads", () => {
    expect(totalRow(["m0", "d0"], "m0", 10)).toEqual([10, "Total"]);
  });
  it("has no row when the result is not totalled", () => {
    expect(totalRow(["d0", "m0"], "m0", null)).toBeNull();
    expect(totalRow(["d0", "m0"], "", 5)).toBeNull();
  });
});
