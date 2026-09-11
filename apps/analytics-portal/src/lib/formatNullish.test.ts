import { describe, expect, it } from "vitest";
import {
  formatCurrency,
  formatNumber,
  formatTooltipCurrency,
  formatTooltipNumber,
} from "@/lib/format";

/**
 * A missing value is not zero, and on a finance canvas the difference is the point.
 *
 * formatCurrency and formatNumber both opened with `Number(value)` and only rejected
 * non-finite results. `Number(null)` is 0 and `Number("")` is 0, so a NULL amount
 * rendered as a real "$0" — while `undefined` rendered "—", because `Number(undefined)`
 * is NaN. The inconsistency between null and undefined is the tell that neither was
 * considered.
 *
 * This is reachable, not theoretical: SQL NULL serializes to JSON null, and a SUM over
 * zero matching rows IS null. The backend explicitly models that state —
 * kpi_runner.empty_window_note branches on `value not in (None, 0)` to tell "none
 * happened" apart from "none in the window you chose" — and the formatter then erased
 * the distinction it exists to preserve. A reader seeing "Total Revenue $0" concludes
 * something false about the business; "—" makes them look at the window.
 *
 * formatCellValue already had the guard (`value == null || value === ""` -> "—"), so
 * the convention existed and these two simply did not follow it. 36 call sites between
 * them.
 */

describe("a missing value renders as missing, not as zero", () => {
  it("null is not $0", () => {
    expect(formatCurrency(null)).toBe("—");
    expect(formatNumber(null)).toBe("—");
    expect(formatTooltipNumber(null)).toBe("—");
    // the tooltip twin had the identical defect; a hovered null must not read $0 either
    expect(formatTooltipCurrency(null)).toBe("—");
  });

  it("an empty string is not $0 either", () => {
    expect(formatCurrency("")).toBe("—");
    expect(formatNumber("")).toBe("—");
  });

  it("undefined already behaved, and still does", () => {
    expect(formatCurrency(undefined)).toBe("—");
    expect(formatNumber(undefined)).toBe("—");
  });

  it("a REAL zero is still a real zero", () => {
    // The whole point: this is the value the missing cases must stop impersonating.
    expect(formatCurrency(0)).toBe("$0");
    expect(formatNumber(0)).toBe("0");
    expect(formatCurrency("0")).toBe("$0");
    expect(formatNumber("0")).toBe("0");
  });

  it("ordinary values are untouched", () => {
    expect(formatCurrency(1234)).toBe("$1,234");
    expect(formatCurrency(1234.56)).toBe("$1,234.56");
    expect(formatNumber(1_500_000)).toBe("1.50M");
    expect(formatNumber(1234)).toBe("1.2K");
    expect(formatNumber(42)).toBe("42");
  });

  it("junk still reads as missing rather than as a number", () => {
    expect(formatCurrency("abc")).toBe("—");
    expect(formatNumber("abc")).toBe("—");
  });
});
