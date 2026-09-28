"""Who owns a saved view or dashboard, who may see it, and who may change it.

'organization' items are listed for everyone in the organization (the behaviour before
owners existed); 'private' items only for their owner, admins included. Only the owner or
an admin may change or delete an item. Items saved before owners existed carry no owner
and stay editable by any writer, so nothing in use breaks.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException

VISIBILITIES = ("organization", "private")


def stamp(payload: dict[str, Any], ctx: Any) -> dict[str, Any]:
    """The payload with its owner and a checked visibility."""
    visibility = payload.get("visibility") or "organization"
    if visibility not in VISIBILITIES:
        raise HTTPException(status_code=400, detail=f"Visibility must be one of {', '.join(VISIBILITIES)}")
    return {**payload, "visibility": visibility, "owner_id": ctx.id, "owner_email": ctx.email}


def visible(item: dict[str, Any], ctx: Any) -> bool:
    return item.get("visibility") != "private" or item.get("owner_id") == ctx.id


def can_edit(item: dict[str, Any], ctx: Any) -> bool:
    return ctx.role == "admin" or not item.get("owner_id") or item.get("owner_id") == ctx.id


def for_caller(items: list[dict[str, Any]], ctx: Any) -> list[dict[str, Any]]:
    """The items this person may see, each saying whether they may edit it."""
    return [{**i, "can_edit": can_edit(i, ctx)} for i in items if visible(i, ctx)]


def require_edit(item: dict[str, Any] | None, ctx: Any, what: str) -> None:
    """404 for what the caller cannot see (a private item is not confirmed to exist), 403
    for what they can see but not change."""
    if not item or not visible(item, ctx):
        raise HTTPException(status_code=404, detail=f"{what} not found")
    if not can_edit(item, ctx):
        raise HTTPException(status_code=403, detail=f"Only the owner ({item.get('owner_email')}) or an administrator can change this {what.lower()}")
