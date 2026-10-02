import { describe, expect, it } from "vitest";
import { kpiExploreHref, parseCardQuestion } from "./kpiLinks";

/**
 * A KPI card opens the question that produced its number (2026-10-01: all 44 cards opened their
 * data set's bare page, "Choose a standard report", and the number could not be traced).
 */
const question = {
  snapshot_id: "rpt_bill_segment",
  dimensions: [],
  measures: [{ field: "Billed Amount", agg: "sum" }],
  filters: [{ field: "Is Frozen", op: "eq", value: true }, { field: "Bill Date", op: "between", value: ["2025-07-17", "2026-07-17"] }],
  chart_type: "bar",
  all_dates: false,
};

describe("a card links to its own question", () => {
  it("a card with a ready-to-run report still opens that report", () => {
    expect(kpiExploreHref({ snapshot_id: "rpt_bill", explore_report_id: "bills_by_status", explore_question: question }))
      .toBe("/explore/rpt_bill?report=bills_by_status");
  });

  it("otherwise the builder opens on the card's question, and reads it back unchanged", () => {
    const href = kpiExploreHref({ snapshot_id: "rpt_bill_segment", explore_question: question });
    expect(href.startsWith("/build?question=")).toBe(true);
    const back = parseCardQuestion(decodeURIComponent(href.slice("/build?question=".length)));
    expect(back?.snapshot_id).toBe("rpt_bill_segment");
    expect(back?.filters).toEqual(question.filters);
    expect(back?.measures).toEqual(question.measures);
  });

  it("an older API without the question keeps the data set link", () => {
    expect(kpiExploreHref({ snapshot_id: "rpt_bill" })).toBe("/explore/rpt_bill");
  });

  it("a malformed or foreign question is ignored", () => {
    expect(parseCardQuestion("not json")).toBeNull();
    expect(parseCardQuestion(JSON.stringify({ measures: [] }))).toBeNull();
    expect(parseCardQuestion(undefined)).toBeNull();
  });
});
