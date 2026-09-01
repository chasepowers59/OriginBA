import { describe, expect, it } from "vitest";
import { visualGuardrail } from "./visualGuardrails";

/**
 * UX-backlog fix, tests first: the visual picker allowed a 200-category pie and
 * stacked charts with a single series. Contract: visualGuardrail returns a human
 * reason when a visual can't work for the current data shape, null when it can.
 */
describe("visualGuardrail", () => {
  it("blocks pie beyond the readable slice count", () => {
    expect(visualGuardrail("pie", { categoryCount: 200, seriesCount: 1 })).toMatch(/pie/i);
    expect(visualGuardrail("pie", { categoryCount: 7, seriesCount: 1 })).toBeNull();
  });

  it("blocks stacked visuals with a single series", () => {
    expect(visualGuardrail("stacked-bar", { categoryCount: 5, seriesCount: 1 })).toMatch(
      /stack/i,
    );
    expect(visualGuardrail("stacked-area", { categoryCount: 5, seriesCount: 1 })).toMatch(
      /stack/i,
    );
    expect(visualGuardrail("stacked-bar", { categoryCount: 5, seriesCount: 2 })).toBeNull();
  });

  it("never blocks with unknown data shape (counts of 0)", () => {
    expect(visualGuardrail("pie", { categoryCount: 0, seriesCount: 0 })).toBeNull();
    expect(visualGuardrail("stacked-bar", { categoryCount: 0, seriesCount: 0 })).toBeNull();
  });

  it("leaves plain visuals alone", () => {
    expect(visualGuardrail("bar", { categoryCount: 500, seriesCount: 1 })).toBeNull();
    expect(visualGuardrail("table", { categoryCount: 500, seriesCount: 9 })).toBeNull();
  });
});
