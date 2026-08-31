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
          <h1 className="portal-heading text-2xl font-bold tracking-tight">SQL</h1>
          <p className="portal-text-muted mt-1 max-w-2xl text-sm">
            Query the CISADM schema you know from CIS. Start with a premade business question or
            browse the table guide, fetch results in 50-row pages, and chart grouped results.
          </p>
        </div>
        <DatabaseWorkspace dbConfigured={index.db_configured} initialTable={table} />
      </div>
    </AppShell>
  );
}
