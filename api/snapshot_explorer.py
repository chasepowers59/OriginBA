"""Snapshot explorer API routes (demo database only)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
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
from api.reporting_dates import (DEFAULT_WINDOW_DAYS, reporting_today,
                                 window_date_field, window_date_label)
from api.executive_dashboard import build_executive_summary
from api.kpi_runner import COMPARE_MODES
from api.workstream_dashboard import build_workstream_about, build_workstream_summary
from api.snapshot_catalog import (CatalogError, allowed_fields, get_snapshot,
                                  list_snapshots, list_workstreams,
                                  load_catalog, snapshot_backend)


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
    """Execute against whichever database serves this snapshot FOR THIS ORG."""
    backend, _, _ = snapshot_backend(snapshot, organization_id)
    if backend == "postgres":
        from api.warehouse_db import execute_query as run_warehouse
        return run_warehouse(sql, binds, organization_id=organization_id, max_rows=max_rows)
    return execute_query(sql, binds, organization_id=organization_id, max_rows=max_rows)


def _qualified(snapshot: dict, organization_id: str | None = None) -> str:
    """schema.table for this org's engine. Quoted lowercase for Postgres; UNQUOTED
    for Oracle (an in-database canvas was created unquoted, so Oracle case-folds the
    reference -- quoting the lowercase name would miss it)."""
    backend, dialect, schema = snapshot_backend(snapshot, organization_id)
    table = snapshot["table_name"]
    if dialect == "postgres":
        return f'{schema}."{table}"'
    return f"{schema}.{table.upper()}"


# Above this, the filter value picker declines to enumerate and the caller falls back
# to free text. Measured on originba_v2_demo25: SELECT DISTINCT over a canvas costs
# roughly linearly with rows -- 46,661 -> 42 ms, 748,848 -> 139 ms, 3,565,096 -> 608 ms
# -- so a 35M-row client fact lands near six seconds for a dropdown. The threshold sits
# between the last two: dimensions keep their picker, facts do not. This is not an index
# problem: the catalog declares no scope_filters, so the picker is offered on any of
# 1,107 dimension columns and there is nothing bounded to index.
SCOPE_ENUMERATION_MAX_ROWS = 1_000_000


def can_enumerate_values(row_estimate: Any) -> bool:
    """Whether a DISTINCT over this table is cheap enough to sit on the UI path.

    An unknown estimate is ATTEMPTED, not refused: a table nothing has analyzed yet
    reports none, and refusing would break every picker on a fresh database before the
    first ANALYZE lands.
    """
    try:
        rows = int(row_estimate)
    except (TypeError, ValueError):
        return True
    return rows <= SCOPE_ENUMERATION_MAX_ROWS if rows > 0 else True


def _row_estimate(snapshot: dict, organization_id: str) -> int | None:
    """The table's row count FROM STATISTICS -- never count(*), which is the scan this
    exists to avoid. None when the database has no estimate to give."""
    _, dialect, schema = snapshot_backend(snapshot, organization_id)
    table = snapshot["table_name"]
    try:
        if dialect == "postgres":
            sql = "SELECT reltuples::bigint FROM pg_class WHERE oid = to_regclass(%(rel)s)"
            binds = {"rel": f'{schema}."{table}"'}
        else:
            sql = "SELECT num_rows FROM all_tables WHERE owner = :owner AND table_name = :tbl"
            binds = {"owner": schema.upper(), "tbl": table.upper()}
        _, rows = _run(snapshot, sql, binds, organization_id=organization_id, max_rows=1)
    except Exception:
        # An estimate is an optimisation, never a gate: if it cannot be read, the
        # picker behaves exactly as it did before this existed.
        return None
    return rows[0][0] if rows and rows[0] and rows[0][0] is not None else None


def _default_date_filter(snapshot: dict[str, Any]) -> FilterRequest | None:
    """The window an unfiltered query falls back to, or None for a canvas with no date.

    The row cap does not substitute for a window: FETCH FIRST applies AFTER GROUP BY,
    so an unfiltered aggregate reads every row before returning its first.

    The window bounds the worst case; it is not a speedup on its own. It pays only when
    selective -- Ellensburg's RPT_GL (6.08M rows, years of history) goes 4,062ms -> 825ms
    on three months, while demo25's rpt_measurement goes 198ms -> 256ms because its dates
    are clumped tightly enough that even 7 days holds 35% of the table.
    """
    field = window_date_field(snapshot)
    if not field:
        return None
    end = reporting_today()
    start = end - timedelta(days=DEFAULT_WINDOW_DAYS)
    return FilterRequest(field=field, op="between", value=[start.isoformat(), end.isoformat()])


def _serialize_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _cross_filter(cross_field: str | None, cross_value: str | None) -> list[dict[str, Any]]:
    """The field name goes through UNTOUCHED.

    This used to upper-case it, which was right when every column was CISADM's
    UPPER_SNAKE and wrong the moment the canvases arrived with Title Case business
    names: "Customer Class" became "CUSTOMER CLASS" and every card in the grid returned
    `Invalid filter field`. Casing is the query builder's job.
    """
    if cross_field and cross_value is not None and str(cross_value).strip():
        return [{"field": cross_field, "op": "eq", "value": cross_value}]
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


@router.get("/questions")
def snapshot_questions(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    """Every canvas's premade reports, flattened into ONE cross-canvas gallery of
    common business questions. Powers the visual builder's "Start from a question"
    panel: each entry is already the /query request shape, so picking one prefills
    the shelves. Cheap -- the catalog is already resident (load_catalog), no DB hit.
    Workstream access is honoured: a user sees only questions on canvases in their
    granted workstreams."""
    ctx.require_permission("snapshots:read")
    org_id = ctx.effective_organization_id()
    catalog = load_catalog(organization_id=org_id)
    order = catalog.get("workstream_order", [])
    labels = catalog.get("workstream_labels", {})
    order_index = {ws: i for i, ws in enumerate(order)}

    questions: list[dict[str, Any]] = []
    for snapshot_id, meta in catalog.get("snapshots", {}).items():
        if not meta.get("portal_enabled", True):
            continue
        workstream = meta.get("workstream", "")
        if not ctx.can_access_workstream(workstream):
            continue
        for report in meta.get("premade_reports", []) or []:
            questions.append({
                "id": f"{snapshot_id}:{report.get('id')}",
                "report_id": report.get("id"),
                "snapshot_id": snapshot_id,
                "snapshot_label": meta.get("label", snapshot_id),
                "workstream": workstream,
                "workstream_label": labels.get(workstream, workstream),
                "title": report.get("title", report.get("id")),
                "description": report.get("description", ""),
                "dimensions": report.get("dimensions", []),
                "measures": report.get("measures", []),
                "filters": report.get("filters", []),
                "chart_type": report.get("chart_type", "bar"),
            })

    questions.sort(key=lambda q: (order_index.get(q["workstream"], 99),
                                  q["snapshot_label"], q["title"]))
    return {
        "organization_id": org_id,
        "workstream_order": order,
        "workstream_labels": labels,
        "count": len(questions),
        "questions": questions,
    }


def _lens_selection(pairs: list[str]) -> dict[str, str]:
    """`?lens=total_customers:inactive` repeated per card.

    The client names a lens; the predicate behind it stays server-side, so this can
    only ever pick from what the KPI already declared. An unparseable pair is dropped
    rather than raising -- a stale bookmark should render the default, not a 400.
    """
    out: dict[str, str] = {}
    for pair in pairs:
        kpi_id, sep, lens_id = pair.partition(":")
        if sep and kpi_id.strip() and lens_id.strip():
            out[kpi_id.strip()] = lens_id.strip()
    return out


@router.get("/executive-summary")
def executive_summary(
    days: int = 30,
    compare: bool = False,
    compare_mode: str = "prior_period",
    cross_field: str | None = None,
    cross_value: str | None = None,
    lens: list[str] = Query(default=[]),
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
        lenses=_lens_selection(lens),
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
    # A canvas carries no load watermark of its own; the row count is the honest figure.
    sql = f"SELECT COUNT(*) AS row_count, NULL AS latest_load_dttm FROM {_qualified(snapshot, org_id)}"
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
    if field not in allowed_fields(snapshot):
        raise HTTPException(status_code=400, detail=f"Unknown field: {field_id}")
    # Any DIMENSION is a valid value source (the builder's filter shelf offers a value
    # picker for every dimension) — declared scope_filters remain valid too. Measures
    # are refused: a distinct over a numeric fact is meaningless and expensive.
    if field not in allowed_scope:
        roles = {f["id"]: f.get("role") for f in snapshot.get("fields", [])}
        if roles.get(field) != "dimension":
            raise HTTPException(status_code=400, detail=f"Scope filter not allowed: {field_id}")


    # Decline BEFORE scanning. A DISTINCT over a fact table costs ~600 ms at 3.5M rows
    # and ~6 s at a 35M-row client, on the path a user takes to add one filter pill.
    # Declining is instant and honest; sampling the table would quietly change what the
    # list means.
    estimate = _row_estimate(snapshot, org_id)
    if not can_enumerate_values(estimate):
        return {
            "client": org_id,
            "organization_id": org_id,
            "snapshot_id": snapshot_id,
            "field": field,
            "label": allowed_scope.get(field, {}).get("label", field),
            "values": [],
            "enumerable": False,
            "reason": (
                f"{int(estimate):,} rows — too many to list values from. "
                f"Type the value instead."
            ),
        }

    col = f'"{field}"'
    sql = (f"SELECT DISTINCT {col} AS val FROM {_qualified(snapshot, org_id)} "
           f"WHERE {col} IS NOT NULL ORDER BY 1 FETCH FIRST 100 ROWS ONLY")
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
        "label": allowed_scope.get(field, {}).get("label", field),
        "values": values,
        "enumerable": True,
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
    # No recency window: the canvases are already scoped to a client's own data and ten
    # rows are cheap, while ordering by a date on a large canvas is not. Only a preview.
    sql = f"SELECT * FROM {_qualified(snapshot, org_id)} FETCH FIRST {row_cap} ROWS ONLY"
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
    from api.access_audit import record_access_event
    record_access_event(
        actor_email=ctx.email, actor_id=ctx.id, action="report_run",
        target_type="snapshot", target_id=snapshot_id,
        detail=f"sample rows; rows={len(serialized_rows)}")
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
    from api.access_audit import record_access_event
    record_access_event(
        actor_email=ctx.email, actor_id=ctx.id, action="raw_sql_run",
        target_type="snapshot", target_id=snapshot_id,
        detail=f"rows={len(serialized_rows)}; sql: {body.sql[:300]}")
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
    # A window the server chose and did not mention is the bug the legacy shape already
    # had: the caller asked for all time, got a quarter, and only the raw SQL said so.
    # Applying the same default to 38 more canvases without disclosing it would spread
    # that rather than fix it, so what we add is reported back and what the CALLER sent
    # is left alone and never described as ours.
    applied_window: dict[str, Any] | None = None
    if not filters:
        default_filter = _default_date_filter(snapshot)
        if default_filter:
            filters = [default_filter.model_dump()]
            # `field` stays the machine name the caller filters on; only the sentence is
            # humanised. On the legacy shape those differ (ACCOUNTING_DT vs "Accounting
            # date"), and that shape is six of the nine orgs.
            label = window_date_label(snapshot, default_filter.field)
            applied_window = {
                "field": default_filter.field,
                "label": label,
                "days": DEFAULT_WINDOW_DAYS,
                "start": default_filter.value[0],
                "end": default_filter.value[1],
                "note": (f"No filter was set, so this shows the trailing "
                         f"{DEFAULT_WINDOW_DAYS} days on {label}."),
            }

    try:
        # The ORG decides the backend and dialect: the same canvas runs in Postgres for
        # a CDC-fed tenant and in the client's own Oracle instance for an in-database
        # one, with quoted Title Case columns identical in both.
        backend, dialect, schema = snapshot_backend(snapshot, org_id)
        warehouse = backend == "postgres"
        trusted = set(snapshot.get("trusted_measures", []))
        sql, binds = build_query(
            table_name=snapshot["table_name"],
            allowed_fields=allowed_fields(snapshot),
            trusted_measures=trusted,
            dimensions=body.dimensions,
            measures=[m.model_dump() for m in body.measures],
            filters=filters,
            limit=min(body.limit, snapshot.get("max_rows", 500)),
            time_dimensions=[t.model_dump() for t in body.time_dimensions],
            dialect=dialect,
            schema=schema,
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
    from api.access_audit import record_access_event
    record_access_event(
        actor_email=ctx.email, actor_id=ctx.id, action="report_run",
        target_type="snapshot", target_id=snapshot_id,
        detail=(f"dims={','.join(body.dimensions) or '-'}; "
                f"measures={','.join(m.agg + '(' + m.field + ')' for m in body.measures)}; "
                f"rows={len(serialized_rows)}"))
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
        # None when the caller set their own filters: only a window WE chose is ours to
        # announce, and labelling the caller's own range as a default would misreport it.
        "applied_window": applied_window,
    }
