import { fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { WorkstreamDashboard } from "@/components/WorkstreamDashboard";
import { WORKSTREAM_ORDER } from "@/lib/businessLabels";
import { notFound } from "next/navigation";

type PageProps = {
  params: Promise<{ workstreamId: string }>;
};

export function generateStaticParams() {
  return WORKSTREAM_ORDER.map((id) => ({ workstreamId: id }));
}

export default async function WorkstreamPage({ params }: PageProps) {
  const { workstreamId } = await params;
  const id = workstreamId.toLowerCase();

  if (!WORKSTREAM_ORDER.includes(id as (typeof WORKSTREAM_ORDER)[number])) {
    notFound();
  }

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

  return (
    <AppShell
      snapshots={index.snapshots}
      workstreams={index.workstreams ?? []}
      dbConfigured={index.db_configured}
    >
      <WorkstreamDashboard
        workstreamId={id}
        snapshotCount={ws?.snapshot_count}
        workstreams={index.workstreams ?? []}
      />
    </AppShell>
  );
}
