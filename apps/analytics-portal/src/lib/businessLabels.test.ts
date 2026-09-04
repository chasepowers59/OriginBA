import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  WORKSTREAM_ORDER,
  WORKSTREAM_LABELS,
  WORKSTREAM_DESCRIPTIONS,
  workstreamDisplayName,
  prettifyFieldName,
} from "./businessLabels";
import { WORKSTREAM_ICONS } from "./workstreamIcons";

/**
 * These maps are a hand-kept copy of the catalog's workstreams, and hand-kept copies
 * drift: this one once lacked `assets` while the catalog carried it, and
 * app/workstream/[workstreamId] calls notFound() for any id not in WORKSTREAM_ORDER, so
 * /workstream/assets was a 404 with two canvases behind it. Pinned against the catalog
 * file itself rather than a list retyped here, because a hand-kept list is the thing
 * that broke.
 */
const ROOT = resolve(__dirname, "../../../..");

const DBT = JSON.parse(readFileSync(resolve(ROOT, "output", "catalog_dbt.json"), "utf8"))
  .workstream_order as string[];

describe("workstream label coverage", () => {
  it("reads the catalog, so this test fails if it is regenerated differently", () => {
    expect(DBT.length).toBeGreaterThan(0);
  });

  it("is the catalog's own order, verbatim", () => {
    expect([...WORKSTREAM_ORDER]).toEqual(DBT);
  });

  it("labels each one, so no surface falls back to a prettified id", () => {
    for (const id of DBT) {
      expect(WORKSTREAM_LABELS[id], id).toBeTruthy();
      expect(WORKSTREAM_DESCRIPTIONS[id], id).toBeTruthy();
    }
  });

  it("gives each one a marker, so none renders as the generic dot", () => {
    for (const id of DBT) expect(WORKSTREAM_ICONS[id], id).toBeTruthy();
  });

  it("keeps every marker distinct, or two workstreams read as the same thing", () => {
    const used = DBT.map((id) => WORKSTREAM_ICONS[id]);
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

describe("prettifyFieldName across BOTH deployment shapes", () => {
  /**
   * A field id reaches user-facing copy in two very different forms, because the two
   * catalogs name columns differently: a dbt canvas field is already a business name
   * ("Bill Date"), a legacy snapshot's is a database column ("ACCOUNTING_DT"). Copy
   * that interpolates the id raw therefore looks correct on the dev org and shows a
   * database column to the six legacy orgs — which is how three cross-filter banners
   * shipped with `{filter.field}` in them.
   *
   * The helper has to be safe in BOTH directions to be usable everywhere: it must
   * humanise the legacy form AND leave an already-human name untouched.
   */
  it("humanises a CISADM column, suffix and all", () => {
    expect(prettifyFieldName("ACCOUNTING_DT")).toBe("Accounting Date");
    expect(prettifyFieldName("CUSTOMER_CLASS_CD")).toBe("Customer Class");
    expect(prettifyFieldName("BILL_AMT")).toBe("Bill Amount");
    expect(prettifyFieldName("PREM_NBR")).toBe("Prem Number");
    expect(prettifyFieldName("FREEZE_DTTM")).toBe("Freeze Date/Time");
  });

  it("leaves an already-human canvas name alone", () => {
    for (const name of ["Bill Date", "Customer Class", "Service Agreement ID"]) {
      expect(prettifyFieldName(name)).toBe(name);
    }
  });

  it("expands a status flag once, not twice", () => {
    // 22 legacy ids end _STATUS_FLG or _STAT_FLG, including the most-used ones
    // (BILL_STAT_FLG, SA_STATUS_FLG, PAY_STATUS_FLG). Appending "status" to a stem
    // that already says it produced "Adj Status Status".
    expect(prettifyFieldName("ADJ_STATUS_FLG")).toBe("Adj Status");
    expect(prettifyFieldName("BILL_STAT_FLG")).toBe("Bill Status");
    expect(prettifyFieldName("SA_STATUS_FLG")).toBe("SA Status");
    // a flag that does NOT already say status still gains the word
    expect(prettifyFieldName("BUDGET_FLG")).toBe("Budget Status");
  });

  it("is idempotent, so passing a prettified name back through is harmless", () => {
    for (const id of ["ACCOUNTING_DT", "CUSTOMER_CLASS_CD", "Bill Date"]) {
      expect(prettifyFieldName(prettifyFieldName(id))).toBe(prettifyFieldName(id));
    }
  });
});
