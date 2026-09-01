"""Load snapshot explorer catalog JSON."""

from __future__ import annotations

import json
import re
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
                f"Missing {path}. The generator lives with the contracts it derives from: "
                f"run `.venv/bin/python scripts/build_portal_catalog.py` in originba_dbt.")
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
    # SAME catalog as the workstreams above. Defaulting here served the dbt
    # canvases to an Oracle tenant whose workstreams came from CISADM.
    snapshots = list_snapshots(organization_id=organization_id)
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


def resolve_snapshot_key(snapshots: Any, snapshot_id: str) -> str:
    """The key `snapshot_id` actually names, whatever case it arrived in.

    Try it AS WRITTEN first. Upper was right while every snapshot was an Oracle table; a
    dbt canvas is lowercase rpt_*, and forcing case made every lookup miss with "Unknown
    snapshot" on a catalog that plainly contained it. Lower is here for the dashboards
    saved while _validate_tiles upper-cased the id -- user state has no migration, so the
    reader forgives what the writer broke.

    One function because there were two of these with DIFFERENT tolerance (the library
    tried two cases, this tried three), which is how the next silent miss gets in.
    Returns the id unchanged when nothing matches, so callers keep their own error.
    """
    for key in (snapshot_id, snapshot_id.upper(), snapshot_id.lower()):
        if key in snapshots:
            return key
    return snapshot_id


def get_snapshot(snapshot_id: str, organization_id: str | None = None) -> dict[str, Any]:
    catalog = load_catalog(organization_id=organization_id)
    key = resolve_snapshot_key(catalog["snapshots"], snapshot_id)
    if key in catalog["snapshots"]:
        return catalog["snapshots"][key]
    raise CatalogError(f"Unknown snapshot: {snapshot_id}")


# Columns that may never be queryable, whatever a catalog says. The SQL workspace
# fences these; the governed query API allow-lists whatever the catalog declares, so
# a catalog carrying one re-opened the same door the fence closes (audit H4). This
# denylist is applied at the ALLOW-LIST, so a regenerated or hand-edited catalog
# cannot re-expose them.
#
# Matched as whole words against the field id, upper-cased and with separators
# normalised, so it catches ALERT_INFO, ACCT_ALERT_INFO, "Alert Info" and
# "Bank Routing Number (MICR ID)" alike -- while leaving columns that merely
# CONTAIN a word ("Open Alert Count", "Has Alert") alone.
PROTECTED_COLUMNS = ("MICR ID", "MICR", "WEB PASSWD", "ALERT INFO", "EXT ACCT ID")
_PROTECTED_RE = re.compile(
    r"(?<![A-Z0-9])(?:" + "|".join(c.replace(" ", r"\s+") for c in PROTECTED_COLUMNS)
    + r")(?![A-Z0-9])"
)


def is_protected_column(field_id: str) -> bool:
    """True when this field id names a protected column in any of our spellings."""
    normalised = re.sub(r"[_\-]+", " ", str(field_id)).upper()
    normalised = re.sub(r"[^A-Z0-9 ]+", " ", normalised)
    return bool(_PROTECTED_RE.search(normalised))


def allowed_fields(snapshot: dict[str, Any]) -> set[str]:
    """The field ids a query may name, AS WRITTEN, minus the protected columns.

    Uppercasing was safe while every field was an Oracle column. The dbt canvases use
    quoted Title Case -- "Billed Amount" -- and upper-casing those produced a set nothing
    could match, so every query failed validation before it reached the database. The
    allow-list is what keeps a query safe, so it has to hold the real names.
    """
    return {field["id"] for field in snapshot.get("fields", [])
            if not is_protected_column(field.get("id", ""))}


def is_warehouse(snapshot: dict[str, Any]) -> bool:
    """True when this snapshot lives in the dbt warehouse rather than Oracle CISADM."""
    return str(snapshot.get("schema", "")).lower() != "cisadm"


def org_backend(organization_id: str | None) -> tuple[str, str]:
    """(engine, catalog) for an org.

    THREE shapes exist since 2026-08-28, so the schema-implies-engine shortcut
    (is_warehouse == Postgres) is no longer safe on its own:

        postgres + dbt     the client's Postgres dbt warehouse (deployment shape A)
        oracle   + cisadm  the legacy *_RPT_CURR snapshots (pre-migration)
        oracle   + dbt     the dbt canvases built INSIDE the client's own Oracle
                           instance (ORIGINBA_REPORTING beside CISADM -- the
                           in-database deployment shape, no CDC)
    """
    catalog = catalog_name_for_org(organization_id)
    engine = "postgres" if catalog == "dbt" else "oracle"
    if organization_id:
        try:
            from api.organizations import get_organization
            org = get_organization(organization_id) or {}
            declared = str(org.get("engine") or "").lower()
            if declared in ("postgres", "oracle"):
                engine = declared
        except Exception:  # noqa: BLE001
            pass
    return engine, catalog


def snapshot_backend(snapshot: dict[str, Any],
                     organization_id: str | None) -> tuple[str, str, str]:
    """(backend, dialect, schema) for running THIS snapshot for THIS org.

    backend  which driver executes: 'postgres' (warehouse pool) or 'oracle'
    dialect  what build_query emits: 'postgres' | 'oracle_dbt' | 'oracle'
    schema   the qualification the SQL uses

    The oracle_dbt dialect exists because the in-database canvases keep their
    quoted Title-Case columns ("Account ID" is identical SQL in both engines)
    while binds, date functions and table casing follow Oracle rules.
    """
    if not is_warehouse(snapshot):
        return "oracle", "oracle", str(snapshot.get("schema", "CISADM"))
    engine, _catalog = org_backend(organization_id)
    if engine == "oracle":
        return "oracle", "oracle_dbt", "ORIGINBA_REPORTING"
    return "postgres", "postgres", str(snapshot.get("schema", "reporting"))
