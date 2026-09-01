/**
 * Guardrails for the visual picker: a reason string when a visual cannot work
 * for the current data shape, null when it can. Unknown shape (count 0 — data
 * not run yet) never blocks: the picker should not fight an empty canvas.
 */
const PIE_MAX_CATEGORIES = 30;

export function visualGuardrail(
  visual: string,
  { categoryCount, seriesCount }: { categoryCount: number; seriesCount: number },
): string | null {
  if (visual === "pie" && categoryCount > PIE_MAX_CATEGORIES) {
    return `A pie with ${categoryCount} slices is unreadable — use horizontal bars for rankings this long.`;
  }
  if ((visual === "stacked-bar" || visual === "stacked-area") && seriesCount === 1) {
    return "Stacking needs two or more series — add another measure or a legend field.";
  }
  return null;
}
