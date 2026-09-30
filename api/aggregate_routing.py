"""Answer a report from a canvas's pre-aggregate only when the answer is provably the same.

A pre-aggregate (originba_dbt models/marts/aggregates/, docs/PRE_AGGREGATES_PLAN.md) holds
a canvas grouped by day: the day of its date, a few dimensions, the row count and the sums.
Its cells are proved equal to the canvas by a dbt test before it is published. This decides,
per query, whether that table can answer it; the answer must equal the canvas answer
always, so everything not provably equal goes to the canvas. A query routes only when ALL
of these hold:

  1. the catalog declares an aggregate for the canvas;
  2. every dimension and filter field -- row-security IN filters included -- is one of the
     aggregate's dimensions (the date is never a plain dimension: the aggregate holds its
     day, the canvas its full timestamp);
  3. the date is filtered only by `between` or `gte` on plain dates, which on whole days
     mean the same thing on both (the builder's window is col >= start AND col < end + 1).
     Never lte/eq/neq/in: on the canvas `<= d` means midnight of d;
  4. time buckets are month/quarter/year of the aggregate's date, exact from the day;
  5. every measure is on the allowlist: count(*) becomes the sum of the stored counts and a
     declared sum the sum of the stored sums. Anything else -- count_distinct, count(field),
     avg, min, max, a filter operator or key this module does not know -- is refused, so a
     new query-builder feature never routes by default;
  6. the aggregate's "Canvas Build" is single-valued and equals the canvas's live identity
     (Postgres oid:relfilenode, Oracle all_objects.object_id). A canvas rebuilt without its
     aggregate -- a partial or killed run, a failed parity test -- is read directly. Any
     error reading it is a refusal, and so is a routed statement that fails to run
     (api/snapshot_explorer.py reads the canvas instead).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from api.query_builder import build_query
from api.snapshot_catalog import snapshot_backend

DIMENSION_OPS = {"eq", "neq", "in", "between", "gte", "lte"}
BUCKET_GRAINS = {"month", "quarter", "year"}
FILTER_KEYS = {"field", "op", "value"}
MEASURE_KEYS = {"field", "agg"}
BUCKET_KEYS = {"field", "grain"}
# a routed count(*): marks the sum of stored counts that must read 0, not NULL, over no cells
ZERO_IF_EMPTY = "zero_if_empty"
_PLAIN_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_COLUMN = re.compile(r"[A-Za-z][A-Za-z0-9 _]*")


def _plain_date(value: Any) -> bool:
    if not isinstance(value, str) or not _PLAIN_DATE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _date_filter_ok(op: str, value: Any) -> bool:
    if op == "gte":
        return _plain_date(value)
    return (op == "between" and isinstance(value, (list, tuple)) and len(value) == 2
            and all(_plain_date(v) for v in value))


def _rewrite(agg: dict[str, Any], filters: list[dict], dimensions: list[str],
             measures: list[dict], time_dimensions: list[dict]) -> list[dict] | None:
    """Rules 2-5: the measures to ask the aggregate for, or None."""
    day, dims = agg["date"], set(agg["dimensions"])
    if any(d not in dims for d in dimensions):
        return None
    for f in filters:
        op = str(f.get("op", "eq")).lower()
        if set(f) - FILTER_KEYS:
            return None
        if f.get("field") == day:
            if not _date_filter_ok(op, f.get("value")):
                return None
        elif f.get("field") not in dims or op not in DIMENSION_OPS:
            return None
    for t in time_dimensions:
        if set(t) - BUCKET_KEYS or t.get("field") != day or str(t.get("grain", "month")).lower() not in BUCKET_GRAINS:
            return None
    out = []
    for m in measures:
        field, fn = str(m.get("field", "*")), str(m.get("agg", "count")).lower()
        if set(m) - MEASURE_KEYS:
            return None
        if field == "*" and fn == "count":
            out.append({"field": agg["count"], "agg": "sum", ZERO_IF_EMPTY: True})
        elif fn == "sum" and agg["measures"].get(field) == "sum":
            out.append({"field": field, "agg": "sum"})
        else:
            return None
    return out


def _builds(snapshot: dict[str, Any], agg: dict[str, Any], org_id: str | None) -> list[tuple]:
    """(the aggregate's Canvas Build, the canvas's live identity) per distinct build, at most two.
    One statement, so both are read from the same moment."""
    backend, dialect, schema = snapshot_backend(snapshot, org_id)
    canvas, table, column = snapshot["table_name"], agg["table"], agg["build_column"]
    if not all(_NAME.fullmatch(n) for n in (schema, canvas, table)) or not _COLUMN.fullmatch(column):
        raise ValueError("unsafe identifier in the aggregate declaration")
    if dialect == "postgres":
        live = ("SELECT c.oid::text || ':' || c.relfilenode::text FROM pg_catalog.pg_class c "
                "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = %(schema)s AND c.relname = %(canvas)s")
        source = f'{schema}."{table}"'
        binds = {"schema": schema, "canvas": canvas}
    else:
        live = ("SELECT TO_CHAR(object_id) FROM all_objects "
                "WHERE owner = :owner AND object_name = :canvas AND object_type = 'TABLE'")
        source = f"{schema}.{table.upper()}"
        binds = {"owner": schema.upper(), "canvas": canvas.upper()}
    sql = (f'SELECT a."{column}", ({live}) FROM (SELECT DISTINCT "{column}" FROM {source}) a '
           "FETCH FIRST 2 ROWS ONLY")
    if backend == "postgres":
        from api.warehouse_db import execute_query
    else:
        from api.demo_db import execute_query
    _, rows = execute_query(sql, binds, organization_id=org_id, max_rows=2)
    return [tuple(r) for r in rows]


def plan(snapshot: dict[str, Any], body_filters: list[dict], dimensions: list[str],
         measures: list[dict], time_dimensions: list[dict],
         org_id: str | None) -> tuple[str, list[dict]] | None:
    """(the aggregate's table, the measures to ask it for) when the aggregate's answer is the
    canvas's, else None. Rule 6 reads the database, so it runs last and only when 1-5 hold."""
    agg = snapshot.get("aggregate")
    if not agg:
        return None
    rewritten = _rewrite(agg, body_filters, dimensions, measures, time_dimensions)
    if rewritten is None:
        return None
    try:
        rows = _builds(snapshot, agg, org_id)
    except Exception:  # noqa: BLE001 -- an unreadable identity is not a proven one
        return None
    if len(rows) != 1 or rows[0][0] is None or rows[0][0] != rows[0][1]:
        return None
    return agg["table"], rewritten


def routed_query(org_id: str | None, snapshot: dict[str, Any], *, dimensions: list[str],
                 measures: list[dict], filters: list[dict], time_dimensions: list[dict],
                 limit: int, dialect: str, schema: str) -> tuple[str, dict, str] | None:
    """(statement, binds, table) against the aggregate, or None to read the canvas."""
    try:
        routed = plan(snapshot, filters, dimensions, measures, time_dimensions, org_id)
        if routed is None:
            return None
        table, rewritten = routed
        agg = snapshot["aggregate"]
        sums = {agg["count"], *agg["measures"]}
        sql, binds = build_query(table_name=table, allowed_fields={agg["date"], *agg["dimensions"], *sums},
                                 trusted_measures=sums, dimensions=dimensions, measures=rewritten,
                                 filters=filters, limit=limit, time_dimensions=time_dimensions,
                                 dialect=dialect, schema=schema)
        for idx, m in enumerate(rewritten):
            if m.get(ZERO_IF_EMPTY):
                # COUNT(*) over no rows is 0 on the canvas; a SUM over no cells is NULL
                stored = f'SUM("{m["field"]}") AS "m{idx}"'
                if sql.count(stored) != 1:
                    return None
                sql = sql.replace(stored, f'COALESCE(SUM("{m["field"]}"), 0) AS "m{idx}"')
        return sql, binds, table
    except Exception:  # noqa: BLE001 -- anything unexpected reads the canvas
        return None
