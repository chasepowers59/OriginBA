import { describe, expect, it } from "vitest";
import { splitTickLabel, tickLabels } from "./axisLabels";

/**
 * UX-backlog fix: the sparkline truncated twice (14 chars into the datum, then 8
 * at the tick), so "Residential Water" and "Residential Waste" both rendered
 * "Resident…" — two different bars with one label. Contract: truncate ONCE, and
 * when a plain truncation would collide, keep the ends so the labels stay
 * distinguishable.
 */
describe("tickLabels", () => {
  it("leaves short labels alone", () => {
    expect(tickLabels(["Water", "Gas"], 9)).toEqual(["Water", "Gas"]);
  });

  it("truncates long labels from the end when that is unambiguous", () => {
    expect(tickLabels(["Residential Water", "Commercial Gas"], 9)).toEqual([
      "Residenti…",
      "Commercia…",
    ]);
  });

  it("keeps head and tail when plain truncation would collide", () => {
    const out = tickLabels(["Residential Water", "Residential Waste"], 9);
    expect(new Set(out).size).toBe(2);
    for (const label of out) expect(label.length).toBeLessThanOrEqual(10);
  });

  it("handles empty and single-entry input", () => {
    expect(tickLabels([], 9)).toEqual([]);
    expect(tickLabels(["Residential Water"], 9)).toEqual(["Residenti…"]);
  });
});

describe("splitTickLabel: two lines before any ellipsis", () => {
  /**
   * Utility category names are two words -- "Electric Residential", "Gas Commercial" --
   * and a 9-character single line turned them into "Elec…tial" and "Elec…cial", which
   * a reader cannot tell apart at a glance. Splitting on the first space puts each
   * word on its own line whole; only a word that STILL does not fit is truncated.
   */
  it("puts a two-word label on two whole lines", () => {
    expect(splitTickLabel("Electric Residential", 11)).toEqual(["Electric", "Residential"]);
    expect(splitTickLabel("Gas Commercial", 11)).toEqual(["Gas", "Commercial"]);
  });

  it("keeps a short label on one line", () => {
    expect(splitTickLabel("Frozen", 11)).toEqual(["Frozen"]);
  });

  it("picks the space that lets both lines fit, most balanced first", () => {
    // The first space gave "Waste" / "Water Resi…" -- the ellipsis landed on the
    // distinguishing word when "Waste Water" / "Residential" fits whole.
    expect(splitTickLabel("Waste Water Residential", 11)).toEqual(["Waste Water", "Residential"]);
    expect(splitTickLabel("Non CIS Payments", 11)).toEqual(["Non CIS", "Payments"]);
    expect(splitTickLabel("Non Billed Budget", 14)).toEqual(["Non Billed", "Budget"]);
  });

  it("falls back to the first space when no split fits, so the head word stays whole", () => {
    expect(splitTickLabel("Wastewater Residential Service", 11)).toEqual(["Wastewater", "Residentia…"]);
  });

  it("only truncates a line that still does not fit", () => {
    expect(splitTickLabel("Wastewater Residential", 8)).toEqual(["Wastewa…", "Residen…"]);
  });

  it("never emits an empty line", () => {
    expect(splitTickLabel("  Electric  ", 11)).toEqual(["Electric"]);
    expect(splitTickLabel("", 11)).toEqual([""]);
  });
});
