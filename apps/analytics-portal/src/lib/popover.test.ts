import { describe, expect, it } from "vitest";
import { menuFocusIndex } from "./popover";

// The Export menu is a WAI-ARIA menu: arrows move between items and wrap, Home and End
// jump; every other key is the browser's.
describe("menuFocusIndex", () => {
  it("moves down and up, wrapping at the ends", () => {
    expect(menuFocusIndex("ArrowDown", 0, 3)).toBe(1);
    expect(menuFocusIndex("ArrowDown", 2, 3)).toBe(0);
    expect(menuFocusIndex("ArrowUp", 0, 3)).toBe(2);
    expect(menuFocusIndex("ArrowUp", 2, 3)).toBe(1);
  });

  it("starts from the first or last item when nothing in the menu has focus", () => {
    expect(menuFocusIndex("ArrowDown", -1, 3)).toBe(0);
    expect(menuFocusIndex("ArrowUp", -1, 3)).toBe(2);
  });

  it("jumps with Home and End and ignores other keys", () => {
    expect(menuFocusIndex("Home", 1, 3)).toBe(0);
    expect(menuFocusIndex("End", 1, 3)).toBe(2);
    expect(menuFocusIndex("Enter", 1, 3)).toBeNull();
    expect(menuFocusIndex("ArrowDown", -1, 0)).toBeNull();
  });
});
