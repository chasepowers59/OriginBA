"""Report-schedule routes: subscribe recipients to a saved view on a cadence.

Org-scoped like saved views: a user manages only their own org's schedules. The
actual delivery happens out-of-band in report_schedule_runner.py (cron); run-now
exists so a schedule can be verified without waiting for the clock.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth.dependencies import AuthContext, get_auth_context
from api.org_db import require_org_for_data
from api import report_schedules as rs

router = APIRouter(prefix="/report-schedules", tags=["report-schedules"])


class ScheduleCreateRequest(BaseModel):
    saved_view_id: str
    recipients: list[str]
    cadence: str = "daily"
    weekday: int = 0
    hour_utc: int = 13
    window_days: int = 30
    format: str = "csv"


@router.get("")
def get_schedules(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    org_id = require_org_for_data(ctx)
    return {"schedules": rs.list_schedules(org_id),
            "smtp_configured": rs.smtp_configured()}


@router.post("")
def create_schedule(
    body: ScheduleCreateRequest,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("saved_views:write")
    org_id = require_org_for_data(ctx)
    try:
        return rs.create_schedule(body.model_dump(), organization_id=org_id,
                                  created_by=ctx.email)
    except rs.ScheduleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: str,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("saved_views:write")
    org_id = require_org_for_data(ctx)
    if not rs.delete_schedule(schedule_id, org_id):
        raise HTTPException(status_code=404, detail="Unknown schedule")
    return {"deleted": schedule_id}


@router.post("/{schedule_id}/run-now")
def run_now(
    schedule_id: str,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    """Render and send ONE schedule immediately — proof the pipe works."""
    ctx.require_permission("saved_views:write")
    org_id = require_org_for_data(ctx)
    schedule = next((s for s in rs.list_schedules(org_id) if s["id"] == schedule_id), None)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Unknown schedule")
    if not rs.smtp_configured():
        raise HTTPException(status_code=503, detail="SMTP is not configured on the API")
    view = rs._find_view(schedule["saved_view_id"], org_id)
    if view is None:
        raise HTTPException(status_code=400, detail="Saved view no longer exists")
    now = datetime.now(timezone.utc)
    try:
        columns, labels, rows = rs.render_schedule(schedule, view)
        rs._smtp_send(rs._build_message(schedule, rs.rows_to_csv(columns, labels, rows), now))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Delivery failed: {exc}") from exc
    return {"status": "sent", "row_count": len(rows), "recipients": schedule["recipients"]}
