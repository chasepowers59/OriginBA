"""
Governed SQL builder for snapshot explorer queries.

Only allowlisted snapshot columns and aggregations are permitted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


IDENT_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
ALLOWED_AGGS = {"count", "count_distinct", "sum", "min", "max"}
ALLOWED_OPS = {"eq", "neq", "in", "between", "gte", "lte"}
ALLOWED_TIME_GRAINS = {"month", "quarter", "year"}


class QueryValidationError(ValueError):
    pass


@dataclass
class MeasureSpec:
    field: str
    agg: str
    alias: str


@dataclass
class FilterSpec:
    field: str
    op: str
    value: Any


def _validate_ident(name: str, allowed: set[str], kind: str) -> str:
    upper = name.upper()
    if upper == "*":
        return upper
    if upper not in allowed or not IDENT_RE.match(upper):
        raise QueryValidationError(f"Invalid {kind}: {name}")
    return upper


def _time_bucket_expr(field: str, grain: str) -> str:
    grain = grain.lower()
    if grain not in ALLOWED_TIME_GRAINS:
        raise QueryValidationError(f"Invalid time grain: {grain}")
    if grain == "month":
        return f"TRUNC({field}, 'MM')"
    if grain == "quarter":
        return f"TRUNC({field}, 'Q')"
    return f"TRUNC({field}, 'YYYY')"


def build_query(
    *,
    table_name: str,
    allowed_fields: set[str],
    trusted_measures: set[str],
    required_date_field: str | None,
    dimensions: list[str],
    measures: list[dict[str, Any]],
    filters: list[dict[str, Any]],
    limit: int,
    time_dimensions: list[dict[str, Any]] | None = None,
) -> tuple[str, dict[str, Any]]:
    if limit < 1 or limit > 5000:
        raise QueryValidationError("limit must be between 1 and 5000")
    if not measures:
        raise QueryValidationError("At least one measure is required")

    dims = [_validate_ident(d, allowed_fields, "dimension") for d in dimensions]
    measure_specs: list[MeasureSpec] = []
    for idx, measure in enumerate(measures):
        field = str(measure.get("field", "*")).upper()
        agg = str(measure.get("agg", "count")).lower()
        if agg not in ALLOWED_AGGS:
            raise QueryValidationError(f"Invalid aggregation: {agg}")
        if field != "*" and field not in allowed_fields:
            raise QueryValidationError(f"Invalid measure field: {field}")
        if agg == "sum" and field != "*" and field not in trusted_measures:
            raise QueryValidationError(f"Sum not allowed on field: {field}")
        if agg == "count_distinct" and field == "*":
            raise QueryValidationError("count_distinct requires a field")
        alias = f"m{idx}"
        measure_specs.append(MeasureSpec(field=field, agg=agg, alias=alias))

    filter_specs: list[FilterSpec] = []
    binds: dict[str, Any] = {}
    has_date_window = False
    for idx, raw in enumerate(filters):
        field = _validate_ident(str(raw.get("field", "")), allowed_fields, "filter field")
        op = str(raw.get("op", "eq")).lower()
        if op not in ALLOWED_OPS:
            raise QueryValidationError(f"Invalid filter op: {op}")
        value = raw.get("value")
        if op == "between":
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise QueryValidationError("between filter requires [start, end]")
            if field == (required_date_field or "").upper():
                has_date_window = True
        filter_specs.append(FilterSpec(field=field, op=op, value=value))

    if required_date_field:
        req = required_date_field.upper()
        if req not in allowed_fields:
            raise QueryValidationError(f"Required date field missing from snapshot: {req}")
        if not has_date_window:
            raise QueryValidationError(
                f"A date filter on {req} is required (use op=between with start and end dates)"
            )

    table = table_name.upper()
    if not IDENT_RE.match(table):
        raise QueryValidationError(f"Invalid table name: {table_name}")

    select_parts: list[str] = []
    group_parts: list[str] = []
    for idx, raw in enumerate(time_dimensions or []):
        field = _validate_ident(str(raw.get("field", "")), allowed_fields, "time dimension field")
        grain = str(raw.get("grain", "month")).lower()
        expr = _time_bucket_expr(field, grain)
        alias = f"TD{idx}"
        select_parts.append(f"{expr} AS {alias}")
        group_parts.append(expr)
    for dim in dims:
        select_parts.append(dim)
        group_parts.append(dim)
    for spec in measure_specs:
        if spec.agg == "count" and spec.field == "*":
            select_parts.append(f"COUNT(*) AS {spec.alias}")
        elif spec.agg == "count":
            select_parts.append(f"COUNT({spec.field}) AS {spec.alias}")
        elif spec.agg == "count_distinct":
            select_parts.append(f"COUNT(DISTINCT {spec.field}) AS {spec.alias}")
        elif spec.agg == "sum":
            select_parts.append(f"SUM({spec.field}) AS {spec.alias}")
        elif spec.agg == "min":
            select_parts.append(f"MIN({spec.field}) AS {spec.alias}")
        elif spec.agg == "max":
            select_parts.append(f"MAX({spec.field}) AS {spec.alias}")

    where_parts: list[str] = []
    for idx, spec in enumerate(filter_specs):
        col = spec.field
        if spec.op == "eq":
            bind = f"b{idx}"
            binds[bind] = spec.value
            where_parts.append(f"{col} = :{bind}")
        elif spec.op == "neq":
            bind = f"b{idx}"
            binds[bind] = spec.value
            where_parts.append(f"{col} <> :{bind}")
        elif spec.op == "in":
            if not isinstance(spec.value, list) or not spec.value:
                raise QueryValidationError("in filter requires non-empty list")
            placeholders = []
            for j, item in enumerate(spec.value):
                bind = f"b{idx}_{j}"
                binds[bind] = item
                placeholders.append(f":{bind}")
            where_parts.append(f"{col} IN ({', '.join(placeholders)})")
        elif spec.op == "gte":
            bind = f"b{idx}"
            binds[bind] = spec.value
            where_parts.append(f"{col} >= :{bind}")
        elif spec.op == "lte":
            bind = f"b{idx}"
            binds[bind] = spec.value
            where_parts.append(f"{col} <= :{bind}")
        elif spec.op == "between":
            bind_start = f"b{idx}_start"
            bind_end = f"b{idx}_end"
            binds[bind_start] = spec.value[0]
            binds[bind_end] = spec.value[1]
            # TO_DATE works for DATE and TIMESTAMP snapshot columns in Oracle.
            where_parts.append(
                f"{col} >= TO_DATE(:{bind_start}, 'YYYY-MM-DD') "
                f"AND {col} < TO_DATE(:{bind_end}, 'YYYY-MM-DD') + 1"
            )

    sql = f"SELECT {', '.join(select_parts)} FROM CISADM.{table}"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    if group_parts:
        sql += " GROUP BY " + ", ".join(group_parts)
    sql += f" FETCH FIRST {int(limit)} ROWS ONLY"
    return sql, binds
