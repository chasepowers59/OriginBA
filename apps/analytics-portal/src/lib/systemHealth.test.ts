import { describe, expect, it } from "vitest";
import { findReference, hitRate } from "./systemHealth";

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
