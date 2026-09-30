import { describe, expect, it } from "vitest";
import { dashboardPdfSections, kpiSections } from "./dashboardPdf";

const tile = (name: string, n: number) => ({
  name,
  headers: ["Category", "Value"],
  rows: Array.from({ length: n }, (_, i) => ({ Category: `c${i}`, Value: i })),
});

describe("dashboard PDF sections", () => {
  it("sends each tile as a titled table", () => {
    expect(dashboardPdfSections([tile("Billed revenue", 2)])).toEqual([
      { title: "Billed revenue", note: "", columns: ["Category", "Value"], rows: [{ Category: "c0", Value: 0 }, { Category: "c1", Value: 1 }], failed: false },
    ]);
  });

  it("keeps within the server's limits: 12 tiles and 5,000 rows in all", () => {
    const out = dashboardPdfSections(Array.from({ length: 14 }, (_, i) => tile(`t${i}`, 600)));
    expect(out).toHaveLength(12);
    expect(out.reduce((n, s) => n + s.rows.length, 0)).toBeLessThanOrEqual(5000);
    expect(out[0].rows).toHaveLength(600);
  });

  it("says so when the row budget cuts a tile short", () => {
    const out = dashboardPdfSections(Array.from({ length: 10 }, (_, i) => tile(`t${i}`, 600)));
    expect(out[0].note).toBe("");
    expect(out[8].rows).toHaveLength(200);
    expect(out[8].note).toBe("Showing the first 200 of 600 rows (truncated)");
    expect(out[9].note).toBe("Showing the first 0 of 600 rows (truncated)");
    expect(dashboardPdfSections([{ ...tile("t", 5001), note: "Last 30 days" }])[0].note)
      .toBe("Last 30 days · Showing the first 5,000 of 5,001 rows (truncated)");
  });

  it("leaves out a tile with no columns, which the server would refuse", () => {
    expect(dashboardPdfSections([{ name: "empty", headers: [], rows: [] }, tile("ok", 1)]).map((s) => s.title)).toEqual(["ok"]);
  });
});

describe("KPI sections", () => {
  const kpi = {
    id: "billed", label: "Billed revenue", subtitle: "Charges on frozen bill segments", snapshot_id: "rpt_bill_segment",
    format: "currency" as const, workstream: "billing", value: 236.18, change_pct: 12.5, compare_label: "vs August",
    trend: [{ label: "Electric Residential", value: 236.18 }],
  };

  it("carries the headline value and its meaning above the breakdown", () => {
    const [s] = kpiSections([kpi]);
    expect(s.name).toBe("Billed revenue");
    expect(s.note).toBe("$236.18 · Charges on frozen bill segments · +12.5% vs August");
    expect(s.rows).toEqual([{ Category: "Electric Residential", Value: 236.18 }]);
  });

  it("says a card that failed could not load, never 'No value'", () => {
    const [s] = kpiSections([{
      ...kpi, value: null, change_pct: null, trend: [],
      error: 'Query failed: relation "reporting.rpt_bill_segment" does not exist\nLINE 1: SELECT "SA Type"',
    }]);
    expect(s.note).toBe('This card could not load: Query failed: relation "reporting.rpt_bill_segment" does not exist');
  });

  it("keeps a long error to a line", () => {
    const [s] = kpiSections([{ ...kpi, value: null, trend: [], error: "x".repeat(400) }]);
    expect(s.note?.length).toBeLessThanOrEqual(160);
    expect(s.note).toMatch(/…$/);
  });

  it("says when a card has no value instead of printing zero", () => {
    expect(kpiSections([{ ...kpi, value: null, change_pct: null }])[0].note).toBe("No value · Charges on frozen bill segments");
  });
});

describe("failed cards in the PDF", () => {
  it("are marked failed so the server does not print \"No rows\" under them", () => {
    const failed = { id: "x", label: "Payments", subtitle: "", snapshot_id: "rpt_payment", format: "number" as const,
      workstream: "cashiering", value: null, trend: [], error: "could not connect" };
    const [section] = kpiSections([failed]);
    expect(section.failed).toBe(true);
    expect(dashboardPdfSections([section])[0].failed).toBe(true);
  });
});
