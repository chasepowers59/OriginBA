"""Snapshot explorer API routes (demo database only)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth.dependencies import AuthContext, get_auth_context, require_permission
from api.auth.workstream_access import (
    assert_workstream_access,
    filter_snapshots_for_auth,
    filter_workstreams_for_auth,
)
from api.demo_db import demo_configured, execute_query
from api.org_db import require_org_for_data
from api.query_builder import QueryValidationError, build_query
from api.raw_sql_validator import RawSqlValidationError, apply_row_cap, validate_raw_sql
from api.executive_dashboard import build_executive_summary
from api.workstream_dashboard import build_workstream_summary
from api.snapshot_catalog import CatalogError, allowed_fields, get_snapshot, list_snapshots, list_workstreams, load_catalog


router = APIRouter(prefix="/snapshots", tags=["snapshots"])


class MeasureRequest(BaseModel):
    field: str = "*"
    agg: str = "count"


class FilterRequest(BaseModel):
    field: str
    op: str = "eq"
    value: Any = None


class TimeDimensionRequest(BaseModel):
    field: str
    grain: str = "month"


class QueryRequest(BaseModel):
    dimensions: list[str] = Field(default_factory=list)
    measures: list[MeasureRequest] = Field(default_factory=lambda: [MeasureRequest()])
    filters: list[FilterRequest] = Field(default_factory=list)
    time_dimensions: list[TimeDimensionRequest] = Field(default_factory=list)
    limit: int = 500


class RawSqlRequest(BaseModel):
    sql: str
    limit: int = 100


def _default_date_filter(snapshot: dict[str, Any]) -> FilterRequest | None:
    field = snapshot.get("required_date_field")
    if not field:
        return None
    end = date.today()
    start = end - timedelta(days=90)
    return FilterRequest(field=field, op="between", value=[start.isoformat(), end.isoformat()])


def _serialize_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _cross_filter(cross_field: str | None, cross_value: str | None) -> list[dict[str, Any]]:
    if cross_field and cross_value is not None and str(cross_value).strip():
        return [{"field": cross_field.upper(), "op": "eq", "value": cross_value}]
    return []


def _workstream_for_snapshot(snapshot_id: str) -> str:
    return get_snapshot(snapshot_id)["workstream"]


def _require_snapshot_access(ctx: AuthContext, snapshot_id: str) -> dict[str, Any]:
    try:
        snapshot = get_snapshot(snapshot_id)
    except CatalogError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    assert_workstream_access(ctx, snapshot["workstream"])
    return snapshot


@router.get("")
def snapshots_index(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    org_id = ctx.effective_organization_id()
    catalog = load_catalog()
    workstreams = filter_workstreams_for_auth(list_workstreams(), ctx)
    snapshots = filter_snapshots_for_auth(list_snapshots(), ctx)
    return {
        "client": org_id or catalog.get("client", "demo"),
        "organization_id": org_id,
        "organization_name": ctx.organization_name,
        "workstream_order": catalog.get("workstream_order", []),
        "workstream_labels": catalog.get("workstream_labels", {}),
        "portal_snapshots": catalog.get("portal_snapshots", []),
        "poc_enabled": catalog.get("poc_enabled", []),
        "db_configured": demo_configured(org_id) if org_id else False,
        "workstreams": workstreams,
        "snapshots": snapshots,
    }


@router.get("/executive-summary")
def executive_summary(
    days: int = 30,
    compare: bool = False,
    cross_field: str | None = None,
    cross_value: str | None = None,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    org_id = require_org_for_data(ctx)
    extra = _cross_filter(cross_field, cross_value)
    return build_executive_summary(
        days,
        compare=compare,
        extra_filters=extra,
        allowed_workstreams=ctx.workstreams,
        organization_id=org_id,
    )


@router.get("/workstream-summary/{workstream_id}")
def workstream_summary(
    workstream_id: str,
    days: int = 30,
    compare: bool = False,
    cross_field: str | None = None,
    cross_value: str | None = None,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    assert_workstream_access(ctx, workstream_id)
    org_id = require_org_for_data(ctx)
    extra = _cross_filter(cross_field, cross_value)
    result = build_workstream_summary(
        workstream_id,
        days,
        compare=compare,
        extra_filters=extra,
        organization_id=org_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{snapshot_id}/metadata")
def snapshot_metadata(
    snapshot_id: str,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    org_id = require_org_for_data(ctx)
    snapshot = _require_snapshot_access(ctx, snapshot_id)
    default_filter = _default_date_filter(snapshot)
    return {
        "id": snapshot_id.upper(),
        "client": org_id,
        "organization_id": org_id,
        **snapshot,
        "suggested_default_filter": default_filter.model_dump() if default_filter else None,
    }


@router.get("/{snapshot_id}/stats")
def snapshot_stats(
    snapshot_id: str,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    org_id = require_org_for_data(ctx)
    snapshot = _require_snapshot_access(ctx, snapshot_id)
    table = snapshot["table_name"].upper()
    sql = f"SELECT COUNT(*) AS ROW_COUNT, MAX(LOAD_DTTM) AS LATEST_LOAD_DTTM FROM CISADM.{table}"
    try:
        columns, rows = execute_query(sql, organization_id=org_id, max_rows=1)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Demo stats failed: {exc}") from exc
    row = rows[0] if rows else [0, None]
    return {
        "client": org_id,
        "organization_id": org_id,
        "snapshot_id": snapshot_id.upper(),
        "row_count": int(row[0] or 0),
        "latest_load_dttm": _serialize_value(row[1]) if len(row) > 1 else None,
    }


@router.get("/{snapshot_id}/scope-options/{field_id}")
def snapshot_scope_options(
    snapshot_id: str,
    field_id: str,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("snapshots:query")
    org_id = require_org_for_data(ctx)
    snapshot = _require_snapshot_access(ctx, snapshot_id)

    allowed_scope = {
        f["field"].upper(): f for f in snapshot.get("scope_filters", [])
    }
    field = field_id.upper()
    if field not in allowed_scope:
        raise HTTPException(status_code=400, detail=f"Scope filter not allowed: {field_id}")
    if field not in allowed_fields(snapshot):
        raise HTTPException(status_code=400, detail=f"Unknown field: {field_id}")

    table = snapshot["table_name"].upper()
    sql = (
        f"SELECT * FROM ("
        f"SELECT DISTINCT {field} AS VAL FROM CISADM.{table} "
        f"WHERE {field} IS NOT NULL ORDER BY 1"
        f") WHERE ROWNUM <= 100"
    )
    try:
        columns, rows = execute_query(sql, organization_id=org_id, max_rows=100)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Scope options failed: {exc}") from exc

    values = [str(row[0]) for row in rows if row and row[0] is not None]
    return {
        "client": org_id,
        "organization_id": org_id,
        "snapshot_id": snapshot_id.upper(),
        "field": field,
        "label": allowed_scope[field].get("label", field),
        "values": values,
    }


@router.get("/{snapshot_id}/sample-rows")
def snapshot_sample_rows(
    snapshot_id: str,
    limit: int = 5,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    org_id = require_org_for_data(ctx)
    snapshot = _require_snapshot_access(ctx, snapshot_id)

    row_cap = max(1, min(limit, 10))
    table = snapshot["table_name"].upper()
    date_field = snapshot.get("required_date_field")
    if date_field:
        # Restrict to recent rows so sample preview stays fast on large snapshots.
        sql = (
            f"SELECT * FROM ("
            f"SELECT * FROM CISADM.{table} "
            f"WHERE {date_field} >= ADD_MONTHS(TRUNC(SYSDATE), -3) "
            f"ORDER BY {date_field} DESC NULLS LAST"
            f") WHERE ROWNUM <= {row_cap}"
        )
    else:
        sql = f"SELECT * FROM CISADM.{table} WHERE ROWNUM <= {row_cap}"
    try:
        columns, rows = execute_query(sql, organization_id=org_id, max_rows=row_cap)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sample rows failed: {exc}") from exc

    field_labels = {
        f["id"].upper(): f.get("label", f["id"]) for f in snapshot.get("fields", [])
    }
    serialized_rows = [
        {columns[i]: _serialize_value(row[i]) for i in range(len(columns))}
        for row in rows
    ]
    return {
        "client": org_id,
        "organization_id": org_id,
        "snapshot_id": snapshot_id.upper(),
        "grain_description": snapshot.get("grain_description"),
        "columns": columns,
        "column_labels": {col: field_labels.get(col.upper(), col) for col in columns},
        "rows": serialized_rows,
        "row_count": len(serialized_rows),
        "sql": sql,
    }


@router.post("/{snapshot_id}/raw-sql")
def snapshot_raw_sql(
    snapshot_id: str,
    body: RawSqlRequest,
    ctx: AuthContext = Depends(require_permission("snapshots:raw_sql")),
) -> dict[str, Any]:
    org_id = require_org_for_data(ctx)
    snapshot = _require_snapshot_access(ctx, snapshot_id)

    table = snapshot["table_name"].upper()
    try:
        validated = validate_raw_sql(body.sql, table)
        capped = apply_row_cap(validated, body.limit)
    except RawSqlValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        columns, rows = execute_query(capped, organization_id=org_id, max_rows=min(body.limit, 500))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Raw SQL failed: {exc}") from exc

    serialized_rows = [
        {columns[i]: _serialize_value(row[i]) for i in range(len(columns))}
        for row in rows
    ]
    return {
        "client": org_id,
        "organization_id": org_id,
        "snapshot_id": snapshot_id.upper(),
        "columns": columns,
        "rows": serialized_rows,
        "row_count": len(serialized_rows),
        "sql": capped,
    }


@router.post("/{snapshot_id}/query")
def snapshot_query(
    snapshot_id: str,
    body: QueryRequest,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("snapshots:query")
    org_id = require_org_for_data(ctx)
    snapshot = _require_snapshot_access(ctx, snapshot_id)

    filters = [f.model_dump() for f in body.filters]
    if not filters and snapshot.get("required_date_field"):
        default_filter = _default_date_filter(snapshot)
        if default_filter:
            filters = [default_filter.model_dump()]

    try:
        sql, binds = build_query(
            table_name=snapshot["table_name"],
            allowed_fields=allowed_fields(snapshot),
            trusted_measures={m.upper() for m in snapshot.get("trusted_measures", [])},
            required_date_field=snapshot.get("required_date_field"),
            dimensions=body.dimensions,
            measures=[m.model_dump() for m in body.measures],
            filters=filters,
            limit=min(body.limit, snapshot.get("max_rows", 500)),
            time_dimensions=[t.model_dump() for t in body.time_dimensions],
        )
    except QueryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        columns, rows = execute_query(sql, binds, organization_id=org_id, max_rows=body.limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Demo query failed: {exc}") from exc

    serialized_rows = [
        {columns[i]: _serialize_value(row[i]) for i in range(len(columns))}
        for row in rows
    ]
    return {
        "client": org_id,
        "organization_id": org_id,
        "snapshot_id": snapshot_id.upper(),
        "columns": columns,
        "rows": serialized_rows,
        "row_count": len(serialized_rows),
        "sql": sql,
    }
