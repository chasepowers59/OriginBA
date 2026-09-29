import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { emphasisFills, MAX_REST_STRENGTH, MIN_STRENGTH } from "./chartEmphasis";

/**
 * Single-series bar colouring (UI-2, 2026-09-29): one hue per series, the leader
 * emphasised by STRENGTH of that hue, red only for negatives. It replaces the
 * primary-to-red value ramp, which painted small ordinary categories dark red (read as
 * "bad") and mid-range bars mauve.
 */
describe("emphasisFills", () => {
  const TINT = /^color-mix\(in oklab, var\(--chart-1\) (\d+)%, var\(--surface\)\)$/;
  /** 1 for the full series hue, the mix share for a tint, null for anything else. */
  const strength = (fill: string) => {
    if (fill === "var(--chart-1)") return 1;
    const m = fill.match(TINT);
    return m ? Number(m[1]) / 100 : null;
  };

  it("gives the leader the full series hue and every other bar a lighter tint", () => {
    const fills = emphasisFills([10, 40, 25]);
    expect(fills[1]).toBe("var(--chart-1)");
    for (const i of [0, 2]) expect(strength(fills[i])).toBeLessThan(1);
  });

  it("strengthens as the value rises, with a visible step up to the leader", () => {
    const s = emphasisFills([5, 10, 15, 20, 40]).map(strength) as number[];
    for (let i = 1; i < s.length; i++) expect(s[i]).toBeGreaterThan(s[i - 1]);
    expect(s[3]).toBeLessThanOrEqual(MAX_REST_STRENGTH);
    expect(s[4]).toBe(1);
  });

  it("uses no colour but the series hue for zero and positive values", () => {
    for (const fill of emphasisFills([0, 1, 2, 3, 50, 1000])) expect(strength(fill)).not.toBeNull();
  });

  it("keeps zero in the series hue at the lightest strength, never red", () => {
    const fills = emphasisFills([0, 30]);
    expect(strength(fills[0])).toBe(MIN_STRENGTH);
    expect(emphasisFills([0, 0]).map(strength)).toEqual([MIN_STRENGTH, MIN_STRENGTH]);
  });

  it("paints negative values, and only negative values, with the over token", () => {
    const fills = emphasisFills([-100, -0.5, 0, 100]);
    expect(fills.slice(0, 2)).toEqual(["var(--over)", "var(--over)"]);
    expect(strength(fills[2])).toBe(MIN_STRENGTH);
    expect(fills[3]).toBe("var(--chart-1)");
  });

  it("makes every tied top value a leader (a single bar is a leader)", () => {
    expect(emphasisFills([7, 7, 7])).toEqual(Array(3).fill("var(--chart-1)"));
    expect(emphasisFills([42])).toEqual(["var(--chart-1)"]);
  });

  it("treats a non-finite value as the lightest strength of the series hue", () => {
    const fills = emphasisFills([Number.NaN, 10]);
    expect(strength(fills[0])).toBe(MIN_STRENGTH);
    expect(fills[1]).toBe("var(--chart-1)");
  });

  it("keeps the cross-filter selection on --chart-selected and leaves the rest alone", () => {
    const values = [10, 40, -5];
    const plain = emphasisFills(values);
    for (const i of [0, 1, 2]) {
      const fills = emphasisFills(values, (j) => j === i);
      expect(fills[i]).toBe("var(--chart-selected)");
      fills.forEach((f, j) => j !== i && expect(f).toBe(plain[j]));
    }
    expect(plain).not.toContain("var(--chart-selected)");
  });
});

/**
 * The fills are tokens, so each theme's colours are decided by globals.css. These checks
 * resolve the real tokens (no hand-kept copy to drift) and do the mix CSS does.
 */
describe("emphasisFills against the palette tokens", () => {
  const css = readFileSync(resolve(__dirname, "../app/globals.css"), "utf8");
  const block = (selector: RegExp) => {
    const body = css.match(selector)?.[1] ?? "";
    return new Map([...body.matchAll(/--([\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
  };
  const light = block(/^:root\s*\{([^}]*)\}/m);
  const dark = block(/^\.dark\s*\{([^}]*)\}/m);
  const token = (theme: Map<string, string>, name: string): string => {
    const value = theme.get(name) ?? light.get(name);
    const ref = value?.match(/^var\(--([\w-]+)\)$/);
    if (ref) return token(theme, ref[1]);
    if (!value || !/^#[0-9a-f]{6}$/i.test(value)) throw new Error(`--${name} is not a hex colour: ${value}`);
    return value;
  };

  const channels = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const toLinear = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const toOklab = (hex: string) => {
    const [r, g, b] = channels(hex).map(toLinear);
    const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [
      0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
      1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
      0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
    ];
  };
  const fromOklab = ([L, a, b]: number[]) => {
    const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
    const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
    const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
    return `#${[
      4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
      -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
      -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
    ]
      .map((c) => {
        const x = c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055;
        return Math.round(Math.max(0, Math.min(1, x)) * 255).toString(16).padStart(2, "0");
      })
      .join("")}`;
  };
  const mix = (a: string, b: string, share: number) => {
    const [x, y] = [toOklab(a), toOklab(b)];
    return fromOklab(x.map((v, i) => v * share + y[i] * (1 - share)));
  };
  const luminance = (hex: string) => {
    const [r, g, b] = channels(hex).map(toLinear);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const contrast = (a: string, b: string) => {
    const [hi, lo] = [luminance(a), luminance(b)].sort((p, q) => q - p);
    return (hi + 0.05) / (lo + 0.05);
  };
  const hue = (hex: string) => {
    const [r, g, b] = channels(hex);
    const mx = Math.max(r, g, b);
    const d = mx - Math.min(r, g, b);
    const h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return (h * 60 + 360) % 360;
  };

  for (const [name, theme] of [["light", light], ["dark", dark]] as const) {
    const series = token(theme, "chart-1");
    const surface = token(theme, "surface");
    const steps = [MIN_STRENGTH, (MIN_STRENGTH + MAX_REST_STRENGTH) / 2, MAX_REST_STRENGTH];

    it(`${name}: every tint stays the series hue (no mauve, no magenta)`, () => {
      for (const s of steps) expect(Math.abs(hue(mix(series, surface, s)) - hue(series))).toBeLessThan(12);
    });

    it(`${name}: the lightest bar still clears 2:1 on the card and muted surfaces`, () => {
      const lightest = mix(series, surface, MIN_STRENGTH);
      for (const ground of ["card", "muted"]) {
        expect(contrast(lightest, token(theme, ground))).toBeGreaterThanOrEqual(2);
      }
    });

    it(`${name}: the leader stands a visible lightness step above the strongest other bar`, () => {
      const step = Math.abs(toOklab(series)[0] - toOklab(mix(series, surface, MAX_REST_STRENGTH))[0]);
      expect(step).toBeGreaterThanOrEqual(0.06);
    });
  }
});
