import { describe, expect, it } from "vitest";
import { measureDisplaysAsCurrency, measureIsCurrency } from "@/lib/businessLabels";

/**
 * Money renders as money on BOTH deployment shapes.
 *
 * The test was `upper.includes("AMT") || includes("DEBT") || includes("REVENUE")` —
 * written for CISADM's `_AMT` suffix, and **"AMOUNT" does not contain "AMT"**
 * (A-M-O-U-N-T). So every Title Case money column on the 38 dbt canvases failed it.
 * Measured: of 47 money-ish measures in catalog_dbt, ONE was detected. "Billed Amount",
 * "Charge Amount", "Current Balance", "Total Arrears" all rendered as bare numbers.
 * The legacy shape was hit too, just less — GL_AMOUNT and STATISTIC_AMOUNT also miss,
 * for the same reason.
 *
 * SUBSTRING MATCHING IS THE DEFECT, not just the vocabulary, and widening the
 * substrings reproduces it in the other direction. Three false positives were caught by
 * listing what a wider rule would newly match and reading it, rather than trusting the
 * count:
 *
 *   "Days Unbalanced"            UNBALANCED contains BALANCE — a count of days
 *   "% of Arrears Collected"     a percentage
 *   GOVERNED_ARREARS_FT_COUNT    a count
 *
 * So: whole TOKENS (split on non-alphanumerics, which is what makes BILL_AMT work where
 * a \b regex would not — underscore is a word character), plus an explicit negative set
 * for count/percent/rate. The aged-debt buckets prove the negative set has to be
 * specific rather than lazy: "Arrears 0-30 Days" IS currency, so excluding on "Days"
 * would have been wrong.
 */

describe("measureIsCurrency on both naming worlds", () => {
  it("detects Title Case canvas money", () => {
    for (const id of [
      "Billed Amount", "Charge Amount", "Base Amount", "Current Balance",
      "Total Amount (Payoff)", "Tender Control End Balance", "Total Arrears",
      "Arrears 0-30 Days", "Replacement Cost", "Average Price Per Unit",
    ]) {
      expect(measureIsCurrency(id), id).toBe(true);
    }
  });

  it("still detects legacy CISADM money, suffix form included", () => {
    for (const id of ["ADJ_AMT", "BILL_AMT", "GL_AMOUNT", "STATISTIC_AMOUNT",
                      "PRIMARY_DEP_CTL_END_BALANCE"]) {
      expect(measureIsCurrency(id), id).toBe(true);
    }
  });

  it("is not fooled by a word that merely CONTAINS a money word", () => {
    // The reason this matches tokens rather than substrings.
    expect(measureIsCurrency("Days Unbalanced")).toBe(false);
  });

  it("excludes counts, percentages and rates that sit next to money words", () => {
    expect(measureIsCurrency("% of Arrears Collected")).toBe(false);
    expect(measureIsCurrency("GOVERNED_ARREARS_FT_COUNT")).toBe(false);
    expect(measureIsCurrency("Arrears Collection Rate")).toBe(false);
  });

  it("leaves plainly non-money measures alone", () => {
    for (const id of ["Service Quantity", "Read Quantity", "Bill Segment Count",
                      "Days Since Actual Measurement", "Consecutive Estimated Bills"]) {
      expect(measureIsCurrency(id), id).toBe(false);
    }
  });
});

describe("measureDisplaysAsCurrency layers the aggregate on top", () => {
  it("a COUNT of an amount column is not dollars", () => {
    expect(measureDisplaysAsCurrency("Billed Amount", "count")).toBe(false);
    expect(measureDisplaysAsCurrency("Billed Amount", "count_distinct")).toBe(false);
  });

  it("a SUM or AVG of one is", () => {
    expect(measureDisplaysAsCurrency("Billed Amount", "sum")).toBe(true);
    expect(measureDisplaysAsCurrency("Billed Amount", "avg")).toBe(true);
  });

  it("record count is never dollars", () => {
    expect(measureDisplaysAsCurrency("*", "count")).toBe(false);
    expect(measureDisplaysAsCurrency("*", "sum")).toBe(false);
  });
});
