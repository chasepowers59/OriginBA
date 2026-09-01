import { describe, expect, it } from "vitest";
import { valueRampColors, RAMP_HIGH, RAMP_LOW } from "./chartEmphasis";

/**
 * Value-ramp colouring: the app-wide convention that BLUE is the highest value and bars
 * shift toward RED as values drop.
 *
 * Rewritten for Soul Palette V2.1. The old ramp swept HUE in HSL, which took the short
 * way round the wheel and rendered mid-range values as vivid magenta (#CF34C6) and
 * violet — colours that exist nowhere in the palette and read as a third category.
 * The ramp now interpolates in Oklab between two PALETTE tokens (primary → over red),
 * so every step stays low-chroma and in-family.
 */
describe("valueRampColors", () => {
  const rgb = (c: string) => {
    const m = c.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
    if (!m) throw new Error(`not a hex colour: ${c}`);
    return [1, 2, 3].map((i) => parseInt(m[i], 16)) as [number, number, number];
  };
  /** How vivid the colour is (HSV saturation), 0..1. */
  const chroma = (c: string) => {
    const [r, g, b] = rgb(c);
    const mx = Math.max(r, g, b);
    return mx === 0 ? 0 : (mx - Math.min(r, g, b)) / mx;
  };
  const hue = (c: string) => {
    const [r, g, b] = rgb(c).map((v) => v / 255);
    const mx = Math.max(r, g, b);
    const d = mx - Math.min(r, g, b);
    if (d === 0) return null;
    const h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return (((h * 60) % 360) + 360) % 360;
  };

  it("gives the max value the blue end and the min value the red end", () => {
    const colors = valueRampColors([10, 40, 25]);
    expect(colors[1].toLowerCase()).toBe(RAMP_HIGH.toLowerCase());
    expect(colors[0].toLowerCase()).toBe(RAMP_LOW.toLowerCase());
  });

  it("never renders a vivid magenta or violet mid-step", () => {
    // The old ramp's failure mode: hue 250-340 at high chroma. Any step in that band
    // must be muted enough to read as a middling value, not a third category.
    for (const c of valueRampColors([1, 2, 3, 4, 5, 6, 7, 8, 9])) {
      const h = hue(c);
      if (h !== null && h > 250 && h < 340) expect(chroma(c)).toBeLessThan(0.35);
    }
  });

  it("stays out of the green and yellow band entirely", () => {
    for (const c of valueRampColors([1, 2, 3, 4, 5, 6, 7])) {
      const h = hue(c);
      if (h !== null) expect(h < 60 || h > 180).toBe(true);
    }
  });

  it("gets redder as the value falls, monotonically", () => {
    const colors = valueRampColors([5, 10, 15, 20]);
    const redness = colors.map((c) => {
      const [r, , b] = rgb(c);
      return r - b;
    });
    for (let i = 1; i < redness.length; i++) {
      expect(redness[i]).toBeLessThan(redness[i - 1]);
    }
  });

  it("colours equal values identically (all blue when all equal)", () => {
    const colors = valueRampColors([7, 7, 7]);
    expect(new Set(colors).size).toBe(1);
    expect(colors[0].toLowerCase()).toBe(RAMP_HIGH.toLowerCase());
  });

  it("a single bar is blue", () => {
    expect(valueRampColors([42])[0].toLowerCase()).toBe(RAMP_HIGH.toLowerCase());
  });

  it("handles negative values (min still gets the red end)", () => {
    const colors = valueRampColors([-100, 0, 100]);
    expect(colors[0].toLowerCase()).toBe(RAMP_LOW.toLowerCase());
    expect(colors[2].toLowerCase()).toBe(RAMP_HIGH.toLowerCase());
  });

  it("treats non-finite values as the minimum, never NaN in output", () => {
    const colors = valueRampColors([NaN, 10]);
    expect(colors.every((c) => /^#[0-9a-f]{6}$/i.test(c))).toBe(true);
    expect(colors[1].toLowerCase()).toBe(RAMP_HIGH.toLowerCase());
  });

  it("emits the dark-theme anchors when asked", () => {
    const colors = valueRampColors([1, 5], { dark: true });
    expect(colors[1].toLowerCase()).toBe("#6bb2ea");
    expect(colors[0].toLowerCase()).toBe("#ff998d");
  });
});
