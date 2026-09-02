import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  WORKSTREAM_ORDER,
  WORKSTREAM_LABELS,
  WORKSTREAM_DESCRIPTIONS,
  workstreamDisplayName,
} from "./businessLabels";
import { WORKSTREAM_ICONS } from "./workstreamIcons";

/**
 * These maps are a hand-kept copy of the catalog's workstreams, and they had drifted:
 * the list was a snapshot of the LEGACY catalog and was never updated when the dbt
 * catalog gained `assets`. Measured 2026-09-02 from the committed catalogs:
 *
 *   output/catalog_dbt.json      billing finance cashiering debt customer_ops
 *                                meter_ops ASSETS field_ops common   (38 canvases,
 *                                assets: 2, no new_services)
 *   output/catalog_cisadm.json   finance billing meter_ops cashiering debt
 *                                customer_ops NEW_SERVICES field_ops common
 *                                (19 canvases, new_services: 1, no assets)
 *
 * So neither id is a phantom -- each is real in one deployment shape and absent in the
 * other, and this file, being a shape-independent fallback, has to carry the UNION.
 * Carrying only the legacy nine had a hard consequence: app/workstream/[workstreamId]
 * calls notFound() for any id not in WORKSTREAM_ORDER, so /workstream/assets was a 404
 * while /workstream/new_services rendered a full dashboard -- exactly inverted for the
 * three dbt orgs.
 *
 * Pinned against the catalog files themselves rather than a list retyped here, because
 * a hand-kept list is the thing that broke.
 */
const ROOT = resolve(__dirname, "../../../..");

function catalogWorkstreams(name: string): string[] {
  const raw = readFileSync(resolve(ROOT, "output", name), "utf8");
  return JSON.parse(raw).workstream_order as string[];
}

const DBT = catalogWorkstreams("catalog_dbt.json");
const CISADM = catalogWorkstreams("catalog_cisadm.json");
const UNION = [...new Set([...DBT, ...CISADM])];

describe("workstream label coverage", () => {
  it("reads both catalogs, so this test fails if either is regenerated differently", () => {
    expect(DBT.length).toBeGreaterThan(0);
    expect(CISADM.length).toBeGreaterThan(0);
  });

  it("covers every workstream in the dbt catalog", () => {
    for (const id of DBT) expect(WORKSTREAM_ORDER).toContain(id);
  });

  it("covers every workstream in the legacy catalog", () => {
    for (const id of CISADM) expect(WORKSTREAM_ORDER).toContain(id);
  });

  it("invents nothing beyond the two catalogs", () => {
    for (const id of WORKSTREAM_ORDER) expect(UNION).toContain(id);
  });

  it("labels each one, so no surface falls back to a prettified id", () => {
    for (const id of UNION) {
      expect(WORKSTREAM_LABELS[id], id).toBeTruthy();
      expect(WORKSTREAM_DESCRIPTIONS[id], id).toBeTruthy();
    }
  });

  it("gives each one a marker, so none renders as the generic dot", () => {
    for (const id of UNION) expect(WORKSTREAM_ICONS[id], id).toBeTruthy();
  });

  it("keeps every marker distinct, or two workstreams read as the same thing", () => {
    const used = UNION.map((id) => WORKSTREAM_ICONS[id]);
    expect(new Set(used).size).toBe(used.length);
  });

  it("gives assets its catalog name, not the prettifier's guess", () => {
    // The fallback would render "Assets"; the catalog and every other surface say
    // "Asset Operations", and three call sites use this without an API label.
    expect(workstreamDisplayName("assets")).toBe("Asset Operations");
  });

  it("still prettifies an id it has never seen", () => {
    expect(workstreamDisplayName("brand_new_area")).toBe("Brand New Area");
  });
});
