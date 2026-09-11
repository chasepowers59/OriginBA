/**
 * Resolve a workstream's "Start here" canvases.
 *
 * The API sends `featured` as plain snapshot-id strings; the hero read `.snapshot_id`
 * off each one and rendered an empty card linking to /explore/undefined on every
 * workstream page. Both shapes are handled here so neither the API's form nor a future
 * report-specific entry can break the card again.
 */

type SnapshotLike = {
  id: string;
  label?: string;
  grain_description?: string;
  summary?: string;
};

type FeaturedEntry = string | { snapshot_id?: string; report_id?: string };

export type FeaturedCanvas = {
  snapshotId: string;
  reportId: string;
  label: string;
  description: string;
};

function entryId(entry: FeaturedEntry): { snapshotId: string; reportId: string } {
  if (typeof entry === "string") return { snapshotId: entry, reportId: "" };
  return { snapshotId: entry?.snapshot_id ?? "", reportId: entry?.report_id ?? "" };
}

export function featuredCanvases(
  featured: FeaturedEntry[] | undefined,
  snapshots: SnapshotLike[] | undefined,
): FeaturedCanvas[] {
  const available = snapshots ?? [];
  const entries: FeaturedEntry[] = featured?.length
    ? featured
    : available.slice(0, 3).map((s) => s.id);

  return entries
    .map(entryId)
    .filter((e) => Boolean(e.snapshotId))
    .map(({ snapshotId, reportId }) => {
      const snap = available.find((s) => s.id === snapshotId);
      return {
        snapshotId,
        reportId,
        // The id is a poor label but an honest one; blank was the bug.
        label: snap?.label ?? snapshotId,
        description: snap?.grain_description ?? snap?.summary ?? "",
      };
    });
}
