import { fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { DatabaseWorkspace } from "@/components/DatabaseWorkspace";

export default async function DatabasePage({
  searchParams,
}: {
  searchParams: Promise<{ table?: string }>;
}) {
  const { table } = await searchParams;
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
      activeNav="database"
    >
      <div className="space-y-4">
        <div>
          {/* The scope sentence lives in the workspace, which is where the engine is
              known: a Postgres org has no CISADM to offer. */}
          <h1 className="portal-heading text-2xl font-bold tracking-tight">SQL</h1>
        </div>
        <DatabaseWorkspace dbConfigured={index.db_configured} initialTable={table} />
      </div>
    </AppShell>
  );
}
