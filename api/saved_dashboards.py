"""Multi-tile custom dashboards for the analytics portal."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = ROOT / "data" / "analytics_portal" / "saved_dashboards.json"
MAX_DASHBOARDS = 12
MAX_TILES = 4

from api import portal_state_store as _pss  # noqa: E402
_COLLECTION = "saved_dashboards"


class DashboardError(ValueError):
    pass


def _ensure_store() -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        STORE_PATH.write_text(json.dumps({"dashboards": []}, indent=2), encoding="utf-8")


def _load_store() -> dict[str, Any]:
    _ensure_store()
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))


def _save_store(data: dict[str, Any]) -> None:
    _ensure_store()
    STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _matches_scope(board: dict[str, Any], organization_id: str) -> bool:
    return board.get("organization_id", board.get("client_id")) == organization_id


def _validate_tiles(tiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(tiles) > MAX_TILES:
        raise DashboardError(f"Maximum {MAX_TILES} tiles allowed")
    cleaned: list[dict[str, Any]] = []
    for raw in tiles:
        # AS GIVEN. Upper-casing was right while every snapshot was an Oracle table;
        # a dbt canvas is lowercase rpt_*, so this stored RPT_BILL_SEGMENT and the tile
        # then 404'd on lookup -- the dashboard saved and could not render.
        snapshot_id = str(raw.get("snapshot_id", "")).strip()
        if not snapshot_id:
            raise DashboardError("Each tile requires snapshot_id")
        visual = str(raw.get("visual", "chart")).lower()
        if visual not in {"chart", "kpi", "table"}:
            raise DashboardError(f"Invalid tile visual: {visual}")
        cleaned.append(
            {
                "id": raw.get("id") or str(uuid.uuid4()),
                "slot": int(raw.get("slot", len(cleaned))),
                "title": str(raw.get("title") or snapshot_id),
                "visual": visual,
                "snapshot_id": snapshot_id,
                "report_id": raw.get("report_id"),
                "dimensions": raw.get("dimensions") or [],
                "measure_field": raw.get("measure_field"),
                "measure_agg": raw.get("measure_agg"),
                "chart_type": raw.get("chart_type") or "bar",
                "time_grain": raw.get("time_grain"),
            }
        )
    return cleaned


def list_dashboards(organization_id: str) -> list[dict[str, Any]]:
    if _pss.enabled():
        return _pss.list_records(_COLLECTION, organization_id)
    store = _load_store()
    boards = [d for d in store.get("dashboards", []) if _matches_scope(d, organization_id)]
    return sorted(boards, key=lambda d: d.get("updated_at", ""), reverse=True)


def get_dashboard(dashboard_id: str, *, organization_id: str) -> dict[str, Any] | None:
    for board in list_dashboards(organization_id):
        if board.get("id") == dashboard_id:
            return board
    return None


def create_dashboard(payload: dict[str, Any], *, organization_id: str) -> dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    if not title:
        raise DashboardError("Dashboard title is required")
    tiles = _validate_tiles(list(payload.get("tiles") or []))
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "client_id": organization_id,
        "title": title,
        "description": payload.get("description") or "",
        "days": int(payload.get("days") or 30),
        "tiles": tiles,
        "created_at": now,
        "updated_at": now,
    }
    if _pss.enabled():
        _pss.upsert(_COLLECTION, entry["id"], organization_id, entry)
        for stale in _pss.list_records(_COLLECTION, organization_id)[MAX_DASHBOARDS:]:
            _pss.delete(_COLLECTION, stale["id"], organization_id)
        return entry
    store = _load_store()
    boards = [d for d in store.get("dashboards", []) if _matches_scope(d, organization_id)]
    boards = [entry, *boards][:MAX_DASHBOARDS]
    other = [d for d in store.get("dashboards", []) if not _matches_scope(d, organization_id)]
    store["dashboards"] = other + boards
    _save_store(store)
    return entry


def _apply_update(found: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("title"):
        found["title"] = str(payload["title"]).strip()
    if "description" in payload:
        found["description"] = payload.get("description") or ""
    if payload.get("days"):
        found["days"] = int(payload["days"])
    if "tiles" in payload:
        found["tiles"] = _validate_tiles(list(payload["tiles"] or []))
    found["updated_at"] = datetime.now(timezone.utc).isoformat()
    return found


def update_dashboard(dashboard_id: str, payload: dict[str, Any], *, organization_id: str) -> dict[str, Any]:
    if _pss.enabled():
        found = get_dashboard(dashboard_id, organization_id=organization_id)
        if not found:
            raise DashboardError("Dashboard not found")
        found = _apply_update(found, payload)
        _pss.upsert(_COLLECTION, dashboard_id, organization_id, found)
        return found
    store = _load_store()
    found: dict[str, Any] | None = None
    for board in store.get("dashboards", []):
        if board.get("id") == dashboard_id and _matches_scope(board, organization_id):
            found = board
            break
    if not found:
        raise DashboardError("Dashboard not found")
    _apply_update(found, payload)
    _save_store(store)
    return found


def delete_dashboard(dashboard_id: str, *, organization_id: str) -> bool:
    if _pss.enabled():
        return _pss.delete(_COLLECTION, dashboard_id, organization_id)
    store = _load_store()
    before = len(store.get("dashboards", []))
    store["dashboards"] = [
        d
        for d in store.get("dashboards", [])
        if not (d.get("id") == dashboard_id and _matches_scope(d, organization_id))
    ]
    if len(store["dashboards"]) == before:
        return False
    _save_store(store)
    return True
