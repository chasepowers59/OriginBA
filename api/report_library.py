"""Build the utility report library from the catalog: the folder tree, and the packs."""

from __future__ import annotations

from typing import Any, Callable

from api.snapshot_catalog import CatalogError, load_catalog, resolve_snapshot_key


def _card(catalog: dict[str, Any], ref: dict[str, Any]) -> dict[str, Any] | None:
    """One {snapshot_id, report_id} reference as a library card, or None if it does not resolve."""
    snapshots = catalog.get("snapshots", {})
    # Do NOT force case. Uppercasing was safe while every snapshot was an
    # Oracle table (CISADM names are uppercase); the dbt canvases are lowercase
    # rpt_* and every lookup missed, so the library came back empty with no
    # error. Try the id as written, then upper, for references saved upper-cased.
    snap_id = resolve_snapshot_key(snapshots, str(ref.get("snapshot_id", "")))
    report_id = ref.get("report_id")
    snap = snapshots.get(snap_id)
    if not snap or not report_id:
        return None
    premade = next((r for r in snap.get("premade_reports") or [] if r.get("id") == report_id), None)
    if not premade:
        return None
    return {
        "snapshot_id": snap_id,
        "snapshot_label": snap.get("label", snap_id),
        "workstream": snap.get("workstream"),
        "workstream_label": catalog.get("workstream_labels", {}).get(snap.get("workstream"), ""),
        "report_id": report_id,
        "title": premade.get("title", report_id),
        "description": premade.get("description", ""),
        "chart_type": premade.get("chart_type", "bar"),
        # The catalog knows the SHAPE of each report; the library used to drop
        # it, so a card said why a question matters and never what it returns.
        "dimensions": premade.get("dimensions") or [],
        "measures": premade.get("measures") or [],
        "filters": premade.get("filters") or [],
        "grain_description": snap.get("grain_description", ""),
        "explore_url": f"/explore/{snap_id}?report={report_id}",
    }


def _with_totals(library: dict[str, Any]) -> dict[str, Any]:
    return {
        **library,
        "pack_count": len(library["packs"]),
        # The library as the reader browses it: the folder tree.
        "report_count": sum(f["report_count"] for f in library["folders"]),
    }


def _group(meta: dict[str, Any], cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The group as a one-item list, or none at all: an empty folder reads as a broken one."""
    return [{**meta, "report_count": len(cards), "reports": cards}] if cards else []


def scope_library(library: dict[str, Any], keep: Callable[[list[dict]], list[dict]]) -> dict[str, Any]:
    """Narrow every card, in packs and folders alike, to what `keep` returns."""
    def narrowed(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [g for group in groups for g in _group(group, keep(group.get("reports") or []))]

    return _with_totals({**library, "packs": narrowed(library.get("packs") or []),
                         "folders": narrowed(library.get("folders") or [])})


def build_report_library(organization_id: str | None = None) -> dict[str, Any]:
    catalog = load_catalog(organization_id=organization_id)
    packs: list[dict[str, Any]] = []
    for pack in catalog.get("report_library_packs") or []:
        cards = [c for ref in pack.get("reports") or [] if (c := _card(catalog, ref))]
        packs += _group({k: pack.get(k) for k in ("id", "title", "description", "audience")}, cards)
    # Folders and their reports keep catalog order, which puts each folder's essentials first.
    folders: list[dict[str, Any]] = []
    for folder in catalog.get("report_library") or []:
        cards = [{**c, "essential": bool(ref.get("essential"))}
                 for ref in folder.get("reports") or [] if (c := _card(catalog, ref))]
        folders += _group({"id": folder.get("id"), "title": folder.get("title"),
                           "description": folder.get("description", "")}, cards)
    return _with_totals({"client": catalog.get("client", "demo"), "packs": packs, "folders": folders})


def get_report_library(organization_id: str | None = None) -> dict[str, Any]:
    try:
        return build_report_library(organization_id)
    except CatalogError as exc:
        return _with_totals({"client": "demo", "packs": [], "folders": [], "error": str(exc)})
