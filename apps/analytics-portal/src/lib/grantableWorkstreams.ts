/**
 * The workstreams an admin may grant, taken from the catalog rather than a list kept
 * by hand beside it. The hand-kept copy had drifted both ways -- it offered
 * `new_services`, which no canvas carries, and omitted `assets`, which two do -- and
 * because access is filtered by exact workstream id, both halves failed silently.
 *
 * `workstream_order` is the source of truth. `workstream_labels` is not: it still
 * carries labels for workstreams the catalog no longer orders.
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
