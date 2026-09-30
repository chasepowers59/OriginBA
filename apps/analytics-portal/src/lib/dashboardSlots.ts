/**
 * Swap (or move) a dashboard tile between two grid slots.
 *
 * Dragging the tile at `fromSlot` onto `toSlot` swaps the two; if the target slot is
 * empty the tile simply moves there. A no-op when the slots are equal or the source is
 * empty. Pure so it is unit-tested directly and reused under @dnd-kit. Returns a new
 * array sorted by slot.
 */
export function swapTileSlots<T extends { slot: number }>(
  tiles: T[],
  fromSlot: number,
  toSlot: number,
): T[] {
  if (fromSlot === toSlot) return tiles;
  const a = tiles.find((t) => t.slot === fromSlot);
  if (!a) return tiles;
  const b = tiles.find((t) => t.slot === toSlot);
  const next = tiles.filter((t) => t.slot !== fromSlot && t.slot !== toSlot);
  next.push({ ...a, slot: toSlot });
  if (b) next.push({ ...b, slot: fromSlot });
  return next.sort((x, y) => x.slot - y.slot);
}

/** Tiles per dashboard; the API enforces the same number (api/saved_dashboards.py MAX_TILES). */
export const MAX_TILES = 8;

export const ALL_SLOTS = Array.from({ length: MAX_TILES }, (_, i) => i);

/** The cells the grid shows: every filled slot, and the first empty one to add the next tile. */
export function visibleSlots(filled: number[]): number[] {
  const used = new Set(filled);
  const next = ALL_SLOTS.find((s) => !used.has(s));
  return ALL_SLOTS.filter((s) => used.has(s) || s === next);
}
