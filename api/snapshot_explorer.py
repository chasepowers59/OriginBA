"""Snapshot explorer API routes (demo database only)."""

from __future__ import annotations

import json
import logging
import re
import time

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
from api.reporting_dates import (DEFAULT_WINDOW_DAYS, DEFAULT_WINDOW_MIN_ROWS, data_as_of, reporting_today,
                                 window_date_field, window_date_label)
from api.executive_dashboard import (DATABASE_UNREACHABLE_NOTE, WAREHOUSE_NOT_BUILT_NOTE, build_executive_summary,
                                     is_missing_relation_error, is_not_connected_error, is_transient_error)
from api.kpi_runner import COMPARE_MODES
from api.data_version import data_version
from api.summary_cache import cached
from api.row_security import enforce as enforce_row_rules, readable, require_unrestricted, row_filters
from api.workstream_dashboard import build_workstream_about, build_workstream_summary
from api.snapshot_catalog import (CatalogError, allowed_fields, boolean_fields, get_snapshot,
                                  list_snapshots, list_workstreams,
                                  load_catalog, snapshot_backend)


logger = logging.getLogger(__name__)
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
    # the reader chose "All dates": no default window, even on a large canvas
    all_dates: bool = False


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


# (organization_id, table) -> (read_at, rows). Statistics move only when the warehouse
# is rebuilt, so a ten-minute memory is plenty and costs one catalog read per canvas.
_ESTIMATES: dict[tuple[str | None, str], tuple[float, int | None]] = {}
_ESTIMATE_TTL_SECONDS = 600


def _row_estimate(snapshot: dict[str, Any], organization_id: str | None) -> int | None:
    """How many rows the ENGINE thinks the canvas has, from its own statistics: no scan.

    Postgres pg_class.reltuples and Oracle ALL_TABLES.NUM_ROWS are both maintained by
    the build's ANALYZE / DBMS_STATS post-hook. None when the statistic cannot be read,
    and the caller treats None as "big" -- the window is a safety bound, and losing it
    on a 6M-row canvas costs far more than keeping it on a small one.
    """
    import time
    table = str(snapshot.get("table_name") or "")
    key = (organization_id, table)
    hit = _ESTIMATES.get(key)
    if hit and time.monotonic() - hit[0] < _ESTIMATE_TTL_SECONDS:
        return hit[1]
    estimate: int | None = None
    try:
        _backend, dialect, schema = snapshot_backend(snapshot, organization_id)
        if not re.fullmatch(r"[A-Za-z0-9_]+", table) or not re.fullmatch(r"[A-Za-z0-9_]+", schema):
            return None
        if dialect == "postgres":
            sql = ("SELECT c.reltuples::bigint AS n FROM pg_class c "
                   "JOIN pg_namespace n ON n.oid = c.relnamespace "
                   f"WHERE n.nspname = '{schema}' AND c.relname = '{table}'")
        else:
            sql = (f"SELECT NUM_ROWS AS n FROM ALL_TABLES WHERE OWNER = '{schema.upper()}' "
                   f"AND TABLE_NAME = '{table.upper()}'")
        _columns, rows = _run(snapshot, sql, organization_id=organization_id, max_rows=1)
        if rows and rows[0] and rows[0][0] is not None:
            estimate = int(rows[0][0])
    except Exception:  # noqa: BLE001 -- an unreadable statistic must not fail the query
        estimate = None
    _ESTIMATES[key] = (time.monotonic(), estimate)
    return estimate


