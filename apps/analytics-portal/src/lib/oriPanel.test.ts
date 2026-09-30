import { describe, expect, it } from "vitest";
import type { OriAnomaly, OriFinding, OriForecast } from "./api";
import { FORECAST_FRAME, forecastRows, investigations, oriPanelShows } from "./oriPanel";

const FINDING: OriFinding = {
  kpi_id: "billed_revenue", change_pct: -17.9,
  headline: "Billed revenue: down 18% vs prior 30d",
  detail: "$3,342,118.20 now, $4,071,002.11 before.",
  question: "Why is billed revenue down?",
};

const ANOMALY: OriAnomaly = {
  kpi_id: "billed_revenue", month: "2026-05", direction: "low",
  headline: "Billed revenue for May 2026: unusually low",
  detail: "$1,212,408.55, below every one of the 12 months before.",
  question: "Why was billed revenue so low in May 2026?",
};

const FORECAST: OriForecast = {
  kpi_id: "billed_revenue", label: "Billed revenue", format: "currency",
  history: [
    { month: "2026-03", value: 4_071_002.11 },
    { month: "2026-04", value: 3_342_118.2 },
  ],
  forecast: [
    { month: "2026-05", value: 4_200_000, low: 3_900_000, high: 4_500_000 },
    { month: "2026-06", value: 4_350_000, low: 3_950_000, high: 4_750_000 },
  ],
  total: 8_550_000, total_low: 7_850_000, total_high: 9_250_000, typical_error_pct: 6.2, checks: 24,
  headline: "Billed revenue: about $8,550,000.00 over May to Jun 2026",
  detail: "Likely between $7,850,000.00 and $9,250,000.00.",
  question: "What is driving the billed revenue projection?",
};

describe("the forecast chart's rows", () => {
  it("the actual months carry the actual value and nothing projected", () => {
    const rows = forecastRows(FORECAST);
    expect(rows.map((r) => r.month)).toEqual(["2026-03", "2026-04", "2026-05", "2026-06"]);
    expect(rows[0]).toEqual({ month: "2026-03", actual: 4_071_002.11 });
  });

  it("the projection grows out of the last actual month, its range starting at no width", () => {
    expect(forecastRows(FORECAST)[1]).toEqual({
      month: "2026-04", actual: 3_342_118.2, projected: 3_342_118.2, range: [3_342_118.2, 3_342_118.2],
    });
  });

  it("the projected months carry the projection and its likely range, never an actual", () => {
    expect(forecastRows(FORECAST).slice(2)).toEqual([
      { month: "2026-05", projected: 4_200_000, range: [3_900_000, 4_500_000] },
      { month: "2026-06", projected: 4_350_000, range: [3_950_000, 4_750_000] },
    ]);
  });

  it("with no projection the actual months stand alone", () => {
    expect(forecastRows({ ...FORECAST, forecast: [] })).toEqual([
      { month: "2026-03", actual: 4_071_002.11 },
      { month: "2026-04", actual: 3_342_118.2 },
    ]);
  });

  it("with no actual months the projection stands alone", () => {
    expect(forecastRows({ ...FORECAST, history: [] }).map((r) => r.actual)).toEqual([undefined, undefined]);
  });
});

describe("what Ori found worth investigating", () => {
  it("lists the moves against the prior period first, then the unusual months", () => {
    expect(investigations([FINDING], [ANOMALY]).map((i) => i.headline)).toEqual([FINDING.headline, ANOMALY.headline]);
  });

  it("keeps each item's question for Ori", () => {
    expect(investigations([FINDING], [ANOMALY]).map((i) => i.question)).toEqual([FINDING.question, ANOMALY.question]);
  });

  it("keys stay unique when one measure has both a move and an unusual month", () => {
    const keys = investigations([FINDING], [ANOMALY, { ...ANOMALY, month: "2026-04" }]).map((i) => i.key);
    expect(new Set(keys).size).toBe(3);
  });
});

describe("whether Ori's panel shows", () => {
  const read = { findings: [] as OriFinding[], brief: null };
  const trends = { through: "2026-05", anomalies: [] as OriAnomaly[], forecasts: [] as OriForecast[] };

  it("waits for the findings, which are fast, before showing anything", () => {
    expect(oriPanelShows(null, null)).toBe(false);
    expect(oriPanelShows(null, { ...trends, forecasts: [FORECAST] })).toBe(false);
  });

  it("shows while the trends are still coming, so Ori can say it is looking", () => {
    expect(oriPanelShows(read, null)).toBe(true);
  });

  it("nothing to say, no panel", () => {
    expect(oriPanelShows(read, trends)).toBe(false);
    expect(oriPanelShows({ findings: [] }, trends)).toBe(false);
    expect(oriPanelShows({ ...read, brief: "   " }, trends)).toBe(false);
  });

  it("any one of the brief, a finding, an unusual month or a projection is enough", () => {
    expect(oriPanelShows({ ...read, brief: "Billed revenue fell 18%." }, trends)).toBe(true);
    expect(oriPanelShows({ ...read, findings: [FINDING] }, trends)).toBe(true);
    expect(oriPanelShows(read, { ...trends, anomalies: [ANOMALY] })).toBe(true);
    expect(oriPanelShows(read, { ...trends, forecasts: [FORECAST] })).toBe(true);
  });
});

describe("the forecast chart's frame", () => {
  // Design review, Ellensburg 1440px: the band ran into the card's right edge, and the
  // lowest value tick ("$2M") sat on the first month label ("Jun 2025").
  it("leaves room right of the last month's band", () => {
    expect(FORECAST_FRAME.margin.right).toBeGreaterThanOrEqual(8);
  });

  it("lifts the lowest value tick off the month labels", () => {
    expect(FORECAST_FRAME.valuePadding.bottom).toBeGreaterThanOrEqual(6);
    expect(FORECAST_FRAME.margin.bottom).toBeGreaterThanOrEqual(4);
  });
});
