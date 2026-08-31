import { describe, expect, it } from "vitest";
import { valueRampColors, RAMP_HIGH_HUE, RAMP_LOW_HUE } from "./chartEmphasis";

/**
 * Value-ramp colouring: the app-wide convention that BLUE is the highest value and bars
 * shift toward RED as values drop. Replaces the old emphasize-max/muted scheme, which
 * read as inconsistent ("some columns dark blue, others faded").
 */
describe("valueRampColors", () => {
  const hueOf = (hsl: string) => Number(hsl.match(/hsl\((-?[\d.]+)/)?.[1]);

  it("gives the max value the blue end and the min value the red end", () => {
    const colors = valueRampColors([10, 40, 25]);
    expect(hueOf(colors[1])).toBe(RAMP_HIGH_HUE); // 40 = highest -> blue
    expect(hueOf(colors[0])).toBe(RAMP_LOW_HUE); // 10 = lowest -> red
  });

  it("interpolates monotonically: higher value -> hue closer to blue", () => {
    const colors = valueRampColors([5, 10, 15, 20]);
    const hues = colors.map(hueOf);
    // The ramp runs blue -> red the warm way round the wheel (through purple/magenta),
    // so hue DEcreases toward the blue endpoint as the value rises.
    for (let i = 1; i < hues.length; i++) expect(hues[i]).toBeLessThan(hues[i - 1]);
  });

  it("never passes through green (no 'good' hues between the endpoints)", () => {
    const hues = valueRampColors([1, 2, 3, 4, 5, 6, 7, 8, 9]).map(hueOf).map((h) => h % 360);
    for (const h of hues) {
      expect(h < 60 || h > 180).toBe(true); // 60-180 = yellow/green band
    }
  });

  it("colours equal values identically (all blue when all equal)", () => {
    const colors = valueRampColors([7, 7, 7]);
    expect(new Set(colors).size).toBe(1);
    expect(hueOf(colors[0])).toBe(RAMP_HIGH_HUE);
  });

  it("a single bar is blue", () => {
    expect(hueOf(valueRampColors([42])[0])).toBe(RAMP_HIGH_HUE);
  });

  it("handles negative values (min still gets the red end)", () => {
    const colors = valueRampColors([-100, 0, 100]);
    expect(hueOf(colors[0])).toBe(RAMP_LOW_HUE);
    expect(hueOf(colors[2])).toBe(RAMP_HIGH_HUE);
  });

  it("treats non-finite values as the minimum, never NaN in output", () => {
    const colors = valueRampColors([NaN, 10]);
    expect(colors.every((c) => /^hsl\(/.test(c))).toBe(true);
    expect(hueOf(colors[1])).toBe(RAMP_HIGH_HUE);
  });
});
