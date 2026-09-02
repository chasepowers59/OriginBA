/**
 * Keep text on the accent gradient legible whatever brand colour a client configures.
 *
 * `.btn-primary` / `.brand-logo` paint white on `linear-gradient(--accent, --accent-2)`,
 * and both accents arrive at runtime from the client brand config, so the pair is never
 * reviewed against the foreground. The shipped default put white at 2.50:1 on the light
 * stop. See accentContrast.test.ts for the measurements and why flipping to dark text
 * cannot fix a gradient that crosses the contrast midpoint.
 */

export const PAPER = "#ffffff";
/** --neutral-6, the ink the rest of the app already reads as "text". */
export const INK = "#1b2530";

const AA_NORMAL = 4.5;

function channelToLinear(value: number): number {
  const c = value / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function linearToChannel(linear: number): number {
  const clamped = Math.min(1, Math.max(0, linear));
  const c = clamped <= 0.0031308 ? clamped * 12.92 : 1.055 * clamped ** (1 / 2.4) - 0.055;
  return Math.round(c * 255);
}

function parseHex(hex: string): [number, number, number] {
  const raw = String(hex).trim().replace(/^#/, "");
  const full =
    raw.length === 3
      ? raw
          .split("")
          .map((c) => c + c)
          .join("")
      : raw;
  if (!/^[0-9a-f]{6}$/i.test(full)) return [0, 0, 0];
  return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16)) as [number, number, number];
}

function toHex(rgb: [number, number, number]): string {
  return `#${rgb.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

export function relativeLuminance(hex: string): number {
  const [r, g, b] = parseHex(hex).map(channelToLinear);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrastRatio(a: string, b: string): number {
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

/**
 * Scale a colour in linear light until it hits `targetLuminance`. Luminance is a linear
 * function of linear-RGB, so one multiply lands exactly on the target, and scaling all
 * three channels together holds the chromaticity -- the hue survives, only the level
 * moves. Scaling toward white uses the complement so a pale brand can go paler.
 */
function atLuminance(hex: string, targetLuminance: number): string {
  const linear = parseHex(hex).map(channelToLinear) as [number, number, number];
  const current = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];

  if (targetLuminance <= current) {
    // Darkening. A black source has nothing to scale, so lift it off zero first.
    if (current <= 0) return toHex([0, 0, 0].map(() => linearToChannel(targetLuminance)) as [number, number, number]);
    const scale = targetLuminance / current;
    return toHex(linear.map((c) => linearToChannel(c * scale)) as [number, number, number]);
  }

  // Lightening: interpolate toward white, which raises luminance without clipping a
  // channel that is already at its ceiling.
  const t = (targetLuminance - current) / (1 - current);
  return toHex(linear.map((c) => linearToChannel(c + (1 - c) * t)) as [number, number, number]);
}

/** The luminance a surface needs so `foreground` clears `ratio` against it. */
function surfaceLuminanceFor(foreground: string, ratio: number, darker: boolean): number {
  const lf = relativeLuminance(foreground);
  return darker ? (lf + 0.05) / ratio - 0.05 : ratio * (lf + 0.05) - 0.05;
}

/**
 * CIE L*, so "how far does this stop have to move" is measured perceptually. Raw
 * luminance is the wrong ruler for that question: the same luminance delta is a far
 * bigger visual change near black than near white, and comparing the two foregrounds
 * on raw luminance picked ink for the blue default by 0.01 -- a tie on the numbers
 * that the eye does not see as a tie.
 */
function lightness(luminance: number): number {
  const y = Math.min(1, Math.max(0, luminance));
  return y > 0.008856 ? 116 * y ** (1 / 3) - 16 : 903.3 * y;
}

/** How far, in L*, the worse stop must move for `foreground` to clear AA on both. */
function moveCost(stops: string[], foreground: string, darker: boolean): number {
  const limit = lightness(surfaceLuminanceFor(foreground, AA_NORMAL, darker));
  return stops.reduce((worst, stop) => {
    const current = lightness(relativeLuminance(stop));
    const move = darker ? current - limit : limit - current;
    return Math.max(worst, move);
  }, 0);
}

export type AccentStops = { from: string; to: string; onAccent: string };

/**
 * Constrain a brand's two accent stops so one foreground reads at AA on both, moving
 * each stop only as far as it has to go and leaving a compliant pair alone.
 */
export function readableAccentStops(accentFrom: string, accentTo: string): AccentStops {
  const stops = [accentFrom, accentTo];

  // Prefer white -- it is what the buttons already use and what a blue brand wants.
  // Fall back to ink only when white would mean darkening the brand past recognition,
  // which is the case for yellows and other high-luminance hues.
  const onAccent = moveCost(stops, INK, false) < moveCost(stops, PAPER, true) ? INK : PAPER;
  const darker = onAccent === PAPER;
  const limit = surfaceLuminanceFor(onAccent, AA_NORMAL, darker);

  const [from, to] = stops.map((stop) => {
    const luminance = relativeLuminance(stop);
    if (darker ? luminance <= limit : luminance >= limit) return stop;

    // Aiming at the exact limit can land a hair under it once the channels round to
    // 8 bits (the blue default came out at 4.4975). Step past the target until the
    // colour we will actually emit clears the bar.
    let target = limit;
    let moved = atLuminance(stop, target);
    for (let i = 0; i < 8 && contrastRatio(onAccent, moved) < AA_NORMAL; i += 1) {
      target = darker ? target - 0.004 : target + 0.004;
      moved = atLuminance(stop, target);
    }
    return moved;
  });

  return { from, to, onAccent };
}
