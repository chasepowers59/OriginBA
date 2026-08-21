"""Shared KPI query runner with optional prior-period comparison."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from api.demo_db import execute_query
from api.snapshot_catalog import is_warehouse
from api.query_builder import QueryValidationError, build_query
from api.snapshot_catalog import allowed_fields, get_snapshot


def date_windows(days: int) -> tuple[tuple[str, str], tuple[str, str]]:
    """Return (current_start, current_end), (prior_start, prior_end) as ISO date strings."""
    capped = max(1, min(days, 365))
    current_end = date.today()
    current_start = current_end - timedelta(days=capped)
    prior_end = current_start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=capped)
    return (
        (current_start.isoformat(), current_end.isoformat()),
        (prior_start.isoformat(), prior_end.isoformat()),
    )


def run_kpi_query(
    snapshot_id: str,
    query_spec: dict[str, Any],
    date_field: str,
    date_start: str,
    date_end: str,
    extra_filters: list[dict[str, Any]] | None = None,
    *,
    organization_id: str,
) -> tuple[list[str], list[list[Any]]]:
    snapshot = get_snapshot(snapshot_id)
    filters = list(query_spec.get("filters") or [])
    if extra_filters:
        filters.extend(extra_filters)
    filters.append({"field": date_field, "op": "between", "value": [date_start, date_end]})
    sql, binds = build_query(
        table_name=snapshot["table_name"],
        allowed_fields=allowed_fields(snapshot),
        trusted_measures=(set(snapshot.get("trusted_measures", []))
                          if is_warehouse(snapshot)
                          else {m.upper() for m in snapshot.get("trusted_measures", [])}),
        required_date_field=snapshot.get("required_date_field"),
        dimensions=query_spec.get("dimensions") or [],
        measures=query_spec.get("measures") or [{"field": "*", "agg": "count"}],
        filters=filters,
        limit=int(query_spec.get("limit") or 500),
        dialect="postgres" if is_warehouse(snapshot) else "oracle",
        schema=snapshot.get("schema", "CISADM"),
    )
    row_cap = int(query_spec.get("limit") or 500)
    if is_warehouse(snapshot):
        from api.warehouse_db import execute_query as run_warehouse
        return run_warehouse(sql, binds, organization_id=organization_id, max_rows=row_cap)
    return execute_query(sql, binds, organization_id=organization_id, max_rows=row_cap)


def scalar_measure_value(columns: list[str], rows: list[list[Any]]) -> float | None:
    if not columns or not rows:
        return None
    raw = rows[0][-1]
    return float(raw) if raw is not None else None


def trend_from_rows(columns: list[str], rows: list[list[Any]]) -> list[dict[str, Any]]:
    if len(columns) < 2:
        return []
    return [
        {
            "label": str(row[0]) if row[0] is not None else "Unknown",
            "value": float(row[-1] or 0),
        }
        for row in rows
    ]


def pct_change(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None or prior == 0:
        return None
    return ((current - prior) / abs(prior)) * 100.0


def execute_kpi_definition(
    kpi: dict[str, Any],
    *,
    days: int,
    compare: bool = False,
    extra_filters: list[dict[str, Any]] | None = None,
    organization_id: str,
) -> dict[str, Any]:
    snapshot_id = kpi["snapshot_id"]
    base = {
        "id": kpi["id"],
        "label": kpi["label"],
        "subtitle": kpi.get("subtitle", ""),
        "snapshot_id": snapshot_id,
        "format": kpi.get("format", "number"),
        "workstream": kpi.get("workstream"),
        "explore_report_id": kpi.get("explore_report_id"),
    }
    try:
        snapshot = get_snapshot(snapshot_id)
        date_field = snapshot.get("required_date_field")
        if not date_field:
            raise ValueError("Snapshot has no required date field")

        (cur_start, cur_end), (pri_start, pri_end) = date_windows(days)

        value_cols, value_rows = run_kpi_query(
            snapshot_id, kpi["value"], date_field, cur_start, cur_end, extra_filters, organization_id=organization_id
        )
        value = scalar_measure_value(value_cols, value_rows)

        prior_value: float | None = None
        if compare:
            prior_cols, prior_rows = run_kpi_query(
                snapshot_id,
                kpi["value"],
                date_field,
                pri_start,
                pri_end,
                extra_filters,
                organization_id=organization_id,
            )
            prior_value = scalar_measure_value(prior_cols, prior_rows)

        trend_cols, trend_rows = run_kpi_query(
            snapshot_id,
            kpi.get("trend", kpi["value"]),
            date_field,
            cur_start,
            cur_end,
            extra_filters,
            organization_id=organization_id,
        )
        trend = trend_from_rows(trend_cols, trend_rows)
        trend_spec = kpi.get("trend") or kpi["value"]
        trend_dims = trend_spec.get("dimensions") or []
        trend_dimension = trend_dims[0] if trend_dims else None

        change_pct = pct_change(value, prior_value) if compare else None
        return {
            **base,
            "value": value,
            "prior_value": prior_value if compare else None,
            "change_pct": change_pct,
            "trend": trend,
            "trend_dimension": trend_dimension,
            "error": None,
        }
    except (QueryValidationError, ValueError) as exc:
        return {**base, "value": None, "prior_value": None, "change_pct": None, "trend": [], "error": str(exc)}
    except Exception as exc:
        return {
            **base,
            "value": None,
            "prior_value": None,
            "change_pct": None,
            "trend": [],
            "error": f"Query failed: {exc}",
        }
