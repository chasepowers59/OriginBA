import { Suspense } from "react";
import { fetchSnapshotMetadata, fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { ExplorerPanel } from "@/components/ExplorerPanel";
import { LargeDomainBanner } from "@/components/LargeDomainBanner";
import { SampleRowsPanel } from "@/components/SampleRowsPanel";
import { SnapshotHeader } from "@/components/SnapshotHeader";

type PageProps = {
  params: Promise<{ snapshotId: string }>;
};

export default async function ExplorePage({ params }: PageProps) {
  const { snapshotId } = await params;
  const id = snapshotId.toUpperCase();

  let index;
  let metadata;
  let error: string | null = null;

  try {
    [index, metadata] = await Promise.all([fetchSnapshots(), fetchSnapshotMetadata(id)]);
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to load snapshot";
    index = {
      client: "demo",
      poc_enabled: [],
      db_configured: false,
      workstreams: [],
      snapshots: [],
    };
    metadata = null;
  }

  const enabled = index.snapshots;

  return (
    <AppShell
      snapshots={enabled}
      workstreams={index.workstreams ?? []}
      activeId={id}
      dbConfigured={index.db_configured}
    >
      {error || !metadata ? (
        <div className="glass-panel border-red-400/20 bg-red-500/10 px-4 py-3 text-red-200">
          {error ?? "Snapshot not found"}
        </div>
      ) : (
        <div className="space-y-6">
          <SnapshotHeader metadata={metadata} />
          {metadata.large_domain || metadata.skip_sample_rows ? (
            <LargeDomainBanner
              snapshotId={metadata.id}
              snapshotLabel={metadata.label}
              grainDescription={metadata.grain_description}
            />
          ) : (
            <SampleRowsPanel
              snapshotId={metadata.id}
              tableName={metadata.table_name}
              grainDescription={metadata.grain_description}
              skipSampleRows={metadata.skip_sample_rows}
            />
          )}
          <Suspense
            fallback={
              <div className="glass-panel p-8">
                <div className="loading-shimmer h-64 rounded-xl" />
              </div>
            }
          >
            <ExplorerPanel metadata={metadata} />
          </Suspense>
        </div>
      )}
    </AppShell>
  );
}
