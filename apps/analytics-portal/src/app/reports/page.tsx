import { fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { ReportLibrary } from "@/components/ReportLibrary";

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

  return (
    <AppShell
      snapshots={index.snapshots}
      workstreams={index.workstreams ?? []}
      dbConfigured={index.db_configured}
      activeNav="reports"
    >
      <ReportLibrary />
    </AppShell>
  );
}
