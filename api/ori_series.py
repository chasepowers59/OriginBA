"""Monthly history of the home cards, for Ori's unusual months and projections.

Each windowed home card's OWN number (its value query, filters and default lens) by calendar
month, complete months only, ending at the organization's reporting date: a partial month
would read as a collapse. Built for every card of the organization, filtered by the reader's
workstreams at the route, and kept until the warehouse is rebuilt (its build stamp).
"""
from __future__ import annotations

import logging
from calendar import monthrange
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Any

from api.data_version import data_version
from api.kpi_runner import lens_filters, resolve_lenses, run_kpi_query
from api.reporting_dates import reporting_today, window_date_field
from api.summary_cache import cached

log = logging.getLogger("originba.api")

HISTORY_MONTHS = 36


def complete_months(today: date, count: int) -> list[str]:
    """The last `count` complete months as YYYY-MM, oldest first."""
    y, m = today.year, today.month
    if today.day != monthrange(y, m)[1]:
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    out = []
    for _ in range(count):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return out[::-1]


def series_from_rows(months: list[str], rows: list[list[Any]]) -> list[dict[str, Any]]:
    """One point per month, a month without rows is zero, and nothing before the first month with data."""
    by_month = {str(r[0])[:7]: float(r[-1] or 0) for r in rows if r and r[0] is not None}
    first = next((i for i, m in enumerate(months) if m in by_month), None)
    return [] if first is None else [{"month": m, "value": by_month.get(m, 0.0)} for m in months[first:]]


def monthly_history(kpi: dict[str, Any], organization_id: str, months: int = HISTORY_MONTHS) -> list[dict[str, Any]]:
    kpi = resolve_lenses(kpi, organization_id=organization_id)
    date_field = kpi.get("date_field")
    if not date_field:
        from api.snapshot_catalog import get_snapshot
        date_field = window_date_field(get_snapshot(kpi["snapshot_id"], organization_id))
    span = complete_months(reporting_today(organization_id), months)
    last_y, last_m = map(int, span[-1].split("-"))
    end = f"{span[-1]}-{monthrange(last_y, last_m)[1]:02d}"
    _, rows = run_kpi_query(kpi["snapshot_id"], {**kpi["value"], "limit": months + 1}, date_field,
                            f"{span[0]}-01", end, lens_filters(kpi, None), organization_id=organization_id,
                            time_dimensions=[{"field": date_field, "grain": "month"}])
    return series_from_rows(span, rows)


def _build(organization_id: str) -> tuple[dict[str, list], dict[str, dict], bool]:
    from api.executive_dashboard import EXECUTIVE_KPIS, available_kpis
    kpis, _ = available_kpis([k for k in EXECUTIVE_KPIS if not k.get("windowless")], organization_id)

    def one(kpi: dict[str, Any]) -> list[dict[str, Any]] | None:
        try:
            return monthly_history(kpi, organization_id)
        except Exception as exc:  # noqa: BLE001 -- one card failing leaves the others
            log.warning("ori history %s %s failed: %s", organization_id, kpi["id"], exc)
            return None

    with ThreadPoolExecutor(max_workers=max(1, min(8, len(kpis)))) as pool:
        histories = list(pool.map(one, kpis))
    history = {k["id"]: h for k, h in zip(kpis, histories) if h}
    meta = {k["id"]: {"label": k["label"], "format": k.get("format", "number"), "workstream": k.get("workstream")}
            for k in kpis if k["id"] in history}
    return history, meta, None in histories


def cached_history(organization_id: str) -> tuple[dict[str, list], dict[str, dict]]:
    # a history missing a card that failed is served but not kept: the next request retries it
    history, meta, _ = cached(("ori history", organization_id), lambda: _build(organization_id),
                              keep=lambda built: bool(built[0]) and not built[2], version=data_version(organization_id))
    return history, meta
