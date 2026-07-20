"""Database workspace API — ad-hoc read-only SQL with paginated results."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.auth.dependencies import AuthContext, require_permission
from api.demo_db import demo_configured, execute_query
from api.org_db import require_org_for_data
from api.sql_workspace_validator import (
    SqlWorkspaceValidationError,
    validate_workspace_sql,
    wrap_count_sql,
    wrap_paginated_sql,
)


router = APIRouter(prefix="/database", tags=["database"])

MAX_PAGE_SIZE = 500
DEFAULT_PAGE_SIZE = 50
MAX_TOTAL_ROWS = 50_000

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


def _require_db(org_id: str) -> None:
    if not demo_configured(org_id):
        raise HTTPException(
            status_code=503,
            detail="Database is not configured for this organization.",
        )


@router.get("/tables")
def list_tables(
    ctx: AuthContext = Depends(require_permission("database:sql")),
    schema: str = Query(default="CISADM", min_length=1, max_length=128),
    search: str = Query(default="", max_length=128),
    snapshots_only: bool = Query(default=True),
    include_stats: bool = Query(default=False),
) -> dict[str, Any]:
    org_id = require_org_for_data(ctx)
    _require_db(org_id)

    schema_upper = schema.strip().upper()
    needle = search.strip().upper()

    if snapshots_only and not needle and not include_stats:
        tables = [
            {"table_name": name, "num_rows": None, "last_analyzed": None}
            for name in ACTIVE_SNAPSHOT_TABLES
        ]
        return {
            "organization_id": org_id,
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
        columns, rows = execute_query(sql, binds, organization_id=org_id, max_rows=200)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to list tables: {exc}") from exc

    items = []
    for row in rows:
        rec = {columns[i]: _serialize_cell(row[i]) for i in range(len(columns))}
        items.append(rec)

    return {
        "organization_id": org_id,
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
    _require_db(org_id)

    if body.offset >= MAX_TOTAL_ROWS:
        raise HTTPException(
            status_code=400,
            detail=f"Offset cannot exceed {MAX_TOTAL_ROWS:,} rows.",
        )

    try:
        validated = validate_workspace_sql(body.sql)
    except SqlWorkspaceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    page_size = max(1, min(body.page_size, MAX_PAGE_SIZE))
    if body.offset + page_size > MAX_TOTAL_ROWS:
        page_size = max(1, MAX_TOTAL_ROWS - body.offset)

    paged_sql = wrap_paginated_sql(validated, offset=body.offset, limit=page_size, probe_extra=1)
    started = time.perf_counter()
    try:
        columns, raw_rows = execute_query(
            paged_sql,
            organization_id=org_id,
            max_rows=page_size + 1,
        )
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
            _, count_rows = execute_query(count_sql, organization_id=org_id, max_rows=1)
            if count_rows:
                total_count = int(count_rows[0][0])
        except Exception:
            total_count = None

    fetched_total = body.offset + len(page_rows)

    return {
        "organization_id": org_id,
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
    _require_db(org_id)

    try:
        validated = validate_workspace_sql(body.sql)
    except SqlWorkspaceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    started = time.perf_counter()
    try:
        count_sql_text = wrap_count_sql(validated)
        _, count_rows = execute_query(count_sql_text, organization_id=org_id, max_rows=1)
        total = int(count_rows[0][0]) if count_rows else 0
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Count failed: {exc}") from exc

    return {
        "organization_id": org_id,
        "total_count": total,
        "execution_ms": int((time.perf_counter() - started) * 1000),
        "sql": validated,
    }
