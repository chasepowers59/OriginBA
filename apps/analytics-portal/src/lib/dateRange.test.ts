import { afterEach, describe, expect, it, vi } from "vitest";
import {
  defaultDateRange,
  defaultDateRangeLastMonth,
  defaultDateRangeYtd,
} from "@/lib/api";

/**
 * A date range must be built in the VIEWER'S calendar, not UTC.
 *
 * All three builders ended `toISOString().slice(0, 10)`. `new Date()` is local but
 * `toISOString()` converts to UTC, so the two disagree for the offset's worth of hours
 * every day — and these ranges filter BUSINESS dates (Bill Date, Accounting Date),
 * which are calendar dates in the utility's own timezone, never UTC instants.
 *
 * This is the same defect already fixed on the backend (api/reporting_dates.py):
 * report_schedules ended its window on a UTC "today" while every other window builder
 * used the local date, so a scheduled report's range did not tie to the screen. Fixing
 * it there and leaving it here would just move the disagreement to the client.
 *
 * TWO distinct failures, and the client base only sees one of them:
 *
 *  - END is `new Date()` -> UTC. WEST of UTC (every US utility here, UTC-5..-8) this
 *    rolls to TOMORROW for the last 5-8 hours of every evening.
 *  - START is a constructed LOCAL MIDNIGHT (`new Date(y, 0, 1)`). EAST of UTC that
 *    converts back to the previous day, so "year to date" starts on Dec 31 of the
 *    PRIOR YEAR and "prior month" starts a day early.
 *
 * Both are latent on a UTC machine, which is why they survived.
 */

const realTZ = process.env.TZ;
afterEach(() => {
  vi.useRealTimers();
  process.env.TZ = realTZ;
});

/** Freeze the clock at a local wall-clock instant in the given zone. */
function freeze(iso: string) {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(iso));
}

describe("date ranges are built in the viewer's calendar", () => {
  it("an evening west of UTC does not roll the end date to tomorrow", () => {
    // 2026-09-02 19:30 local in UTC-6 is 2026-09-03 01:30 UTC.
    freeze("2026-09-03T01:30:00Z");
    const [, end] = defaultDateRange(30);
    const localToday = new Date();
    const expected = [
      localToday.getFullYear(),
      String(localToday.getMonth() + 1).padStart(2, "0"),
      String(localToday.getDate()).padStart(2, "0"),
    ].join("-");
    expect(end).toBe(expected);
  });

  it("the span between start and end is the number of days asked for", () => {
    freeze("2026-09-03T01:30:00Z");
    const [start, end] = defaultDateRange(30);
    const days = Math.round(
      (new Date(`${end}T00:00:00`).getTime() - new Date(`${start}T00:00:00`).getTime()) /
        86400000,
    );
    expect(days).toBe(30);
  });

  it("year to date starts on January 1 of the CURRENT year", () => {
    freeze("2026-09-03T01:30:00Z");
    const [start] = defaultDateRangeYtd();
    expect(start).toBe("2026-01-01");
  });

  it("prior month starts on the 1st and ends on the last day of that month", () => {
    freeze("2026-09-03T01:30:00Z");
    const [start, end] = defaultDateRangeLastMonth();
    expect(start).toBe("2026-08-01");
    expect(end).toBe("2026-08-31");
  });

  it("east of UTC, a constructed local midnight does not fall into the prior year", () => {
    // The latent half: `new Date(y, 0, 1)` is LOCAL midnight, and toISOString() moved
    // it back a day for any positive offset -- so "year to date" began on Dec 31 of the
    // previous year. No current client sits east of UTC; the fix should hold anyway.
    process.env.TZ = "Australia/Sydney";
    freeze("2026-09-02T02:00:00Z"); // 12:00 local, well inside the Sydney day
    expect(defaultDateRangeYtd()[0]).toBe("2026-01-01");
  });

  it("every boundary is a plain YYYY-MM-DD", () => {
    freeze("2026-09-03T01:30:00Z");
    for (const range of [defaultDateRange(7), defaultDateRangeYtd(), defaultDateRangeLastMonth()]) {
      for (const value of range) expect(value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }
  });
});
