import { fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { HomeDashboard } from "@/components/HomeDashboard";

// "/" is the Executive Overview — the app's single dashboard surface. Workstream
// browsing lives in the shell's sidebar, so this page doesn't repeat it below.
export default async function HomePage() {
  let index;
  let error: string | null = null;
  try {
    index = await fetchSnapshots();
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to load snapshots";
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
      activeNav="home"
    >
      <HomeDashboard />
      {error ? (
        <p className="mb-6 rounded-xl border border-amber-400/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-200">
          Connection unavailable — start the analytics API to load the full catalog.
        </p>
      ) : null}
    </AppShell>
  );
}
