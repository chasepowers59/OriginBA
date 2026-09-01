"""Database workspace API — ad-hoc read-only SQL with paginated results.

ENGINE ROUTING: the workspace queries whatever database serves this org's catalog —
the same decision the explorer and dashboards make. A dbt-catalog org reads the
Postgres reporting warehouse and sees ONLY the governed reporting canvases (search_path
pinned to `reporting`, other schemas rejected by the validator); a legacy cisadm-catalog
org still reads the Oracle *_RPT_CURR snapshots until it is migrated.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.auth.dependencies import AuthContext, require_permission
from api.demo_db import demo_configured
from api.demo_db import execute_query as execute_demo_query
from api.org_db import require_org_for_data
from api.snapshot_catalog import org_backend
from api.sql_workspace_validator import (
    SqlWorkspaceValidationError,
    validate_oracle_reporting_scope,
    validate_reporting_scope,
    validate_workspace_sql,
    wrap_count_sql,
    wrap_paginated_sql,
)
from api.warehouse_db import execute_query as execute_warehouse_query
from api.warehouse_db import warehouse_configured


router = APIRouter(prefix="/database", tags=["database"])

MAX_PAGE_SIZE = 500
DEFAULT_PAGE_SIZE = 50
MAX_TOTAL_ROWS = 50_000

# The legacy Oracle workspace's curated list. The warehouse needs no equivalent:
# every rpt_* canvas in the reporting schema is governed by construction.
ACTIVE_SNAPSHOT_TABLES = (
    "FT_RPT_CURR",
    "BSEG_BILLED_USAGE_RPT_CURR",
    "BSEG_SQ_USAGE_RPT_CURR",
    "D1_MSRMT_RPT_CURR",
    "FT_GL_DISTRIBUTION_RPT_CURR",
    "D1_USAGE_RPT_CURR",
    "D1_USAGE_SCALAR_DTL_RPT_CURR",
)


class SqlExecuteRequest(BaseModel):
    sql: str
    offset: int = Field(default=0, ge=0)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
    include_total_count: bool = False


def _serialize_cell(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "read"):
        try:
            data = value.read()
        except Exception:
            return str(value)
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        text = str(data)
        if len(text) > 4000:
            return text[:4000] + "…"
        return text
    return value


def _rows_to_dicts(columns: list[str], rows: list[list[Any]]) -> list[dict[str, Any]]:
    return [
        {columns[i]: _serialize_cell(row[i]) for i in range(len(columns))}
        for row in rows
    ]


def _engine(org_id: str) -> str:
    """Workspace engine for this org -- the portal-wide routing decision.

    Three shapes since 2026-08-28: 'postgres' (dbt warehouse, shape A), 'oracle'
    (legacy CISADM snapshots), 'oracle_dbt' (the dbt canvases inside the client's
    own Oracle instance -- ORIGINBA_REPORTING, no CDC)."""
    engine, catalog = org_backend(org_id)
    if catalog == "dbt":
        return "postgres" if engine == "postgres" else "oracle_dbt"
    return "oracle"


def _require_db(org_id: str) -> str:
    engine = _engine(org_id)
    ok = warehouse_configured(org_id) if engine == "postgres" else demo_configured(org_id)
    if not ok:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured for this organization.",
        )
    return engine


def _validate(engine: str, sql: str) -> str:
    validated = validate_workspace_sql(sql)
    if engine == "postgres":
        validate_reporting_scope(validated)
    elif engine == "oracle_dbt":
        validate_oracle_reporting_scope(validated)
    return validated


def _run(engine: str, sql: str, org_id: str, max_rows: int) -> tuple[list[str], list[list[Any]]]:
    if engine == "postgres":
        # search_path resolves unqualified names against CISADM first (the schema
        # analysts actually know), then the reporting layer; the validator already
        # rejected explicit references to any other schema and guards secrets.
        return execute_warehouse_query(
            sql, organization_id=org_id, max_rows=max_rows, search_path="cisadm, reporting")
    if engine == "oracle_dbt":
        # CURRENT_SCHEMA is the Oracle analogue: unqualified names resolve to
        # CISADM (rpt_* stays reachable as ORIGINBA_REPORTING.rpt_*); the
        # validator fenced everything else and guards secrets.
        return execute_demo_query(
            sql, organization_id=org_id, max_rows=max_rows,
            current_schema="CISADM")
    return execute_demo_query(sql, organization_id=org_id, max_rows=max_rows)


def _list_oracle_reporting_tables(org_id: str, needle: str) -> list[dict[str, Any]]:
    """CISADM tables (the schema analysts know) with optimizer stats, uppercase
    per Oracle convention. Empty tables are skipped — a full CISADM install has
    thousands of never-used tables that would bury the ones with data."""
    binds: dict[str, Any] = {}
    # Log tables (D1_USAGE_LOG, *_LOG_PARM, ...) carry no business value and their
    # row counts bury the tables that do -- excluded outright.
    where = ("WHERE owner = 'CISADM' AND num_rows > 0"
             " AND table_name NOT LIKE '%\\_LOG' ESCAPE '\\'"
             " AND table_name NOT LIKE '%\\_LOG\\_%' ESCAPE '\\'"
             " AND table_name NOT LIKE '%LOGPARM'")
    if needle:
        binds["pattern"] = f"%{needle.upper()}%"
        where += " AND table_name LIKE :pattern"
    sql = f"""
        SELECT table_name, num_rows, last_analyzed
        FROM all_tables
        {where}
        ORDER BY num_rows DESC
        FETCH FIRST 200 ROWS ONLY
    """
    columns, rows = execute_demo_query(sql, binds, organization_id=org_id, max_rows=200)
    return [
        {columns[i].lower(): _serialize_cell(row[i]) for i in range(len(columns))}
        for row in rows
    ]


def _list_warehouse_tables(org_id: str, needle: str) -> list[dict[str, Any]]:
    """CISADM landing tables with live row estimates, busiest first — the
    schema analysts know. Empty tables are skipped so the ones with data lead."""
    sql = """
        select c.relname as table_name,
               s.n_live_tup as num_rows,
               greatest(s.last_analyze, s.last_autoanalyze) as last_analyzed
        from pg_stat_user_tables s
        join pg_class c on c.oid = s.relid
        where s.schemaname = 'cisadm'
          and s.n_live_tup > 0
          -- log tables carry no business value; keep them out of the browser
          and c.relname not like '%%\\_log' escape '\\'
          and c.relname not like '%%\\_log\\_%%' escape '\\'
          and c.relname not like '%%logparm'
          and (%(pattern)s = '' or c.relname ilike '%%' || %(pattern)s || '%%')
        order by s.n_live_tup desc
        limit 200
    """
    columns, rows = execute_warehouse_query(
        sql, {"pattern": needle}, organization_id=org_id, max_rows=200)
    return [
        {columns[i].lower(): _serialize_cell(row[i]) for i in range(len(columns))}
        for row in rows
    ]


@router.get("/tables")
def list_tables(
    ctx: AuthContext = Depends(require_permission("database:sql")),
    schema: str = Query(default="", min_length=0, max_length=128),
    search: str = Query(default="", max_length=128),
    snapshots_only: bool = Query(default=True),
    include_stats: bool = Query(default=False),
) -> dict[str, Any]:
    org_id = require_org_for_data(ctx)
    engine = _require_db(org_id)

    if engine == "postgres":
        try:
            tables = _list_warehouse_tables(org_id, search.strip().lower())
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to list tables: {exc}") from exc
        return {
            "organization_id": org_id,
            "engine": engine,
            "schema": "cisadm",
            "tables": tables,
            "table_count": len(tables),
            "source": "database",
        }

    if engine == "oracle_dbt":
        try:
            tables = _list_oracle_reporting_tables(org_id, search.strip())
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to list tables: {exc}") from exc
        return {
            "organization_id": org_id,
            "engine": engine,
            "schema": "CISADM",
            "tables": tables,
            "table_count": len(tables),
            "source": "database",
        }

    schema_upper = (schema.strip() or "CISADM").upper()
    needle = search.strip().upper()

    if snapshots_only and not needle and not include_stats:
        tables = [
            {"table_name": name, "num_rows": None, "last_analyzed": None}
            for name in ACTIVE_SNAPSHOT_TABLES
        ]
        return {
            "organization_id": org_id,
            "engine": engine,
            "schema": schema_upper,
            "tables": tables,
            "table_count": len(tables),
            "source": "catalog",
        }

    binds: dict[str, Any] = {"owner": schema_upper}
    where = "WHERE owner = :owner"
    if snapshots_only:
        where += " AND table_name LIKE '%RPT_CURR'"
    if needle:
        binds["pattern"] = f"%{needle}%"
        where += " AND table_name LIKE :pattern"

    if include_stats:
        sql = f"""
            SELECT table_name, num_rows, last_analyzed
            FROM all_tables
            {where}
            ORDER BY table_name
            FETCH FIRST 200 ROWS ONLY
        """
    else:
        sql = f"""
            SELECT table_name, CAST(NULL AS NUMBER) AS num_rows, CAST(NULL AS DATE) AS last_analyzed
            FROM all_tables
            {where}
            ORDER BY table_name
            FETCH FIRST 200 ROWS ONLY
        """
    try:
        columns, rows = execute_demo_query(sql, binds, organization_id=org_id, max_rows=200)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to list tables: {exc}") from exc

    items = []
    for row in rows:
        # Lowercase the keys: Oracle reports TABLE_NAME and the UI reads table_name.
        rec = {columns[i].lower(): _serialize_cell(row[i]) for i in range(len(columns))}
        items.append(rec)

    return {
        "organization_id": org_id,
        "engine": engine,
        "schema": schema_upper,
        "tables": items,
        "table_count": len(items),
        "source": "database",
    }


@router.post("/sql/execute")
def execute_sql(
    body: SqlExecuteRequest,
    ctx: AuthContext = Depends(require_permission("database:sql")),
) -> dict[str, Any]:
    org_id = require_org_for_data(ctx)
    engine = _require_db(org_id)

    if body.offset >= MAX_TOTAL_ROWS:
        raise HTTPException(
            status_code=400,
            detail=f"Offset cannot exceed {MAX_TOTAL_ROWS:,} rows.",
        )

    try:
        validated = _validate(engine, body.sql)
    except SqlWorkspaceValidationError as exc:
        from api.access_audit import record_access_event
        record_access_event(
            actor_email=ctx.email, actor_id=ctx.id, action="sql_refused",
            target_type="sql", target_id=org_id,
            detail=f"{exc} | sql: {body.sql[:300]}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    page_size = max(1, min(body.page_size, MAX_PAGE_SIZE))
    if body.offset + page_size > MAX_TOTAL_ROWS:
        page_size = max(1, MAX_TOTAL_ROWS - body.offset)

    paged_sql = wrap_paginated_sql(validated, offset=body.offset, limit=page_size, probe_extra=1)
    started = time.perf_counter()
    try:
        columns, raw_rows = _run(engine, paged_sql, org_id, page_size + 1)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Query failed: {exc}") from exc
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    has_more = len(raw_rows) > page_size
    page_rows = raw_rows[:page_size]
    serialized = _rows_to_dicts(columns, page_rows)

    total_count: int | None = None
    if body.include_total_count:
        try:
            count_sql = wrap_count_sql(validated)
            _, count_rows = _run(engine, count_sql, org_id, 1)
            if count_rows:
                total_count = int(count_rows[0][0])
        except Exception:
            total_count = None

    fetched_total = body.offset + len(page_rows)

    from api.access_audit import record_access_event
    record_access_event(
        actor_email=ctx.email, actor_id=ctx.id, action="sql_execute",
        target_type="sql", target_id=org_id,
        detail=f"rows={len(serialized)}; ms={elapsed_ms}; sql: {validated[:300]}")

    return {
        "organization_id": org_id,
        "engine": engine,
        "columns": columns,
        "rows": serialized,
        "row_count": len(serialized),
        "offset": body.offset,
        "page_size": page_size,
        "has_more": has_more,
        "fetched_total": fetched_total,
        "total_count": total_count,
        "execution_ms": elapsed_ms,
        "sql": validated,
    }


@router.post("/sql/count")
def count_sql(
    body: SqlExecuteRequest,
    ctx: AuthContext = Depends(require_permission("database:sql")),
) -> dict[str, Any]:
    org_id = require_org_for_data(ctx)
    engine = _require_db(org_id)

    try:
        validated = _validate(engine, body.sql)
    except SqlWorkspaceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    started = time.perf_counter()
    try:
        count_sql_text = wrap_count_sql(validated)
        _, count_rows = _run(engine, count_sql_text, org_id, 1)
        total = int(count_rows[0][0]) if count_rows else 0
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Count failed: {exc}") from exc

    return {
        "organization_id": org_id,
        "engine": engine,
        "total_count": total,
        "execution_ms": int((time.perf_counter() - started) * 1000),
        "sql": validated,
    }
