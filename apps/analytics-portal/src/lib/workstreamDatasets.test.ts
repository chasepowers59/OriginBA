import { describe, expect, it } from "vitest";
import { groupByDataset, WORKSTREAM_DATASETS } from "./workstreamDatasets";
import type { WorkstreamGroup } from "./types";

/**
 * C2M is two systems and a asset register, and utility people think in those terms:
 * the C side (CCB — customers, bills, money), the M side (MDM — meters, usage, the
 * field work that feeds it) and the shared plumbing. The rail listed nine workstreams
 * flat, so that shape was invisible.
 *
 * The split is evidence-based, from what each workstream's canvases actually read:
 * billing/cashiering/customer_ops/debt/finance are ci_* (CCB); meter_ops is d1_* plus
 * the w1_* asset tables; field_ops is d1_* activities; common is ci_* shared services.
 */
describe("workstream data sets", () => {
  const ws = (id: string) =>
    ({ id, label: id, snapshot_count: 1, snapshots: [], processes: [] }) as unknown as WorkstreamGroup;

  it("puts the money-and-customer workstreams on the C side", () => {
    const groups = groupByDataset([ws("billing"), ws("cashiering"), ws("debt"), ws("finance")]);
    expect(groups).toHaveLength(1);
    expect(groups[0].id).toBe("customer");
    expect(groups[0].workstreams.map((w) => w.id)).toEqual([
      "billing",
      "cashiering",
      "debt",
      "finance",
    ]);
  });

  it("puts metering and the field work that feeds it on the M side", () => {
    const groups = groupByDataset([ws("meter_ops"), ws("field_ops")]);
    expect(groups[0].id).toBe("metering");
    expect(groups[0].workstreams.map((w) => w.id)).toEqual(["meter_ops", "field_ops"]);
  });

  it("gives asset operations its own data set, separate from metering", () => {
    const groups = groupByDataset([ws("meter_ops"), ws("assets")]);
    expect(groups.map((g) => g.id)).toEqual(["metering", "assets"]);
    expect(groups[1].workstreams.map((w) => w.id)).toEqual(["assets"]);
  });

  it("keeps the data sets in a stable reading order, C side first", () => {
    const groups = groupByDataset([ws("common"), ws("meter_ops"), ws("billing")]);
    expect(groups.map((g) => g.id)).toEqual(["customer", "metering", "shared"]);
  });

  it("orders the data sets C side, M side, assets, shared", () => {
    const all = groupByDataset([ws("common"), ws("assets"), ws("meter_ops"), ws("billing")]);
    expect(all.map((g) => g.id)).toEqual(["customer", "metering", "assets", "shared"]);
  });

  it("omits a data set with nothing in it", () => {
    const groups = groupByDataset([ws("billing")]);
    expect(groups.map((g) => g.id)).toEqual(["customer"]);
  });

  it("never silently drops an unrecognised workstream", () => {
    // A new workstream must still be reachable, not vanish from the rail.
    const groups = groupByDataset([ws("brand_new_thing")]);
    expect(groups.flatMap((g) => g.workstreams.map((w) => w.id))).toContain("brand_new_thing");
  });

  it("every declared workstream has a data set", () => {
    const assigned = new Set(WORKSTREAM_DATASETS.flatMap((d) => d.workstreamIds));
    for (const id of [
      "billing",
      "cashiering",
      "common",
      "customer_ops",
      "debt",
      "field_ops",
      "finance",
      "meter_ops",
      "new_services",
      "assets",
    ]) {
      expect(assigned.has(id)).toBe(true);
    }
  });

  it("assigns each workstream to exactly one data set", () => {
    const all = WORKSTREAM_DATASETS.flatMap((d) => d.workstreamIds);
    expect(all.length).toBe(new Set(all).size);
  });
});
