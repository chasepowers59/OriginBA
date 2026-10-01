import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { isUnitOfMeasureField } from "./businessLabels";
import { TRUNCATED_NOTE, leaderParts, MIXED_UNITS_NOTE, summarizeResult, NOT_ADDITIVE_NOTE, totalRow } from "./resultSummary";

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

describe("the leader sentence names the leader's amount AND the total (2026-10-01)", () => {
  it("never reads as though the leader's amount were the total", () => {
    // was "Water Residential leads this view at 19.8% of the total ($2,886,283.15)", and
    // $2,886,283.15 was Water Residential's amount; the total was $14,606,601.93
    const parts = leaderParts({ label: "Water Residential", share: 19.76, value: 2886283.15 }, 14606601.93,
      (n) => `$${n.toFixed(2)}`, (p) => `${p.toFixed(1)}%`);
    expect(Object.values(parts).join("|")).toBe("Water Residential|$2886283.15|19.8%|$14606601.93");
    expect(`${parts.label} leads this view with ${parts.value}, ${parts.share} of the ${parts.total} total.`)
      .toBe("Water Residential leads this view with $2886283.15, 19.8% of the $14606601.93 total.");
  });
});

describe("one group has no leader (2026-10-01: 'Sewer Residential leads ... 100.0% of the total')", () => {
  it("a single row, e.g. after clicking a bar to cross-filter, is totalled but leads nothing", () => {
    const s = summarizeResult({ columns: ["SA Type", "m0"], rows: [{ "SA Type": "Sewer Residential", m0: 2808607.08 }],
      measureKey: "m0", dimensionKey: "SA Type", measureField: "Billed Amount", measureAgg: "sum" });
    expect(s.total).toBe(2808607.08);
    expect(s.leader).toBeNull();
  });
});

describe("a breakdown cut to its top groups is totalled over every group (2026-10-01)", () => {
  // CityCorp on/off churn: 500 premises summing 1,971 out of 3,591 events in the period
  const top = [{ "Premise Address": "1605 S KNOXVILLE AVE", m0: 12 }, { "Premise Address": "604 E M ST", m0: 11 }];
  const base = { columns: ["Premise Address", "m0"], rows: top, measureKey: "m0", dimensionKey: "Premise Address",
    measureField: "*", measureAgg: "count" };

  it("takes the total from the unbroken answer, and every share from that total", () => {
    const s = summarizeResult({ ...base, grandTotal: 3591 });
    expect(s.total).toBe(3591);
    expect(s.leader?.share).toBeCloseTo((12 / 3591) * 100, 6);
  });

  it("without the unbroken answer, a cut breakdown is not totalled at all", () => {
    const s = summarizeResult({ ...base, truncated: true });
    expect(s.total).toBeNull();
    expect(s.notTotalled).toBe(TRUNCATED_NOTE);
  });
});
