import { Suspense } from "react";
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

  const workstreams = index.workstreams ?? [];

  return (
    <AppShell
      snapshots={index.snapshots}
      workstreams={workstreams}
      dbConfigured={index.db_configured}
      activeNav="reports"
    >
      <Suspense fallback={<div className="loading-shimmer h-48 rounded-2xl" />}>
        <ReportLibrary />
      </Suspense>
    </AppShell>
  );
}
