import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  formatCellValue,
  formatCompact,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatMonth,
  formatNumber,
  niceTicks,
  valueAxis,
} from "./format";

/**
 * UI-16 (issues log, Decisions, 2026-09-29): one format set, used everywhere. Dates
 * "Sep 1, 2026"; date-times "Sep 1, 2026, 10:11 AM"; a date never shows a time; tables
 * show full numbers; compact only on chart axes and KPI headlines, by one rule; money
 * "-$12,071.26" and "-$9.5K", never "$-9.5K"; axis steps 1, 2, 2.5 or 5 x 10^n.
 */

describe("dates", () => {
  it("a date reads Sep 1, 2026", () => {
    expect(formatDate("2026-09-01")).toBe("Sep 1, 2026");
    expect(formatDate("2026-09-01T10:11:00")).toBe("Sep 1, 2026");
    expect(formatDate(new Date(2026, 8, 1, 23, 59))).toBe("Sep 1, 2026");
  });

  it("a date-time reads Sep 1, 2026, 10:11 AM", () => {
    expect(formatDateTime("2026-09-01T10:11:00")).toBe("Sep 1, 2026, 10:11 AM");
    expect(formatDateTime("2026-09-01T14:05:00")).toBe("Sep 1, 2026, 2:05 PM");
  });

  it("a date-only value never shows a time", () => {
    expect(formatDateTime("2026-09-01")).toBe("Sep 1, 2026");
  });

  it("missing and unreadable values stay honest", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("")).toBe("—");
    expect(formatDate("not a date")).toBe("not a date");
  });
});

describe("months", () => {
  // Ori's trends speak in months ("2026-05"); a month reads like a date, short month first.
  it("a month reads May 2026", () => {
    expect(formatMonth("2026-05")).toBe("May 2026");
    expect(formatMonth("2025-12")).toBe("Dec 2025");
  });

  it("stays in its own month west and east of UTC", () => {
    const tz = process.env.TZ;
    try {
      for (const zone of ["America/Denver", "Australia/Sydney"]) {
        process.env.TZ = zone;
        expect(formatMonth("2026-01")).toBe("Jan 2026");
      }
    } finally {
      process.env.TZ = tz;
    }
  });

  it("missing and unreadable values stay honest", () => {
    expect(formatMonth(null)).toBe("—");
    expect(formatMonth("")).toBe("—");
    expect(formatMonth("2026-13")).toBe("2026-13");
    expect(formatMonth("soon")).toBe("soon");
  });
});

describe("a midnight timestamp from a DATE column is a date", () => {
  // CISADM DATE columns and truncated time buckets both arrive as local midnight.
  it("drops 12:00 AM from a canvas Date column, a CISADM _DT column and a time bucket", () => {
    expect(formatCellValue("2026-09-01T00:00:00", { columnId: "Bill Date" })).toBe("Sep 1, 2026");
    expect(formatCellValue("2026-09-01T00:00:00", { columnId: "BILL_DT" })).toBe("Sep 1, 2026");
    expect(formatCellValue("2026-09-01T00:00:00", { columnId: "TD0" })).toBe("Sep 1, 2026");
    expect(formatCellValue("2026-09-01 00:00:00")).toBe("Sep 1, 2026");
  });

  it("keeps the time a date-time column recorded, midnight included", () => {
    expect(formatCellValue("2026-09-01T00:00:00", { columnId: "Freeze Date/Time" })).toBe("Sep 1, 2026, 12:00 AM");
    expect(formatCellValue("2026-09-01T00:00:00", { columnId: "CRE_DTTM" })).toBe("Sep 1, 2026, 12:00 AM");
    expect(formatCellValue("2026-09-01T10:11:00", { columnId: "TD0" })).toBe("Sep 1, 2026, 10:11 AM");
  });
});

describe("numbers: full in tables, compact from 10,000 on axes and headlines", () => {
  it("tables and sentences show every digit", () => {
    expect(formatNumber(1_234_567)).toBe("1,234,567");
    expect(formatNumber(1234.5)).toBe("1,234.5");
    expect(formatCellValue(1_234_567, { isMeasure: true })).toBe("1,234,567");
    expect(formatCellValue("1234567", { isMeasure: true })).toBe("1,234,567");
  });

  it("compacts at 10,000 and not below", () => {
    expect(formatCompact(9_999)).toBe("9,999");
    expect(formatCompact(-9_999)).toBe("-9,999");
    expect(formatCompact(10_000)).toBe("10K");
    expect(formatCompact(-10_000)).toBe("-10K");
    expect(formatCompact(12_345)).toBe("12.3K");
    expect(formatCompact(1_500_000)).toBe("1.5M");
    expect(formatCompact(2_400_000)).toBe("2.4M");
    expect(formatCompact(999_950)).toBe("1M");
    expect(formatCompact(null)).toBe("—");
  });
});

