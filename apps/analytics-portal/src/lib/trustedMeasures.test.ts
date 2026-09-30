import { describe, expect, it } from "vitest";
import { trustedMeasureSet } from "./trustedMeasures";

/**
 * The data-model panel marks which measures are safe to SUM. It built its lookup with
 * `trustedMeasures.map((m) => m.toUpperCase())` and then tested `has(field.id)` — right
 * while every field id was CISADM's UPPER_SNAKE, and dead for a canvas, whose ids are
 * Title Case. Measured on rpt_financial_txn: five trusted measures, five matching
 * measure fields, and the badge showed on NONE of them.
 *
 * A governance signal that silently stops appearing is worse than one that was never
 * built, so the match is case-insensitive on both sides and both dialects resolve.
 */
describe("trustedMeasureSet", () => {
  it("matches a canvas's Title Case ids", () => {
    const trusted = trustedMeasureSet(["Current Amount", "Pay Segment Amount"]);
    expect(trusted.has("Current Amount")).toBe(true);
    expect(trusted.has("Pay Segment Amount")).toBe(true);
  });

  it("matches CISADM's UPPER_SNAKE ids", () => {
    expect(trustedMeasureSet(["CUR_AMT"]).has("CUR_AMT")).toBe(true);
  });

  it("matches across a case difference in either direction", () => {
    expect(trustedMeasureSet(["CUR_AMT"]).has("cur_amt")).toBe(true);
    expect(trustedMeasureSet(["Current Amount"]).has("CURRENT AMOUNT")).toBe(true);
  });

  it("keeps punctuation and spacing significant", () => {
    const trusted = trustedMeasureSet(["Total Amount (Payoff)"]);
    expect(trusted.has("Total Amount (Payoff)")).toBe(true);
    expect(trusted.has("Total Amount Payoff")).toBe(false);
  });

  it("does not claim an untrusted measure", () => {
    const trusted = trustedMeasureSet(["Current Amount"]);
    expect(trusted.has("Arrears 0-30 Days")).toBe(false);
  });

  it("handles an empty or missing list", () => {
    expect(trustedMeasureSet([]).has("anything")).toBe(false);
    expect(trustedMeasureSet(undefined).has("anything")).toBe(false);
  });
});
