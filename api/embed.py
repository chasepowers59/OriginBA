"""Embed a saved view in another site with a signed, expiring link.

An owner or admin mints a token for ONE organization-visible saved view (POST
/portal/embed-tokens). The token is signed with the portal secret and carries the
organization, the view, the creator's row rules and an expiry of at most a day. The public
route GET /embed/{token}/data runs that view's definition through the query builder with
those rules and returns its rows: nothing else is reachable with the token. Which sites may
frame the embed page is the web app's EMBED_ALLOWED_ORIGINS (frame-ancestors).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth.config import jwt_secret
from api.auth.dependencies import AuthContext, require_permission
from api.ownership import require_edit
from api.row_security import RowAccessDenied, creator_rules, row_filters
from api.saved_views import list_saved_views
from api.summary_cache import cached

router = APIRouter(tags=["embed"])

MAX_TTL_MINUTES = 24 * 60
PURPOSE = "embed"


class EmbedTokenRequest(BaseModel):
    view_id: str
    ttl_minutes: int = Field(default=60, ge=1)


def _find_view(org_id: str, view_id: str) -> dict[str, Any] | None:
    return next((v for v in list_saved_views(org_id) if v.get("id") == view_id), None)


@router.post("/portal/embed-tokens")
def create_embed_token(body: EmbedTokenRequest,
                       ctx: AuthContext = Depends(require_permission("saved_views:write"))) -> dict[str, Any]:
    org_id = ctx.require_organization()
    view = _find_view(org_id, body.view_id)
    require_edit(view, ctx, "Saved view")
    if view.get("visibility") == "private":
        raise HTTPException(status_code=400, detail="A private view cannot be embedded; share it with your organization first.")
    now = int(time.time())
    exp = now + min(body.ttl_minutes, MAX_TTL_MINUTES) * 60
    token = jwt.encode({"purpose": PURPOSE, "org": org_id, "view": view["id"], "rules": list(ctx.row_rules),
                        "by": ctx.email, "iat": now, "exp": exp}, jwt_secret(), algorithm="HS256")
    from api.access_audit import record_access_event
    record_access_event(actor_email=ctx.email, actor_id=ctx.id, action="embed_token_created",
                        target_type="saved_view", target_id=view["id"], detail=f"expires {exp}")
    return {"token": token, "expires_at": datetime.fromtimestamp(exp, timezone.utc).isoformat()}


def _claims(token: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(token, jwt_secret(), algorithms=["HS256"])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="This embed link is not valid or has expired.") from exc
    if claims.get("purpose") != PURPOSE:
        raise HTTPException(status_code=401, detail="This embed link is not valid or has expired.")
    return claims


@router.get("/embed/{token}/data")
def embed_data(token: str) -> dict[str, Any]:
    from api.query_builder import build_query
    from api.snapshot_catalog import allowed_fields, get_snapshot, snapshot_backend
    from api.snapshot_explorer import _result_labels, _run, _serialize_value

    claims = _claims(token)
    org_id = claims["org"]
    view = _find_view(org_id, claims["view"])
    if view is None or view.get("visibility") == "private":
        raise HTTPException(status_code=404, detail="This view is no longer available.")
    snapshot = get_snapshot(view["snapshot_id"], org_id)
    try:
        # The creator's CURRENT rules: restricting or deactivating them reaches their embeds.
        rules = row_filters(creator_rules(claims.get("by", ""), claims.get("rules")), snapshot)
    except RowAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    measures = view.get("measures") or [{"field": view.get("measure_field") or "*",
                                         "agg": view.get("measure_agg") or "count"}]
    # The saved filters at their saved values (an unanswered parameter narrows nothing).
    filters = [{"field": f["field"], "op": f["op"], "value": f["value"]} for f in view.get("filters") or []
               if f.get("value") not in (None, "")]
    _, dialect, schema = snapshot_backend(snapshot, org_id)
    sql, binds = build_query(table_name=snapshot["table_name"], allowed_fields=allowed_fields(snapshot),
                             trusted_measures=set(snapshot.get("trusted_measures") or []),
                             dimensions=view.get("dimensions") or [], measures=measures, filters=filters + rules,
                             limit=500, dialect=dialect, schema=schema)
    # Public route: repeated loads of an embed are served from memory, not re-queried.
    columns, rows = cached(("embed", org_id, view["id"], sql, repr(sorted(binds.items()))),
                           lambda: _run(snapshot, sql, binds, organization_id=org_id, max_rows=500), keep=lambda _: True)
    from api.access_audit import record_access_event
    record_access_event(actor_email=f"embed:{claims.get('by', '')}", actor_id=None, action="embed_view",
                        target_type="saved_view", target_id=view["id"], detail=f"rows={len(rows)}")
    names = _result_labels(snapshot, columns, view.get("dimensions") or [], measures, [])
    shown = [names.get(c, c) for c in columns]
    return {"title": view.get("title"), "columns": shown, "rows": [{shown[i]: _serialize_value(r[i]) for i in range(len(columns))} for r in rows]}
