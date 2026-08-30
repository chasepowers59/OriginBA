export type BarEmphasis = "selected" | "emphasis" | "base";

/**
 * Per-bar visual role for a single-measure bar chart.
 *
 * A single measure across categories does not vary by hue, so the max bar(s) are
 * emphasized and the rest muted (dataviz: color should encode meaning). A cross-filter
 * selection overrides emphasis for the selected category. Ported from the old ChartView
 * so BuilderChart can be the one renderer; kept pure so it is unit-tested directly.
 */
export function barEmphasisRoles(
  categories: string[],
  values: number[],
  selectedCategory?: string | null,
): BarEmphasis[] {
  const max = values.reduce((m, v) => Math.max(m, Number.isFinite(v) ? v : 0), 0);
  const selected = selectedCategory ? selectedCategory : null;
  return categories.map((category, i) => {
    if (selected !== null && category === selected) return "selected";
    const value = Number.isFinite(values[i]) ? values[i] : 0;
    return value >= max && max > 0 ? "emphasis" : "base";
  });
}
