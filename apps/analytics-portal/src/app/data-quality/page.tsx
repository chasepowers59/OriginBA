import { fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { DataQualityBoard } from "@/components/DataQualityBoard";

export default async function DataQualityPage() {
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
      activeNav="dq"
    >
      <DataQualityBoard />
    </AppShell>
  );
}
