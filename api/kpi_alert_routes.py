"""KPI-alert routes: watch an executive KPI, get emailed when it breaks a threshold.

Org-scoped like report schedules; evaluation runs out-of-band in the hourly
runner (report_schedule_runner.py evaluates alerts after delivering schedules).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth.dependencies import AuthContext, get_auth_context
from api.org_db import require_org_for_data
from api import kpi_alerts as ka

router = APIRouter(prefix="/kpi-alerts", tags=["kpi-alerts"])


class AlertCreateRequest(BaseModel):
    kpi_id: str
    condition: str
    threshold: float
    window_days: int = 7
    recipients: list[str]


@router.get("")
def get_alerts(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    org_id = require_org_for_data(ctx)
    return {"alerts": ka.list_alerts(org_id),
            "available_kpis": ka.watchable_kpis(),
            "smtp_configured": ka.smtp_configured()}


@router.post("")
def create_alert(
    body: AlertCreateRequest,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("saved_views:write")
    org_id = require_org_for_data(ctx)
    try:
        return ka.create_alert(body.model_dump(), organization_id=org_id,
                               created_by=ctx.email)
    except ka.AlertError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: str,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("saved_views:write")
    org_id = require_org_for_data(ctx)
    if not ka.delete_alert(alert_id, org_id):
        raise HTTPException(status_code=404, detail="Unknown alert")
    return {"deleted": alert_id}
