import { describe, expect, it } from "vitest";
import { barEmphasisRoles } from "./chartEmphasis";

/**
 * Single-series bar emphasis + cross-filter selection, extracted as pure logic from the
 * old ChartView so BuilderChart can absorb it. A single measure across categories does
 * not vary by hue, so the max bar is emphasized and the rest are muted; a cross-filter
 * selection overrides that for the selected category.
 */
describe("barEmphasisRoles", () => {
  const cats = ["A", "B", "C"];

  it("emphasizes the single max bar, mutes the rest", () => {
    expect(barEmphasisRoles(cats, [10, 30, 20])).toEqual(["base", "emphasis", "base"]);
  });

  it("emphasizes all bars tied at the max (matches >= semantics)", () => {
    expect(barEmphasisRoles(cats, [30, 30, 10])).toEqual(["emphasis", "emphasis", "base"]);
  });

  it("marks the selected category as selected, overriding emphasis", () => {
    // B is the max, but A is selected: A=selected, B stays emphasis, C base
    expect(barEmphasisRoles(cats, [10, 30, 20], "A")).toEqual(["selected", "emphasis", "base"]);
  });

  it("selected wins even when the selected bar is also the max", () => {
    expect(barEmphasisRoles(cats, [10, 30, 20], "B")).toEqual(["base", "selected", "base"]);
  });

  it("emphasizes nothing when all values are zero or negative", () => {
    expect(barEmphasisRoles(cats, [0, 0, 0])).toEqual(["base", "base", "base"]);
    expect(barEmphasisRoles(cats, [-5, -2, -9])).toEqual(["base", "base", "base"]);
  });

  it("treats a missing value as zero and never throws on length mismatch", () => {
    expect(barEmphasisRoles(cats, [10, 30])).toEqual(["base", "emphasis", "base"]);
  });

  it("ignores an empty selectedCategory string", () => {
    expect(barEmphasisRoles(cats, [10, 30, 20], "")).toEqual(["base", "emphasis", "base"]);
  });
});
