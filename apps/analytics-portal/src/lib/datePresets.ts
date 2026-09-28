import {
  anchorDate,
  defaultDateRange,
  defaultDateRangeLastMonth,
  defaultDateRangeYtd,
} from "@/lib/api";
import type { DatePresetConfig } from "@/lib/types";

// The period label a reader sees: an anchored window says what date it is measured from, so "Last 6
// months" on a frozen copy is not read as the six months before today. The preset chips
// keep the plain label (they match on it); a custom range already shows its own dates.
export function anchoredLabel(label: string, asOf?: string | null): string {
  if (!asOf || label === "Custom range") return label;
  const d = anchorDate(asOf);
  return `${label}, as of ${d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}`;
}

export function applyDatePresetConfig(preset: DatePresetConfig | undefined, asOf?: string | null): {
  range: [string, string];
  label: string;
} {
  const p = preset ?? { kind: "days", days: 180, label: "Last 6 months" };
  if (p.kind === "ytd") {
    return { range: defaultDateRangeYtd(asOf), label: p.label || "Year to date" };
  }
  if (p.kind === "last_month") {
    return { range: defaultDateRangeLastMonth(asOf), label: p.label || "Prior month" };
  }
  return {
    range: defaultDateRange(p.days ?? 180, asOf),
    label: p.label || `Last ${p.days ?? 180} days`,
  };
}

export function widenDateRange(currentDays: number, asOf?: string | null): {
  range: [string, string];
  label: string;
  days: number;
} {
  const next = currentDays <= 90 ? 180 : currentDays <= 180 ? 365 : 730;
  return {
    range: defaultDateRange(next, asOf),
    label: `Last ${Math.round(next / 30)} months`,
    days: next,
  };
}

export function estimatePeriodDays(start: string, end: string): number {
  const a = new Date(start);
  const b = new Date(end);
  return Math.max(1, Math.round((b.getTime() - a.getTime()) / 86400000));
}

export const ALL_DATES = "All dates";

/** The explorer's date filter: none when the reader chose all dates or the canvas has no date. */
export function windowFilter(
  dateField: string | null | undefined,
  allDates: boolean,
  start: string,
  end: string,
): { field: string; op: "between"; value: [string, string] }[] {
  return dateField && !allDates ? [{ field: dateField, op: "between", value: [start, end] }] : [];
}

/**
 * Whether the page should drop its opening window. A canvas dated by an effective date
 * (rate versions, configuration) can hold every row outside any recent window; the
 * reader should land on the data, told why, not on "No data". Only the first run: a
 * window the reader picked themselves is theirs to widen.
 */
export function fallBackToAllDates(r: { rowCount: number; windowed: boolean; firstRun: boolean }): boolean {
  return r.firstRun && r.windowed && r.rowCount === 0;
}
