import { formatDateTime, formatNumber } from "@/lib/format";

/** GET /portal/freshness: when the organization's reporting tables were last built (api/freshness.py). */
export type Freshness = { built_at: string | null; age_hours: number | null; stale: boolean };

/** The notice every page shows once the last build is over a day and a half old; null otherwise. */
export function freshnessNotice(f: Freshness | null): string | null {
  if (!f?.stale || !f.built_at || f.age_hours == null) return null;
  const ago = f.age_hours < 48 ? `${formatNumber(Math.floor(f.age_hours))} hours` : `${formatNumber(Math.floor(f.age_hours / 24))} days`;
  return (
    `Reporting data was last refreshed ${formatDateTime(f.built_at)} (${ago} ago). The scheduled refresh has ` +
    "not completed since, so figures may be out of date."
  );
}
