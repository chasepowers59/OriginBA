import { aggIsAdditive } from "@/lib/chartLayout";

const DAY = 86_400_000;
const iso = (t: number) => new Date(t).toISOString().slice(0, 10);
const utc = (d: string) => Date.parse(`${d}T00:00:00Z`);

/** The window of the same length that ends the day before this one starts. */
export function priorWindow(start: string, end: string): [string, string] {
  const s = utc(start);
  const days = Math.round((utc(end) - s) / DAY);
  return [iso(s - (days + 1) * DAY), iso(s - DAY)];
}

/** A comparison only means something on a dated window, and only for totals and counts:
 *  the difference of two averages or two shares is not what changed. */
export function canCompare(p: {
  allDates: boolean;
  dateField: string | null;
  measures: { field: string; agg: string }[];
}): boolean {
  return !p.allDates && Boolean(p.dateField) && p.measures.length > 0 && p.measures.every((m) => aggIsAdditive(m.agg));
}

export type GroupChange = { key: string; current: number; prior: number; change: number; pct: number | null };

const pct = (change: number, prior: number) => (prior === 0 ? null : (change / prior) * 100);

/** Each group in either period, the totals, and the groups that moved most (by size, either way). */
export function comparePeriods(
  current: Record<string, unknown>[],
  prior: Record<string, unknown>[],
  dimension: string,
  measure: string,
  top = 3,
  /** each period's unbroken total when the API cut its breakdown (QueryResult.totals) */
  totals: { current?: number | null; prior?: number | null } = {},
): { total: Omit<GroupChange, "key">; groups: GroupChange[]; movers: GroupChange[] } {
  const sums = new Map<string, { current: number; prior: number }>();
  const add = (rows: Record<string, unknown>[], side: "current" | "prior") => {
    for (const r of rows) {
      const key = String(r[dimension] ?? "(not recorded)");
      const entry = sums.get(key) ?? { current: 0, prior: 0 };
      entry[side] += Number(r[measure] ?? 0);
      sums.set(key, entry);
    }
  };
  add(current, "current");
  add(prior, "prior");
  const groups = [...sums].map(([key, v]) => ({ key, ...v, change: v.current - v.prior, pct: pct(v.current - v.prior, v.prior) }));
  const cur = totals.current ?? groups.reduce((s, g) => s + g.current, 0);
  const pri = totals.prior ?? groups.reduce((s, g) => s + g.prior, 0);
  const movers = [...groups].filter((g) => g.change !== 0)
    .sort((a, b) => Math.abs(b.change) - Math.abs(a.change)).slice(0, top);
  return { total: { current: cur, prior: pri, change: cur - pri, pct: pct(cur - pri, pri) }, groups, movers };
}
