"""Portal-wide routes: client config, saved views."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth.dependencies import AuthContext, get_auth_context, require_permission
from api.auth.workstream_access import (
    assert_snapshot_access,
    filter_dashboard_for_auth,
    filter_dashboards_for_auth,
    filter_nlq_metrics_for_auth,
    filter_report_library_for_auth,
)
from api.portal_config import load_portal_config
from api.org_db import require_org_for_data
from api.organizations import get_organization
from api.saved_dashboards import (
    DashboardError,
    create_dashboard,
    delete_dashboard,
    get_dashboard,
    list_dashboards,
    update_dashboard,
)
from api.saved_views import (
    SavedViewError,
    bulk_import_views,
    create_saved_view,
    delete_saved_view,
    list_saved_views,
)


router = APIRouter(prefix="/portal", tags=["portal"])


class SavedViewCreate(BaseModel):
    snapshot_id: str
    snapshot_label: str
    title: str
    kind: str
    report_id: str | None = None
    dimensions: list[str] | None = None
    measure_field: str | None = None
    measure_agg: str | None = None
    # The store has always handled `measures`, and the builder has always sent it —
    # but this schema did not declare it, and Pydantic drops what it does not declare,
    # so model_dump() handed the store a payload without it. A multi-measure view
    # reopened with one measure. `filters` was missing end to end, so a scoped view
    # reopened showing every row. The store-level test could not see either, because
    # it calls create_saved_view() directly and never crosses this schema.
    measures: list[dict[str, Any]] | None = None
    filters: list[dict[str, Any]] | None = None
    chart_type: str | None = None
    date_preset: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    scope_field: str | None = None
    scope_value: str | None = None


class SavedViewBulkImport(BaseModel):
    views: list[SavedViewCreate] = Field(default_factory=list)


class DashboardTile(BaseModel):
    id: str | None = None
    slot: int = 0
    title: str
    visual: str = "chart"
    snapshot_id: str
    report_id: str | None = None
    dimensions: list[str] = Field(default_factory=list)
    measure_field: str | None = None
    measure_agg: str | None = None
    chart_type: str | None = "bar"
    time_grain: str | None = None


class DashboardCreate(BaseModel):
    title: str
    description: str | None = None
    days: int = 30
    tiles: list[DashboardTile] = Field(default_factory=list)


class DashboardUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    days: int | None = None
    tiles: list[DashboardTile] | None = None


class AnalyticsNlqRequest(BaseModel):
    query: str = ""
    metric_id: str | None = None
    days: int | None = Field(default=None, ge=1, le=730)
    bill_cycle: str | None = None
    customer_class: str | None = None
    payment_type: str | None = None
    uom: str | None = None
    rate_code: str | None = None


@router.get("/config")
def portal_config(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    config = load_portal_config().copy()
    org_id = ctx.effective_organization_id()
    if org_id:
        org = get_organization(org_id)
        config["organization_id"] = org_id
        if org:
            config["organization_name"] = org["display_name"]
    return config


@router.get("/report-library")
def report_library(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("report_library:read")
    from api.report_library import get_report_library

    return filter_report_library_for_auth(
        get_report_library(ctx.effective_organization_id()), ctx)


@router.get("/saved-views")
def get_saved_views(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    org_id = ctx.require_organization()
    return {
        "client_id": org_id,
        "organization_id": org_id,
        "views": list_saved_views(org_id),
    }


@router.post("/saved-views")
def post_saved_view(
    body: SavedViewCreate,
    ctx: AuthContext = Depends(require_permission("saved_views:write")),
) -> dict[str, Any]:
    org_id = ctx.require_organization()
    try:
        entry = create_saved_view(body.model_dump(), organization_id=org_id)
    except SavedViewError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return entry


@router.post("/saved-views/import")
def import_saved_views(
    body: SavedViewBulkImport,
    ctx: AuthContext = Depends(require_permission("saved_views:write")),
) -> dict[str, Any]:
    org_id = ctx.require_organization()
    imported = bulk_import_views([v.model_dump() for v in body.views], organization_id=org_id)
    return {"imported": len(imported), "views": imported}


@router.delete("/saved-views/{view_id}")
def remove_saved_view(
    view_id: str,
    ctx: AuthContext = Depends(require_permission("saved_views:write")),
) -> dict[str, Any]:
    org_id = ctx.require_organization()
    if not delete_saved_view(view_id, organization_id=org_id):
        raise HTTPException(status_code=404, detail="Saved view not found")
    return {"deleted": view_id}


@router.get("/dashboards")
def get_dashboards(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    org_id = ctx.require_organization()
    return {
        "client_id": org_id,
        "organization_id": org_id,
        "dashboards": filter_dashboards_for_auth(list_dashboards(org_id), ctx),
    }


@router.get("/dashboards/{dashboard_id}")
def get_dashboard_by_id(
    dashboard_id: str,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    org_id = ctx.require_organization()
    board = get_dashboard(dashboard_id, organization_id=org_id)
    if not board:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    scoped = filter_dashboard_for_auth(board, ctx)
    if not scoped:
        raise HTTPException(status_code=403, detail="Access denied for this dashboard")
    return scoped


@router.post("/dashboards")
def post_dashboard(
    body: DashboardCreate,
    ctx: AuthContext = Depends(require_permission("dashboards:write")),
) -> dict[str, Any]:
    org_id = ctx.require_organization()
    payload = body.model_dump()
    for tile in payload.get("tiles") or []:
        assert_snapshot_access(ctx, str(tile.get("snapshot_id", "")))
    try:
        return create_dashboard(payload, organization_id=org_id)
    except DashboardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/dashboards/{dashboard_id}")
def put_dashboard(
    dashboard_id: str,
    body: DashboardUpdate,
    ctx: AuthContext = Depends(require_permission("dashboards:write")),
) -> dict[str, Any]:
    org_id = ctx.require_organization()
    patch = body.model_dump(exclude_unset=True)
    for tile in patch.get("tiles") or []:
        assert_snapshot_access(ctx, str(tile.get("snapshot_id", "")))
    try:
        return update_dashboard(dashboard_id, patch, organization_id=org_id)
    except DashboardError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


@router.delete("/dashboards/{dashboard_id}")
def remove_dashboard(
    dashboard_id: str,
    ctx: AuthContext = Depends(require_permission("dashboards:write")),
) -> dict[str, Any]:
    org_id = ctx.require_organization()
    if not delete_dashboard(dashboard_id, organization_id=org_id):
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return {"deleted": dashboard_id}


@router.get("/analytics-nlq/metrics")
def analytics_nlq_metrics(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("nlq:read")
    from api.snapshot_analytics_nlq import get_nlq_metric_catalog

    # Per-org: only metrics whose snapshot exists in this org's catalog are offered.
    org_id = ctx.effective_organization_id()
    return {"metrics": filter_nlq_metrics_for_auth(get_nlq_metric_catalog(org_id), ctx)}


@router.post("/analytics-nlq")
def analytics_nlq(
    body: AnalyticsNlqRequest,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("nlq:read")
    from api.demo_db import demo_configured
    from api.snapshot_analytics_nlq import run_snapshot_analytics_nlq
    from api.warehouse_db import warehouse_configured

    org_id = require_org_for_data(ctx)
    if not (demo_configured(org_id) or warehouse_configured(org_id)):
        raise HTTPException(status_code=503, detail="Database not configured")
    params = body.model_dump(exclude={"query", "metric_id"}, exclude_none=True)
    from api.snapshot_analytics_nlq import match_nlq_metric

    metric = match_nlq_metric(body.query, metric_id=body.metric_id)
    if metric:
        assert_snapshot_access(ctx, str(metric.get("snapshot_id", "")))
    result = run_snapshot_analytics_nlq(
        body.query,
        metric_id=body.metric_id,
        params=params,
        organization_id=org_id,
    )
    if not result:
        raise HTTPException(status_code=404, detail="No matching snapshot analytics pattern for this question")
    snapshot_id = str(result.get("resolved_from") or (metric or {}).get("snapshot_id") or "")
    if snapshot_id:
        assert_snapshot_access(ctx, snapshot_id)
    return result
