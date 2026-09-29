"""Ori's home surfaces (api/ori_insights.py): findings and Ori's read (fast, from the home summary),
unusual months and projections (the monthly history, api/ori_series.py)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.auth.dependencies import AuthContext, get_auth_context
from api.ori_insights import anomalies, brief, findings, forecasts
from api.ori_series import cached_history
from api.org_db import require_org_for_data

router = APIRouter(prefix="/portal/ori", tags=["ori"])


@router.get("/findings")
def ori_findings(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    # Ori is not offered to a person limited to part of the data (it writes its own SQL)
    if ctx.row_rules:
        return {"findings": [], "brief": None}
    from api.snapshot_explorer import cached_home_summary
    summary = cached_home_summary(require_org_for_data(ctx), 30, True, "prior_period", [], ctx.workstreams, {}, ())
    return {"findings": findings(summary), "brief": brief(summary), "period": summary.get("period")}


@router.get("/trends")
def ori_trends(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    if ctx.row_rules:
        return {"anomalies": [], "forecasts": [], "through": None}
    history, meta = cached_history(require_org_for_data(ctx))
    # the home page's rule (_kpis_for_workstreams): no list or "*" is every workstream
    if ctx.workstreams and "*" not in ctx.workstreams:
        history = {k: v for k, v in history.items() if meta[k].get("workstream") in set(ctx.workstreams)}
    return {"anomalies": anomalies(history, meta), "forecasts": forecasts(history, meta),
            "through": max((v[-1]["month"] for v in history.values()), default=None)}
