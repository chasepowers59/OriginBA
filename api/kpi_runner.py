"""Shared KPI query runner with optional prior-period comparison."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from api.demo_db import execute_query
from api.query_builder import QueryValidationError, build_query
from api.reporting_dates import window_date_field
from api.snapshot_catalog import allowed_fields, get_snapshot, snapshot_backend


COMPARE_MODES = ("prior_period", "mom", "yoy")


# ── Lenses ────────────────────────────────────────────────────────────────────
# A card can offer several readings of the same question. "Total customers" counted
# EVERY account while a reader hears "customers we bill" -- both are legitimate, so the
# card names which one it is showing and lets the reader switch. The lens carries its
# own subtitle, because the subtitle is what makes the number honest.
#
# Filters stay SERVER-SIDE: the client names a lens by id and never sends a predicate,
# so a lens can never widen what an org is allowed to read.


def select_lens(kpi: dict[str, Any], lens_id: str | None) -> dict[str, Any] | None:
    """The chosen lens, or the first as default. An unknown id falls back rather than
    erroring -- a stale bookmark must not blank the dashboard."""
    lenses = kpi.get("lenses") or []
    if not lenses:
        return None
    for lens in lenses:
        if lens.get("id") == lens_id:
            return lens
    return lenses[0]


def lens_filters(kpi: dict[str, Any], lens_id: str | None) -> list[dict[str, Any]]:
    lens = select_lens(kpi, lens_id)
    return [dict(f) for f in (lens or {}).get("filters", [])]


def public_lenses(kpi: dict[str, Any]) -> list[dict[str, Any]]:
    """What the client is told: names only, never the predicates behind them."""
    return [
        {"id": lens["id"], "label": lens["label"], "subtitle": lens.get("subtitle", "")}
        for lens in kpi.get("lenses") or []
    ]


def _lens_id(value: str) -> str:
    """A URL-safe id for a discovered value. Collisions are broken by the caller."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return slug or "value"


def _discover_lens_values(
    kpi: dict[str, Any], spec: dict[str, Any], organization_id: str
) -> list[str]:
    """The tenant's own status values for this field, most common first.

    Runs through the SAME governed builder as everything else, so the field is
    validated against the catalog and the org's scope applies.
    """
    columns, rows = run_kpi_query(
        kpi["snapshot_id"],
        {
            "dimensions": [spec["field"]],
            "measures": [{"field": "*", "agg": "count"}],
            "filters": [],
            "limit": int(spec.get("limit", 8)),
        },
        None,
        "",
        "",
        organization_id=organization_id,
    )
    idx = columns.index(spec["field"]) if spec["field"] in columns else 0
    return [str(r[idx]) for r in rows if r[idx] is not None and str(r[idx]) != ""]


def resolve_lenses(kpi: dict[str, Any], *, organization_id: str) -> dict[str, Any]:
    """Give a KPI concrete lenses, discovering them when the vocabulary is the client's.

    A status held in a base-product `_FLG` lookup (bill, payment, SA) is named in the
    spec, because the set is fixed and can be grouped into something a reader
    recognises. A business-object lifecycle state is not: a client extends it, so the
    lenses are read from that tenant's data instead of guessed. Demo 25.4 alone carries
    seven activity statuses, and a hardcoded list would be wrong at the next client.

    Never mutates the shared spec, and a discovery failure costs the card its switcher,
    never its number.
    """
    spec = kpi.get("lens_field")
    if not spec:
        return kpi
    try:
        values = _discover_lens_values(kpi, spec, organization_id)
    except Exception:  # noqa: BLE001 - a switcher is not worth failing a KPI over
        return {**kpi, "lenses": []}
    if not values:
        return {**kpi, "lenses": []}

    noun = spec.get("noun", "Status")
    lenses = [{
        "id": "all",
        "label": "All",
        "subtitle": spec.get("all_subtitle", "Every status"),
        "filters": [],
    }]
    seen = {"all"}
    for value in values:
        base = _lens_id(value)
        lens_id, n = base, 2
        while lens_id in seen:
            lens_id, n = f"{base}-{n}", n + 1
        seen.add(lens_id)
        lenses.append({
            "id": lens_id,
            "label": str(value),
            "subtitle": f"{noun} {value}",
            "filters": [{"field": spec["field"], "op": "eq", "value": value}],
        })
    return {**kpi, "lenses": lenses}


