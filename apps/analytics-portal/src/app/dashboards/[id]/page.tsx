import { Suspense } from "react";
import { fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { CustomDashboardPage } from "@/components/CustomDashboardPage";

type PageProps = { params: Promise<{ id: string }> };

export default async function EditCustomDashboardPage({ params }: PageProps) {
  const { id } = await params;
  let index;
  try {
    index = await fetchSnapshots();
  } catch {
    index = { client: "demo", poc_enabled: [], db_configured: false, workstreams: [], snapshots: [] };
  }
  return (
    <AppShell
      snapshots={index.snapshots}
      workstreams={index.workstreams ?? []}
      dbConfigured={index.db_configured}
      activeNav="custom"
    >
      <Suspense
        fallback={
          <div className="glass-panel p-8">
            <div className="loading-shimmer h-64 rounded-xl" />
          </div>
        }
      >
        <CustomDashboardPage dashboardId={id} />
      </Suspense>
    </AppShell>
  );
}
