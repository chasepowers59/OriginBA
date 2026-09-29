import { describe, expect, it } from "vitest";
import { reportsByWorkstream, sectionsStartOpen } from "./libraryLayout";
import type { ReportLibraryEntry, ReportLibraryPack } from "./types";

const report = (report_id: string, workstream: string, workstream_label: string): ReportLibraryEntry => ({
  snapshot_id: "rpt_x", snapshot_label: "X", workstream, workstream_label, report_id,
  title: report_id, description: "", chart_type: "bar", explore_url: `/explore/rpt_x?report=${report_id}`,
});
const pack = (id: string, reports: ReportLibraryEntry[]): ReportLibraryPack => ({
  id, title: id, description: "", audience: "", report_count: reports.length, reports,
});

describe("the report library's one grouping", () => {
  it("puts every report under its workstream, in the rail's order, whatever pack carried it", () => {
    const packs = [
      pack("usage_and_billing", [report("a", "billing", "Billing & Rates"), report("b", "meter_ops", "Meter Operations")]),
      pack("financials", [report("c", "finance", "Finance"), report("d", "billing", "Billing & Rates")]),
    ];
    const sections = reportsByWorkstream(packs, ["finance", "billing", "meter_ops"]);
    expect(sections.map((s) => [s.label, s.reports.map((r) => r.report_id)])).toEqual([
      ["Finance", ["c"]],
      ["Billing & Rates", ["a", "d"]],
      ["Meter Operations", ["b"]],
    ]);
  });

  it("keeps a workstream the rail does not list, last, rather than hiding its reports", () => {
    const sections = reportsByWorkstream(
      [pack("p", [report("a", "new_services", "New Services"), report("b", "billing", "Billing & Rates")])],
      ["billing"],
    );
    expect(sections.map((s) => s.workstream)).toEqual(["billing", "new_services"]);
  });

  it("lists a report once when two packs carry it", () => {
    const shared = report("a", "billing", "Billing & Rates");
    expect(reportsByWorkstream([pack("p", [shared]), pack("q", [shared])], ["billing"])[0].reports).toHaveLength(1);
  });
});

describe("report library sections", () => {
  it("start folded when the reader is browsing everything", () => {
    expect(sectionsStartOpen({ query: "", workstream: null, sectionCount: 9 })).toBe(false);
  });

  it("open when the reader has narrowed the list", () => {
    expect(sectionsStartOpen({ query: "arrears", workstream: null, sectionCount: 9 })).toBe(true);
    expect(sectionsStartOpen({ query: " ", workstream: "billing", sectionCount: 9 })).toBe(true);
    expect(sectionsStartOpen({ query: "", workstream: null, sectionCount: 1 })).toBe(true);
  });
});
