"""GET /portal/ori/findings -- "Ori found something worth investigating" (api/ori_insights.py)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.auth.dependencies import AuthContext, get_auth_context
from api.ori_insights import findings
from api.org_db import require_org_for_data

router = APIRouter(prefix="/portal/ori", tags=["ori"])


@router.get("/findings")
def ori_findings(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    # Ori is not offered to a person limited to part of the data (it writes its own SQL)
    if ctx.row_rules:
        return {"findings": []}
    from api.snapshot_explorer import cached_home_summary
    summary = cached_home_summary(require_org_for_data(ctx), 30, True, "prior_period", [], ctx.workstreams, {}, ())
    return {"findings": findings(summary), "period": summary.get("period")}
