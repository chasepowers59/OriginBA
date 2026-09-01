"""
Governed SQL builder for snapshot explorer queries.

Only allowlisted snapshot columns and aggregations are permitted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


IDENT_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
# A dbt canvas column is quoted Title Case and may hold spaces, brackets, a slash or a
# percent -- "Billed Usage less Read Quantity", "Duration (min)", "% of Arrears Collected".
# The ALLOW-LIST is what makes a query safe: nothing reaches the SQL that is not already
# a declared field of the snapshot. This pattern is the second line, rejecting anything
# that could not be a column name at all, and a double quote most of all.
WAREHOUSE_IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 _()/%.,+-]*$")
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


# Dialects that carry the dbt canvases' quoted Title-Case identifiers as written.
# oracle_dbt (2026-08-28) is the in-database warehouse: same identifiers as the
# Postgres form (double-quoting is identical SQL in Oracle), Oracle everything else.
_TITLECASE_DIALECTS = ("postgres", "oracle_dbt")


def _validate_ident(name: str, allowed: set[str], kind: str, dialect: str = "oracle") -> str:
    if dialect in _TITLECASE_DIALECTS:
        if name == "*":
            return name
        if name not in allowed or not WAREHOUSE_IDENT_RE.match(name) or '"' in name:
            raise QueryValidationError(f"Invalid {kind}: {name}")
        return name
    upper = name.upper()
    if upper == "*":
        return upper
    if upper not in allowed or not IDENT_RE.match(upper):
        raise QueryValidationError(f"Invalid {kind}: {name}")
    return upper


def _quote(name: str, dialect: str) -> str:
    """Render a validated identifier for the dialect."""
    return f'"{name}"' if dialect in _TITLECASE_DIALECTS else name


def _bind(name: str, dialect: str) -> str:
    """psycopg takes %(name)s; oracledb takes :name."""
    return f"%({name})s" if dialect == "postgres" else f":{name}"


def _time_bucket_expr(field: str, grain: str, dialect: str = "oracle") -> str:
    grain = grain.lower()
    if grain not in ALLOWED_TIME_GRAINS:
        raise QueryValidationError(f"Invalid time grain: {grain}")
    if dialect == "postgres":
        return f"date_trunc('{grain}', {field})"
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
    dialect: str = "oracle",
    schema: str = "CISADM",
) -> tuple[str, dict[str, Any]]:
    if limit < 1 or limit > 5000:
        raise QueryValidationError("limit must be between 1 and 5000")
    if not measures:
        raise QueryValidationError("At least one measure is required")

    pg = dialect == "postgres"
    titlecase = dialect in _TITLECASE_DIALECTS
    dims = [_validate_ident(d, allowed_fields, "dimension", dialect) for d in dimensions]
    measure_specs: list[MeasureSpec] = []
    for idx, measure in enumerate(measures):
        raw_field = str(measure.get("field", "*"))
        field = raw_field if titlecase else raw_field.upper()
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
        field = _validate_ident(str(raw.get("field", "")), allowed_fields, "filter field", dialect)
        op = str(raw.get("op", "eq")).lower()
        if op not in ALLOWED_OPS:
            raise QueryValidationError(f"Invalid filter op: {op}")
        value = raw.get("value")
        if op == "between":
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise QueryValidationError("between filter requires [start, end]")
            required_cmp = required_date_field or ""
            if field == (required_cmp if titlecase else required_cmp.upper()):
                has_date_window = True
        filter_specs.append(FilterSpec(field=field, op=op, value=value))

    if required_date_field:
        req = required_date_field if titlecase else required_date_field.upper()
        if req not in allowed_fields:
            raise QueryValidationError(f"Required date field missing from snapshot: {req}")
        if not has_date_window:
            raise QueryValidationError(
                f"A date filter on {req} is required (use op=between with start and end dates)"
            )

    table = table_name if pg else table_name.upper()
    # A table name is interpolated (never bound), so it is validated strictly:
    # word characters only for anything that lands in Oracle UNQUOTED.
    ident_ok = WAREHOUSE_IDENT_RE if pg else IDENT_RE
    if not ident_ok.match(table) or '"' in table:
        raise QueryValidationError(f"Invalid table name: {table_name}")

    select_parts: list[str] = []
    group_parts: list[str] = []
    for idx, raw in enumerate(time_dimensions or []):
        field = _validate_ident(str(raw.get("field", "")), allowed_fields, "time dimension field", dialect)
        grain = str(raw.get("grain", "month")).lower()
        expr = _time_bucket_expr(_quote(field, dialect), grain, dialect)
        # Aliases are quoted so they reach the client with the case it asked for. Bare,
        # an identifier folds to lower case in Postgres and UPPER in Oracle, so the same
        # request answered by two engines returned two different column names -- and the
        # client, which looks for "TD0", found neither.
        select_parts.append(f'{expr} AS "TD{idx}"')
        group_parts.append(expr)
    for dim in dims:
        select_parts.append(_quote(dim, dialect))
        group_parts.append(_quote(dim, dialect))
    for spec in measure_specs:
        alias = f'"{spec.alias}"'
        if spec.agg == "count" and spec.field == "*":
            select_parts.append(f"COUNT(*) AS {alias}")
        elif spec.agg == "count":
            select_parts.append(f"COUNT({_quote(spec.field, dialect)}) AS {alias}")
        elif spec.agg == "count_distinct":
            select_parts.append(f"COUNT(DISTINCT {_quote(spec.field, dialect)}) AS {alias}")
        elif spec.agg == "sum":
            select_parts.append(f"SUM({_quote(spec.field, dialect)}) AS {alias}")
        elif spec.agg == "min":
            select_parts.append(f"MIN({_quote(spec.field, dialect)}) AS {alias}")
        elif spec.agg == "max":
            select_parts.append(f"MAX({_quote(spec.field, dialect)}) AS {alias}")

    where_parts: list[str] = []
    for idx, spec in enumerate(filter_specs):
        col = _quote(spec.field, dialect)
        if spec.op == "eq":
            bind = f"b{idx}"
            binds[bind] = spec.value
            where_parts.append(f"{col} = {_bind(bind, dialect)}")
        elif spec.op == "neq":
            bind = f"b{idx}"
            binds[bind] = spec.value
            where_parts.append(f"{col} <> {_bind(bind, dialect)}")
        elif spec.op == "in":
            if not isinstance(spec.value, list) or not spec.value:
                raise QueryValidationError("in filter requires non-empty list")
            placeholders = []
            for j, item in enumerate(spec.value):
                bind = f"b{idx}_{j}"
                binds[bind] = item
                placeholders.append(_bind(bind, dialect))
            where_parts.append(f"{col} IN ({', '.join(placeholders)})")
        elif spec.op == "gte":
            bind = f"b{idx}"
            binds[bind] = spec.value
            where_parts.append(f"{col} >= {_bind(bind, dialect)}")
        elif spec.op == "lte":
            bind = f"b{idx}"
            binds[bind] = spec.value
            where_parts.append(f"{col} <= {_bind(bind, dialect)}")
        elif spec.op == "between":
            bind_start = f"b{idx}_start"
            bind_end = f"b{idx}_end"
            binds[bind_start] = spec.value[0]
            binds[bind_end] = spec.value[1]
            if pg:
                # The end of the window is EXCLUSIVE and one day on, so a timestamp
                # anywhere inside the closing day is still inside the window -- the same
                # semantics the Oracle branch gets from "+ 1".
                where_parts.append(
                    f"{col} >= {_bind(bind_start, dialect)}::date "
                    f"AND {col} < {_bind(bind_end, dialect)}::date + 1"
                )
            else:
                # TO_DATE works for DATE and TIMESTAMP snapshot columns in Oracle.
                where_parts.append(
                    f"{col} >= TO_DATE(:{bind_start}, 'YYYY-MM-DD') "
                    f"AND {col} < TO_DATE(:{bind_end}, 'YYYY-MM-DD') + 1"
                )

    # oracle_dbt: the canvas name arrives lowercase (rpt_financial_txn) and the
    # table was created unquoted, so Oracle case-folds an UNQUOTED reference to
    # match -- quoting the lowercase name here would miss the uppercase object.
    qualified = f'{schema}."{table}"' if pg else f"{schema}.{table}"
    sql = f"SELECT {', '.join(select_parts)} FROM {qualified}"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    if group_parts:
        sql += " GROUP BY " + ", ".join(group_parts)
    # Without this the row limit keeps an ARBITRARY slice: every KPI trend asks for six
    # groups, and the six that survived were whatever the planner produced first. The
    # "Active service agreements" card drew the 13th and 14th largest SA Types and none
    # of the top four, while looking like a breakdown of its own headline number.
    # A time bucket ranks by recency instead -- the newest months are the interesting
    # ones, and the client re-sorts them chronologically to draw.
    # measure_specs is never empty -- a query with no measure is rejected above.
    if time_dimensions:
        sql += ' ORDER BY "TD0" DESC'
    else:
        sql += f' ORDER BY "{measure_specs[0].alias}" DESC'
    # FETCH FIRST is standard SQL and valid in both, so the tail needs no branch.
    sql += f" FETCH FIRST {int(limit)} ROWS ONLY"
    return sql, binds
