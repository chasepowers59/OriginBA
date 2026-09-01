/**
 * Value-ramp anchors, straight from the palette: the top of a measured range is the
 * brand primary and the bottom is the SAME red the suite uses for "over target", so one
 * red means one thing everywhere. Interpolation happens in Oklab — an HSL hue sweep
 * between these two takes the short way round the wheel and lands mid-range values in
 * vivid magenta and violet, which read as a third category rather than a middling value.
 */
export const RAMP_HIGH = "#006FAC"; // --primary (light)
export const RAMP_LOW = "#8B1515"; // --over (light)
export const RAMP_HIGH_DARK = "#6BB2EA";
export const RAMP_LOW_DARK = "#FF998D";

type Oklab = [number, number, number];

function srgbToLinear(c: number): number {
  const x = c / 255;
  return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
}

function linearToSrgb(c: number): number {
  const x = c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055;
  return Math.max(0, Math.min(255, Math.round(x * 255)));
}

function toOklab(hex: string): Oklab {
  const n = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => srgbToLinear(parseInt(n.slice(i, i + 2), 16)));
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ];
}

function fromOklab([L, a, b]: Oklab): string {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const channels = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ].map((c) => linearToSrgb(c).toString(16).padStart(2, "0"));
  return `#${channels.join("")}`;
}

/**
 * App-wide single-series bar colouring: BLUE is the highest value and bars shift toward
 * RED as values drop. Equal values are equal colours — all blue when everything ties.
 * Non-finite values sink to the red end. Cross-filter selection is layered on top by the
 * callers via var(--chart-selected).
 */
export function valueRampColors(values: number[], options?: { dark?: boolean }): string[] {
  const high = toOklab(options?.dark ? RAMP_HIGH_DARK : RAMP_HIGH);
  const low = toOklab(options?.dark ? RAMP_LOW_DARK : RAMP_LOW);

  const clean = values.map((v) => (Number.isFinite(v) ? v : Number.NEGATIVE_INFINITY));
  const finite = clean.filter((v) => v !== Number.NEGATIVE_INFINITY);
  const max = finite.length ? Math.max(...finite) : 0;
  const min = finite.length ? Math.min(...finite) : 0;
  const span = max - min;

  return clean.map((v) => {
    // All equal (or a single bar): everything sits at the blue end.
    const t = span > 0 ? (v === Number.NEGATIVE_INFINITY ? 0 : (v - min) / span) : 1;
    return fromOklab([0, 1, 2].map((i) => low[i] + (high[i] - low[i]) * t) as Oklab);
  });
}
