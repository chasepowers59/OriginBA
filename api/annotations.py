"""Report annotations — the "why" pinned next to the number.

A short note on a saved view, a dashboard, or one dashboard tile: who wrote it,
when, and what they saw ("spike is the CYCLE3 rebill batch"). The author or an
admin can remove one.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.org_store import OrgRecordStore

ROOT = Path(__file__).resolve().parent.parent
ANNOTATIONS_PATH = ROOT / "data" / "analytics_portal" / "annotations.json"
TARGET_TYPES = ("saved_view", "dashboard", "dashboard_tile")
MAX_TEXT = 2000
MAX_PER_TARGET = 50

_store = OrgRecordStore("annotations", lambda: ANNOTATIONS_PATH, "annotations")


class AnnotationError(ValueError):
    pass


def list_annotations(organization_id: str, *, target_type: str,
                     target_id: str) -> list[dict[str, Any]]:
    notes = [a for a in _store.list(organization_id)
             if a.get("target_type") == target_type and a.get("target_id") == target_id]
    return sorted(notes, key=lambda a: a.get("created_at", ""), reverse=True)


def create_annotation(payload: dict[str, Any], *, organization_id: str,
                      author_email: str) -> dict[str, Any]:
    target_type = str(payload.get("target_type") or "")
    if target_type not in TARGET_TYPES:
        raise AnnotationError(f"target_type must be one of {', '.join(TARGET_TYPES)}")
    target_id = str(payload.get("target_id") or "").strip()
    if not target_id:
        raise AnnotationError("target_id is required")
    text = str(payload.get("text") or "").strip()
    if not text:
        raise AnnotationError("The note text is empty")
    if len(text) > MAX_TEXT:
        raise AnnotationError(f"Notes are capped at {MAX_TEXT} characters")
    if len(list_annotations(organization_id, target_type=target_type,
                            target_id=target_id)) >= MAX_PER_TARGET:
        raise AnnotationError(f"This item already has {MAX_PER_TARGET} notes")

    return _store.add({
        "id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "target_type": target_type,
        "target_id": target_id,
        "text": text,
        "author_email": author_email.strip().lower(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def delete_annotation(annotation_id: str, *, organization_id: str,
                      requester_email: str, is_admin: bool) -> bool:
    """The author or an admin removes a note; anyone else is refused."""
    note = next((a for a in _store.list(organization_id)
                 if a.get("id") == annotation_id), None)
    if note is None:
        return False
    if not is_admin and note.get("author_email") != requester_email.strip().lower():
        return False
    return _store.delete(annotation_id, organization_id)
