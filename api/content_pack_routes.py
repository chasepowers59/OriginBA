"""GET /portal/content-pack (editors) and POST /portal/content-pack/import (admins): api/content_packs.py."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api import content_packs as cp
from api.auth.dependencies import AuthContext, require_permission

router = APIRouter(prefix="/portal/content-pack", tags=["content-packs"])


class ImportRequest(BaseModel):
    pack: dict[str, Any]


@router.get("")
def export_content_pack(folder: str | None = None,
                        ctx: AuthContext = Depends(require_permission("saved_views:write"))) -> dict[str, Any]:
    return cp.build_pack(ctx.require_organization(), ctx, folder=folder or None)


@router.post("/import")
def import_content_pack(body: ImportRequest, dry_run: bool = True,
                        ctx: AuthContext = Depends(require_permission("saved_views:write"))) -> dict[str, Any]:
    if ctx.role != "admin":
        raise HTTPException(status_code=403, detail="Only an administrator can import a content pack.")
    org_id = ctx.require_organization()
    out = cp.import_pack(body.pack, org_id, ctx, dry_run=dry_run)
    if not dry_run:
        from api.access_audit import record_access_event
        record_access_event(actor_email=ctx.email, actor_id=ctx.id, action="content_pack_imported",
                            target_type="organization", target_id=org_id,
                            detail=f"from {body.pack.get('source_organization')}: "
                                   f"{len(out['views']['imported'])} views, {len(out['dashboards']['imported'])} dashboards")
    return out
