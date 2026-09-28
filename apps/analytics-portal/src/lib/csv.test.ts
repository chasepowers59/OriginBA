import { describe, expect, it } from "vitest";
import { toCsv } from "./format";

describe("CSV that opens safely in Excel", () => {
  it("quotes commas, quotes and line breaks, and escapes the headers too", () => {
    expect(toCsv(["Name, Full", "Note"], [{ "Name, Full": 'Smith, "J"', Note: "line1\nline2" }]))
      .toBe('"Name, Full",Note\r\n"Smith, ""J""","line1\nline2"');
  });

  it("never lets a cell run as a formula", () => {
    // =, +, -, @ at the start of a cell make Excel evaluate it: a customer name of
    // =HYPERLINK(...) would become a live link in whoever opens the export.
    expect(toCsv(["A"], [{ A: "=HYPERLINK(\"http://x\")" }, { A: "@SUM(1)" }, { A: "+1" }]))
      .toBe('A\r\n"\'=HYPERLINK(""http://x"")"\r\n\'@SUM(1)\r\n\'+1');
  });

  it("leaves real numbers alone, negatives included", () => {
    expect(toCsv(["Amount"], [{ Amount: -1265.5 }, { Amount: 0 }, { Amount: null }])).toBe("Amount\r\n-1265.5\r\n0\r\n");
  });
});
