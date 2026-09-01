import { fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { VisualBuilder } from "@/components/builder/VisualBuilder";

export default async function BuildPage({
  searchParams,
}: {
  searchParams: Promise<{ canvas?: string; report?: string; view?: string }>;
}) {
  const { canvas, report, view } = await searchParams;
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
      activeNav="build"
    >
      <section className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-600 dark:text-sky-400">
            Visual builder
          </p>
          <h1 className="portal-heading mt-1 text-2xl font-bold">Build a view</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Pick a reporting canvas, drag columns onto the shelves, and choose a
            visualization — or start from a governed business question.
          </p>
        </div>
        <VisualBuilder initialCanvas={canvas} initialReport={report} initialView={view} />
      </section>
    </AppShell>
  );
}
