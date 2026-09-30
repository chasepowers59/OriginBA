import { describe, expect, it } from "vitest";
import type { ReportLibraryEntry, ReportLibraryFolder } from "@/lib/types";
import { MAX_TILES } from "./dashboardSlots";
import { folderDashboard } from "./folderDashboard";

const report = (id: string, extra: Partial<ReportLibraryEntry> = {}): ReportLibraryEntry => ({
  snapshot_id: "rpt_customer_account",
  snapshot_label: "Customer accounts",
  workstream: "customer",
  workstream_label: "Customer",
  report_id: id,
  title: `Report ${id}`,
  description: "",
  chart_type: "bar",
  explore_url: `/explore/rpt_customer_account?report=${id}`,
  ...extra,
});

const folder = (reports: ReportLibraryEntry[]): ReportLibraryFolder => ({
  id: "budget_billing",
  title: "Budget Billing",
  description: "Who is on a budget plan and what it bills.",
  report_count: reports.length,
  reports,
});

describe("folderDashboard", () => {
  it("names the board after the folder and lays the essentials out in order", () => {
    const board = folderDashboard(folder([
      report("a", { essential: true }), report("b", { essential: true }), report("c"),
      report("d"), report("e"),
    ]));
    expect(board.title).toBe("Budget Billing");
    expect(board.description).toBe("Who is on a budget plan and what it bills.");
    expect(board.tiles.map((t) => [t.slot, t.report_id])).toEqual([
      [0, "a"], [1, "b"], [2, "c"], [3, "d"],
    ]);
  });

  it("each tile runs its report, as a chart of the report's own kind", () => {
    const [tile] = folderDashboard(folder([report("a", { essential: true, chart_type: "line",
      title: "Budget amount by month", snapshot_id: "rpt_financial_txn" })])).tiles;
    expect(tile).toEqual({ slot: 0, title: "Budget amount by month", visual: "chart",
      snapshot_id: "rpt_financial_txn", report_id: "a", chart_type: "line" });
  });

  it("keeps every essential up to the grid, and tops a thin folder up to four", () => {
    const many = Array.from({ length: 10 }, (_, i) => report(String(i), { essential: i < 6 }));
    expect(folderDashboard(folder(many)).tiles).toHaveLength(6);
    const all = Array.from({ length: 12 }, (_, i) => report(String(i), { essential: true }));
    expect(folderDashboard(folder(all)).tiles).toHaveLength(MAX_TILES);
    expect(folderDashboard(folder([report("x")])).tiles).toHaveLength(1);
  });
});
