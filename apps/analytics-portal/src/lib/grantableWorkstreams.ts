/**
 * The workstreams an admin may grant, taken from the catalog rather than a list kept
 * by hand beside it. The hand-kept copy once offered a workstream the catalog did not
 * carry and omitted `assets`, which it did; access is filtered by exact workstream id,
 * so the first granted nothing and the second could not be granted at all, both in
 * silence. Deriving from the catalog is what keeps the picker and the data in step.
 *
 * `workstream_order` is the source of truth. `workstream_labels` is not: it carries
 * labels for workstreams this organization's catalog does not order.
 */

export type GrantableWorkstream = { id: string; label: string };

function humanize(id: string): string {
  return id
    .split(/[_-]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function grantableWorkstreams(
  order: string[] | undefined,
  labels: Record<string, string> | undefined,
): GrantableWorkstream[] {
  return (order ?? [])
    .filter((id) => Boolean(id))
    .map((id) => ({ id, label: labels?.[id] ?? humanize(id) }));
}
