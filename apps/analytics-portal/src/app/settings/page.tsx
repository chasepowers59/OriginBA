import { fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { SettingsTabs } from "@/components/SettingsTabs";

export default async function SettingsPage() {
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
      activeNav="settings"
    >
      <SettingsTabs />
    </AppShell>
  );
}
