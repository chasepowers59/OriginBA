import { describe, expect, it } from "vitest";
import { formatCellValue, isIdentifierColumn } from "@/lib/format";

/**
 * A string that is not a number must not be rendered as one.
 *
 * formatCellValue numeric-formats anything that starts with a digit and parses finite,
 * with `isIdentifierColumn` as the only guard — and that guard is NAME-based, so it
 * only protects columns whose name ends _ID / _NBR / _CD / " Code" / " Number" / _KEY.
 * Measured against every text column in originba_v2_demo25 (958 of them, 430 unmatched
 * by the guard), EIGHT hold leading-zero digit strings and were being corrupted:
 *
 *   rpt_gl."GL Account"                   '01000123923000000000000'
 *   rpt_characteristics."Ad Hoc Value"    '01000125703000000000000'
 *   rpt_characteristics."Value" / "Searchable Value" / "Foreign Key Value"
 *   rpt_asset_location."Hierarchy Path" / "Location Level 1"
 *   rpt_todo."Drill Key Values"
 *
 * "GL Account" is the worst: it is the key field of a FINANCE canvas, it exceeds
 * 2^53, and it rendered as "1,000,123,923,000,000,000,000" — leading zero dropped,
 * separators inserted, and the digits themselves wrong past the float's precision.
 *
 * Adding those names to the guard is whack-a-mole; "GL Account", "Value" and
 * "Hierarchy Path" share no suffix, and the next canvas brings another. The rule
 * instead: a STRING is only formatted as a number when doing so ROUND-TRIPS. That is
 * exactly the set of strings where numeric rendering loses nothing, and it needs no
 * knowledge of column naming.
 *
 * The name guard still earns its place — '1358301387' round-trips, so only the NAME
 * says an Account ID should not wear thousand separators. The two are complementary.
 */

describe("a string is only formatted as a number when that round-trips", () => {
  it("keeps a leading-zero identifier verbatim", () => {
    expect(formatCellValue("052736280362")).toBe("052736280362");
    expect(formatCellValue("038438779964")).toBe("038438779964");
  });

  it("keeps a GL account verbatim, digits and all", () => {
    const gl = "01000123923000000000000";
    expect(formatCellValue(gl, { columnId: "GL Account" })).toBe(gl);
    // the specific corruption this replaces
    expect(formatCellValue(gl, { columnId: "GL Account" })).not.toContain(",");
  });

  it("does not silently lose precision above 2^53", () => {
    const big = "9007199254740993"; // 2^53 + 1, unrepresentable as a double
    expect(formatCellValue(big)).toBe(big);
  });

  it("still formats a plain number string, which loses nothing", () => {
    expect(formatCellValue("1234567", { isMeasure: true })).toBe("1.23M");
    expect(formatCellValue("4210")).toBe("4,210");
  });

  it("still formats real numbers", () => {
    expect(formatCellValue(4210)).toBe("4,210");
    expect(formatCellValue(1234.5)).toBe("1,234.5");
  });

  it("leaves identifiers alone by NAME even when they round-trip", () => {
    // '1358301387' parses and round-trips, so only the column name can save it.
    expect(isIdentifierColumn("Account ID")).toBe(true);
    expect(formatCellValue("1358301387", { columnId: "Account ID" })).toBe("1358301387");
  });

  it("does not disturb the other branches", () => {
    expect(formatCellValue(null)).toBe("—");
    expect(formatCellValue("")).toBe("—");
    expect(formatCellValue(true, { isBoolean: true })).toBe("True");
    expect(formatCellValue("CYCLE1")).toBe("CYCLE1");
    expect(formatCellValue(0)).toBe("0");
  });
});

describe("identifier detection covers names whose shape is not a suffix", () => {
  /**
   * Found by running REAL Ellensburg values through the live formatter, which is the
   * only reason these surfaced — they round-trip, so the round-trip rule above cannot
   * see them, and the suffix rule missed them:
   *
   *   RPT_ASSET_LOCATION."Hierarchy Path"  '498295347400' -> "498,295,347,400"
   *   RPT_TODO."Drill Key Values"          '579558819100' -> "579,558,819,100"
   *
   * Matching whole TOKENS also catches "Adjustment ID (Pay Seg)", a plain identifier
   * the `endsWith(" ID")` rule missed because the name ends in a parenthetical.
   */
  it("treats key and path columns as identifiers", () => {
    for (const col of ["Hierarchy Path", "Drill Key Values", "Foreign Key Value",
                       "Attachment Path", "Adjustment ID (Pay Seg)"]) {
      expect(isIdentifierColumn(col), col).toBe(true);
    }
    expect(formatCellValue("498295347400", { columnId: "Hierarchy Path" }))
      .toBe("498295347400");
    expect(formatCellValue("579558819100", { columnId: "Drill Key Values" }))
      .toBe("579558819100");
  });

  it("does not swallow a COUNT or a FLAG that sits next to the word", () => {
    // "Drill Key Count" is a measure and wants its separators; "Key Required" is a flag.
    expect(isIdentifierColumn("Drill Key Count")).toBe(false);
    expect(isIdentifierColumn("Key Required")).toBe(false);
    expect(formatCellValue("1234", { columnId: "Drill Key Count" })).toBe("1,234");
  });

  it("leaves ordinary measures alone", () => {
    for (const col of ["Billed Amount", "Service Quantity", "Bill Segment Count"]) {
      expect(isIdentifierColumn(col), col).toBe(false);
    }
  });
});
