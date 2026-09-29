import { fetchSnapshots } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { LettersWorkspace } from "@/components/letters/LettersWorkspace";

export default async function LettersPage() {
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
      activeNav="letters"
    >
      <LettersWorkspace />
    </AppShell>
  );
}
