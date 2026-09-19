"""GET /portal/integrity -- when each canvas was last proven against the client's own database,
and against what (raw CISADM; the legacy snapshot tables today's reports read)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path

from api.auth.dependencies import AuthContext, get_auth_context
from api.integrity import canvas_summary, overview
from api.org_db import require_org_for_data

router = APIRouter(prefix="/portal/integrity", tags=["integrity"])


@router.get("")
def integrity_overview(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    return overview(require_org_for_data(ctx))


@router.get("/{canvas_id}")
def integrity_canvas(canvas_id: str = Path(pattern=r"^rpt_[a-z0-9_]{1,80}$"),
                     ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    return canvas_summary(require_org_for_data(ctx), canvas_id)
