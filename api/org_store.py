"""Org-scoped record storage for portal user-state collections.

Saved views, report schedules, KPI alerts and annotations all store the same
shape: JSON records owned by one organization, in portal_state.records when the
shared Postgres is configured and a local JSON file otherwise (so local dev needs
no database). This is that pattern, once.

The file path is read through a callable so a module can keep its own patchable
`*_PATH` attribute (tests point it at a temp directory).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from api import portal_state_store as _pss


class OrgRecordStore:
    def __init__(self, collection: str, path: Callable[[], Path], key: str):
        self._collection = collection
        self._path = path
        self._key = key

    # --- local JSON fallback -------------------------------------------------
    def _load(self) -> dict[str, Any]:
        path = self._path()
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {self._key: []}

    def _save(self, data: dict[str, Any]) -> None:
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # --- API -----------------------------------------------------------------
    def list(self, organization_id: str) -> list[dict[str, Any]]:
        if _pss.enabled():
            return _pss.list_records(self._collection, organization_id)
        return [r for r in self._load().get(self._key, [])
                if r.get("organization_id") == organization_id]

    def list_all(self) -> list[dict[str, Any]]:
        """Every org's records — for cross-org sweeps like the schedule runner.
        Route handlers must use list() so one org never sees another's."""
        if _pss.enabled():
            return _pss.list_all_records(self._collection)
        return list(self._load().get(self._key, []))

    def add(self, entry: dict[str, Any]) -> dict[str, Any]:
        if _pss.enabled():
            _pss.upsert(self._collection, entry["id"], entry["organization_id"], entry)
        else:
            data = self._load()
            data.setdefault(self._key, []).append(entry)
            self._save(data)
        return entry

    def update(self, entry: dict[str, Any]) -> None:
        if _pss.enabled():
            _pss.upsert(self._collection, entry["id"], entry["organization_id"], entry)
            return
        data = self._load()
        data[self._key] = [entry if r.get("id") == entry["id"] else r
                           for r in data.get(self._key, [])]
        self._save(data)

    def delete(self, record_id: str, organization_id: str) -> bool:
        if _pss.enabled():
            return _pss.delete(self._collection, record_id, organization_id)
        data = self._load()
        remaining = [r for r in data.get(self._key, [])
                     if not (r.get("id") == record_id
                             and r.get("organization_id") == organization_id)]
        if len(remaining) == len(data.get(self._key, [])):
            return False
        data[self._key] = remaining
        self._save(data)
        return True
