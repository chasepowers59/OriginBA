import { describe, expect, it } from "vitest";
import { folderNames, groupByFolder } from "./folders";
import { savedViewToFavorite } from "./savedViews";

const items = [
  { id: "1", folder: "Month-end close" }, { id: "2", folder: null }, { id: "3", folder: "Collections" },
  { id: "4", folder: "Month-end close" }, { id: "5" },
];

describe("folders", () => {
  it("groups by folder, named folders alphabetically and unfiled last", () => {
    expect(groupByFolder(items).map((g) => [g.folder, g.items.map((i) => i.id)])).toEqual([
      ["Collections", ["3"]], ["Month-end close", ["1", "4"]], [null, ["2", "5"]],
    ]);
  });

  it("lists the folder names in use, for the save box's suggestions", () => {
    expect(folderNames(items)).toEqual(["Collections", "Month-end close"]);
  });

  it("a saved view keeps its folder", () => {
    expect(savedViewToFavorite({ id: "v", client_id: "d", snapshot_id: "s", snapshot_label: "S", title: "t",
                                 kind: "custom", saved_at: "", folder: "Collections" }).folder).toBe("Collections");
  });
});
