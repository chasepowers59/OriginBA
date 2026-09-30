import { describe, expect, it } from "vitest";
import { folderToShow, libraryHref, searchLibrary, shapeLine, splitFolder } from "./libraryLayout";
import type { ReportLibraryEntry, ReportLibraryFolder } from "./types";

const report = (report_id: string, essential: boolean, extra: Partial<ReportLibraryEntry> = {}): ReportLibraryEntry => ({
  snapshot_id: "rpt_x", snapshot_label: "Bill Segment", workstream: "billing", workstream_label: "Billing", report_id,
  title: report_id, description: "", chart_type: "bar", explore_url: `/explore/rpt_x?report=${report_id}`,
  essential, ...extra,
});
const folder = (id: string, reports: ReportLibraryEntry[]): ReportLibraryFolder => ({
  id, title: id, description: `About ${id}`, report_count: reports.length, reports,
});

const LIBRARY = [
  folder("billing", [report("billed", true), report("rebilled", true, { description: "Arrears carried forward" }),
    report("late", false, { dimensions: ["Arrears Band"] })]),
  folder("budget", []),
  folder("usage", [report("reads", true, { snapshot_label: "Meter Read", title: "How good are the reads?" })]),
];

describe("which folder the library shows", () => {
  it("shows the folder the URL names", () => {
    expect(folderToShow(LIBRARY, "usage")?.id).toBe("usage");
  });

  it("defaults to the first folder with reports in it", () => {
    expect(folderToShow(LIBRARY, null)?.id).toBe("billing");
    expect(folderToShow([folder("budget", []), ...LIBRARY.slice(2)], null)?.id).toBe("usage");
  });

  it("falls back to the default for a folder that is unknown or empty, rather than a blank page", () => {
    expect(folderToShow(LIBRARY, "no_such_folder")?.id).toBe("billing");
    expect(folderToShow(LIBRARY, "budget")?.id).toBe("billing");
  });

  it("is null when nothing has reports", () => {
    expect(folderToShow([folder("budget", [])], null)).toBeNull();
  });
});

describe("a folder's two tiers", () => {
  it("puts the essentials first and the rest under 'more', each in catalog order", () => {
    const { essentials, more } = splitFolder(
      folder("f", [report("a", false), report("b", true), report("c", false), report("d", true)]),
    );
    expect(essentials.map((r) => r.report_id)).toEqual(["b", "d"]);
    expect(more.map((r) => r.report_id)).toEqual(["a", "c"]);
  });

  it("has nothing under 'more' when every report is essential", () => {
    expect(splitFolder(LIBRARY[2]).more).toEqual([]);
  });
});

describe("searching the library", () => {
  const ids = (q: string) => searchLibrary(LIBRARY, q).map((g) => [g.folder.id, g.reports.map((r) => r.report_id)]);

  it("searches every folder, not just the one on screen, and groups matches under their folder", () => {
    expect(ids("arrears")).toEqual([["billing", ["rebilled", "late"]]]);
  });

  it("matches the title, the why, the data set and the dimensions, ignoring case", () => {
    expect(ids("GOOD READS")).toEqual([["usage", ["reads"]]]);
    expect(ids("meter read")).toEqual([["usage", ["reads"]]]);
    expect(ids("arrears band")).toEqual([["billing", ["late"]]]);
    expect(ids("bill segment")).toEqual([["billing", ["billed", "rebilled", "late"]]]);
  });

  it("keeps essentials first within a folder's matches", () => {
    const lib = [folder("f", [report("x_more", false), report("x_essential", true)])];
    expect(searchLibrary(lib, "x").map((g) => g.reports.map((r) => r.report_id))).toEqual([["x_essential", "x_more"]]);
  });

  it("returns nothing for a blank query, which means the folder view", () => {
    expect(searchLibrary(LIBRARY, "  ")).toEqual([]);
  });

  it("returns no empty groups", () => {
    expect(ids("nothing matches this")).toEqual([]);
  });
});

describe("a card's shape line", () => {
  it("says what the report groups by and what it measures", () => {
    expect(shapeLine({ dimensions: ["Bill Cycle"], measures: [{ agg: "share", field: "*" }] }))
      .toBe("By Bill Cycle · Share of rows (%)");
    expect(shapeLine({ dimensions: ["SA Type", "Bill Cycle"], measures: [{ agg: "sum", field: "Billed Amount" }] }))
      .toBe("By SA Type and Bill Cycle · Total Billed Amount");
  });

  it("does not repeat the aggregation when the field already names it", () => {
    expect(shapeLine({ dimensions: ["Oldest Debt Band"], measures: [{ agg: "sum", field: "Total Balance" }] }))
      .toBe("By Oldest Debt Band · Total Balance");
  });

  it("counts extra measures rather than listing them", () => {
    expect(shapeLine({ dimensions: [], measures: [{ agg: "count", field: "*" }, { agg: "sum", field: "A" }] }))
      .toBe("Count of records and 1 more");
  });

  it("is empty when the catalog gives no shape", () => {
    expect(shapeLine({})).toBe("");
  });
});

describe("library links", () => {
  it("carry the folder and the search in the URL, so a link and Back restore the view", () => {
    expect(libraryHref({ folder: "billing" })).toBe("/reports?folder=billing");
    expect(libraryHref({ folder: "billing", q: "arrears band" })).toBe("/reports?folder=billing&q=arrears+band");
    expect(libraryHref({ folder: null, q: " " })).toBe("/reports");
  });
});
