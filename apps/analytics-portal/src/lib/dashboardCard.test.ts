import { describe, expect, it } from "vitest";
import { tileSummary } from "./dashboardCard";

/**
 * The dashboard list showed "4 tiles · last 180 days" and nothing else, so two boards
 * built from different templates were indistinguishable without opening both. The API
 * already returned every tile's title; the card discarded them.
 */
describe("tileSummary", () => {
  const tiles = (...titles: string[]) => titles.map((title, slot) => ({ title, slot }));

  it("names a single tile", () => {
    expect(tileSummary(tiles("Billed revenue by customer class"))).toBe(
      "Billed revenue by customer class",
    );
  });

  it("names two", () => {
    expect(tileSummary(tiles("Billed revenue", "Top charges"))).toBe(
      "Billed revenue and Top charges",
    );
  });

  it("names the first two and counts the rest, so the card stays one line", () => {
    expect(tileSummary(tiles("A", "B", "C", "D"))).toBe("A, B and 2 more");
  });

  it("says three when there are exactly three", () => {
    expect(tileSummary(tiles("A", "B", "C"))).toBe("A, B and 1 more");
  });

  it("skips a tile with no title rather than printing an empty gap", () => {
    expect(tileSummary([{ title: "A", slot: 0 }, { title: "", slot: 1 }])).toBe("A");
  });

  it("returns empty for an empty board", () => {
    expect(tileSummary([])).toBe("");
    expect(tileSummary(undefined)).toBe("");
  });
});
