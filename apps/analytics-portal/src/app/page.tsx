import { fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { HomeDashboard } from "@/components/HomeDashboard";

// "/" is the Executive Overview — the app's single dashboard surface. Workstream
// browsing lives in the Library's filter rail (/reports).
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
      {error ? (
        <p className="mb-6 rounded-xl border border-warn bg-warn-bg px-4 py-3 text-sm text-warn">
          Connection unavailable — start the analytics API to load the full catalog.
        </p>
      ) : null}
      <HomeDashboard />
    </AppShell>
  );
}
