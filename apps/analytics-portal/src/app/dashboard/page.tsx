import { fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { ExecutiveDashboard } from "@/components/ExecutiveDashboard";
import { NlqSearchPanel } from "@/components/NlqSearchPanel";

export default async function DashboardPage() {
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

  return (
    <AppShell
      snapshots={index.snapshots}
      workstreams={index.workstreams ?? []}
      dbConfigured={index.db_configured}
      activeNav="dashboard"
    >
      <ExecutiveDashboard variant="full" initialDays={30} />
      <div className="mt-8">
        <NlqSearchPanel />
      </div>
      <p className="mt-8 text-sm text-slate-500">
        Click any metric to drill into the Ad Hoc Builder, detail table, and council pack export
        for that domain. Toggle prior-period compare to see period-over-period movement.
      </p>
    </AppShell>
  );
}
