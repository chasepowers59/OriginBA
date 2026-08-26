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
from api.warehouse_db import warehouse_configured
from api.org_db import require_org_for_data
from api.query_builder import QueryValidationError, build_query
from api.raw_sql_validator import RawSqlValidationError, apply_row_cap, validate_raw_sql
from api.executive_dashboard import build_executive_summary
from api.kpi_runner import COMPARE_MODES
from api.workstream_dashboard import build_workstream_about, build_workstream_summary
from api.snapshot_catalog import CatalogError, allowed_fields, get_snapshot, list_snapshots, list_workstreams, load_catalog, is_warehouse


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



def _run(snapshot: dict, sql: str, binds=None, *, organization_id: str, max_rows: int):
    """Execute against whichever database this snapshot lives in."""
    if is_warehouse(snapshot):
        from api.warehouse_db import execute_query as run_warehouse
        return run_warehouse(sql, binds, organization_id=organization_id, max_rows=max_rows)
    return execute_query(sql, binds, organization_id=organization_id, max_rows=max_rows)


def _qualified(snapshot: dict) -> str:
    """schema.table, quoted for Postgres because a canvas name is lowercase."""
    table, schema = snapshot["table_name"], snapshot.get("schema", "CISADM")
    return f'{schema}."{table}"' if is_warehouse(snapshot) else f"{schema}.{table.upper()}"


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


def _workstream_for_snapshot(snapshot_id: str, organization_id: str | None = None) -> str:
    return get_snapshot(snapshot_id, organization_id)["workstream"]


def _require_snapshot_access(ctx: AuthContext, snapshot_id: str) -> dict[str, Any]:
    # The caller's EFFECTIVE organization decides which catalog this id is looked up in --
    # effective, not home. Using ctx.organization_id here meant an admin who switched
    # tenant still had every snapshot resolved against the tenant they belong to, so the
    # switcher changed the lists and not the lookups: "Unknown snapshot: rpt_aged_debt"
    # against a catalog the sidebar was displaying at that moment.
    try:
        snapshot = get_snapshot(snapshot_id, ctx.effective_organization_id())
    except CatalogError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    assert_workstream_access(ctx, snapshot["workstream"])
    return snapshot


