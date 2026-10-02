import { formatDate } from "@/lib/format";

const ISO = /^(\d{4})-(\d{2})-(\d{2})(?:[T ]|$)/;

/** The last calendar day of the bucket that starts on y-m-d at this grain, as YYYY-MM-DD. */
function bucketEnd(y: number, m: number, d: number, grain: string): string | null {
  const pad = (n: number) => String(n).padStart(2, "0");
  const lastOfMonth = (yy: number, mm: number) => new Date(Date.UTC(yy, mm, 0)).getUTCDate();   // mm is 1-based: day 0 of the next month
  switch (grain) {
    case "day":
      return `${y}-${pad(m)}-${pad(d)}`;
    case "week": {
      const t = new Date(Date.UTC(y, m - 1, d + 6));
      return `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())}`;
    }
    case "month":
      return `${y}-${pad(m)}-${pad(lastOfMonth(y, m))}`;
    case "quarter": {
      const last = m + 2 - ((m - 1) % 3);
      return `${y}-${pad(last)}-${pad(lastOfMonth(y, last))}`;
    }
    case "year":
      return `${y}-12-31`;
    default:
      return null;
  }
}

/**
 * Whether the bucket starting at `bucket` is cut short by a window ending on `windowEnd`
 * (both ISO dates, zone-free): the bucket's own last day lies past the window. A monthly
 * series over a window that ends inside a month otherwise draws that month as a collapse.
 */
export function partialBucket(bucket: string, grain: string | null | undefined, windowEnd: string | null | undefined): { through: string } | null {
  if (!grain || !windowEnd) return null;
  const m = ISO.exec(bucket);
  const w = ISO.exec(windowEnd);
  if (!m || !w) return null;
  const end = bucketEnd(Number(m[1]), Number(m[2]), Number(m[3]), grain);
  if (!end) return null;
  const through = `${w[1]}-${w[2]}-${w[3]}`;
  return through < end && through >= `${m[1]}-${m[2]}-${m[3]}` ? { through } : null;
}

/** "Jun 2026 (to Jun 2, 2026)" for a cut-short bucket's tick; the note names the window. */
export function partialLabel(label: string, through: string): string {
  return `${label} (to ${formatDate(through)})`;
}

export function partialNote(label: string, through: string): string {
  return `${label} is partial: the window ends ${formatDate(through)}.`;
}
