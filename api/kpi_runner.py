"""Shared KPI query runner with optional prior-period comparison."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from api.demo_db import execute_query
from api.snapshot_catalog import is_warehouse
from api.query_builder import QueryValidationError, build_query
from api.snapshot_catalog import allowed_fields, get_snapshot


COMPARE_MODES = ("prior_period", "mom", "yoy")


def date_windows(
    days: int, compare_mode: str = "prior_period"
) -> tuple[tuple[str, str], tuple[str, str], str]:
    """(current_start, current_end), (prior_start, prior_end), compare_label.

    prior_period -- rolling: last N days vs the N days before them.
    mom -- calendar: month-to-date vs the same day-span of the previous month
           (a July bill compared to June is weather; the label says which month).
    yoy -- seasonal: the same window one year earlier (July vs LAST July is signal).
    """
    capped = max(1, min(days, 365))
    today = date.today()

    if compare_mode == "mom":
        cur_start = today.replace(day=1)
        prev_last = cur_start - timedelta(days=1)
        prior_start = prev_last.replace(day=1)
        # same day-span, clamped to the previous month's length
        prior_end = prior_start + timedelta(
            days=min((today - cur_start).days, (prev_last - prior_start).days))
        return ((cur_start.isoformat(), today.isoformat()),
                (prior_start.isoformat(), prior_end.isoformat()),
                f"vs {prior_start.strftime('%B')}")

    cur_start = today - timedelta(days=capped)
    if compare_mode == "yoy":
        try:
            prior_start = cur_start.replace(year=cur_start.year - 1)
            prior_end = today.replace(year=today.year - 1)
        except ValueError:  # Feb 29
            prior_start = cur_start - timedelta(days=365)
            prior_end = today - timedelta(days=365)
        return ((cur_start.isoformat(), today.isoformat()),
                (prior_start.isoformat(), prior_end.isoformat()),
                f"vs {today.year - 1}")

    prior_end = cur_start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=capped)
    return ((cur_start.isoformat(), today.isoformat()),
            (prior_start.isoformat(), prior_end.isoformat()),
            f"vs prior {capped}d")


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
    # organization_id is already a parameter here; the catalog must follow it.
    snapshot = get_snapshot(snapshot_id, organization_id)
    filters = list(query_spec.get("filters") or [])
    if extra_filters:
        filters.extend(extra_filters)
    # STOCK metrics (a balance, a population) have no date window -- date_field is
    # None for a windowless KPI and no range filter is added.
    if date_field:
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
    compare_mode: str = "prior_period",
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
        snapshot = get_snapshot(snapshot_id, organization_id)
        # KPI may name its own date field (dbt canvases carry default_date_field, not
        # required_date_field); a WINDOWLESS KPI (stock metric: total customers, AR
        # balance) skips the window and the period comparison entirely.
        windowless = bool(kpi.get("windowless"))
        date_field = None if windowless else (
            kpi.get("date_field")
            or snapshot.get("required_date_field")
            or snapshot.get("default_date_field"))
        if not date_field and not windowless:
            raise ValueError("Snapshot has no date field and KPI is not windowless")

        (cur_start, cur_end), (pri_start, pri_end), compare_label = date_windows(days, compare_mode)

        value_cols, value_rows = run_kpi_query(
            snapshot_id, kpi["value"], date_field, cur_start, cur_end, extra_filters, organization_id=organization_id
        )
        value = scalar_measure_value(value_cols, value_rows)

        prior_value: float | None = None
        if compare and not windowless:
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
            "compare_label": compare_label if compare and not windowless else None,
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