@router.get("")
def snapshots_index(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    org_id = ctx.effective_organization_id()
    catalog = load_catalog(organization_id=org_id)
    workstreams = filter_workstreams_for_auth(list_workstreams(org_id), ctx)
    snapshots = filter_snapshots_for_auth(list_snapshots(organization_id=org_id), ctx)
    return {
        "client": org_id or catalog.get("client", "demo"),
        "organization_id": org_id,
        "organization_name": ctx.organization_name,
        "workstream_order": catalog.get("workstream_order", []),
        "workstream_labels": catalog.get("workstream_labels", {}),
        "portal_snapshots": catalog.get("portal_snapshots", []),
        "poc_enabled": catalog.get("poc_enabled", []),
        # Either backend counts: dbt-catalog orgs read the Postgres warehouse, legacy
        # orgs the Oracle demo. Demo-only here showed warehouse tenants "Connect
        # database" with a live warehouse behind them.
        "db_configured": (demo_configured(org_id) or warehouse_configured(org_id))
        if org_id else False,
        "workstreams": workstreams,
        "snapshots": snapshots,
    }


@router.get("/executive-summary")
def executive_summary(
    days: int = 30,
    compare: bool = False,
    compare_mode: str = "prior_period",
    cross_field: str | None = None,
    cross_value: str | None = None,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    org_id = require_org_for_data(ctx)
    extra = _cross_filter(cross_field, cross_value)
    if compare_mode not in COMPARE_MODES:
        raise HTTPException(status_code=400, detail=f"compare_mode must be one of {COMPARE_MODES}")
    return build_executive_summary(
        days,
        compare=compare,
        compare_mode=compare_mode,
        extra_filters=extra,
        allowed_workstreams=ctx.workstreams,
        organization_id=org_id,
    )


@router.get("/workstream-summary/{workstream_id}")
def workstream_summary(
    workstream_id: str,
    days: int = 30,
    compare: bool = False,
    compare_mode: str = "prior_period",
    cross_field: str | None = None,
    cross_value: str | None = None,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    assert_workstream_access(ctx, workstream_id)
    org_id = require_org_for_data(ctx)
    extra = _cross_filter(cross_field, cross_value)
    if compare_mode not in COMPARE_MODES:
        raise HTTPException(status_code=400, detail=f"compare_mode must be one of {COMPARE_MODES}")
    result = build_workstream_summary(
        workstream_id,
        days,
        compare=compare,
        compare_mode=compare_mode,
        extra_filters=extra,
        organization_id=org_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/workstream-about/{workstream_id}")
def workstream_about(
    workstream_id: str,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    """What this workstream includes, deliberately excludes, and links to."""
    ctx.require_permission("snapshots:read")
    assert_workstream_access(ctx, workstream_id)
    return build_workstream_about(
        workstream_id, organization_id=ctx.effective_organization_id())


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
        "id": snapshot_id,
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
    # LOAD_DTTM is the CDC watermark on a CISADM snapshot; a dbt canvas has no such
    # column, so the warehouse form reports the row count alone rather than inventing one.
    if is_warehouse(snapshot):
        sql = f"SELECT COUNT(*) AS row_count, NULL AS latest_load_dttm FROM {_qualified(snapshot)}"
    else:
        sql = (f"SELECT COUNT(*) AS ROW_COUNT, MAX(LOAD_DTTM) AS LATEST_LOAD_DTTM "
               f"FROM {_qualified(snapshot)}")
    try:
        columns, rows = _run(snapshot, sql, organization_id=org_id, max_rows=1)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Demo stats failed: {exc}") from exc
    row = rows[0] if rows else [0, None]
    return {
        "client": org_id,
        "organization_id": org_id,
        # As written. Upper-casing was an Oracle habit and a dbt canvas id is lowercase;
        # returning RPT_BILL_SEGMENT for rpt_bill_segment breaks the caller's own lookups.
        "snapshot_id": snapshot_id,
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
        f["field"]: f for f in snapshot.get("scope_filters", [])
    }
    field = field_id if field_id in allowed_fields(snapshot) else field_id.upper()
    if field not in allowed_scope:
        raise HTTPException(status_code=400, detail=f"Scope filter not allowed: {field_id}")
    if field not in allowed_fields(snapshot):
        raise HTTPException(status_code=400, detail=f"Unknown field: {field_id}")


    if is_warehouse(snapshot):
        col = f'"{field}"'
        sql = (f"SELECT DISTINCT {col} AS val FROM {_qualified(snapshot)} "
               f"WHERE {col} IS NOT NULL ORDER BY 1 FETCH FIRST 100 ROWS ONLY")
    else:
        sql = (
            f"SELECT * FROM ("
            f"SELECT DISTINCT {field} AS VAL FROM {_qualified(snapshot)} "
            f"WHERE {field} IS NOT NULL ORDER BY 1"
            f") WHERE ROWNUM <= 100"
        )
    try:
        columns, rows = _run(snapshot, sql, organization_id=org_id, max_rows=100)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Scope options failed: {exc}") from exc

    values = [str(row[0]) for row in rows if row and row[0] is not None]
    return {
        "client": org_id,
        "organization_id": org_id,
        # As written. Upper-casing was an Oracle habit and a dbt canvas id is lowercase;
        # returning RPT_BILL_SEGMENT for rpt_bill_segment breaks the caller's own lookups.
        "snapshot_id": snapshot_id,
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
    if is_warehouse(snapshot):
        # No recency window on the warehouse form. The canvases are already scoped to a
        # client's own data and a sample of ten rows is cheap; ordering by a date on an
        # unindexed canvas is not, and this is only ever a preview.
        sql = f"SELECT * FROM {_qualified(snapshot)} FETCH FIRST {row_cap} ROWS ONLY"
    elif date_field:
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
        columns, rows = _run(snapshot, sql, organization_id=org_id, max_rows=row_cap)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sample rows failed: {exc}") from exc

    # Label lookup keyed BOTH ways: an Oracle snapshot's columns come back uppercase from
    # the driver, a canvas's come back exactly as declared.
    field_labels = {
        f["id"]: f.get("label", f["id"]) for f in snapshot.get("fields", [])
    }
    serialized_rows = [
        {columns[i]: _serialize_value(row[i]) for i in range(len(columns))}
        for row in rows
    ]
    return {
        "client": org_id,
        "organization_id": org_id,
        # As written. Upper-casing was an Oracle habit and a dbt canvas id is lowercase;
        # returning RPT_BILL_SEGMENT for rpt_bill_segment breaks the caller's own lookups.
        "snapshot_id": snapshot_id,
        "grain_description": snapshot.get("grain_description"),
        "columns": columns,
        "column_labels": {col: field_labels.get(col, field_labels.get(col.upper(), col))
                          for col in columns},
        "rows": serialized_rows,
        "row_count": len(serialized_rows),
        "sql": sql,
    }



# Aggregate aliases are m0, m1, TD0 -- deliberately opaque, so a measure name can never be
# interpolated into SQL. That safety property is worth keeping, but it means the RESPONSE
# has to carry the translation back or the reader sees "m0" where a number's name should
# be. The builder assigns the aliases in request order, so they can be reconstructed here
# without loosening anything.
_AGG_WORD = {"sum": "Total", "count": "Count of", "count_distinct": "Distinct",
             "min": "Lowest", "max": "Highest", "avg": "Average"}


def _result_labels(snapshot: dict, columns: list[str], dimensions: list[str],
                   measures: list[dict], time_dimensions: list[dict]) -> dict[str, str]:
    field_labels = {f["id"]: f.get("label", f["id"]) for f in snapshot.get("fields", [])}

    def label_of(field_id: str) -> str:
        return field_labels.get(field_id, field_labels.get(field_id.upper(), field_id))

    labels: dict[str, str] = {}
    for idx, td in enumerate(time_dimensions or []):
        grain = str(td.get("grain", "month")).lower()
        labels[f"TD{idx}"] = f"{label_of(str(td.get('field', '')))} ({grain})"
    for dim in dimensions or []:
        labels[dim] = label_of(dim)
    for idx, m in enumerate(measures or []):
        field = str(m.get("field", "*"))
        agg = str(m.get("agg", "count")).lower()
        if field == "*":
            labels[f"m{idx}"] = "Number of records"
        else:
            labels[f"m{idx}"] = f"{_AGG_WORD.get(agg, agg.title())} {label_of(field)}"
    # Anything the query returned that was not requested keeps its own name rather than
    # disappearing from the map.
    return {c: labels.get(c, field_labels.get(c, c)) for c in columns}


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
        # As written. Upper-casing was an Oracle habit and a dbt canvas id is lowercase;
        # returning RPT_BILL_SEGMENT for rpt_bill_segment breaks the caller's own lookups.
        "snapshot_id": snapshot_id,
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
        # WHICH WORLD THIS SNAPSHOT LIVES IN decides the dialect and the backend. The
        # dbt canvases are Postgres with quoted Title Case columns; the legacy
        # *_RPT_CURR snapshots are Oracle CISADM. The snapshot says which, so the two
        # coexist while the migration finishes and nothing needs configuring twice.
        warehouse = is_warehouse(snapshot)
        dialect = "postgres" if warehouse else "oracle"
        trusted = set(snapshot.get("trusted_measures", []))
        sql, binds = build_query(
            table_name=snapshot["table_name"],
            allowed_fields=allowed_fields(snapshot),
            trusted_measures=trusted if warehouse else {m.upper() for m in trusted},
            required_date_field=snapshot.get("required_date_field"),
            dimensions=body.dimensions,
            measures=[m.model_dump() for m in body.measures],
            filters=filters,
            limit=min(body.limit, snapshot.get("max_rows", 500)),
            time_dimensions=[t.model_dump() for t in body.time_dimensions],
            dialect=dialect,
            schema=snapshot.get("schema", "CISADM"),
        )
    except QueryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        if warehouse:
            from api.warehouse_db import execute_query as run_warehouse
            columns, rows = run_warehouse(sql, binds, organization_id=org_id,
                                          max_rows=body.limit)
        else:
            columns, rows = execute_query(sql, binds, organization_id=org_id,
                                          max_rows=body.limit)
    except Exception as exc:
        where = "Warehouse" if warehouse else "Demo"
        raise HTTPException(status_code=502, detail=f"{where} query failed: {exc}") from exc

    serialized_rows = [
        {columns[i]: _serialize_value(row[i]) for i in range(len(columns))}
        for row in rows
    ]
    return {
        "client": org_id,
        "organization_id": org_id,
        # As written. Upper-casing was an Oracle habit and a dbt canvas id is lowercase;
        # returning RPT_BILL_SEGMENT for rpt_bill_segment breaks the caller's own lookups.
        "snapshot_id": snapshot_id,
        "columns": columns,
        "column_labels": _result_labels(
            snapshot, columns, body.dimensions,
            [m.model_dump() for m in body.measures],
            [t.model_dump() for t in body.time_dimensions]),
        "rows": serialized_rows,
        "row_count": len(serialized_rows),
        "sql": sql,
    }
