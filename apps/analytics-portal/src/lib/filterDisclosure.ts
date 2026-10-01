import { formatDate } from "@/lib/format";
import type { FilterDef } from "@/lib/types";
import type { RowRule } from "@/lib/rowRules";

const val = (v: unknown) => (typeof v === "string" && /^\d{4}-\d{2}-\d{2}/.test(v) ? formatDate(v) : String(v));

/** One filter as a reader would say it. */
export function describeFilter(f: FilterDef): string {
  const v = f.value;
  if (typeof v === "boolean" && (f.op === "eq" || f.op === "=")) return `${f.field}: ${v ? "yes" : "no"}`;
  if (f.op === "between" && Array.isArray(v)) return `${f.field} from ${val(v[0])} to ${val(v[1])}`;
  if (f.op === "in" && Array.isArray(v)) return `${f.field} is ${v.map(val).join(" or ")}`;
  if (f.op === "not_in" && Array.isArray(v)) return `${f.field} is not ${v.map(val).join(" or ")}`;
  const words: Record<string, string> = { eq: "is", "=": "is", ne: "is not", "!=": "is not", gt: "over", gte: "at least",
    lt: "under", lte: "at most", contains: "contains" };
  return `${f.field} ${words[f.op] ?? f.op} ${val(v)}`;
}

/**
 * Everything a result is filtered to, in plain words and in the order a reader needs it: the
 * dates, the report's own rules (frozen only, not cancelled...), the scope and click-through
 * the reader chose, and any limit on their account. A report that sums only frozen segments
 * used to say only "Last 12 months".
 */
export function filterDisclosure(p: {
  window?: { field: string; start: string; end: string } | null;
  allDates?: boolean;
  reportFilters?: FilterDef[];
  scope?: { field: string; value: string } | null;
  drill?: { field: string; value: string } | null;
  rowRules?: RowRule[] | null;
}): string[] {
  const out: string[] = [];
  if (p.allDates) out.push("all dates");
  else if (p.window) out.push(describeFilter({ field: p.window.field, op: "between", value: [p.window.start, p.window.end] }));
  out.push(...(p.reportFilters ?? []).map(describeFilter));
  for (const f of [p.scope, p.drill]) if (f?.field && f.value) out.push(`${f.field} is ${f.value}`);
  for (const r of p.rowRules ?? []) out.push(`your access: ${r.field} is ${r.values.join(" or ")}`);
  return out;
}
