"""GET /portal/integrity -- when each canvas was last proven against the client's own database,
and against what (raw CISADM; the snapshot tables today's Jaspersoft reports read)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path

from api.auth.dependencies import AuthContext, get_auth_context
from api.auth import workstream_access as wa
from api.integrity import canvas_summary, overview
from api.org_db import require_org_for_data

router = APIRouter(prefix="/portal/integrity", tags=["integrity"])


@router.get("")
def integrity_overview(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    out = overview(require_org_for_data(ctx))
    return {**out, "canvases": [c for c in out.get("canvases") or [] if wa.can_access_snapshot(ctx, c["canvas"])]}


def _verdict_only(summary: dict[str, Any]) -> dict[str, Any]:
    """The verdict and how many checks held, without the organization-wide figures compared."""
    src, snap = summary.get("source"), summary.get("snapshot")
    return {**summary,
            "source": src and {k: src.get(k) for k in ("run_at", "checks", "green")},
            "snapshot": snap and {k: snap.get(k) for k in ("run_at", "against", "ok")}}


@router.get("/{canvas_id}")
def integrity_canvas(canvas_id: str = Path(pattern=r"^rpt_[a-z0-9_]{1,80}$"),
                     ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    org_id = require_org_for_data(ctx)
    wa.assert_snapshot_access(ctx, canvas_id)
    summary = canvas_summary(org_id, canvas_id)
    return _verdict_only(summary) if ctx.row_rules else summary
