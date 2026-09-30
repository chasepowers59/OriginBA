import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { freshnessNotice } from "./freshness";

// Ellensburg 2026-09-29: the reporting tables dated Sep 10 and no page said so.
describe("freshnessNotice", () => {
  const tz = process.env.TZ;
  beforeAll(() => {
    process.env.TZ = "America/Denver"; // the reader's clock; the build time carries its own offset
  });
  afterAll(() => {
    process.env.TZ = tz;
  });

  it("says nothing while the data is fresh or its build time is unknown", () => {
    expect(freshnessNotice({ built_at: "2026-09-29T12:39:07-04:00", age_hours: 0.3, stale: false })).toBeNull();
    expect(freshnessNotice({ built_at: null, age_hours: null, stale: false })).toBeNull();
    expect(freshnessNotice(null)).toBeNull();
  });

  it("names the last refresh and how long ago, in days past two days", () => {
    const text = freshnessNotice({ built_at: "2026-09-10T08:41:38-06:00", age_hours: 462.3, stale: true });
    expect(text).toBe(
      "Reporting data was last refreshed Sep 10, 2026, 8:41 AM (19 days ago). The scheduled refresh has " +
        "not completed since, so figures may be out of date.",
    );
  });

  it("counts hours under two days", () => {
    expect(freshnessNotice({ built_at: "2026-09-28T04:00:00-06:00", age_hours: 37.2, stale: true })).toContain(
      "(37 hours ago)",
    );
  });
});
