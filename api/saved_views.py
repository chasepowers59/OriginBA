"""Server-side saved report views for the analytics portal."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
VIEWS_PATH = ROOT / "data" / "analytics_portal" / "saved_views.json"
# Per organization. Past it a save is refused out loud: the store used to drop the oldest
# view silently, so saving one could delete a colleague's.
MAX_VIEWS = 200

from api import portal_state_store as _pss  # noqa: E402
from api.ownership import clean_folder  # noqa: E402
_COLLECTION = "saved_views"


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
    if _pss.enabled():
        return _pss.list_records(_COLLECTION, organization_id)
    store = _load_store()
    views = [v for v in store.get("views", []) if _matches_scope(v, organization_id)]
    return sorted(views, key=lambda v: v.get("saved_at", ""), reverse=True)


def _refuse_past_limit(others: list[dict[str, Any]]) -> None:
    if len(others) >= MAX_VIEWS:
        raise SavedViewError(f"This organization has reached its limit of {MAX_VIEWS} saved views. "
                             "Delete one you no longer need, then save again.")


def create_saved_view(payload: dict[str, Any], *, organization_id: str) -> dict[str, Any]:
    required = ("snapshot_id", "snapshot_label", "title", "kind")
    for key in required:
        if not payload.get(key):
            raise SavedViewError(f"Missing required field: {key}")

    entry = {
        "id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "client_id": organization_id,
        "snapshot_id": str(payload["snapshot_id"]),
        "snapshot_label": payload["snapshot_label"],
        "title": payload["title"],
        "kind": payload["kind"],
        "report_id": payload.get("report_id"),
        "dimensions": payload.get("dimensions"),
        "measure_field": payload.get("measure_field"),
        "measure_agg": payload.get("measure_agg"),
        # Multi-measure builder views carry the full list; the singular fields
        # above stay populated with the first measure for backward compatibility
        # with tiles/readers that predate the array.
        "measures": payload.get("measures"),
        # The scoping the user applied when they saved. Without it the view reopens
        # over the whole canvas: different numbers, no warning. scope_field/value
        # below hold only ONE pair and predate the builder's filters shelf.
        "filters": payload.get("filters"),
        "chart_type": payload.get("chart_type"),
        "date_preset": payload.get("date_preset"),
        "date_start": payload.get("date_start"),
        "date_end": payload.get("date_end"),
        "scope_field": payload.get("scope_field"),
        "scope_value": payload.get("scope_value"),
        "owner_id": payload.get("owner_id"),
        "owner_email": payload.get("owner_email"),
        "visibility": payload.get("visibility") or "organization",
        "folder": clean_folder(payload.get("folder")),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }

    # Re-saving YOUR view (same canvas, title and owner) replaces it; a colleague's view
    # with the same title is theirs and is left alone.
    same = lambda v: (v.get("snapshot_id") == entry["snapshot_id"] and v.get("title") == entry["title"]  # noqa: E731
                      and v.get("owner_id") == entry["owner_id"])
    if _pss.enabled():
        # re-saving a view (same canvas and title) replaces it; a new one needs room
        existing = _pss.list_records(_COLLECTION, organization_id)
        _refuse_past_limit([v for v in existing if not same(v)])
        for v in existing:
            if same(v):
                _pss.delete(_COLLECTION, v["id"], organization_id)
        _pss.upsert(_COLLECTION, entry["id"], organization_id, entry)
        return entry

    store = _load_store()
    views = [v for v in store.get("views", []) if _matches_scope(v, organization_id)]
    views = [v for v in views if not same(v)]
    _refuse_past_limit(views)
    views = [entry, *views]

    other = [v for v in store.get("views", []) if not _matches_scope(v, organization_id)]
    store["views"] = other + views
    _save_store(store)
    return entry


def update_saved_view(view_id: str, patch: dict[str, Any], *, organization_id: str) -> dict[str, Any] | None:
    """Change what a view is filed under; its definition is never edited in place (save anew)."""
    found = next((v for v in list_saved_views(organization_id) if v.get("id") == view_id), None)
    if not found:
        return None
    if "folder" in patch:
        found = {**found, "folder": clean_folder(patch["folder"])}
    if _pss.enabled():
        _pss.upsert(_COLLECTION, view_id, organization_id, found)
        return found
    store = _load_store()
    store["views"] = [found if (v.get("id") == view_id and _matches_scope(v, organization_id)) else v
                      for v in store.get("views", [])]
    _save_store(store)
    return found


def delete_saved_view(view_id: str, *, organization_id: str) -> bool:
    if _pss.enabled():
        return _pss.delete(_COLLECTION, view_id, organization_id)
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
