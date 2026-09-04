import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { WORKSTREAM_ORDER, WORKSTREAM_LABELS } from "./businessLabels";
import { ALL_DASHBOARD_TEMPLATES } from "./dashboardTemplates";
import { DATABASE_QUERY_TEMPLATES } from "./databaseQueryTemplates";
import { WORKSTREAM_ICONS } from "./workstreamIcons";
import { dateScope } from "./dateScope";
import { resolveDateField } from "./tileDateField";

/**
 * There is ONE catalog shape on the front-end. The legacy CISADM snapshot shape is
 * retired — see tests/test_single_catalog_shape.py for the six bugs it produced in one
 * session and why a dormant branch is where the next one hides.
 *
 * Two things this retirement FIXES rather than merely tidies, both found in the survey:
 * the explorer's date presets and the dashboard's day window only ever emitted a filter
 * when `required_date_field` was set, and no dbt canvas sets it. So on the shape that
 * every org now uses, "Prior month" changed state and sent nothing. Windowing now keys
 * off the canvas's real date — the same field the server indexes and defaults on.
 */

const SRC = resolve(__dirname, "..");
const ROOT = resolve(SRC, "..", "..", "..");
const catalog = JSON.parse(readFileSync(join(ROOT, "output", "catalog_dbt.json"), "utf8"));
const canvasIds = new Set(Object.keys(catalog.snapshots));

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (name === "node_modules") continue;
    if (statSync(p).isDirectory()) walk(p, out);
    else if (/\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name)) out.push(p);
  }
  return out;
}

describe("the workstream vocabulary is the dbt catalog's, and nothing else", () => {
  it("carries no workstream that exists only in the retired catalog", () => {
    expect(WORKSTREAM_ORDER).not.toContain("new_services");
    expect(Object.keys(WORKSTREAM_LABELS)).not.toContain("new_services");
    expect(Object.keys(WORKSTREAM_ICONS)).not.toContain("new_services");
  });

  it("matches the catalog's order exactly, with no union to maintain", () => {
    expect([...WORKSTREAM_ORDER]).toEqual(catalog.workstream_order);
  });
});

describe("every template runs on the one catalog", () => {
  it("names no legacy snapshot", () => {
    for (const t of ALL_DASHBOARD_TEMPLATES) {
      for (const tile of t.tiles) {
        expect(tile.snapshot_id, `${t.id}: ${tile.snapshot_id}`).not.toMatch(/_RPT_CURR$/i);
        expect(canvasIds.has(tile.snapshot_id), `${t.id}: ${tile.snapshot_id}`).toBe(true);
      }
    }
  });

  it("offers no SQL against a legacy snapshot", () => {
    for (const q of DATABASE_QUERY_TEMPLATES) {
      expect(q.sql, q.id).not.toMatch(/_RPT_CURR/i);
    }
  });
});

describe("the date a canvas works in comes from its measured default", () => {
  it("resolves the default date field, then the first declared date", () => {
    expect(resolveDateField({ default_date_field: "Bill Date" })).toBe("Bill Date");
    expect(resolveDateField({ default_date_field: null, date_fields: [{ id: "Due Date" }] }))
      .toBe("Due Date");
    expect(resolveDateField({ default_date_field: null, date_fields: [] })).toBeNull();
    expect(resolveDateField(null)).toBeNull();
  });

  it("describes the date as the one the canvas works in, never as compulsory", () => {
    const scope = dateScope({
      default_date_field: "Bill Date",
      date_fields: [{ id: "Bill Date", label: "Bill Date" }],
    });
    expect(scope).toEqual({ label: "Dates on", value: "Bill Date", required: false });
    expect(dateScope({ default_date_field: null })).toBeNull();
  });
});

describe("the legacy shape is not mentioned anywhere in the app", () => {
  it("no source file names a retired concept", () => {
    const legacy = /_RPT_CURR|catalog_cisadm|cisadm[-_ ]catalog|required_date_field|required_date_label|new_services/i;
    const hits: string[] = [];
    for (const file of walk(SRC)) {
      const lines = readFileSync(file, "utf8").split("\n");
      lines.forEach((line, i) => {
        if (legacy.test(line)) hits.push(`${file.replace(ROOT + "/", "")}:${i + 1}: ${line.trim().slice(0, 90)}`);
      });
    }
    expect(hits, "\n" + hits.join("\n")).toEqual([]);
  });
});
