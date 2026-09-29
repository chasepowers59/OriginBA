"""Row-level security within an organization.

A user may carry row rules, e.g. [{"field": "Service Type", "values": ["Water"]}]. Every
governed query adds each rule as an IN filter. It fails closed: a canvas that does not carry
a rule's column is refused to that person, never shown whole. Raw SQL cannot be filtered
safely, so it is refused to a restricted person (require_unrestricted).
"""
from __future__ import annotations

from typing import Any, Iterable

from fastapi import HTTPException

MAX_RULES = 5
MAX_VALUES = 50
RESTRICTED = ("This is not available to accounts limited to part of the data: it runs SQL the portal "
              "cannot restrict. Ask an administrator if you need it.")


class RowAccessDenied(Exception):
    pass


def clean_rules(rules: Any) -> list[dict[str, Any]]:
    """Validated rules: a field and a non-empty list of distinct values each."""
    if rules in (None, ""):
        return []
    if not isinstance(rules, list) or len(rules) > MAX_RULES:
        raise ValueError(f"Row rules must be a list of at most {MAX_RULES}")
    out = []
    for r in rules:
        field = str((r or {}).get("field") or "").strip() if isinstance(r, dict) else ""
        values = [str(v).strip() for v in (r.get("values") or [])] if isinstance(r, dict) else []
        values = list(dict.fromkeys(v for v in values if v))[:MAX_VALUES]
        if not field or not values:
            raise ValueError("Each row rule needs a field and at least one value")
        out.append({"field": field, "values": values})
    return out


def row_filters(rules: Iterable[dict[str, Any]], snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """The filters a restricted person's query must carry on this canvas."""
    fields = {f.get("id") for f in snapshot.get("fields") or []}
    out = []
    for r in rules or ():
        if r["field"] not in fields:
            raise RowAccessDenied(f"{snapshot.get('label') or 'This report'} does not carry {r['field']}, "
                                  "which your access is limited by.")
        out.append({"field": r["field"], "op": "in", "value": list(r["values"])})
    return out


def rule_filters(rules: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """The IN filters for a set of rules, for callers that have already kept to readable canvases."""
    return [{"field": r["field"], "op": "in", "value": list(r["values"])} for r in rules or ()]


def only_readable(items: list[dict[str, Any]], rules: Iterable[dict[str, Any]], organization_id: str | None,
                  key: str = "snapshot_id") -> list[dict[str, Any]]:
    """The KPIs, tiles or metrics whose canvas carries every rule's column."""
    rules = list(rules or ())
    if not rules:
        return items
    from api.snapshot_catalog import get_snapshot
    kept = []
    for item in items:
        try:
            if readable(rules, get_snapshot(item[key], organization_id)):
                kept.append(item)
        except Exception:  # noqa: BLE001 -- a canvas this org's catalog lacks is not readable either
            continue
    return kept


def readable(rules: Iterable[dict[str, Any]], snapshot: dict[str, Any]) -> bool:
    try:
        row_filters(rules, snapshot)
        return True
    except RowAccessDenied:
        return False


def require_unrestricted(ctx: Any) -> None:
    if getattr(ctx, "row_rules", ()):
        raise HTTPException(status_code=403, detail=RESTRICTED)


def enforce(ctx: Any, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """row_filters for a request: a 403 naming the missing column when it is refused."""
    try:
        return row_filters(getattr(ctx, "row_rules", ()), snapshot)
    except RowAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def auth_disabled() -> bool:
    # imported here: the auth package imports this module (clean_rules), so a top-level
    # import would be circular
    from api.auth.config import auth_disabled as disabled
    return disabled()


def _user_record(email: str) -> dict[str, Any] | None:
    """The account's current access, or None when there is no such account."""
    from sqlalchemy import func, select

    from api.auth.database import get_session_factory
    from api.auth.models import User

    with get_session_factory()() as session:
        user = session.scalar(select(User).where(func.lower(User.email) == (email or "").strip().lower()))
        if user is None:
            return None
        import json

        from api.auth.service import _workstreams_for_user
        return {"is_active": user.is_active, "role": user.role, "workstreams": _workstreams_for_user(user),
                "row_rules": json.loads(user.row_rules_json) if user.row_rules_json else []}


def creator_rules(email: str, stored: Iterable[dict[str, Any]] | None) -> tuple:
    """The row rules a schedule or embed runs with: its creator's CURRENT rules. Restricting
    or deactivating someone later reaches what they set up; with sign-in switched off (local
    development) there are no accounts, so the rules stored with it are used."""
    if auth_disabled():
        return tuple(stored or ())
    record = _user_record(email)
    if record is None or not record["is_active"]:
        raise RowAccessDenied("The person who set this up no longer has access, so it no longer runs.")
    return () if record["role"] == "admin" else tuple(record["row_rules"])


def creator_can_read(email: str, snapshot_id: str, organization_id: str | None) -> bool:
    """Whether the person who set something up may STILL open this canvas: their current
    workstream grants, like their current row rules. Without sign-in (local development) yes."""
    if auth_disabled():
        return True
    record = _user_record(email)
    if record is None or not record["is_active"]:
        return False
    if record["role"] == "admin":
        return True
    from api.auth.service import workstreams_allowed
    from api.auth.workstream_access import snapshot_workstream
    return workstreams_allowed(record.get("workstreams") or [], snapshot_workstream(snapshot_id, organization_id))

