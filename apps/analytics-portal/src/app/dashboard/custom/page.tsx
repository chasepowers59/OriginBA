import { redirect } from "next/navigation";

/** Renamed to /dashboards. Preserve old bookmarks and pinned-report links. */
export default async function LegacyCustomDashboardRedirect({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (typeof v === "string") qs.set(k, v);
    else if (Array.isArray(v) && v[0]) qs.set(k, v[0]);
  }
  const query = qs.toString();
  redirect(query ? `/dashboards/new?${query}` : "/dashboards");
}
