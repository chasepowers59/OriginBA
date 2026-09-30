import {
  anchorDate,
  defaultDateRange,
  defaultDateRangeLastMonth,
  defaultDateRangeYtd,
} from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { DatePresetConfig } from "@/lib/types";

// The period label a reader sees: an anchored window says what date it is measured from, so "Last 6
// months" on a frozen copy is not read as the six months before today. The preset chips
// keep the plain label (they match on it); a custom range already shows its own dates.
export function anchoredLabel(label: string, asOf?: string | null): string {
  if (!asOf || label === "Custom range") return label;
  return `${label}, as of ${formatDate(anchorDate(asOf))}`;
}

// A canvas may name its default (the catalog builder writes "last_12_months"): the name picks
// the explorer's chip of that label. Mirrored by api/date_presets.py.
const NAMED: Record<string, DatePresetConfig> = {
  last_30_days: { kind: "days", days: 30, label: "Last 30 days" },
  last_quarter: { kind: "days", days: 90, label: "Last quarter" },
  prior_month: { kind: "last_month", label: "Prior month" },
  year_to_date: { kind: "ytd", label: "Year to date" },
  last_12_months: { kind: "days", days: 365, label: "Last 12 months" },
};

/** A canvas of what exists now (the catalog's "all_dates") has no default window. */
export function canvasOpensOnAllDates(preset: DatePresetConfig | string | undefined): boolean {
  return preset === "all_dates";
}

export function applyDatePresetConfig(preset: DatePresetConfig | string | undefined, asOf?: string | null): {
  range: [string, string];
  label: string;
} {
  const named = typeof preset === "string" ? NAMED[preset] : preset;
  const p = named ?? { kind: "days", days: 180, label: "Last 6 months" };
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

const WIDEST_DAYS = 730;

export function widenDateRange(currentDays: number, asOf?: string | null): {
  range: [string, string];
  label: string;
  days: number;
} {
  const next = currentDays <= 90 ? 180 : currentDays <= 180 ? 365 : WIDEST_DAYS;
  return {
    range: defaultDateRange(next, asOf),
    label: `Last ${Math.round(next / 30)} months`,
    days: next,
  };
}

/** "Widen date range" only when a wider window exists: under All dates, or past the widest step, it would narrow. */
export function canWidenDateRange(p: { allDates: boolean; dateField: string | null; currentDays: number }): boolean {
  return !p.allDates && Boolean(p.dateField) && p.currentDays < WIDEST_DAYS;
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
/**
 * Whether picking this report switches the page to All dates. A backlog question (what is
 * still open, however old) declares all_dates; only picking it switches, so a reader who
 * then narrows the window keeps their choice on the re-run.
 */
export function opensOnAllDates(r: {
  report: { id: string; all_dates?: boolean };
  activeReportId: string | null;
  allDates: boolean;
  hasDateField: boolean;
  /** a saved view restores its own window */
  keepWindow?: boolean;
}): boolean {
  return Boolean(r.report.all_dates) && r.report.id !== r.activeReportId && !r.allDates && r.hasDateField
    && !r.keepWindow;
}

export function fallBackToAllDates(r: { rowCount: number; windowed: boolean; firstRun: boolean }): boolean {
  return r.firstRun && r.windowed && r.rowCount === 0;
}

/**
 * The period the page names. Under All dates the request carries no window, but a
 * request with no filters at all gets the SERVER's trailing window on a large canvas
 * (applied_window); naming "All dates" then describes a scope the query did not apply.
 */
export function explorerPeriodLabel(p: {
  allDates: boolean;
  activePreset: string;
  asOf?: string | null;
  fellBackFrom?: string | null;
  appliedWindow?: { days: number } | null;
}): string {
  if (!p.allDates) return anchoredLabel(p.activePreset, p.asOf);
  if (p.appliedWindow) return `Last ${p.appliedWindow.days} days`;
  if (!p.fellBackFrom) return ALL_DATES;
  const from = anchoredLabel(p.fellBackFrom, p.asOf);
  return `${ALL_DATES} (nothing in ${from.charAt(0).toLowerCase()}${from.slice(1)})`;
}