def _default_date_filter(snapshot: dict[str, Any],
                         organization_id: str | None = None) -> FilterRequest | None:
    """The window an unfiltered query falls back to, or None for a canvas with no date
    -- or for a canvas too small for a window to buy anything (DEFAULT_WINDOW_MIN_ROWS).

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
    if organization_id is not None:
        estimate = _row_estimate(snapshot, organization_id)
        if estimate is not None and estimate < DEFAULT_WINDOW_MIN_ROWS:
            return None
    end = reporting_today(organization_id)
    start = end - timedelta(days=DEFAULT_WINDOW_DAYS)
    return FilterRequest(field=field, op="between", value=[start.isoformat(), end.isoformat()])


def _query_failure(prefix: str, exc: Exception) -> HTTPException:
    """A 502 that reads as a sentence when the cause is an unbuilt warehouse.

    Every org reads the dbt catalog, so an org whose in-database warehouse has not been
    built yet reaches every canvas route and fails each one with ORA-00942. Forwarding
    the driver's text told the reader nothing they could act on; the note does.
    """
    if is_missing_relation_error(str(exc)):
        return HTTPException(status_code=502, detail=WAREHOUSE_NOT_BUILT_NOTE)
    # a dropped connection or a timeout is said in words: the driver's text can name hosts
    if is_not_connected_error(str(exc)):
        return HTTPException(status_code=503, detail=DATABASE_UNREACHABLE_NOTE)
    if is_transient_error(str(exc)):
        return HTTPException(status_code=504, detail="This took too long to load. Try a shorter period.")
    return HTTPException(status_code=502, detail=f"{prefix}: {exc}")


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
    enforce_row_rules(ctx, snapshot)   # a canvas without a rule's column is refused
    return snapshot


@router.get("")
def snapshots_index(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    org_id = ctx.effective_organization_id()
    catalog = load_catalog(organization_id=org_id)
    workstreams = filter_workstreams_for_auth(list_workstreams(org_id), ctx)
    snapshots = filter_snapshots_for_auth(list_snapshots(organization_id=org_id), ctx)
    from api.client_capabilities import hidden_canvases
    unused = hidden_canvases(org_id)   # a data set the client never used opens empty
    snapshots = [s for s in snapshots if s["id"] not in unused]
    if ctx.row_rules:
        snapshots = [s for s in snapshots if readable(ctx.row_rules, get_snapshot(s["id"], org_id))]
    return {
        "client": org_id or catalog.get("client", "demo"),
        "organization_id": org_id,
        "organization_name": ctx.organization_name,
        "workstream_order": catalog.get("workstream_order", []),
        "workstream_labels": catalog.get("workstream_labels", {}),
        "portal_snapshots": catalog.get("portal_snapshots", []),
        "poc_enabled": catalog.get("poc_enabled", []),
        # Either backend counts: Postgres orgs read the warehouse, Oracle orgs their
        # own instance. Checking only one showed warehouse tenants "Connect database"
        # with a live warehouse behind them.
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

    from api.client_capabilities import hidden_reports
    unused = hidden_reports(org_id, catalog)   # the same reports the Library hides
    questions: list[dict[str, Any]] = []
    for snapshot_id, meta in catalog.get("snapshots", {}).items():
        if not meta.get("portal_enabled", True):
            continue
        workstream = meta.get("workstream", "")
        if not ctx.can_access_workstream(workstream) or not readable(ctx.row_rules, meta):
            continue
        for report in meta.get("premade_reports", []) or []:
            if (snapshot_id, report.get("id")) in unused:
                continue
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
    return cached_home_summary(org_id, days, compare, compare_mode, extra, ctx.workstreams,
                               _lens_selection(lens), ctx.row_rules)


def cached_home_summary(org_id: str, days: int, compare: bool, compare_mode: str, extra: list,
                        workstreams: list | None, lenses: dict | None, row_rules: tuple) -> dict[str, Any]:
    """The home summary through the cache; api/cache_warmer.py builds the same keys."""
    key = ("home", org_id, days, compare, compare_mode, repr(extra), tuple(sorted(workstreams or [])),
           repr(sorted((lenses or {}).items())), repr(row_rules))
    return cached(key, lambda: build_executive_summary(
        days,
        compare=compare,
        compare_mode=compare_mode,
        extra_filters=extra,
        allowed_workstreams=workstreams,
        lenses=lenses,
        organization_id=org_id,
        row_rules=row_rules,
    ), version=data_version(org_id))


def cached_workstream_summary(org_id: str, workstream_id: str, days: int, compare: bool, compare_mode: str,
                              extra: list, row_rules: tuple) -> dict[str, Any]:
    return cached(("workstream", org_id, workstream_id, days, compare, compare_mode, repr(extra), repr(row_rules)),
                  lambda: build_workstream_summary(
                      workstream_id,
                      days,
                      compare=compare,
                      compare_mode=compare_mode,
                      extra_filters=extra,
                      organization_id=org_id,
                      row_rules=row_rules,
                  ), version=data_version(org_id))


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
    result = cached_workstream_summary(org_id, workstream_id, days, compare, compare_mode, extra, ctx.row_rules)
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
    default_filter = _default_date_filter(snapshot, org_id)
    return {
        "id": snapshot_id,
        "client": org_id,
        "organization_id": org_id,
        **snapshot,
        "suggested_default_filter": default_filter.model_dump() if default_filter else None,
        # The browser computes its date presets; a frozen copy's presets end here.
        "data_as_of": data_as_of(org_id),
    }


@router.get("/{snapshot_id}/stats")
def snapshot_stats(
    snapshot_id: str,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("snapshots:read")
    org_id = require_org_for_data(ctx)
    snapshot = _require_snapshot_access(ctx, snapshot_id)
    key = (org_id, snapshot_id, repr(ctx.row_rules))
    hit = _STATS_CACHE.get(key)
    if hit and time.monotonic() - hit[0] < STATS_TTL_SECONDS:
        count = hit[1]
    else:
        try:
            count = _row_count(snapshot, org_id, ctx.row_rules)
        except Exception as exc:
            raise _query_failure("Stats failed", exc) from exc
        _STATS_CACHE[key] = (time.monotonic(), count)
    return {
        "client": org_id,
        "organization_id": org_id,
        # As written. Upper-casing was an Oracle habit and a dbt canvas id is lowercase;
        # returning RPT_BILL_SEGMENT for rpt_bill_segment breaks the caller's own lookups.
        "snapshot_id": snapshot_id,
        "row_count": count,
        # A canvas carries no load watermark of its own; the row count is the honest figure.
        "latest_load_dttm": None,
    }


# A canvas changes only when the warehouse is rebuilt, so its count is not re-taken per
# visit. COUNT(*) over Ellensburg's rpt_gl (6.08M rows) cost ~10 s of every page view.
_STATS_CACHE: dict[tuple[str, str], tuple[float, int]] = {}
STATS_TTL_SECONDS = 900


def _row_count(snapshot: dict, org_id: str, row_rules: tuple = ()) -> int:
    backend, dialect, schema = snapshot_backend(snapshot, org_id)
    if row_rules:
        # A restricted person's count is of their rows: no table statistics, a filtered count.
        sql, binds = build_query(table_name=snapshot["table_name"], allowed_fields=allowed_fields(snapshot),
                                 trusted_measures=set(), dimensions=[], measures=[{"field": "*", "agg": "count"}],
                                 filters=row_filters(row_rules, snapshot), limit=1, dialect=dialect, schema=schema)
        _, rows = _run(snapshot, sql, binds, organization_id=org_id, max_rows=1)
        return int(rows[0][0] or 0) if rows else 0
    if backend != "postgres":
        # The build gathers statistics after every table, so NUM_ROWS is the count as built.
        _, rows = _run(snapshot, "SELECT num_rows FROM all_tables WHERE owner = :owner AND table_name = :t",
                       {"owner": schema.upper(), "t": snapshot["table_name"].upper()},
                       organization_id=org_id, max_rows=1)
        if rows and rows[0][0] is not None:
            return int(rows[0][0])
    _, rows = _run(snapshot, f"SELECT COUNT(*) AS row_count FROM {_qualified(snapshot, org_id)}",
                   organization_id=org_id, max_rows=1)
    return int(rows[0][0] or 0) if rows else 0


def _where_filters(where: Any) -> list[dict[str, Any]]:
    if not isinstance(where, str) or not where:   # absent (or the route called directly)
        return []
    try:
        parsed = json.loads(where)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="where must be a JSON list of filters") from exc
    if not isinstance(parsed, list) or not all(isinstance(f, dict) for f in parsed) or len(parsed) > 10:
        raise HTTPException(status_code=400, detail="where must be a JSON list of at most 10 filters")
    return [{"field": str(f.get("field")), "op": str(f.get("op")), "value": f.get("value")} for f in parsed]


@router.get("/{snapshot_id}/scope-options/{field_id}")
def snapshot_scope_options(
    snapshot_id: str,
    field_id: str,
    where: str | None = Query(default=None, description="JSON list of filters the values must occur under"),
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
            "reason": "Too many rows to list this column's values. Type the value instead.",
        }

    col = f'"{field}"'
    sql = (f"SELECT DISTINCT {col} AS val FROM {_qualified(snapshot, org_id)} "
           f"WHERE {col} IS NOT NULL ORDER BY 1 FETCH FIRST 100 ROWS ONLY")
    binds = None
    narrowing = _where_filters(where)
    if narrowing or ctx.row_rules:
        # Only the values that occur under the answers above (cascading parameters) and in
        # this person's rows: grouped through the query builder, which validates every filter.
        _, dialect, schema = snapshot_backend(snapshot, org_id)
        try:
            sql, binds = build_query(table_name=snapshot["table_name"], allowed_fields=allowed_fields(snapshot),
                                     trusted_measures=set(), dimensions=[field],
                                     measures=[{"field": "*", "agg": "count"}],
                                     filters=narrowing + row_filters(ctx.row_rules, snapshot),
                                     limit=100, dialect=dialect, schema=schema)
        except QueryValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        columns, rows = _run(snapshot, sql, binds, organization_id=org_id, max_rows=100)
    except Exception as exc:
        raise _query_failure("Scope options failed", exc) from exc

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
    require_unrestricted(ctx)   # the preview is SELECT *, which cannot carry row rules

    row_cap = max(1, min(limit, 10))
    # No recency window: the canvases are already scoped to a client's own data and ten
    # rows are cheap, while ordering by a date on a large canvas is not. Only a preview.
    sql = f"SELECT * FROM {_qualified(snapshot, org_id)} FETCH FIRST {row_cap} ROWS ONLY"
    try:
        columns, rows = _run(snapshot, sql, organization_id=org_id, max_rows=row_cap)
    except Exception as exc:
        raise _query_failure("Sample rows failed", exc) from exc

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
        elif agg == "share":
            labels[f"m{idx}"] = f"% {label_of(field)}"
        else:
            word, name = _AGG_WORD.get(agg, agg.title()), label_of(field)
            # "Total Balance" summed is "Total Balance", not "Total Total Balance"
            labels[f"m{idx}"] = name if name.split(" ", 1)[0] == word else f"{word} {name}"
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
    require_unrestricted(ctx)

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


def cached_query(org_id: str, snapshot: dict[str, Any], body: QueryRequest,
                 filters: list[dict[str, Any]]) -> tuple[str, list[str], list, str]:
    """The governed statement for this request, its columns and rows, and the table that
    answered: the canvas, or its pre-aggregate when api/aggregate_routing.py proves the answer
    is the canvas's. The same request for the same org is answered from memory until the
    warehouse is rebuilt: a report over Ellensburg's rpt_billed_charge took ~25 s.
    api/cache_warmer.py runs the same path."""
    # The ORG decides the backend and dialect: the same canvas runs in Postgres for a
    # CDC-fed tenant and in the client's own Oracle instance for an in-database one, with
    # quoted Title Case columns identical in both.
    backend, dialect, schema = snapshot_backend(snapshot, org_id)
    request = {"dimensions": body.dimensions, "measures": [m.model_dump() for m in body.measures],
               "filters": filters, "time_dimensions": [t.model_dump() for t in body.time_dimensions],
               "limit": min(body.limit, snapshot.get("max_rows", 500))}
    # Always built, so a request the canvas refuses is refused whichever table would answer it.
    sql, binds = build_query(
        table_name=snapshot["table_name"],
        allowed_fields=allowed_fields(snapshot),
        trusted_measures=set(snapshot.get("trusted_measures", [])),
        boolean_fields=boolean_fields(snapshot),
        dialect=dialect,
        schema=schema,
        **request,
    )

    def run() -> tuple[str, list[str], list, str]:
        # Routing is decided on a miss: it reads the aggregate's build once per miss, and the
        # answer is the canvas's either way, so the canvas statement stays the key.
        from api.aggregate_routing import routed_query
        if backend == "postgres":
            from api.warehouse_db import execute_query as run
        else:
            run = execute_query
        routed = routed_query(org_id, snapshot, dialect=dialect, schema=schema, **request)
        if routed:
            statement, statement_binds, served_from = routed
            try:
                columns, rows = run(statement, statement_binds, organization_id=org_id, max_rows=body.limit)
                return statement, columns, rows, served_from
            except Exception:  # noqa: BLE001 -- an aggregate older than the catalog (a
                # dimension the nightly has not added yet) passes the identity check and
                # fails here; the canvas still holds the answer
                logger.warning("aggregate %s could not answer; reading %s", served_from, snapshot["table_name"])
        columns, rows = run(sql, binds, organization_id=org_id, max_rows=body.limit)
        return sql, columns, rows, snapshot["table_name"]

    return cached(("query", org_id, backend, sql, repr(sorted(binds.items())), body.limit),
                  run, keep=lambda _: True, version=data_version(org_id))


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
    # A window the server chose and did not mention is a bug this code once had: the
    # caller asked for all time, got a quarter, and only the raw SQL said so.
    # Applying the same default to 38 more canvases without disclosing it would spread
    # that rather than fix it, so what we add is reported back and what the CALLER sent
    # is left alone and never described as ours.
    applied_window: dict[str, Any] | None = None
    if not filters and not body.all_dates:
        default_filter = _default_date_filter(snapshot, org_id)
        if default_filter:
            filters = [default_filter.model_dump()]
            # `field` stays the machine name the caller filters on; only the sentence is
            # humanised, from the canvas's declared date_fields label.
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

    # A restricted person's rows only (api/row_security.py). Added after the default window
    # so it never counts as a filter the caller set.
    filters = filters + enforce_row_rules(ctx, snapshot)

    try:
        sql, columns, rows, served_from = cached_query(org_id, snapshot, body, filters)
    except QueryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        warehouse = snapshot_backend(snapshot, org_id)[0] == "postgres"
        raise _query_failure("The query failed", exc) from exc

    serialized_rows = [
        {columns[i]: _serialize_value(row[i]) for i in range(len(columns))}
        for row in rows
    ]
    # A breakdown cut to its top groups must not be totalled by the reader: CityCorp's
    # on/off churn (2026-10-01) showed 1,971 for a period that held 3,591. Say it was cut,
    # and answer the same question unbroken so the total and every share are the real ones.
    truncated = bool(body.dimensions or body.time_dimensions) \
        and len(rows) >= min(body.limit, snapshot.get("max_rows", 500))
    totals = None
    if truncated:
        whole = body.model_copy(update={"dimensions": [], "time_dimensions": [], "limit": 1})
        _, total_columns, total_rows, _ = cached_query(org_id, snapshot, whole, filters)
        if total_rows:
            totals = {c: _serialize_value(v) for c, v in zip(total_columns, total_rows[0])}
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
        "truncated": truncated,
        "totals": totals,
        "sql": sql,
        # None when the caller set their own filters: only a window WE chose is ours to
        # announce, and labelling the caller's own range as a default would misreport it.
        "applied_window": applied_window,
        # the canvas, or its pre-aggregate when that provably gives the same answer
        "served_from": served_from,
    }
