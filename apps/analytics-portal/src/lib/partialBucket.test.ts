import { describe, expect, it } from "vitest";
import { partialBucket } from "./partialBucket";

/**
 * A monthly series over a window that ends inside a month draws the last bucket as a
 * collapse: CityCorp's "Billed revenue by month" (Dec 4 to Jun 2, 2026) fell to nothing at
 * Jun 2026, which held two days (2026-10-02). The last bucket is named for what it holds.
 */
describe("partialBucket: the trailing bucket a window cuts short", () => {
  it("a month the window ends inside is partial, to the window's end", () => {
    expect(partialBucket("2026-06-01T00:00:00", "month", "2026-06-02")).toEqual({ through: "2026-06-02" });
    expect(partialBucket("2026-06-01", "month", "2026-06-30")).toBeNull();          // the whole month
    expect(partialBucket("2026-05-01", "month", "2026-06-02")).toBeNull();          // an earlier, whole month
  });

  it("quarters, years, weeks and days", () => {
    expect(partialBucket("2026-04-01", "quarter", "2026-06-02")).toEqual({ through: "2026-06-02" });
    expect(partialBucket("2026-04-01", "quarter", "2026-06-30")).toBeNull();
    expect(partialBucket("2026-01-01", "year", "2026-06-02")).toEqual({ through: "2026-06-02" });
    expect(partialBucket("2026-06-01", "week", "2026-06-02")).toEqual({ through: "2026-06-02" });
    expect(partialBucket("2026-06-01", "week", "2026-06-07")).toBeNull();
    expect(partialBucket("2026-06-02", "day", "2026-06-02")).toBeNull();
  });

  it("nothing to say without a window end, a grain, or a parsable bucket", () => {
    expect(partialBucket("2026-06-01", "month", null)).toBeNull();
    expect(partialBucket("2026-06-01", null, "2026-06-02")).toBeNull();
    expect(partialBucket("June", "month", "2026-06-02")).toBeNull();
  });
});
