import { formatDateTime, formatNumber } from "@/lib/format";

/** GET /portal/freshness: when the organization's reporting tables were last built (api/freshness.py). */
export type Freshness = { built_at: string | null; age_hours: number | null; stale: boolean; scheduled?: boolean };

/** The notice every page shows once the last build is over a day and a half old; null otherwise. */
export function freshnessNotice(f: Freshness | null): string | null {
  if (!f?.stale || !f.built_at || f.age_hours == null) return null;
  return (
    `Reporting data was last refreshed ${formatDateTime(f.built_at)} (${age(f.age_hours)} ago). The scheduled refresh has ` +
    "not completed since, so figures may be out of date."
  );
}

/** "1 hour", "37 hours", "19 days": hours under two days, whole days after. */
export function age(hours: number): string {
  const [n, unit] = hours < 48 ? [Math.floor(hours), "hour"] : [Math.floor(hours / 24), "day"];
  return `${formatNumber(n)} ${unit}${n === 1 ? "" : "s"}`;
}
