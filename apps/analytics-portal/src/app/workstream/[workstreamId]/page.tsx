import { fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { WorkstreamDashboard } from "@/components/WorkstreamDashboard";
import { WORKSTREAM_ORDER } from "@/lib/businessLabels";
import { notFound } from "next/navigation";

type PageProps = {
  params: Promise<{ workstreamId: string }>;
};

// Prerender hints only. Which workstreams EXIST is decided per organization by the
// catalog, below -- gating on this list is what made /workstream/assets a 404 while
// a workstream present in the catalog 404'd, because the list was a hand-kept copy.
export function generateStaticParams() {
  return WORKSTREAM_ORDER.map((id) => ({ workstreamId: id }));
}

export default async function WorkstreamPage({ params }: PageProps) {
  const { workstreamId } = await params;
  const id = workstreamId.toLowerCase();

  let index;
  try {
    index = await fetchSnapshots();
  } catch {
    index = {
      client: "demo",
      poc_enabled: [],
      db_configured: false,
      workstreams: [],
      snapshots: [],
    };
  }

  const ws = index.workstreams?.find((w) => w.id === id);
  // The catalog is the authority on what this organization has. Only 404 when it
  // answered and does not know the id -- an unreachable API must not turn every
  // workstream into a missing page.
  if (!ws && (index.workstreams?.length ?? 0) > 0) {
    notFound();
  }

  return (
    <AppShell
      snapshots={index.snapshots}
      workstreams={index.workstreams ?? []}
      dbConfigured={index.db_configured}
      activeNav="reports"
    >
      <WorkstreamDashboard
        workstreamId={id}
        snapshotCount={ws?.snapshot_count}
        workstreams={index.workstreams ?? []}
      />
    </AppShell>
  );
}
