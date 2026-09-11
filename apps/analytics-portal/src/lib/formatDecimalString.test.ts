import { describe, expect, it } from "vitest";
import { formatCellValue } from "./format";

/**
 * The API serializes NUMERIC columns as strings at the column's scale: "0.00",
 * "-1265.00", "-1561.11". The round-trip guard (bug class 14) compared String(Number(v))
 * to the string, so "-1561.11" was formatted and "-1265.00" was not: one row preview
 * read "-1,561.11" beside "-1265.00" and "0.00" (rpt_sa_aged_balance, demo25,
 * 2026-09-04). A plain decimal with no leading zero and a safe integer part loses
 * nothing when formatted at its own scale, which is the whole of what the guard exists
 * to protect.
 */
describe("formatCellValue on decimal strings", () => {
  it("formats a trailing-zero decimal at its own scale", () => {
    expect(formatCellValue("-1265.00")).toBe("-1,265.00");
    expect(formatCellValue("0.00")).toBe("0.00");
    expect(formatCellValue("969.87")).toBe("969.87");
    expect(formatCellValue("-1561.11")).toBe("-1,561.11");
  });

  it("still leaves alone what formatting would corrupt", () => {
    expect(formatCellValue("01000123923000000000000")).toBe("01000123923000000000000");
    expect(formatCellValue("9007199254740993")).toBe("9007199254740993");
    expect(formatCellValue("498295347400", { columnId: "Hierarchy Path" })).toBe("498295347400");
    expect(formatCellValue("1.2.3")).toBe("1.2.3");
  });
});
