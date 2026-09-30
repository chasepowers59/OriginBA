/** Content packs (api/content_packs.py): an organization's shared views and dashboards as one file. */

export type PackImportResult = {
  dry_run: boolean;
  views: { imported: string[]; skipped: { title: string; reason: string }[] };
  dashboards: { imported: string[]; skipped: { title: string; reason: string }[] };
};

export function packFilename(org: string, day: string, folder: string | null): string {
  const part = folder ? `-${folder.replace(/[^A-Za-z0-9]+/g, "_").replace(/^_|_$/g, "")}` : "";
  return `originba-pack-${org}${part}-${day}.json`;
}

const count = (n: number, one: string) => `${n} ${one}${n === 1 ? "" : "s"}`;

export function packSummary(r: PackImportResult): string {
  const added = r.views.imported.length + r.dashboards.imported.length;
  const skipped = r.views.skipped.length + r.dashboards.skipped.length;
  const verb = r.dry_run ? "will be" : "were";
  const head = added
    ? `${count(r.views.imported.length, "view")} and ${count(r.dashboards.imported.length, "dashboard")} ${verb} added.`
    : `Nothing ${verb} added.`;
  return skipped ? `${head} ${count(skipped, "item")} ${r.dry_run ? "will be" : "were"} skipped.` : head;
}
