import { describe, expect, it } from "vitest";
import { packsStartOpen } from "./libraryLayout";

describe("report library packs", () => {
  it("start folded when the reader is browsing everything", () => {
    expect(packsStartOpen({ query: "", workstream: null, pack: "all", packCount: 6 })).toBe(false);
  });

  it("open when the reader has narrowed the list", () => {
    expect(packsStartOpen({ query: "arrears", workstream: null, pack: "all", packCount: 6 })).toBe(true);
    expect(packsStartOpen({ query: " ", workstream: "billing", pack: "all", packCount: 6 })).toBe(true);
    expect(packsStartOpen({ query: "", workstream: null, pack: "finance", packCount: 6 })).toBe(true);
    expect(packsStartOpen({ query: "", workstream: null, pack: "all", packCount: 1 })).toBe(true);
  });
});
