"""Load snapshot explorer catalog JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "output" / "snapshot_explorer_catalog.json"

_catalog_cache: dict[str, Any] | None = None
_catalog_mtime: float | None = None


class CatalogError(RuntimeError):
    pass


# ONE CATALOG PER ENGINE, chosen by the organization.
#
# A Postgres tenant is served the dbt reporting layer -- 38 governed canvases with
# enforced contracts. An Oracle tenant is served the legacy CISADM snapshots, because the
# dbt canvases do not exist in that database and pointing a tenant at a catalog its
# warehouse cannot satisfy produces a portal full of tiles that error on click.
#
# This is what lets a client be migrated ONE AT A TIME: deploy their dbt warehouse, flip
# engine to postgres in config/portal_organizations.json, and they move. Nothing else
# changes and no other tenant is affected.
CATALOGS = {
    "dbt": ROOT / "output" / "catalog_dbt.json",
    "cisadm": ROOT / "output" / "catalog_cisadm.json",
}
_caches: dict[str, tuple[float, dict[str, Any]]] = {}


def catalog_name_for_org(organization_id: str | None) -> str:
    """Which catalog an organization reads. Defaults to the dbt layer."""
    if not organization_id:
        return "dbt"
    try:
        from api.organizations import get_organization
        org = get_organization(organization_id) or {}
    except Exception:  # noqa: BLE001
        return "dbt"
    name = str(org.get("catalog") or "").lower()
    return name if name in CATALOGS else "dbt"


def load_catalog(*, force: bool = False, organization_id: str | None = None) -> dict[str, Any]:
    """Load the catalog for this organization; auto-reloads when the file changes."""
    name = catalog_name_for_org(organization_id)
    path = CATALOGS[name]
    if not path.exists():
        # Fall back to whichever catalog IS present rather than failing the whole portal:
        # a half-migrated deployment should still serve the tenants it can.
        alt = next((p for p in CATALOGS.values() if p.exists()), None)
        if alt is None:
            raise CatalogError(
                f"Missing {path}. Run: python3 scripts/build_dbt_reporting_catalog.py")
        path = alt
    mtime = path.stat().st_mtime
    cached = _caches.get(name)
    if force or cached is None or cached[0] != mtime:
        _caches[name] = (mtime, json.loads(path.read_text(encoding="utf-8")))
    return _caches[name][1]


def reload_catalog() -> dict[str, Any]:
    """Force reload after rebuilding snapshot_explorer_catalog.json."""
    return load_catalog(force=True)


def list_snapshots(*, portal_only: bool = True, organization_id: str | None = None) -> list[dict[str, Any]]:
    catalog = load_catalog(organization_id=organization_id)
    order = catalog.get("workstream_order", [])
    order_index = {ws: idx for idx, ws in enumerate(order)}
    result = []
    for snapshot_id, meta in catalog["snapshots"].items():
        if portal_only and not meta.get("portal_enabled", True):
            continue
        result.append(
            {
                "id": snapshot_id,
                "label": meta["label"],
                "workstream": meta["workstream"],
                "workstream_label": meta.get("workstream_label"),
                "grain": meta["grain"],
                "grain_description": meta.get("grain_description"),
                "summary": meta.get("summary"),
                "trusted_measures": meta.get("trusted_measures", []),
                "required_date_field": meta.get("required_date_field"),
                "portal_enabled": meta.get("portal_enabled", True),
                "poc_enabled": meta.get("poc_enabled", False),
                "large_domain": meta.get("large_domain", False),
            }
        )
    return sorted(
        result,
        key=lambda row: (order_index.get(row["workstream"], 99), row["label"]),
    )


def list_business_processes(*, workstream: str | None = None, organization_id: str | None = None) -> list[dict[str, Any]]:
    catalog = load_catalog(organization_id=organization_id)
    processes = catalog.get("business_processes", [])
    if workstream:
        return [row for row in processes if row.get("workstream") == workstream]
    return processes


def list_workstreams(organization_id: str | None = None) -> list[dict[str, Any]]:
    catalog = load_catalog(organization_id=organization_id)
    labels = catalog.get("workstream_labels", {})
    order = catalog.get("workstream_order", [])
    featured = catalog.get("workstream_featured", {})
    processes = catalog.get("business_processes", [])
    processes_by_ws: dict[str, list[dict[str, Any]]] = {ws: [] for ws in order}
    for process in processes:
        processes_by_ws.setdefault(process["workstream"], []).append(process)
    snapshots = list_snapshots()
    grouped: dict[str, list[dict[str, Any]]] = {ws: [] for ws in order}
    for snap in snapshots:
        grouped.setdefault(snap["workstream"], []).append(snap)
    return [
        {
            "id": ws,
            "label": labels.get(ws, ws),
            "snapshot_count": len(grouped.get(ws, [])),
            "snapshots": grouped.get(ws, []),
            "processes": processes_by_ws.get(ws, []),
            "featured": featured.get(ws, []),
        }
        for ws in order
    ]


def get_snapshot(snapshot_id: str, organization_id: str | None = None) -> dict[str, Any]:
    catalog = load_catalog(organization_id=organization_id)
    # Try the id AS WRITTEN before upper-casing it. Upper was right while every snapshot
    # was an Oracle table; a dbt canvas is lowercase rpt_*, and forcing case made every
    # lookup miss with "Unknown snapshot" on a catalog that plainly contained it.
    for key in (snapshot_id, snapshot_id.upper()):
        if key in catalog["snapshots"]:
            return catalog["snapshots"][key]
    raise CatalogError(f"Unknown snapshot: {snapshot_id}")


def allowed_fields(snapshot: dict[str, Any]) -> set[str]:
    """The field ids a query may name, AS WRITTEN.

    Uppercasing was safe while every field was an Oracle column. The dbt canvases use
    quoted Title Case -- "Billed Amount" -- and upper-casing those produced a set nothing
    could match, so every query failed validation before it reached the database. The
    allow-list is what keeps a query safe, so it has to hold the real names.
    """
    return {field["id"] for field in snapshot.get("fields", [])}


def is_warehouse(snapshot: dict[str, Any]) -> bool:
    """True when this snapshot lives in the dbt warehouse rather than Oracle CISADM."""
    return str(snapshot.get("schema", "")).lower() != "cisadm"
