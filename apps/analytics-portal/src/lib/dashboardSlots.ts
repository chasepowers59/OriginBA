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
