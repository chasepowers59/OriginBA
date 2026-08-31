/** Value-ramp hue endpoints: blue = highest value, red = lowest. The low end is 368
 *  (≡ 8° red, wrapped past 360) so interpolation runs blue → purple → magenta → red —
 *  the warm way round the wheel — and never passes through green, which would falsely
 *  read as "good" on a BI surface. CSS wraps hues over 360 natively. */
export const RAMP_HIGH_HUE = 207; // Origin blue
export const RAMP_LOW_HUE = 368; // red (8° + 360)

/**
 * App-wide single-series bar colouring: BLUE is the highest value, and bars shift
 * toward RED as values drop (hue interpolated between the endpoints; saturation and
 * lightness held constant so the ramp reads on both themes). Equal values are equal
 * colours — all blue when everything ties. Non-finite values sink to the red end.
 *
 * Replaced the old emphasize-max/muted scheme (2026-08-31), which read as inconsistent
 * ("some columns dark blue, others faded"). Cross-filter selection is layered on top by
 * the callers via var(--chart-selected).
 */
export function valueRampColors(values: number[]): string[] {
  const clean = values.map((v) => (Number.isFinite(v) ? v : Number.NEGATIVE_INFINITY));
  const finite = clean.filter((v) => v !== Number.NEGATIVE_INFINITY);
  const max = finite.length ? Math.max(...finite) : 0;
  const min = finite.length ? Math.min(...finite) : 0;
  const span = max - min;
  return clean.map((v) => {
    // All equal (or a single bar): everything sits at the blue end.
    const t = span > 0 ? (v === Number.NEGATIVE_INFINITY ? 0 : (v - min) / span) : 1;
    // t=1 -> blue (207), t=0 -> red (368 ≡ 8), passing through purple/magenta.
    const hue = RAMP_LOW_HUE + (RAMP_HIGH_HUE - RAMP_LOW_HUE) * t;
    return `hsl(${Math.round(hue * 10) / 10} 62% 51%)`;
  });
}
