/**
 * Single-series bar colouring (UI-2, 2026-09-29): ONE hue per series. The leader takes
 * the full --chart-1; every other bar is a tint of it, mixed toward the chart surface in
 * proportion to its value, so the leader is emphasised by strength, never by another
 * colour. Red (--over) means a negative value and nothing else: the primary-to-red value
 * ramp this replaces painted small ordinary categories dark red, which read as "bad", and
 * put mauve in the middle of the range.
 *
 * Every fill is a token, so each theme (and print) resolves it in CSS; the tests check
 * the mix against the real globals.css values in both columns.
 */

/** The lightest tint: 2:1 on the card and muted surfaces in both themes (tested). */
export const MIN_STRENGTH = 0.55;
/** The strongest non-leader, one visible lightness step below the leader (tested). */
export const MAX_REST_STRENGTH = 0.8;

const SERIES = "var(--chart-1)";

/**
 * Fills for one series' bars, in order. Ties at the top are all leaders; zero and
 * non-finite values take the lightest tint. A bar in the cross-filter selection leaves
 * the series palette for var(--chart-selected).
 */
export function emphasisFills(values: number[], isSelected?: (index: number) => boolean): string[] {
  const max = Math.max(0, ...values.filter(Number.isFinite));
  return values.map((v, i) => {
    if (isSelected?.(i)) return "var(--chart-selected)";
    if (v < 0) return "var(--over)";
    if (max > 0 && v === max) return SERIES;
    const share = max > 0 && Number.isFinite(v) ? v / max : 0;
    const strength = MIN_STRENGTH + (MAX_REST_STRENGTH - MIN_STRENGTH) * share;
    return `color-mix(in oklab, ${SERIES} ${Math.round(strength * 100)}%, var(--surface))`;
  });
}
