import { describe, expect, it } from "vitest";
import { featuredCanvases } from "./featuredCanvases";

/**
 * "Start here" is the primary call-to-action on every workstream page, and it was dead
 * on all of them. The API returns workstream.featured as plain snapshot-id STRINGS:
 *
 *   GET /snapshots -> workstreams[].featured = ["rpt_asset_location", "rpt_device_asset"]
 *
 * WorkstreamHeroLinks read `item.snapshot_id` off each entry, which a string does not
 * have, so every card rendered an empty title and linked to /explore/undefined
 * (measured on /workstream/assets, 2026-09-02 -- all four links). The object shape it
 * expected is only ever produced by its OWN fallback branch, which never ran because
 * `featured` was non-empty. That is why no amount of catalog data would have fixed it.
 *
 * Both shapes are accepted here: the string is what the API sends, and the object is
 * what the fallback and any future report-specific entry would send.
 */
const SNAPS = [
  { id: "rpt_device_asset", label: "Device Asset", grain_description: "One row per device" },
  { id: "rpt_asset_location", label: "Asset Location", summary: "Where assets sit" },
  { id: "rpt_extra", label: "Extra" },
  { id: "rpt_fourth", label: "Fourth" },
];

describe("featuredCanvases", () => {
  it("reads the string form the API actually sends", () => {
    const out = featuredCanvases(["rpt_device_asset", "rpt_asset_location"], SNAPS);
    expect(out.map((c) => c.snapshotId)).toEqual(["rpt_device_asset", "rpt_asset_location"]);
    expect(out.map((c) => c.label)).toEqual(["Device Asset", "Asset Location"]);
  });

  it("prefers the grain description, falling back to the summary", () => {
    const out = featuredCanvases(["rpt_device_asset", "rpt_asset_location"], SNAPS);
    expect(out[0].description).toBe("One row per device");
    expect(out[1].description).toBe("Where assets sit");
  });

  it("still reads the object form", () => {
    const out = featuredCanvases(
      [{ snapshot_id: "rpt_device_asset", report_id: "top_devices" }],
      SNAPS,
    );
    expect(out[0].snapshotId).toBe("rpt_device_asset");
    expect(out[0].reportId).toBe("top_devices");
  });

  it("falls back to the first three canvases when nothing is featured", () => {
    expect(featuredCanvases([], SNAPS).map((c) => c.snapshotId)).toEqual([
      "rpt_device_asset",
      "rpt_asset_location",
      "rpt_extra",
    ]);
    expect(featuredCanvases(undefined, SNAPS)).toHaveLength(3);
  });

  it("never yields an entry without an id -- that was the /explore/undefined link", () => {
    const out = featuredCanvases(["", null, undefined, { report_id: "x" }] as never, SNAPS);
    expect(out).toEqual([]);
  });

  it("labels a featured id the catalog does not carry, rather than rendering blank", () => {
    const out = featuredCanvases(["rpt_missing"], SNAPS);
    expect(out[0].snapshotId).toBe("rpt_missing");
    expect(out[0].label).toBe("rpt_missing");
  });

  it("returns nothing when there is nothing at all", () => {
    expect(featuredCanvases([], [])).toEqual([]);
    expect(featuredCanvases(undefined, undefined)).toEqual([]);
  });
});
