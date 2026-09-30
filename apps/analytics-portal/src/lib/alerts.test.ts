import { describe, expect, it } from "vitest";
import { alertConditions, alertsFor } from "./alerts";

const alerts = [
  { id: "a", kpi_id: "billed", saved_view_id: null },
  { id: "b", kpi_id: null, saved_view_id: "v1" },
  { id: "c", kpi_id: null, saved_view_id: "v2" },
];

describe("alerts", () => {
  it("lists a view's own alerts in its dialog, and KPI alerts on the home dialog", () => {
    expect(alertsFor(alerts, "v1").map((a) => a.id)).toEqual(["b"]);
    expect(alertsFor(alerts, null).map((a) => a.id)).toEqual(["a"]);
  });

  it("offers period-over-period only on KPIs", () => {
    expect(alertConditions(true)).toEqual(["above", "below"]);
    expect(alertConditions(false)).toEqual(["above", "below", "pct_change_above", "pct_change_below"]);
  });
});
