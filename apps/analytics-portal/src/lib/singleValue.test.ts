import { describe, expect, it } from "vitest";
import { singleValue } from "./singleValue";

/**
 * "See where this number comes from" on a Home card opens the builder with the card's
 * question: one measure, no column. The chart layer rightly refuses to draw one bar, but
 * it said "Nothing to compare: one group (Not recorded)" where the reader expected the
 * number (Ellensburg, 2026-10-02). A result with no category and one row IS a number.
 */
describe("singleValue: a one-row result with no category is shown as its number", () => {
  const series = [{ key: "m0", label: "Pay Segment Amount", currency: true }];

  it("formats the one value by its series", () => {
    expect(singleValue({ xKey: "", rows: [{ m0: 4412345.67 }], series })).toEqual({
      values: [{ label: "Pay Segment Amount", text: "$4,412,345.67" }],
    });
    expect(singleValue({ xKey: "", rows: [{ m0: 141231 }], series: [{ key: "m0", label: "Bills" }] })).toEqual({
      values: [{ label: "Bills", text: "141,231" }],
    });
  });

  it("shows every measure of the row", () => {
    const two = [{ key: "m0", label: "Bills" }, { key: "m1", label: "Billed", currency: true }];
    expect(singleValue({ xKey: "", rows: [{ m0: 10, m1: 2500 }], series: two })?.values.map((v) => v.text))
      .toEqual(["10", "$2,500.00"]);
  });

  it("is not for a result with a category, several rows, or no value", () => {
    expect(singleValue({ xKey: "Customer Class", rows: [{ "Customer Class": null, m0: 5 }], series })).toBeNull();
    expect(singleValue({ xKey: "", rows: [{ m0: 1 }, { m0: 2 }], series })).toBeNull();
    expect(singleValue({ xKey: "", rows: [{ m0: null }], series })).toBeNull();
    expect(singleValue({ xKey: "", rows: [], series })).toBeNull();
  });
});
