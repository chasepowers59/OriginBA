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


def load_catalog(*, force: bool = False) -> dict[str, Any]:
    """Load catalog JSON; auto-reloads when the file changes on disk."""
    global _catalog_cache, _catalog_mtime
    if not CATALOG_PATH.exists():
        raise CatalogError(
            f"Missing {CATALOG_PATH}. Run: python3 scripts/build_snapshot_explorer_catalog.py"
        )
    mtime = CATALOG_PATH.stat().st_mtime
    if force or _catalog_cache is None or _catalog_mtime != mtime:
        _catalog_cache = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        _catalog_mtime = mtime
    return _catalog_cache


def reload_catalog() -> dict[str, Any]:
    """Force reload after rebuilding snapshot_explorer_catalog.json."""
    return load_catalog(force=True)


def list_snapshots(*, portal_only: bool = True) -> list[dict[str, Any]]:
    catalog = load_catalog()
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


def list_business_processes(*, workstream: str | None = None) -> list[dict[str, Any]]:
    catalog = load_catalog()
    processes = catalog.get("business_processes", [])
    if workstream:
        return [row for row in processes if row.get("workstream") == workstream]
    return processes


def list_workstreams() -> list[dict[str, Any]]:
    catalog = load_catalog()
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


def get_snapshot(snapshot_id: str) -> dict[str, Any]:
    catalog = load_catalog()
    key = snapshot_id.upper()
    if key not in catalog["snapshots"]:
        raise CatalogError(f"Unknown snapshot: {snapshot_id}")
    return catalog["snapshots"][key]


def allowed_fields(snapshot: dict[str, Any]) -> set[str]:
    return {field["id"].upper() for field in snapshot.get("fields", [])}
