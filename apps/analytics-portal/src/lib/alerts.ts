/** Which alerts a dialog shows, and which conditions it offers (api/kpi_alerts.py). */

const ALL = ["above", "below", "pct_change_above", "pct_change_below"];

export function alertsFor<T extends { kpi_id?: string | null; saved_view_id?: string | null }>(
  alerts: T[],
  viewId: string | null,
): T[] {
  return alerts.filter((a) => (viewId ? a.saved_view_id === viewId : !a.saved_view_id));
}

/** A saved view has no prior period defined, so it is watched above or below a threshold. */
export function alertConditions(forView: boolean): string[] {
  return forView ? ALL.slice(0, 2) : ALL;
}
