/**
 * The workstreams an admin may grant, taken from the catalog rather than a list kept
 * by hand beside it. The hand-kept copy was a snapshot of the LEGACY catalog: it
 * offered `new_services` and omitted `assets`. Neither id is dead in general -- the
 * dbt catalog has assets (2 canvases) and no new_services, the CISADM catalog has
 * new_services (1 canvas) and no assets -- but the list was applied to every
 * organization, so for a dbt org it offered one workstream that grants nothing there
 * and hid one that grants two canvases. Access is filtered by exact workstream id, so
 * both halves failed silently.
 *
 * Deriving per organization is therefore not just drift-proofing: it is the only way
 * ONE list can be right for both deployment shapes.
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
