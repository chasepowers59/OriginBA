"""Filter catalog navigation by user workstream access groups.

ONE rule decides access and it lives in service.workstreams_allowed: an empty grant or
"*" means every workstream, anything else is a membership test. Every filter here
delegates to it rather than re-deciding, because the half that re-decided disagreed on
the empty case and would have returned an empty portal to a user the permission check
had just approved (tests/test_workstream_filter_agreement.py).

The `if "*" in ctx.workstreams: return ...` lines are a fast path, not a second rule --
the fall-through delegates and handles empty correctly. Do not "fix" them into
membership tests.
"""

from __future__ import annotations

from typing import Any

from api.auth.dependencies import AuthContext
from api.auth.service import workstreams_allowed
from api.snapshot_catalog import CatalogError, get_snapshot


def snapshot_workstream(snapshot_id: str, organization_id: str | None = None) -> str:
    """The workstream a snapshot belongs to, IN THE CALLER'S CATALOG.

    organization_id is load-bearing, not decorative. When a second catalog existed,
    calling get_snapshot() without the org resolved every authorization lookup against
    the default one; the shapes shared no snapshot ids, so on the orgs using the other
    catalog the lookup missed, returned "", and an empty workstream fails every
    restricted grant -- a user granted "finance" was refused their own finance
    snapshots, and their metrics and tiles filtered to empty in silence. Invisible in
    development because "*" and an empty grant never reach the comparison. There is one
    catalog now; the org is still threaded because that is what the lookup means.

    The id is passed AS WRITTEN: resolve_snapshot_key already tries all three cases, and
    upper-casing a lowercase dbt canvas id is the habit that broke lookups elsewhere.
    """
    try:
        return str(get_snapshot(snapshot_id, organization_id=organization_id)
                   .get("workstream", ""))
    except CatalogError:
        return ""


def can_access_snapshot(ctx: AuthContext, snapshot_id: str) -> bool:
    return ctx.can_access_workstream(
        snapshot_workstream(snapshot_id, ctx.effective_organization_id()))


def filter_workstreams_for_auth(workstreams: list[dict[str, Any]], ctx: AuthContext) -> list[dict[str, Any]]:
    if "*" in ctx.workstreams:
        return workstreams
    return [ws for ws in workstreams if workstreams_allowed(ctx.workstreams, ws.get("id", ""))]


def filter_snapshots_for_auth(snapshots: list[dict[str, Any]], ctx: AuthContext) -> list[dict[str, Any]]:
    # Delegates rather than re-testing "*": workstreams_allowed is the authority the
    # permission check uses, and it also treats an EMPTY grant as full access. Set
    # membership alone disagreed with it there and would have handed back an empty
    # portal to a user ctx.can_access_workstream had just approved.
    return [snap for snap in snapshots
            if workstreams_allowed(ctx.workstreams, snap.get("workstream", ""))]


def assert_workstream_access(ctx: AuthContext, workstream_id: str) -> None:
    if not ctx.can_access_workstream(workstream_id):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail=f"Access denied for workstream: {workstream_id}")


# filter_kpis_for_auth used to sit here, unused. executive_dashboard has its own
# _kpis_for_workstreams and that one already handled an empty grant correctly, so of
# the two implementations the dead one was the weaker.


def filter_nlq_metrics_for_auth(metrics: list[dict[str, Any]], ctx: AuthContext) -> list[dict[str, Any]]:
    if "*" in ctx.workstreams:
        return metrics
    return [m for m in metrics if can_access_snapshot(ctx, str(m.get("snapshot_id", "")))]


def filter_dashboard_for_auth(board: dict[str, Any], ctx: AuthContext) -> dict[str, Any] | None:
    if "*" in ctx.workstreams:
        return board
    tiles = [
        tile
        for tile in board.get("tiles") or []
        if can_access_snapshot(ctx, str(tile.get("snapshot_id", "")))
    ]
    if not tiles:
        return None
    return {**board, "tiles": tiles}


def filter_dashboards_for_auth(boards: list[dict[str, Any]], ctx: AuthContext) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for board in boards:
        scoped = filter_dashboard_for_auth(board, ctx)
        if scoped:
            filtered.append(scoped)
    return filtered


def assert_snapshot_access(ctx: AuthContext, snapshot_id: str) -> None:
    if not can_access_snapshot(ctx, snapshot_id):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail=f"Access denied for snapshot: {snapshot_id}")


def filter_report_library_for_auth(library: dict[str, Any], ctx: AuthContext) -> dict[str, Any]:
    if not ctx.workstreams or "*" in ctx.workstreams:
        return library
    packs: list[dict[str, Any]] = []
    for pack in library.get("packs") or []:
        # workstreams_allowed, not set membership — see filter_snapshots_for_auth.
        reports = [r for r in pack.get("reports") or []
                   if workstreams_allowed(ctx.workstreams, r.get("workstream", ""))]
        if not reports:
            continue
        packs.append({**pack, "reports": reports, "report_count": len(reports)})
    return {
        **library,
        "packs": packs,
        "pack_count": len(packs),
        "report_count": sum(p.get("report_count", 0) for p in packs),
    }