def applicable_filters(
    filters: list[dict[str, Any]] | None, fields: set[str]
) -> list[dict[str, Any]]:
    """Keep only the filters this canvas has a column for.

    A cross-filter is raised on one card and applied to all of them, but "Customer
    Class" exists on the account canvas and not on the payment or aged-balance ones.
    Erroring those out emptied the whole grid; every BI tool instead leaves an unrelated
    visual alone. Matched case-insensitively so either dialect's spelling resolves.
    """
    if not filters:
        return []
    known = {f.casefold() for f in fields}
    return [f for f in filters if str(f.get("field", "")).casefold() in known]


def _latest_date(snapshot_id: str, date_field: str, organization_id: str) -> str | None:
    """The newest value the canvas holds for this date, ignoring any window."""
    _, rows = run_kpi_query(
        snapshot_id,
        {"dimensions": [], "measures": [{"field": date_field, "agg": "max"}],
         "filters": [], "limit": 1},
        None,
        "",
        "",
        organization_id=organization_id,
    )
    value = rows[0][0] if rows and rows[0] else None
    return str(value)[:10] if value else None


def empty_window_note(
    *, value: Any, windowless: bool, snapshot_id: str,
    date_field: str | None, organization_id: str,
) -> dict[str, str] | None:
    """Distinguish "none happened" from "none in the window you chose".

    A bare 0 sent three separate investigations down the wrong road -- the number was
    right every time, and useless, because nothing on the card said whether the window
    had missed the data. When a WINDOWED metric comes back empty, the card is told the
    newest date its canvas actually holds so it can say so.

    Only pays for the extra query when the answer is already empty; a canvas with no
    rows at all gets no note, because then the zero is the whole truth.
    """
    if windowless or not date_field or value not in (None, 0):
        return None
    try:
        latest = _latest_date(snapshot_id, date_field, organization_id)
    except Exception:  # noqa: BLE001 - an explanation is not worth failing a KPI over
        return None
    return {"latest": latest} if latest else None


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
    # (backend, dialect, schema) resolve from the ORG as well as the snapshot: the
    # same dbt canvas runs in Postgres for shape-A tenants and in the client's own
    # Oracle instance (ORIGINBA_REPORTING) for in-database tenants.
    backend, dialect, schema = snapshot_backend(snapshot, organization_id)
    trusted = set(snapshot.get("trusted_measures", []))
    sql, binds = build_query(
        table_name=snapshot["table_name"],
        allowed_fields=allowed_fields(snapshot),
        trusted_measures=trusted,
        dimensions=query_spec.get("dimensions") or [],
        measures=query_spec.get("measures") or [{"field": "*", "agg": "count"}],
        filters=filters,
        limit=int(query_spec.get("limit") or 500),
        dialect=dialect,
        schema=schema,
    )
    row_cap = int(query_spec.get("limit") or 500)
    if backend == "postgres":
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
    lens_id: str | None = None,
    organization_id: str,
) -> dict[str, Any]:
    snapshot_id = kpi["snapshot_id"]
    # The lens narrows BOTH the headline and its trend, so the bars always break down
    # the number above them. Its subtitle replaces the card's, because that line is
    # what tells the reader which population they are looking at.
    kpi = resolve_lenses(kpi, organization_id=organization_id)
    lens = select_lens(kpi, lens_id)
    extra_filters = list(extra_filters or []) + lens_filters(kpi, lens_id)
    base = {
        "id": kpi["id"],
        "label": kpi["label"],
        "subtitle": (lens or {}).get("subtitle") or kpi.get("subtitle", ""),
        "lenses": public_lenses(kpi),
        "lens": (lens or {}).get("id"),
        "snapshot_id": snapshot_id,
        "format": kpi.get("format", "number"),
        "workstream": kpi.get("workstream"),
        "explore_report_id": kpi.get("explore_report_id"),
    }
    try:
        snapshot = get_snapshot(snapshot_id, organization_id)
        # A cross-filter is raised on one card and sent to all of them; the ones whose
        # canvas has no such column are left unfiltered rather than failed.
        extra_filters = applicable_filters(extra_filters, allowed_fields(snapshot))
        # A KPI may name its own date field; a WINDOWLESS KPI (stock metric: total
        # customers, AR balance) skips the window and the period comparison entirely.
        windowless = bool(kpi.get("windowless"))
        # The KPI's own override first, then the ONE shared rule. That
        # required-or-default chain was written out here as a fourth copy, and the
        # copies are what caused the explorer to window 19 canvases and none of the 38.
        date_field = None if windowless else (
            kpi.get("date_field") or window_date_field(snapshot))
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
            "empty_window": empty_window_note(
                value=value, windowless=windowless, snapshot_id=snapshot_id,
                date_field=date_field, organization_id=organization_id),
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
