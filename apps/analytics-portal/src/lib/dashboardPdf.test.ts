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
      { title: "Billed revenue", note: "", columns: ["Category", "Value"], rows: [{ Category: "c0", Value: 0 }, { Category: "c1", Value: 1 }] },
    ]);
  });

  it("keeps within the server's limits: 12 tiles and 5,000 rows in all", () => {
    const out = dashboardPdfSections(Array.from({ length: 14 }, (_, i) => tile(`t${i}`, 600)));
    expect(out).toHaveLength(12);
    expect(out.reduce((n, s) => n + s.rows.length, 0)).toBeLessThanOrEqual(5000);
    expect(out[0].rows).toHaveLength(600);
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

  it("says when a card has no value instead of printing zero", () => {
    expect(kpiSections([{ ...kpi, value: null, change_pct: null }])[0].note).toBe("No value · Charges on frozen bill segments");
  });
});
