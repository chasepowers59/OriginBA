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