describe("money", () => {
  it("reads $1,234.56 with the sign before the dollar", () => {
    expect(formatCurrency(1234.56)).toBe("$1,234.56");
    expect(formatCurrency(-12_071.26)).toBe("-$12,071.26");
    expect(formatCurrency(1234)).toBe("$1,234.00");
  });

  it("keeps a unit price's stored precision, but not float noise", () => {
    expect(formatCurrency(0.04523)).toBe("$0.04523");
    expect(formatCurrency("1265.000000")).toBe("$1,265.00");
    expect(formatCurrency(0.1 + 0.2)).toBe("$0.30");
  });

  it("compacts a headline by the same rule, sign first", () => {
    expect(formatCompact(-12_071.26, { currency: true })).toBe("-$12.1K");
    expect(formatCompact(-9_500, { currency: true })).toBe("-$9,500.00");
    expect(formatCompact(2_400_000, { currency: true })).toBe("$2.4M");
  });
});

describe("axis ticks are round numbers", () => {
  const STEP_RATIOS = [1, 2, 2.5, 5];
  const isRound = (step: number) => {
    const ratio = step / 10 ** Math.floor(Math.log10(step));
    return STEP_RATIOS.some((r) => Math.abs(ratio - r) < 1e-9);
  };

  it("0..5,500 steps by 2,000, never 5.5K", () => {
    expect(niceTicks(0, 5_500)).toEqual([0, 2000, 4000, 6000]);
  });

  it("spans negatives through zero", () => {
    expect(niceTicks(-9_500, 20_000)).toEqual([-10_000, 0, 10_000, 20_000]);
  });

  it("small steps come out exact", () => {
    expect(niceTicks(0, 0.9)).toEqual([0, 0.2, 0.4, 0.6, 0.8, 1]);
  });

  it("every range gets a 1, 2, 2.5 or 5 step, covering zero and the data, in at most six ticks", () => {
    for (const [lo, hi] of [[0, 7], [0, 13], [3, 97], [0, 5_500], [-120, 40], [0, 123_456], [0, 9_870_000], [-0.3, 0.7]]) {
      const ticks = niceTicks(lo, hi);
      expect(ticks.length, `${lo}..${hi}`).toBeLessThanOrEqual(6);
      expect(ticks[0]).toBeLessThanOrEqual(Math.min(0, lo));
      expect(ticks[ticks.length - 1]).toBeGreaterThanOrEqual(Math.max(0, hi));
      expect(isRound(ticks[1] - ticks[0]), `${lo}..${hi} step ${ticks[1] - ticks[0]}`).toBe(true);
    }
  });
});

describe("value axis labels", () => {
  it("money on an axis reads -$9.5K, never $-9.5K", () => {
    const axis = valueAxis([-9_500, 12_000], { currency: true });
    expect(axis.format(-9_500)).toBe("-$9.5K");
    expect(axis.ticks.map(axis.format).join(" ")).not.toContain("$-");
  });

  it("one axis compacts all its ticks or none", () => {
    const big = valueAxis([0, 12_000]);
    expect(big.ticks).toEqual([0, 2500, 5000, 7500, 10_000, 12_500]);
    expect(big.ticks.map(big.format)).toEqual(["0", "2.5K", "5K", "7.5K", "10K", "12.5K"]);
    const small = valueAxis([0, 5_500], { currency: true });
    expect(small.ticks.map(small.format)).toEqual(["$0", "$2,000", "$4,000", "$6,000"]);
  });

  it("a trend line's axis fits its data in round steps, rather than flattening it against zero", () => {
    expect(niceTicks(3_450_000, 4_380_000, 4, { zero: false })).toEqual([3_000_000, 3_500_000, 4_000_000, 4_500_000]);
    const bills = valueAxis([30_300, 32_220], { zero: false, maxTicks: 4 });
    expect(bills.ticks.map(bills.format)).toEqual(["30K", "31K", "32K", "33K"]);
  });

  it("a fitted axis over one repeated value falls back to zero, so it still has a height", () => {
    expect(valueAxis([5, 5], { zero: false }).domain[0]).toBe(0);
  });

  it("the axis runs from its first tick to its last", () => {
    const axis = valueAxis([3_000, -4_000, 5_000]);
    expect(axis.domain).toEqual([axis.ticks[0], axis.ticks[axis.ticks.length - 1]]);
  });
});

describe("nothing formats a date or number by hand", () => {
  const SRC = resolve(__dirname, "..");
  const HAND_FORMAT = [
    /\.toLocale(Date|Time)?String\(/,
    /Intl\.(NumberFormat|DateTimeFormat)/,
    /`\$\$\{/,
  ];
  function sources(dir: string): Array<[string, string]> {
    return readdirSync(dir, { withFileTypes: true }).flatMap((e): Array<[string, string]> => {
      const path = resolve(dir, e.name);
      if (e.isDirectory()) return sources(path);
      if (!/\.tsx?$/.test(e.name) || /\.test\.tsx?$/.test(e.name)) return [];
      return [[path.slice(SRC.length + 1), readFileSync(path, "utf8")]];
    });
  }

  it("only lib/format.ts calls toLocaleString, Intl or prefixes a dollar sign", () => {
    const offenders = sources(SRC)
      .filter(([path]) => path !== "lib/format.ts")
      .filter(([, src]) => HAND_FORMAT.some((re) => re.test(src)))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });
});
