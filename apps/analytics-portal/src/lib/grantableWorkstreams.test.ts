import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { grantableWorkstreams } from "./grantableWorkstreams";

/**
 * The admin access picker carried its own hardcoded copy of the workstream list, and
 * it had drifted from the catalog in BOTH directions. Measured against the live
 * catalog (api.snapshot_catalog.load_catalog) on 2026-09-02:
 *
 *   workstream_order  billing finance cashiering debt customer_ops meter_ops
 *                     assets field_ops common          <- 9, authoritative
 *   picker offered    ... new_services ...              <- phantom, 0 canvases
 *   picker omitted    assets                            <- 2 canvases, ungrantable
 *
 * The backend filters by exact workstream id (workstream_access.py), so both halves
 * are silent: a group scoped to "New Services" grants nothing at all, and no group
 * scoped to specific workstreams could ever include Device Asset or Asset Location.
 * That is the access-grant half of making assets its own data set.
 *
 * workstream_labels is NOT the source of truth -- it still carries a new_services
 * label. Only workstream_order says what exists.
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
  new_services: "New Services",
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
    expect(opts.some((o) => o.id === "new_services")).toBe(false);
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
    expect(SOURCE).not.toMatch(/new_services/);
    expect(SOURCE).not.toMatch(/WORKSTREAM_OPTIONS\s*=\s*\[/);
  });

  it("derives its options from the catalog", () => {
    expect(SOURCE).toMatch(/grantableWorkstreams/);
  });
});
