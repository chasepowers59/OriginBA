import { describe, expect, it } from "vitest";
import { suggestChart } from "./databaseChartUtils";

/**
 * UX-backlog fix: suggestChart used to take the first ≥60%-numeric column as the
 * measure — ACCT_ID qualified, producing bars of summed account ids. Contract:
 * identifier columns are never measures NOR dimensions-by-default when a better
 * column exists, and the dimension pick samples more than one row.
 */
describe("suggestChart", () => {
  const rows = (n: number, make: (i: number) => Record<string, unknown>) =>
    Array.from({ length: n }, (_, i) => make(i));

  it("never picks an identifier column as the measure", () => {
    const data = rows(10, (i) => ({
      TENDER_TYPE: `T${i % 3}`,
      ACCT_ID: 1358301000 + i,
      TOTAL_AMT: 100 + i,
    }));
    const s = suggestChart(["TENDER_TYPE", "ACCT_ID", "TOTAL_AMT"], data);
    expect(s?.measureKey).toBe("TOTAL_AMT");
  });

  it("returns null rather than charting only identifiers", () => {
    const data = rows(5, (i) => ({ ACCT_ID: 100 + i, SA_ID: 200 + i }));
    expect(suggestChart(["ACCT_ID", "SA_ID"], data)).toBeNull();
  });

  it("prefers a non-identifier dimension when one exists", () => {
    const data = rows(6, (i) => ({
      BSEG_ID: `9${i}`, // string id — old logic grabbed it as the dimension
      "Customer Class": `Class ${i % 2}`,
      "Billed Amount": 50 + i,
    }));
    const s = suggestChart(["BSEG_ID", "Customer Class", "Billed Amount"], data);
    expect(s?.dimensionKey).toBe("Customer Class");
    expect(s?.measureKey).toBe("Billed Amount");
  });

  it("samples beyond the first row for the dimension", () => {
    // first row's category is null; the old single-row sample skipped the column
    const data = [
      { "Bill Cycle": null, Segments: 5 },
      { "Bill Cycle": "CYCLE1", Segments: 7 },
      { "Bill Cycle": "CYCLE2", Segments: 9 },
    ];
    const s = suggestChart(["Bill Cycle", "Segments"], data);
    expect(s?.dimensionKey).toBe("Bill Cycle");
  });

  it("still detects time series and currency", () => {
    const data = rows(6, (i) => ({
      BILL_MONTH: `2026-0${i + 1}-01`,
      CALC_AMT: 1000 + i,
    }));
    const s = suggestChart(["BILL_MONTH", "CALC_AMT"], data);
    expect(s?.chartType).toBe("line");
    expect(s?.isCurrency).toBe(true);
    expect(s?.sortTimeSeries).toBe(true);
  });
});
