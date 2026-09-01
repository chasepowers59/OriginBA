import { Suspense } from "react";
import { fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { ReportLibrary } from "@/components/ReportLibrary";
import { WorkstreamSidebar, WorkstreamSidebarNav } from "@/components/WorkstreamExplorer";

export default async function ReportsPage() {
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

  const workstreams = index.workstreams ?? [];

  return (
    <AppShell
      snapshots={index.snapshots}
      workstreams={workstreams}
      dbConfigured={index.db_configured}
      activeNav="reports"
    >
      {/* Library is the one browseable catalog: the workstream tree is the filter rail,
          the governed report packs are the content. This is the tree's single home now
          that the global sidebar is gone. */}
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <aside className="no-print lg:sticky lg:top-24 lg:self-start">
          <div className="glass-panel p-4">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-heading-accent">
              Workstreams
            </p>
            <Suspense fallback={<WorkstreamSidebar workstreams={workstreams} />}>
              <WorkstreamSidebarNav workstreams={workstreams} />
            </Suspense>
          </div>
        </aside>
        <div className="min-w-0">
          <ReportLibrary />
        </div>
      </div>
    </AppShell>
  );
}
