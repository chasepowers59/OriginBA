import { describe, expect, it } from "vitest";
import { measureColumnLabel, withoutRepeatedLeadingWord } from "./businessLabels";
import { isMeasureColumn } from "./resultSummary";

// Six catalog measures already start with "Total" (Total Balance, Total Arrears, Total
// Paid...), so "sum of" + label read "Total Total Balance" in the detail table header.
describe("measure headers never double their prefix", () => {
  it("does not add Total to a measure already named Total", () => {
    expect(measureColumnLabel("Total Balance", "sum", "Total Balance")).toBe("Total balance");
    expect(measureColumnLabel("Billed Amount", "sum", "Billed Amount")).toBe("Total billed amount");
  });

  it("collapses the doubled word the server's label carries", () => {
    expect(withoutRepeatedLeadingWord("Total Total Balance")).toBe("Total Balance");
    expect(withoutRepeatedLeadingWord("Average Average Price Per Unit")).toBe("Average Price Per Unit");
    expect(withoutRepeatedLeadingWord("Total Billed Amount")).toBe("Total Billed Amount");
    expect(withoutRepeatedLeadingWord("Totals Total")).toBe("Totals Total");
  });
});

// The query names aggregates m0, m1... (api/query_builder.py); those are the number
// columns the detail table right-aligns.
describe("isMeasureColumn", () => {
  it("is true for the query's aggregate columns only", () => {
    expect(isMeasureColumn("m0")).toBe(true);
    expect(isMeasureColumn("m12")).toBe(true);
    for (const c of ["Unit of Measure", "TD0", "mode", "m0x"]) expect(isMeasureColumn(c), c).toBe(false);
  });
});
