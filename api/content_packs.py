"""Content packs: an organization's shared saved views and dashboards as one JSON file that
another organization can import -- the portal's equivalent of Jaspersoft's repository
export/import, which is how the Standard Offering reaches each client.

C2M differs by client and release, so an import checks every item against the TARGET
organization's catalog: a view or tile naming a canvas, column or ready-to-run report the
client does not have is skipped with its reason, never saved broken. Private items never
leave; imported items belong to the admin who imported them, shared with the organization.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from api.auth.workstream_access import can_access_snapshot, filter_dashboards_for_auth
from api.ownership import stamp
from api.saved_dashboards import DashboardError, create_dashboard, list_dashboards
from api.saved_views import SavedViewError, create_saved_view, list_saved_views
from api.snapshot_catalog import CatalogError, get_snapshot

FORMAT = "originba-content-pack/1"

# what an item is, never who or where it was
_VIEW_KEYS = ("snapshot_id", "snapshot_label", "title", "kind", "report_id", "dimensions", "measure_field",
              "measure_agg", "measures", "filters", "chart_type", "date_preset", "date_start", "date_end",
              "scope_field", "scope_value", "folder")
_BOARD_KEYS = ("title", "description", "days", "folder")
_TILE_KEYS = ("slot", "title", "visual", "snapshot_id", "report_id", "dimensions", "measure_field", "measure_agg",
              "chart_type", "time_grain")


def _shared(items: list[dict[str, Any]], folder: str | None) -> list[dict[str, Any]]:
    return [i for i in items if i.get("visibility") != "private" and (folder is None or i.get("folder") == folder)]


def build_pack(organization_id: str, ctx: Any, folder: str | None = None) -> dict[str, Any]:
    """Only what the caller's workstream grants show them: a billing-only editor exported the
    debt dashboards GET /portal/dashboards withholds."""
    views = [{k: v.get(k) for k in _VIEW_KEYS} for v in _shared(list_saved_views(organization_id), folder)
             if can_access_snapshot(ctx, str(v.get("snapshot_id") or ""))]
    boards = [{**{k: b.get(k) for k in _BOARD_KEYS}, "tiles": [{k: t.get(k) for k in _TILE_KEYS} for t in b.get("tiles") or []]}
              for b in filter_dashboards_for_auth(_shared(list_dashboards(organization_id), folder), ctx)]
    return {"format": FORMAT, "exported_at": datetime.now(timezone.utc).isoformat(),
            "source_organization": organization_id, "exported_by": ctx.email, "folder": folder,
            "views": views, "dashboards": boards}


def _fields(item: dict[str, Any]) -> set[str]:
    named = list(item.get("dimensions") or [])
    named += [item.get("measure_field"), item.get("scope_field")]
    named += [m.get("field") for m in item.get("measures") or [] if isinstance(m, dict)]
    named += [f.get("field") for f in item.get("filters") or [] if isinstance(f, dict)]
    return {str(n) for n in named if n and n != "*"}


def _problem(item: dict[str, Any], organization_id: str) -> str | None:
    """Why this view or tile cannot work in this organization, or None when it can."""
    snapshot_id = str(item.get("snapshot_id") or "")
    try:
        snapshot = get_snapshot(snapshot_id, organization_id)
    except CatalogError:
        return f"this organization has no {snapshot_id} report data"
    have = {f.get("id") for f in snapshot.get("fields") or []}
    missing = sorted(_fields(item) - have)
    if missing:
        return f"{snapshot.get('label') or snapshot_id} has no {', '.join(missing)} here"
    report = item.get("report_id")
    if report and report not in {r.get("id") for r in snapshot.get("premade_reports") or []}:
        return f"the ready-to-run report {report} is not available here"
    return None


def _note(bucket: dict[str, list], title: str, reason: str | None) -> None:
    if reason:
        bucket["skipped"].append({"title": title, "reason": reason})
    else:
        bucket["imported"].append(title)


def import_pack(pack: dict[str, Any], organization_id: str, ctx: Any, dry_run: bool) -> dict[str, Any]:
    if not isinstance(pack, dict) or pack.get("format") != FORMAT:
        raise HTTPException(status_code=400, detail="This file is not an Origin BA content pack.")
    out = {"dry_run": dry_run, "views": {"imported": [], "skipped": []}, "dashboards": {"imported": [], "skipped": []}}

    have = {(v.get("snapshot_id"), v.get("title")) for v in list_saved_views(organization_id)}
    for view in pack.get("views") or []:
        title = str(view.get("title") or "")
        reason = ("already in this organization" if (view.get("snapshot_id"), title) in have
                  else _problem(view, organization_id))
        if reason is None and not dry_run:
            try:
                create_saved_view(stamp({**{k: view.get(k) for k in _VIEW_KEYS}, "visibility": "organization"}, ctx),
                                  organization_id=organization_id)
            except SavedViewError as exc:
                reason = str(exc)
        _note(out["views"], title, reason)
        have.add((view.get("snapshot_id"), title))

    boards = {b.get("title") for b in list_dashboards(organization_id)}
    for board in pack.get("dashboards") or []:
        title = str(board.get("title") or "")
        tiles = board.get("tiles") or []
        broken = [f"tile {t.get('title')!r}: {why}" for t in tiles if (why := _problem(t, organization_id))]
        reason = "already in this organization" if title in boards else "; ".join(broken) or None
        if reason is None and not dry_run:
            try:
                create_dashboard(stamp({**{k: board.get(k) for k in _BOARD_KEYS}, "tiles": tiles,
                                        "visibility": "organization"}, ctx), organization_id=organization_id)
            except DashboardError as exc:
                reason = str(exc)
        _note(out["dashboards"], title, reason)
        boards.add(title)
    return out
