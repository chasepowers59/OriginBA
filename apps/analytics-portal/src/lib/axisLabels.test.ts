import { describe, expect, it } from "vitest";
import { axisTickLines, splitTickLabel, tickLabels } from "./axisLabels";

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

describe("axisTickLines: a whole axis, where no two categories may look alike", () => {
  /**
   * UI-8 (2026-09-29): the explorer cut every tick at 15 characters, so categories sharing
   * a long head rendered identically and the reader could not tell the bars apart. Each
   * label is laid out by splitTickLabel; where two DIFFERENT labels would still render
   * alike, those take a middle ellipsis (the distinguishing ends survive), and as a last
   * resort their whole text. The full label always stays in the tooltip.
   */
  const distinct = (labels: string[], out: string[][]) => {
    const seen = new Map<string, string>();
    out.forEach((lines, i) => {
      const key = lines.join("\n");
      const owner = seen.get(key);
      if (owner !== undefined) expect(owner).toBe(labels[i]);
      seen.set(key, labels[i]);
    });
  };

  it("lays each label out on two whole lines when they fit", () => {
    expect(axisTickLines(["Electric Residential", "Gas Commercial"], 11)).toEqual([
      ["Electric", "Residential"],
      ["Gas", "Commercial"],
    ]);
  });

  it("keeps the distinguishing suffix when a plain cut would collide", () => {
    const labels = ["Wastewater Residential Service", "Wastewater Residential Special"];
    const out = axisTickLines(labels, 11);
    distinct(labels, out);
    expect(out[0][1].endsWith("rvice")).toBe(true);
    expect(out[1][1].endsWith("ecial")).toBe(true);
    for (const lines of out) for (const line of lines) expect(line.length).toBeLessThanOrEqual(11);
  });

  it("does the same on a one-line axis", () => {
    const labels = ["Residential Water", "Residential Waste", "Commercial"];
    const out = axisTickLines(labels, 9, 1);
    distinct(labels, out);
    for (const lines of out) {
      expect(lines).toHaveLength(1);
      expect(lines[0].length).toBeLessThanOrEqual(9);
    }
  });

  it("shows the whole text rather than two identical labels", () => {
    const labels = ["Account 1001 Closed", "Account 1002 Closed"];
    const out = axisTickLines(labels, 6, 1);
    expect(out).toEqual([["Account 1001 Closed"], ["Account 1002 Closed"]]);
  });

  it("lets a repeated category render alike: it IS the same label", () => {
    expect(axisTickLines(["Not recorded", "Not recorded"], 20)).toEqual([
      ["Not recorded"],
      ["Not recorded"],
    ]);
  });

  it("never renders two distinct labels identically, at any budget", () => {
    const labels = [
      "Electric Residential",
      "Electric Residential Low Income",
      "Electric Commercial",
      "Waste Water Residential",
      "Waste Water Commercial",
      "Water Residential",
      "Water Residential Irrigation",
      "Residential",
      "Account 1001 Closed",
      "Account 1002 Closed",
    ];
    for (let budget = 3; budget <= 16; budget++) {
      distinct(labels, axisTickLines(labels, budget, 1));
      distinct(labels, axisTickLines(labels, budget, 2));
    }
  });

  it("does not leave a space in front of the ellipsis", () => {
    expect(axisTickLines(["Customer Class Residential"], 10, 1)).toEqual([["Customer…"]]);
  });
});
