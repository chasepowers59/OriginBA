import { redirect } from "next/navigation";

/** Renamed to /dashboards/[id]. Preserve old bookmarks. */
export default async function LegacyEditCustomDashboardRedirect({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/dashboards/${id}`);
}
