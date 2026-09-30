import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { findReference, freshnessRows, hitRate } from "./systemHealth";

describe("system health", () => {
  const errors = [
    { reference: "3f9c0a1b2c3d", at: "2026-09-29T12:00:00+00:00", route: "GET /boom", org: "demo25", error: "RuntimeError: x" },
  ];

  it("finds an error by the reference a user reported, however it was pasted", () => {
    expect(findReference(errors, "Reference: 3f9c0a1b2c3d")?.route).toBe("GET /boom");
    expect(findReference(errors, " 3F9C0A1B2C3D ")?.route).toBe("GET /boom");
    expect(findReference(errors, "nothing")).toBeNull();
  });

  it("gives the cache hit rate, or a dash before any request", () => {
    expect(hitRate({ hits: 3, misses: 1, entries: 2 })).toBe("75%");
    expect(hitRate({ hits: 0, misses: 0, entries: 0 })).toBe("—");
  });
});

describe("data refresh by organization", () => {
  const tz = process.env.TZ;
  beforeAll(() => {
    process.env.TZ = "America/Denver";
  });
  afterAll(() => {
    process.env.TZ = tz;
  });

  it("stale organizations first, each with its last build and how long ago", () => {
    const rows = freshnessRows({
      ellensburg: { built_at: "2026-09-29T12:39:07-04:00", age_hours: 1.2, stale: false },
      int_dev: { built_at: "2026-09-27T05:45:00-04:00", age_hours: 55.4, stale: true },
      citycorp: null,
      demo25: { built_at: "2026-09-01T10:11:22", age_hours: 675, stale: false, scheduled: false },
    });
    expect(rows).toEqual([
      ["int_dev", "Sep 27, 2026, 3:45 AM", "2 days ago", "Stale"],
      ["demo25", "Sep 1, 2026, 10:11 AM", "28 days ago", "Not scheduled"],
      ["ellensburg", "Sep 29, 2026, 10:39 AM", "1 hour ago", "Fresh"],
      ["citycorp", "—", "—", "Unknown"],
    ]);
  });
});
