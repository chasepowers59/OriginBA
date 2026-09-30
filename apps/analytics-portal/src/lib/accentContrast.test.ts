import { describe, expect, it } from "vitest";
import { contrastRatio, readableAccentStops, INK, PAPER } from "./accentContrast";

/**
 * `.btn-primary` and `.brand-logo` paint hardcoded white text on
 * `linear-gradient(var(--accent), var(--accent-2))`, and both accents come from the
 * CLIENT brand config at runtime (PortalThemeProvider writes them inline on <html>),
 * so no palette review can vouch for them. Measured on the shipped default
 * (config/analytics_portal_client.json, and the same pair hardcoded in
 * api/portal_config.py):
 *
 *   accent_from #3BAFE2   white 2.50:1  FAIL (AA wants 4.5 for 14px/600)
 *   accent_to   #1348AB   white 8.26:1  pass
 *
 * So the left half of every primary button in the app fails AA today. Swapping to
 * dark text does not rescue it -- ink is 6.21:1 on the light stop but 1.88:1 on the
 * dark one. A gradient that crosses the contrast midpoint carries NO single text
 * colour, which is why this has to be fixed by constraining the stops rather than by
 * picking a better foreground.
 *
 * The rule: keep the brand hue, scale the stop in LINEAR light (luminance is linear
 * there, so one multiply hits the target exactly and chromaticity is preserved) until
 * the chosen foreground clears AA. Decorative accent uses -- mesh glows, shadows,
 * focus rings -- keep the untouched brand colour; only text-bearing surfaces get the
 * constrained pair.
 */
const AA_NORMAL = 4.5;

describe("contrastRatio", () => {
  it("measures the shipped default that fails", () => {
    expect(contrastRatio(PAPER, "#3BAFE2")).toBeCloseTo(2.5, 1);
  });

  it("measures the stylesheet's own accent, which passes", () => {
    // globals.css --accent: var(--primary) = #006fac. The default brand config is the
    // regression; the palette underneath it was fine.
    expect(contrastRatio(PAPER, "#006fac")).toBeCloseTo(5.43, 1);
  });

  it("is symmetric and bounded", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 5);
    expect(contrastRatio("#ffffff", "#000000")).toBeCloseTo(21, 5);
    expect(contrastRatio("#7a8fa0", "#7a8fa0")).toBeCloseTo(1, 5);
  });

  it("reads shorthand hex", () => {
    expect(contrastRatio("#fff", "#000")).toBeCloseTo(21, 5);
  });
});

describe("readableAccentStops", () => {
  it("makes BOTH stops of the shipped default carry its text at AA", () => {
    const { from, to, onAccent } = readableAccentStops("#3BAFE2", "#1348AB");
    expect(contrastRatio(onAccent, from)).toBeGreaterThanOrEqual(AA_NORMAL);
    expect(contrastRatio(onAccent, to)).toBeGreaterThanOrEqual(AA_NORMAL);
  });

  it("keeps white as the foreground for a blue brand rather than flipping to ink", () => {
    // Flipping would fail the dark stop (1.88:1) and would also read as a different
    // product. White is the achievable side for this palette.
    expect(readableAccentStops("#3BAFE2", "#1348AB").onAccent).toBe(PAPER);
  });

  it("leaves a pair that already passes completely untouched", () => {
    const { from, to } = readableAccentStops("#006fac", "#004b86");
    expect(from).toBe("#006fac");
    expect(to).toBe("#004b86");
  });

  it("preserves the hue when it darkens -- a blue stays blue", () => {
    const { from } = readableAccentStops("#3BAFE2", "#1348AB");
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(from.slice(i, i + 2), 16));
    expect(b).toBeGreaterThan(g);
    expect(g).toBeGreaterThan(r);
  });

  it("only ever darkens toward the target, never past it", () => {
    const { from } = readableAccentStops("#3BAFE2", "#1348AB");
    // Landing far below 4.5 would mean throwing away brand colour we did not need to.
    expect(contrastRatio(PAPER, from)).toBeLessThan(AA_NORMAL + 0.35);
  });

  it("fixes the provider's offline fallback pair too", () => {
    const { from, to, onAccent } = readableAccentStops("#38bdf8", "#6366f1");
    expect(contrastRatio(onAccent, from)).toBeGreaterThanOrEqual(AA_NORMAL);
    expect(contrastRatio(onAccent, to)).toBeGreaterThanOrEqual(AA_NORMAL);
  });

  it("chooses ink for a brand too pale for white to ever work", () => {
    // A yellow/amber brand cannot carry white at any brightness without going brown,
    // so the foreground flips instead of the hue being destroyed.
    const { from, to, onAccent } = readableAccentStops("#FFD400", "#FFE873");
    expect(onAccent).toBe(INK);
    expect(contrastRatio(onAccent, from)).toBeGreaterThanOrEqual(AA_NORMAL);
    expect(contrastRatio(onAccent, to)).toBeGreaterThanOrEqual(AA_NORMAL);
  });

  it("survives a malformed brand config instead of blanking the button", () => {
    const { from, to, onAccent } = readableAccentStops("not-a-colour", "");
    expect(contrastRatio(onAccent, from)).toBeGreaterThanOrEqual(AA_NORMAL);
    expect(contrastRatio(onAccent, to)).toBeGreaterThanOrEqual(AA_NORMAL);
  });

  it("handles a pure-black brand without dividing by zero", () => {
    const { from, to, onAccent } = readableAccentStops("#000000", "#000000");
    expect(onAccent).toBe(PAPER);
    expect(contrastRatio(onAccent, from)).toBeGreaterThanOrEqual(AA_NORMAL);
    expect(contrastRatio(onAccent, to)).toBeGreaterThanOrEqual(AA_NORMAL);
  });
});
