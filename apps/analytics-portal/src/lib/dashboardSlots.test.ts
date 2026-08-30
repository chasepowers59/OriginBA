import { describe, expect, it } from "vitest";
import { swapTileSlots } from "./dashboardSlots";

/**
 * Pure slot-swap logic for the 2x2 dashboard pinboard, extracted from the old native
 * drag-and-drop handler so it can be unit-tested and reused under @dnd-kit. Dragging a
 * tile onto another slot swaps them; dropping onto an empty slot moves the tile.
 */
type Tile = { slot: number; id: string };
const at = (tiles: Tile[], slot: number) => tiles.find((t) => t.slot === slot)?.id ?? null;

describe("swapTileSlots", () => {
  it("swaps two occupied slots", () => {
    const out = swapTileSlots([{ slot: 0, id: "a" }, { slot: 1, id: "b" }], 0, 1);
    expect(at(out, 0)).toBe("b");
    expect(at(out, 1)).toBe("a");
  });

  it("moves a tile onto an empty slot", () => {
    const out = swapTileSlots([{ slot: 0, id: "a" }], 0, 2);
    expect(at(out, 0)).toBeNull();
    expect(at(out, 2)).toBe("a");
  });

  it("leaves other tiles untouched", () => {
    const out = swapTileSlots(
      [{ slot: 0, id: "a" }, { slot: 1, id: "b" }, { slot: 3, id: "d" }],
      0,
      3,
    );
    expect(at(out, 0)).toBe("d");
    expect(at(out, 3)).toBe("a");
    expect(at(out, 1)).toBe("b");
  });

  it("returns rows sorted by slot", () => {
    const out = swapTileSlots([{ slot: 0, id: "a" }, { slot: 2, id: "c" }], 0, 2);
    expect(out.map((t) => t.slot)).toEqual([0, 2]);
  });

  it("is a no-op when source and target are the same slot", () => {
    const input = [{ slot: 0, id: "a" }, { slot: 1, id: "b" }];
    expect(swapTileSlots(input, 1, 1)).toEqual(input);
  });

  it("is a no-op when the source slot is empty", () => {
    const input = [{ slot: 1, id: "b" }];
    expect(swapTileSlots(input, 0, 1)).toEqual(input);
  });
});
