"""Embed a saved view in another site with a signed, expiring link.

An owner or admin mints a token for ONE organization-visible saved view (POST
/portal/embed-tokens). The token is signed with the embed key (embed_key: its own secret,
never the one that signs sessions) and carries the
organization, the view, the creator's row rules and an expiry of at most a day. The public
route GET /embed/{token}/data runs that view's definition through the query builder with
those rules and returns its rows: nothing else is reachable with the token. Which sites may
frame the embed page is the web app's EMBED_ALLOWED_ORIGINS (frame-ancestors).

Every link is recorded per organization (never the token itself) and served only while its
record stands: the owner or an admin lists a view's links and turns any one off
(GET /portal/embed-tokens?view_id=, DELETE /portal/embed-tokens/{id}). Until 2026-10-05 a
shared link could not be withdrawn before it expired.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth.config import jwt_secret
from api.auth.dependencies import AuthContext, require_permission
from api.auth.workstream_access import assert_snapshot_access
from api.date_presets import saved_window
from api.ownership import require_edit
from api.reporting_dates import data_as_of
from api.row_security import RowAccessDenied, creator_can_read, creator_rules, row_filters
from api.saved_views import list_saved_views
from api.data_version import data_version
from api.org_store import OrgRecordStore
from api.summary_cache import cached
from api.request_limits import client_address, limited

router = APIRouter(tags=["embed"])

MAX_TTL_MINUTES = 24 * 60
PURPOSE = "embed"
EMBED_LINKS_PATH = Path(__file__).resolve().parent.parent / "data" / "analytics_portal" / "embed_links.json"
_links = OrgRecordStore("embed_links", lambda: EMBED_LINKS_PATH, "links")
_TURNED_OFF = "This embed link was turned off by the person who shared it."


def embed_key() -> str:
    """The key embed links are signed with: PORTAL_EMBED_SECRET when set, else one derived from
    the session secret, so the two are never the same key and either can be rotated alone."""
    own = os.getenv("PORTAL_EMBED_SECRET", "").strip()
    if len(own) >= 32:
        return own
    return hmac.new(jwt_secret().encode(), b"originba-embed-links-v1", hashlib.sha256).hexdigest()


def _link(org_id: str, link_id: str) -> dict[str, Any] | None:
    return next((l for l in _links.list(org_id) if l.get("id") == link_id), None)


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
    # an ownerless legacy view is editable by any writer, so the grant is what stops publishing
    # a canvas this person may not open
    assert_snapshot_access(ctx, view["snapshot_id"])
    now = int(time.time())
    exp = now + min(body.ttl_minutes, MAX_TTL_MINUTES) * 60
    for stale in [l for l in _links.list(org_id) if int(l.get("exp", 0)) < now]:
        _links.delete(stale["id"], org_id)
    link_id = secrets.token_urlsafe(12)
    _links.add({"id": link_id, "organization_id": org_id, "view_id": view["id"], "created_by": ctx.email,
                "created_at": datetime.fromtimestamp(now, timezone.utc).isoformat(), "exp": exp,
                "expires_at": datetime.fromtimestamp(exp, timezone.utc).isoformat(), "revoked_at": None})
    token = jwt.encode({"purpose": PURPOSE, "org": org_id, "view": view["id"], "rules": list(ctx.row_rules),
                        "by": ctx.email, "iat": now, "exp": exp, "jti": link_id}, embed_key(), algorithm="HS256")
    from api.access_audit import record_access_event
    record_access_event(actor_email=ctx.email, actor_id=ctx.id, action="embed_token_created",
                        target_type="saved_view", target_id=view["id"], detail=f"expires {exp}")
    return {"token": token, "id": link_id, "expires_at": datetime.fromtimestamp(exp, timezone.utc).isoformat()}


@router.get("/portal/embed-tokens")
def list_embed_links(view_id: str,
                     ctx: AuthContext = Depends(require_permission("saved_views:write"))) -> dict[str, Any]:
    """The links shared for one view, live or turned off, for its owner or an admin."""
    org_id = ctx.require_organization()
    require_edit(_find_view(org_id, view_id), ctx, "Saved view")
    now = int(time.time())
    links = [{k: l.get(k) for k in ("id", "created_by", "created_at", "expires_at", "revoked_at")}
             for l in _links.list(org_id) if l.get("view_id") == view_id and int(l.get("exp", 0)) >= now]
    return {"links": sorted(links, key=lambda l: l["created_at"] or "", reverse=True)}


@router.delete("/portal/embed-tokens/{link_id}")
def revoke_embed_link(link_id: str,
                      ctx: AuthContext = Depends(require_permission("saved_views:write"))) -> dict[str, Any]:
    org_id = ctx.require_organization()
    link = _link(org_id, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="That embed link does not exist.")
    require_edit(_find_view(org_id, link["view_id"]), ctx, "Saved view")
    if not link.get("revoked_at"):
        _links.update({**link, "revoked_at": datetime.now(timezone.utc).isoformat()})
        from api.access_audit import record_access_event
        record_access_event(actor_email=ctx.email, actor_id=ctx.id, action="embed_token_revoked",
                            target_type="saved_view", target_id=link["view_id"], detail=f"link {link_id}")
    return {"id": link_id, "turned_off": True}


def _view_filters(view: dict[str, Any], snapshot: dict[str, Any], org_id: str) -> list[dict[str, Any]]:
    """The view as its creator saved it: its window (a named one stays relative to the data's end),
    its scope, its ready-to-run report's own filters and its saved filters with a value."""
    field = snapshot.get("default_date_field") or ((snapshot.get("date_fields") or [{}])[0] or {}).get("id")
    anchored = data_as_of(org_id)
    window = saved_window(view.get("date_preset"), view.get("date_start"), view.get("date_end"),
                          date.fromisoformat(anchored) if anchored else date.today()) if field else None
    out = [{"field": field, "op": "between", "value": window}] if window else []
    if view.get("scope_field") and view.get("scope_value") not in (None, ""):
        out.append({"field": view["scope_field"], "op": "eq", "value": view["scope_value"]})
    report = next((r for r in snapshot.get("premade_reports") or [] if r.get("id") == view.get("report_id")), None)
    out += list((report or {}).get("filters") or [])
    # an unanswered parameter narrows nothing; a saved range on the windowed date gives way to the window
    out += [{"field": f["field"], "op": f["op"], "value": f["value"]} for f in view.get("filters") or []
            if f.get("value") not in (None, "") and not (window and f.get("field") == field)]
    return out


def _claims(token: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(token, embed_key(), algorithms=["HS256"])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="This embed link is not valid or has expired.") from exc
    if claims.get("purpose") != PURPOSE:
        raise HTTPException(status_code=401, detail="This embed link is not valid or has expired.")
    link = _link(str(claims.get("org")), str(claims.get("jti")))
    if link is None:
        raise HTTPException(status_code=401, detail="This embed link is not valid or has expired.")
    if link.get("revoked_at"):
        raise HTTPException(status_code=401, detail=_TURNED_OFF)
    return claims


@router.get("/embed/{token}/data", dependencies=[Depends(limited("embed_data", 120, key=client_address))])
def embed_data(token: str) -> dict[str, Any]:
    from api.query_builder import build_query
    from api.snapshot_catalog import allowed_fields, boolean_fields, get_snapshot, snapshot_backend
    from api.snapshot_explorer import _result_labels, _run, _serialize_value

    claims = _claims(token)
    org_id = claims["org"]
    view = _find_view(org_id, claims["view"])
    if view is None or view.get("visibility") == "private":
        raise HTTPException(status_code=404, detail="This view is no longer available.")
    snapshot = get_snapshot(view["snapshot_id"], org_id)
    if not creator_can_read(claims.get("by", ""), view["snapshot_id"], org_id):
        raise HTTPException(status_code=403, detail="The person who shared this view can no longer open it, so it no longer shows.")
    try:
        # The creator's CURRENT rules: restricting or deactivating them reaches their embeds.
        rules = row_filters(creator_rules(claims.get("by", ""), claims.get("rules")), snapshot)
    except RowAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    measures = view.get("measures") or [{"field": view.get("measure_field") or "*",
                                         "agg": view.get("measure_agg") or "count"}]
    filters = _view_filters(view, snapshot, org_id)
    _, dialect, schema = snapshot_backend(snapshot, org_id)
    sql, binds = build_query(table_name=snapshot["table_name"], allowed_fields=allowed_fields(snapshot),
                             trusted_measures=set(snapshot.get("trusted_measures") or []),
                             boolean_fields=boolean_fields(snapshot),
                             dimensions=view.get("dimensions") or [], measures=measures, filters=filters + rules,
                             limit=500, dialect=dialect, schema=schema)
    # Public route: repeated loads of an embed are served from memory, not re-queried.
    columns, rows = cached(("embed", org_id, view["id"], sql, repr(sorted(binds.items()))),
                           lambda: _run(snapshot, sql, binds, organization_id=org_id, max_rows=500), keep=lambda _: True,
                           version=data_version(org_id))
    from api.access_audit import record_access_event
    record_access_event(actor_email=f"embed:{claims.get('by', '')}", actor_id=None, action="embed_view",
                        target_type="saved_view", target_id=view["id"], detail=f"rows={len(rows)}")
    names = _result_labels(snapshot, columns, view.get("dimensions") or [], measures, [])
    shown = [names.get(c, c) for c in columns]
    return {"title": view.get("title"), "columns": shown, "rows": [{shown[i]: _serialize_value(r[i]) for i in range(len(columns))} for r in rows]}
