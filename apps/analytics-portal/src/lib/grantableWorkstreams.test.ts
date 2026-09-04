import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { grantableWorkstreams } from "./grantableWorkstreams";

/**
 * The admin access picker carried its own hardcoded copy of the workstream list, and
 * it drifted: it offered a workstream the catalog did not carry and omitted `assets`,
 * which it did. The backend filters by exact workstream id (workstream_access.py), so
 * both halves were silent -- a group scoped to the phantom granted nothing at all, and
 * no scoped group could ever include Device Asset or Asset Location.
 *
 * Deriving from the catalog is the point. workstream_labels is NOT the source of
 * truth: it can carry a label for a workstream the catalog no longer orders. Only
 * workstream_order says what exists.
 */
const CATALOG_ORDER = [
  "billing",
  "finance",
  "cashiering",
  "debt",
  "customer_ops",
  "meter_ops",
  "assets",
  "field_ops",
  "common",
];

const CATALOG_LABELS: Record<string, string> = {
  assets: "Asset Operations",
  billing: "Billing & Rates",
  cashiering: "Cashiering & Payments",
  common: "Operations & Shared Services",
  customer_ops: "Customer Operations",
  debt: "Collections & Debt",
  field_ops: "Field Operations",
  finance: "Finance",
  meter_ops: "Meter Operations",
  retired_area: "Retired Area",
};

describe("grantableWorkstreams", () => {
  it("offers exactly what the catalog orders, in that order", () => {
    const opts = grantableWorkstreams(CATALOG_ORDER, CATALOG_LABELS);
    expect(opts.map((o) => o.id)).toEqual(CATALOG_ORDER);
  });

  it("makes Asset Operations grantable", () => {
    const opts = grantableWorkstreams(CATALOG_ORDER, CATALOG_LABELS);
    expect(opts.find((o) => o.id === "assets")?.label).toBe("Asset Operations");
  });

  it("drops a labelled workstream the catalog no longer orders", () => {
    const opts = grantableWorkstreams(CATALOG_ORDER, CATALOG_LABELS);
    expect(opts.some((o) => o.id === "retired_area")).toBe(false);
  });

  it("falls back to a readable label rather than printing a raw id", () => {
    const opts = grantableWorkstreams(["meter_ops", "new_thing"], { meter_ops: "Meter Operations" });
    expect(opts).toEqual([
      { id: "meter_ops", label: "Meter Operations" },
      { id: "new_thing", label: "New Thing" },
    ]);
  });

  it("returns nothing when the catalog has not loaded, so the caller can say so", () => {
    // Falling back to a stale built-in list is what caused this bug; an empty list the
    // UI explains is safer than a confident wrong one.
    expect(grantableWorkstreams(undefined, undefined)).toEqual([]);
    expect(grantableWorkstreams([], CATALOG_LABELS)).toEqual([]);
  });

  it("ignores blank ids", () => {
    expect(grantableWorkstreams(["", "billing"], CATALOG_LABELS).map((o) => o.id)).toEqual(["billing"]);
  });
});

describe("AdminAccessPanel", () => {
  const SOURCE = readFileSync(resolve(__dirname, "../components/AdminAccessPanel.tsx"), "utf8");

  it("keeps no second hardcoded copy of the workstream list", () => {
    expect(SOURCE).not.toMatch(/WORKSTREAM_OPTIONS\s*=\s*\[/);
  });

  it("derives its options from the catalog", () => {
    expect(SOURCE).toMatch(/grantableWorkstreams/);
  });
});
