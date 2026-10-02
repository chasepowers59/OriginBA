import { describe, expect, it } from "vitest";
import { groupMetrics } from "./nlqMetrics";
import type { NlqMetricCatalogItem } from "./types";

/**
 * The vetted-metric form on Home (folded under Ori) showed a free-text box, a disabled
 * Run button and no way to see the 31 metrics it answers (2026-10-02): the catalogue chips
 * only rendered in the full panel. A grouped picker lists them wherever the form is.
 */
const item = (id: string, category: string, label = id): NlqMetricCatalogItem =>
  ({ id, label, category, snapshot_id: "rpt_x", default_days: 90, format: "number", param_keys: ["days"], example: `Example ${id}` }) as NlqMetricCatalogItem;

describe("groupMetrics: the catalogue by category, in the order the API lists it", () => {
  it("keeps category order and item order", () => {
    const groups = groupMetrics([item("a", "Customers"), item("b", "Billing"), item("c", "Customers")]);
    expect(groups.map((g) => g.category)).toEqual(["Customers", "Billing"]);
    expect(groups[0].items.map((m) => m.id)).toEqual(["a", "c"]);
  });

  it("is empty for an empty catalogue", () => {
    expect(groupMetrics([])).toEqual([]);
  });
});
