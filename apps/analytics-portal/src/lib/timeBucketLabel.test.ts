import { describe, expect, it } from "vitest";
import { formatTimeBucket } from "./timeBucketLabel";

/**
 * A time bucket comes back as the raw start of the period -- date_trunc / TRUNC both
 * return a timestamp -- so a "by month" axis rendered "2022-07-01T00:0…", the generic
 * 16-character truncation applied to an ISO string. The grain is known by the caller,
 * so the label can say what the bucket actually is.
 */
describe("formatTimeBucket", () => {
  it("labels a month bucket", () => {
    expect(formatTimeBucket("2022-07-01T00:00:00", "month")).toBe("Jul 2022");
  });

  it("labels a year bucket", () => {
    expect(formatTimeBucket("2029-01-01T00:00:00", "year")).toBe("2029");
  });

  it("labels a quarter bucket by its quarter, not its first month", () => {
    expect(formatTimeBucket("2024-04-01T00:00:00", "quarter")).toBe("Q2 2024");
    expect(formatTimeBucket("2024-10-01T00:00:00", "quarter")).toBe("Q4 2024");
  });

  it("labels day and week buckets with the date", () => {
    expect(formatTimeBucket("2024-03-05T00:00:00", "day")).toBe("5 Mar 2024");
    expect(formatTimeBucket("2024-03-04T00:00:00", "week")).toBe("4 Mar 2024");
  });

  it("accepts a date with no time part", () => {
    expect(formatTimeBucket("2022-07-01", "month")).toBe("Jul 2022");
  });

  it("passes through anything that is not a date, rather than inventing one", () => {
    // Guards against a NaN axis if a caller mislabels a categorical column as time.
    expect(formatTimeBucket("Residential", "month")).toBe("Residential");
    expect(formatTimeBucket("—", "month")).toBe("—");
    expect(formatTimeBucket("", "month")).toBe("");
  });

  it("defaults to the month shape when the grain is unknown", () => {
    expect(formatTimeBucket("2022-07-01T00:00:00", undefined)).toBe("Jul 2022");
  });
});
