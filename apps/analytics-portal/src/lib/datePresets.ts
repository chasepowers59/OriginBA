import {
  defaultDateRange,
  defaultDateRangeLastMonth,
  defaultDateRangeYtd,
} from "@/lib/api";
import type { DatePresetConfig } from "@/lib/types";

export function applyDatePresetConfig(preset: DatePresetConfig | undefined): {
  range: [string, string];
  label: string;
} {
  const p = preset ?? { kind: "days", days: 180, label: "Last 6 months" };
  if (p.kind === "ytd") {
    return { range: defaultDateRangeYtd(), label: p.label || "Year to date" };
  }
  if (p.kind === "last_month") {
    return { range: defaultDateRangeLastMonth(), label: p.label || "Prior month" };
  }
  return {
    range: defaultDateRange(p.days ?? 180),
    label: p.label || `Last ${p.days ?? 180} days`,
  };
}

export function widenDateRange(currentDays: number): {
  range: [string, string];
  label: string;
  days: number;
} {
  const next = currentDays <= 90 ? 180 : currentDays <= 180 ? 365 : 730;
  return {
    range: defaultDateRange(next),
    label: `Last ${Math.round(next / 30)} months`,
    days: next,
  };
}

export function estimatePeriodDays(start: string, end: string): number {
  const a = new Date(start);
  const b = new Date(end);
  return Math.max(1, Math.round((b.getTime() - a.getTime()) / 86400000));
}
