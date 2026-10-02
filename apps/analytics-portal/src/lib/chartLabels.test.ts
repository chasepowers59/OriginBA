import { describe, expect, it } from "vitest";
import { categoryLabel } from "./chartLabels";

/**
 * A chart category is a business value, rendered like a table cell. BuilderChart used
 * String(value ?? "—"), so a boolean dimension -- "Service off but installed" by
 * "Installed But Switched Off" -- drew bars labelled "true" and "false" while the
 * table beside it said True / False (demo25, 2026-09-04).
 */
describe("categoryLabel", () => {
  it("renders a boolean as a state, like the table", () => {
    expect(categoryLabel(true)).toBe("True");
    expect(categoryLabel(false)).toBe("False");
  });
  // UI-15: a dash in a legend or on an axis reads as a glitch, not as a group of rows.
  it("names a missing category in plain words, not a dash", () => {
    expect(categoryLabel(null)).toBe("Not recorded");
    expect(categoryLabel(undefined)).toBe("Not recorded");
    expect(categoryLabel("")).toBe("Not recorded");
  });
  it("leaves text and numbers as they are", () => {
    expect(categoryLabel("Residential")).toBe("Residential");
    expect(categoryLabel(2026)).toBe("2026");
  });
});

import { tickText } from "./chartLabels";

describe("tickText: a time-axis tick is kept short, except the one that must say more", () => {
  it("cuts a long tick to fifteen characters and an ellipsis", () => {
    expect(tickText("Electric Commercial (Demand)")).toBe("Electric Commer…");
    expect(tickText("Jun 2026")).toBe("Jun 2026");
  });

  it("a cut-short bucket's tick is shown whole: it is what the chart is saying", () => {
    expect(tickText("Jun 2026 (to Jun 2, 2026)", { whole: true })).toBe("Jun 2026 (to Jun 2, 2026)");
  });
});
