"""Server-side saved report views for the analytics portal."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
VIEWS_PATH = ROOT / "data" / "analytics_portal" / "saved_views.json"
MAX_VIEWS = 24


class SavedViewError(ValueError):
    pass


def _ensure_store() -> None:
    VIEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not VIEWS_PATH.exists():
        VIEWS_PATH.write_text(json.dumps({"views": []}, indent=2), encoding="utf-8")


def _load_store() -> dict[str, Any]:
    _ensure_store()
    return json.loads(VIEWS_PATH.read_text(encoding="utf-8"))


def _save_store(data: dict[str, Any]) -> None:
    _ensure_store()
    VIEWS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _matches_scope(view: dict[str, Any], organization_id: str) -> bool:
    return view.get("organization_id", view.get("client_id")) == organization_id


def list_saved_views(organization_id: str) -> list[dict[str, Any]]:
    store = _load_store()
    views = [v for v in store.get("views", []) if _matches_scope(v, organization_id)]
    return sorted(views, key=lambda v: v.get("saved_at", ""), reverse=True)


def create_saved_view(payload: dict[str, Any], *, organization_id: str) -> dict[str, Any]:
    required = ("snapshot_id", "snapshot_label", "title", "kind")
    for key in required:
        if not payload.get(key):
            raise SavedViewError(f"Missing required field: {key}")

    entry = {
        "id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "client_id": organization_id,
        "snapshot_id": str(payload["snapshot_id"]).upper(),
        "snapshot_label": payload["snapshot_label"],
        "title": payload["title"],
        "kind": payload["kind"],
        "report_id": payload.get("report_id"),
        "dimensions": payload.get("dimensions"),
        "measure_field": payload.get("measure_field"),
        "measure_agg": payload.get("measure_agg"),
        "chart_type": payload.get("chart_type"),
        "date_preset": payload.get("date_preset"),
        "date_start": payload.get("date_start"),
        "date_end": payload.get("date_end"),
        "scope_field": payload.get("scope_field"),
        "scope_value": payload.get("scope_value"),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }

    store = _load_store()
    views = [v for v in store.get("views", []) if _matches_scope(v, organization_id)]
    views = [v for v in views if not (v["snapshot_id"] == entry["snapshot_id"] and v["title"] == entry["title"])]
    views = [entry, *views][:MAX_VIEWS]

    other = [v for v in store.get("views", []) if not _matches_scope(v, organization_id)]
    store["views"] = other + views
    _save_store(store)
    return entry


def delete_saved_view(view_id: str, *, organization_id: str) -> bool:
    store = _load_store()
    before = len(store.get("views", []))
    store["views"] = [
        v
        for v in store.get("views", [])
        if not (v.get("id") == view_id and _matches_scope(v, organization_id))
    ]
    if len(store["views"]) == before:
        return False
    _save_store(store)
    return True


def bulk_import_views(views: list[dict[str, Any]], *, organization_id: str) -> list[dict[str, Any]]:
    imported: list[dict[str, Any]] = []
    for raw in views:
        try:
            imported.append(create_saved_view(raw, organization_id=organization_id))
        except SavedViewError:
            continue
    return imported
