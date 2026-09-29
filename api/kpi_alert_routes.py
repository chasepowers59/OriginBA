"""KPI-alert routes: watch an executive KPI, get emailed when it breaks a threshold.

Org-scoped like report schedules; evaluation runs out-of-band in the hourly
runner (report_schedule_runner.py evaluates alerts after delivering schedules).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth.dependencies import AuthContext, get_auth_context
from api.notifications import smtp_configured
from api.org_db import require_org_for_data
from api import kpi_alerts as ka
from api.row_security import require_unrestricted

router = APIRouter(prefix="/kpi-alerts", tags=["kpi-alerts"])


class AlertCreateRequest(BaseModel):
    kpi_id: str | None = None
    saved_view_id: str | None = None
    condition: str
    threshold: float
    window_days: int = 7
    recipients: list[str]


def _may_see(alert: dict[str, Any], org_id: str, ctx: AuthContext) -> bool:
    """A view alert shows only to someone who can see the view and open its canvas; a KPI alert
    only to someone whose workstreams include the KPI's."""
    from api.auth import workstream_access as wa
    from api.ownership import visible
    if alert.get("saved_view_id"):
        from api.report_schedules import _find_view
        view = _find_view(alert["saved_view_id"], org_id)
        return view is not None and visible(view, ctx) and wa.can_access_snapshot(ctx, view["snapshot_id"])
    kpi = ka._kpi_by_id(alert.get("kpi_id") or "")
    return kpi is None or ctx.can_access_workstream(kpi.get("workstream") or "")


@router.get("")
def get_alerts(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    org_id = require_org_for_data(ctx)
    # Alerts watch organization-wide cards and carry their last value: none of that is
    # for a person limited to part of the data.
    return {"alerts": [] if ctx.row_rules else [a for a in ka.list_alerts(org_id) if _may_see(a, org_id, ctx)],
            "available_kpis": ka.watchable_kpis(),
            "smtp_configured": smtp_configured()}


@router.post("")
def create_alert(
    body: AlertCreateRequest,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("saved_views:write")
    # An alert watches an organization-wide card and emails it: not for part of the data.
    require_unrestricted(ctx)
    org_id = require_org_for_data(ctx)
    if body.saved_view_id:
        from api.auth.workstream_access import assert_snapshot_access
        from api.ownership import visible
        from api.report_schedules import _find_view
        view = _find_view(body.saved_view_id, org_id)
        if view is None or not visible(view, ctx):
            raise HTTPException(status_code=404, detail="Saved view not found")
        assert_snapshot_access(ctx, view["snapshot_id"])
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
    alert = next((a for a in ka.list_alerts(org_id) if a["id"] == alert_id), None)
    if alert is None:
        raise HTTPException(status_code=404, detail="Unknown alert")
    if ctx.role != "admin" and alert.get("created_by") not in (None, "", ctx.email):
        raise HTTPException(status_code=403, detail=f"Only the alert's creator ({alert['created_by']}) "
                                                    "or an administrator can remove it")
    ka.delete_alert(alert_id, org_id)
    return {"deleted": alert_id}
