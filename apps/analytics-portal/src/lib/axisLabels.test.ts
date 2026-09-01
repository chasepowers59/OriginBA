import { describe, expect, it } from "vitest";
import { tickLabels } from "./axisLabels";

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
