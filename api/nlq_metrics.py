"""Governed everyday metric questions mapped to reporting-canvas queries.

REBOUND onto the dbt canvases 2026-08-26: every metric queries a governed
reporting canvas (rpt_*) through the same routed KPI runner the dashboards use.
Every field name was verified against output/catalog_dbt.json or lifted from a
live-verified dashboard KPI spec before it was written here -- never guess a
canvas column, the allow-list holds queries to the real names.

snapshot_analytics_nlq filters the metric set per org to the canvases that org's
catalog actually carries, so a metric is never offered where it cannot run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable

from api.kpi_runner import run_kpi_query, trend_from_rows
from api.snapshot_catalog import allowed_fields, get_snapshot


@dataclass
class NlqMetric:
    id: str
    label: str
    category: str
    patterns: list[str]
    snapshot_id: str
    default_days: int = 90
    format: str = "number"  # number | currency
    param_keys: list[str] = field(default_factory=lambda: ["days"])
    example: str = ""
    build: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _window(days: int) -> tuple[str, str]:
    capped = max(1, min(int(days), 730))
    end = date.today()
    start = end - timedelta(days=capped)
    return start.isoformat(), end.isoformat()


# Optional question parameters -> conformed canvas columns. Applied only when the
# target canvas actually carries the column (the conformed blocks make that true
# almost everywhere); a param the canvas cannot express is simply not applied.
_PARAM_FIELDS = {
    "customer_class": "Customer Class",
    "payment_type": "Tender Type",
    "uom": "Unit of Measure",
    "bill_cycle": "Bill Cycle",
}


def _extra(params: dict[str, Any], allowed: set[str]) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = []
    for key, field_name in _PARAM_FIELDS.items():
        if params.get(key) and field_name in allowed:
            filters.append({"field": field_name, "op": "eq", "value": params[key]})
    return filters


def _scalar(
    snapshot_id: str,
    query: dict[str, Any],
    params: dict[str, Any],
    *,
    organization_id: str,
    date_field: str | None = None,
    windowless: bool = False,
) -> tuple[float, list[dict[str, Any]]]:
    # The catalog is per-org; resolving without it looks up ids in the wrong
    # catalog and misses (this had NLQ erroring for every tenant).
    snap = get_snapshot(snapshot_id, organization_id)
    field_name = None if windowless else (
        date_field or snap.get("default_date_field"))
    if not field_name and not windowless:
        raise ValueError(f"No date field for {snapshot_id}")
    days = int(params.get("days") or 90)
    start, end = _window(days)
    filters = list(query.get("filters") or [])
    filters.extend(_extra(params, allowed_fields(snap)))
    payload = {**query, "filters": filters}
    cols, rows = run_kpi_query(
        snapshot_id, payload, field_name, start, end, organization_id=organization_id
    )
    value = float(rows[0][-1] or 0) if rows else 0.0
    table = trend_from_rows(cols, rows) if len(cols) >= 2 and rows else []
    return value, table


def _trend(
    snapshot_id: str,
    query: dict[str, Any],
    params: dict[str, Any],
    *,
    organization_id: str,
    date_field: str | None = None,
    windowless: bool = False,
) -> list[dict[str, Any]]:
    snap = get_snapshot(snapshot_id, organization_id)
    field_name = None if windowless else (
        date_field or snap.get("default_date_field"))
    days = int(params.get("days") or 90)
    start, end = _window(days)
    filters = list(query.get("filters") or [])
    filters.extend(_extra(params, allowed_fields(snap)))
    payload = {**query, "filters": filters}
    cols, rows = run_kpi_query(
        snapshot_id, payload, field_name, start, end, organization_id=organization_id
    )
    return trend_from_rows(cols, rows)


def parse_params(question: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    params: dict[str, Any] = dict(overrides or {})
    q = question or ""
    if params.get("days") is None:
        m = re.search(r"last\s+(\d+)\s+days?", q, re.I)
        if m:
            params["days"] = int(m.group(1))
        elif re.search(r"this\s+week", q, re.I):
            params["days"] = 7
        elif re.search(r"ytd|year\s+to\s+date", q, re.I):
            params["days"] = (date.today() - date(date.today().year, 1, 1)).days or 30
    for label, key in (
        (r"residential|commercial|c\s*&\s*i|irrigation", "customer_class"),
    ):
        if params.get(key):
            continue
        m = re.search(label, q, re.I)
        if m:
            params[key] = m.group(0).title().replace("C&I", "Commercial")
    return params


def _fmt(value: float, fmt: str) -> str:
    if fmt == "currency":
        return f"${value:,.2f}"
    return f"{value:,.0f}"


def _pin_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    query = spec.get("query") or {}
    measures = query.get("measures") or []
    dimensions = query.get("dimensions") or []
    kind = spec.get("kind", "scalar")
    measure = measures[0] if measures else {"field": "*", "agg": "count"}
    visual = "kpi" if kind == "scalar" and not dimensions else "chart"
    return {
        "visual": visual,
        "measure_field": measure.get("field"),
        "measure_agg": measure.get("agg"),
        "dimensions": dimensions,
    }


def _source_label(snapshot_id: str) -> str:
    return snapshot_id.removeprefix("rpt_").replace("_", " ").title()


def _result(
    metric: NlqMetric,
    params: dict[str, Any],
    value: float,
    table: list[dict[str, Any]] | None = None,
    *,
    narrative_extra: str = "",
    spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    days = int(params.get("days") or metric.default_days)
    window_txt = "as of now" if (spec or {}).get("windowless") else f"last {days} days"
    narrative = (
        f"{metric.label}: {_fmt(value, metric.format)} "
        f"({window_txt} on {_source_label(metric.snapshot_id)})."
    )
    if narrative_extra:
        narrative += " " + narrative_extra
    if table:
        top = table[:5]
        if top and metric.format == "currency":
            narrative += " Top: " + ", ".join(
                f"{r['label']} ({_fmt(float(r['value']), 'currency')})" for r in top
            )
        elif top:
            narrative += " Top: " + ", ".join(
                f"{r['label']} ({int(r['value']):,})" for r in top
            )
    out: dict[str, Any] = {
        "metric_id": metric.id,
        "metric_label": metric.label,
        "format": metric.format,
        "narrative": narrative,
        "metrics": {"value": value, "period_days": days},
        "resolved_from": metric.snapshot_id,
        "source": "snapshot_analytics",
        "param_schema": metric.param_keys,
        "params_used": {k: params.get(k) for k in metric.param_keys if params.get(k) is not None},
    }
    if spec is not None:
        out["pin"] = _pin_from_spec(spec)
    if table:
        out["table"] = {
            "columns": ["Category", "Value"],
            "rows": table,
        }
    return out


def _run_metric(metric: NlqMetric, params: dict[str, Any], *, organization_id: str) -> dict[str, Any]:
    if not metric.build:
        raise ValueError(f"Metric {metric.id} has no builder")
    spec = metric.build(params)
    kind = spec.get("kind", "scalar")
    kwargs = {
        "organization_id": organization_id,
        "date_field": spec.get("date_field"),
        "windowless": bool(spec.get("windowless")),
    }
    if kind == "trend":
        table = _trend(metric.snapshot_id, spec["query"], params, **kwargs)
        total = sum(float(r["value"]) for r in table)
        return _result(
            metric, params, total, table, narrative_extra=spec.get("note", ""), spec=spec
        )
    value, table = _scalar(metric.snapshot_id, spec["query"], params, **kwargs)
    return _result(
        metric, params, value, table or None, narrative_extra=spec.get("note", ""), spec=spec
    )


def _count(filters: list[dict[str, Any]] | None = None,
           dims: list[str] | None = None) -> dict[str, Any]:
    return {"dimensions": dims or [], "measures": [{"field": "*", "agg": "count"}],
            "filters": filters or []}


def _sum(field_name: str, filters: list[dict[str, Any]] | None = None,
         dims: list[str] | None = None) -> dict[str, Any]:
    return {"dimensions": dims or [], "measures": [{"field": field_name, "agg": "sum"}],
            "filters": filters or []}


METRICS: list[NlqMetric] = [
    # ------------------------------------------------------------- Customers
    NlqMetric(
        id="total_customers",
        label="Total customer accounts",
        category="Customers",
        patterns=[r"how\s+many\s+customers", r"total\s+customers", r"customer\s+count",
                  r"number\s+of\s+(customers|accounts)"],
        snapshot_id="rpt_customer_account",
        example="How many customers do we have?",
        build=lambda _p: {"kind": "scalar", "windowless": True, "query": _count()},
    ),
    NlqMetric(
        id="new_service_agreements",
        label="New service agreements",
        category="Customers",
        patterns=[r"new\s+service\s+agreements?", r"new\s+sas?\b", r"service\s+starts",
                  r"new\s+services\b"],
        snapshot_id="rpt_service_agreement",
        example="New service agreements last 90 days",
        build=lambda _p: {"kind": "scalar", "date_field": "SA Start Date",
                          "query": _count(dims=["SA Type"])},
    ),
    NlqMetric(
        id="customer_contacts",
        label="Customer contacts logged",
        category="Customers",
        patterns=[r"customer\s+contacts?", r"contact\s+volume", r"calls\s+logged"],
        snapshot_id="rpt_customer_contact",
        example="Customer contacts this week",
        build=lambda _p: {"kind": "scalar", "date_field": "Contact Date/Time",
                          "query": _count(dims=["Contact Type"])},
    ),
    NlqMetric(
        id="estimate_streaks",
        label="SAs with 3+ consecutive estimated bills",
        category="Customers",
        patterns=[r"estimat(e|ed)\s+streaks?", r"consecutive\s+estimated"],
        snapshot_id="rpt_service_agreement",
        example="How many estimate streaks do we have?",
        build=lambda _p: {"kind": "scalar", "windowless": True, "query": _count(
            [{"field": "Consecutive Estimated Bills", "op": "gte", "value": 3}])},
    ),
    # --------------------------------------------------------------- Billing
    NlqMetric(
        id="billed_revenue",
        label="Billed revenue",
        category="Billing",
        patterns=[r"billed\s+revenue", r"total\s+billed", r"billed\s+(amount|dollars)",
                  r"revenue\s+billed", r"how\s+much\s+did\s+we\s+bill"],
        snapshot_id="rpt_bill_segment",
        format="currency",
        param_keys=["days", "customer_class", "bill_cycle"],
        example="Total billed revenue last 90 days",
        build=lambda _p: {"kind": "scalar", "query": _sum("Billed Amount")},
    ),
    NlqMetric(
        id="billed_by_class",
        label="Billed revenue by customer class",
        category="Billing",
        patterns=[r"(billed|revenue)\s+by\s+(customer\s+)?class"],
        snapshot_id="rpt_bill_segment",
        format="currency",
        example="Billed revenue by customer class",
        build=lambda _p: {"kind": "trend",
                          "query": _sum("Billed Amount", dims=["Customer Class"])},
    ),
    NlqMetric(
        id="billed_by_cycle",
        label="Billed revenue by bill cycle",
        category="Billing",
        patterns=[r"(billed|revenue)\s+by\s+(bill\s+)?cycle"],
        snapshot_id="rpt_bill_segment",
        format="currency",
        example="Billed revenue by bill cycle",
        build=lambda _p: {"kind": "trend",
                          "query": _sum("Billed Amount", dims=["Bill Cycle"])},
    ),
    NlqMetric(
        id="bills_completed",
        label="Bills completed",
        category="Billing",
        patterns=[r"bills\s+completed", r"completed\s+bills", r"how\s+many\s+bills"],
        snapshot_id="rpt_bill",
        example="How many bills completed last 30 days?",
        default_days=30,
        build=lambda _p: {"kind": "scalar", "date_field": "Window Start Date",
                          "query": _count(
                              [{"field": "Is Completed", "op": "eq", "value": True}])},
    ),
    NlqMetric(
        id="stuck_bills",
        label="Bills stuck open over 30 days",
        category="Billing",
        patterns=[r"stuck\s+bills", r"bills\s+stuck", r"bills?\s+open\s+(over|more)"],
        snapshot_id="rpt_bill",
        example="How many bills are stuck open?",
        build=lambda _p: {"kind": "scalar", "windowless": True, "query": _count(
            [{"field": "Days Bill Open", "op": "gte", "value": 31}])},
    ),
    NlqMetric(
        id="billed_usage_by_uom",
        label="Billed usage by unit of measure",
        category="Billing",
        patterns=[r"(billed\s+)?usage\s+by\s+(uom|unit)", r"quantity\s+by\s+(uom|unit)",
                  r"gallons\s+billed", r"kwh\s+billed"],
        snapshot_id="rpt_billed_usage",
        param_keys=["days", "uom", "customer_class"],
        example="Billed usage by unit of measure",
        # Usage is only additive WITHIN a unit of measure -- always grouped, never
        # a bare total (the cisadm-sql never-sum-across-UOMs rule).
        build=lambda _p: {"kind": "trend",
                          "query": _sum("Billed Quantity", dims=["Unit of Measure"])},
    ),
    # -------------------------------------------------------------- Payments
    NlqMetric(
        id="payments_collected",
        label="Payments collected",
        category="Payments",
        patterns=[r"payments?\s+collected", r"how\s+much\s+(was\s+)?(collected|paid)",
                  r"total\s+payments", r"cash\s+collected"],
        snapshot_id="rpt_payment_tender",
        format="currency",
        param_keys=["days", "payment_type", "customer_class"],
        example="Payments collected last 30 days",
        default_days=30,
        build=lambda _p: {"kind": "scalar", "date_field": "Payment Date",
                          "query": _sum("Tender Amount")},
    ),
    NlqMetric(
        id="payments_by_type",
        label="Payments by tender type",
        category="Payments",
        patterns=[r"payments?\s+by\s+(tender\s+)?type", r"tender\s+mix"],
        snapshot_id="rpt_payment_tender",
        format="currency",
        example="Payments by tender type",
        build=lambda _p: {"kind": "trend", "date_field": "Payment Date",
                          "query": _sum("Tender Amount", dims=["Tender Type"])},
    ),
    NlqMetric(
        id="cancelled_tenders",
        label="Cancelled tenders",
        category="Payments",
        patterns=[r"cancell?ed\s+(tenders?|payments?)", r"payment\s+reversals"],
        snapshot_id="rpt_payment_tender",
        example="Cancelled tenders last 30 days",
        default_days=30,
        build=lambda _p: {"kind": "scalar", "date_field": "Payment Date",
                          "query": _count(
                              [{"field": "Is Cancelled", "op": "eq", "value": True}])},
    ),
    # ----------------------------------------------------------- Collections
    NlqMetric(
        id="accounts_receivable",
        label="Accounts receivable",
        category="Collections",
        patterns=[r"accounts?\s+receivable", r"\bar\b", r"total\s+(debt|balance)\b",
                  r"outstanding\s+balance"],
        snapshot_id="rpt_sa_aged_balance",
        format="currency",
        example="What is our accounts receivable?",
        build=lambda _p: {"kind": "scalar", "windowless": True,
                          "query": _sum("Total Balance")},
    ),
    NlqMetric(
        id="past_due",
        label="Past-due balance",
        category="Collections",
        patterns=[r"past\s+due", r"overdue\s+(balance|amount|dollars)", r"arrears\s+total"],
        snapshot_id="rpt_sa_aged_balance",
        format="currency",
        example="How much is past due?",
        build=lambda _p: {"kind": "scalar", "windowless": True, "query": _sum(
            "Total Balance", [{"field": "Is Past Due", "op": "eq", "value": True}])},
    ),
    NlqMetric(
        id="debt_by_age",
        label="Debt by age band",
        category="Collections",
        patterns=[r"debt\s+by\s+age", r"aged?\s+(debt|balance|receivables)",
                  r"aging\s+buckets?"],
        snapshot_id="rpt_sa_aged_balance",
        format="currency",
        example="Debt dollars by age bucket",
        build=lambda _p: {"kind": "trend", "windowless": True,
                          "query": _sum("Total Balance", dims=["Oldest Debt Band"])},
    ),
    NlqMetric(
        id="collection_processes",
        label="Collection processes started",
        category="Collections",
        patterns=[r"collection\s+process", r"collections?\s+started", r"dunning"],
        snapshot_id="rpt_debt_process",
        example="Collection processes last 90 days",
        build=lambda _p: {"kind": "scalar", "date_field": "Process Created",
                          "query": _count(dims=["Process Type"])},
    ),
    NlqMetric(
        id="active_pay_plans",
        label="Active pay plans",
        category="Collections",
        patterns=[r"active\s+pay(ment)?\s+plans?", r"how\s+many\s+pay(ment)?\s+plans"],
        snapshot_id="rpt_pay_plan",
        example="How many active pay plans?",
        build=lambda _p: {"kind": "scalar", "windowless": True, "query": _count(
            [{"field": "Is Active", "op": "eq", "value": True}])},
    ),
    NlqMetric(
        id="broken_pay_plans",
        label="Broken pay plans",
        category="Collections",
        patterns=[r"broken\s+pay(ment)?\s+plans?", r"defaulted\s+plans?"],
        snapshot_id="rpt_pay_plan",
        example="How many broken pay plans?",
        build=lambda _p: {"kind": "scalar", "windowless": True, "query": _count(
            [{"field": "Is Broken", "op": "eq", "value": True}])},
    ),
    # ------------------------------------------------------------- Meter ops
    NlqMetric(
        id="measurements",
        label="Measurements recorded",
        category="Meter ops",
        patterns=[r"measurements?\s+(recorded|taken|count)", r"meter\s+read(s|ings)"],
        snapshot_id="rpt_measurement",
        example="Meter readings last 30 days",
        default_days=30,
        build=lambda _p: {"kind": "scalar", "date_field": "Measurement Date/Time",
                          "query": _count()},
    ),
    NlqMetric(
        id="estimated_measurements",
        label="Estimated measurements",
        category="Meter ops",
        patterns=[r"estimated\s+(measurements?|read(s|ings))", r"estimation\s+(rate|share)"],
        snapshot_id="rpt_measurement",
        example="Estimated reads last 30 days",
        default_days=30,
        build=lambda _p: {"kind": "scalar", "date_field": "Measurement Date/Time",
                          "query": _count([{"field": "Is Estimated Measurement",
                                            "op": "eq", "value": True}])},
    ),
    NlqMetric(
        id="devices_dark",
        label="Devices switched off 60+ days",
        category="Meter ops",
        patterns=[r"devices?\s+(dark|switched\s+off)", r"meters?\s+off\b"],
        snapshot_id="rpt_device_asset",
        example="How many devices are switched off over 60 days?",
        build=lambda _p: {"kind": "scalar", "windowless": True, "query": _count(
            [{"field": "Days Switched Off", "op": "gte", "value": 60}])},
    ),
    NlqMetric(
        id="never_registered_devices",
        label="Installed devices never registered at head-end",
        category="Meter ops",
        patterns=[r"never\s+registered", r"head[- ]end\s+registration"],
        snapshot_id="rpt_device_asset",
        example="Devices never registered at the head-end",
        build=lambda _p: {"kind": "scalar", "windowless": True, "query": _count(
            [{"field": "Never Registered At Head-End", "op": "eq", "value": True},
             {"field": "Is Attached To Service Point", "op": "eq", "value": True}])},
    ),
    NlqMetric(
        id="meterless_service_points",
        label="In-service points with no installed meter",
        category="Meter ops",
        patterns=[r"(service\s+points?|sps?)\s+with(out|\s+no)\s+(a\s+)?meter",
                  r"no\s+meter\s+installed", r"meterless"],
        snapshot_id="rpt_premise_sp",
        example="Active service points with no meter installed right now",
        build=lambda _p: {"kind": "scalar", "windowless": True, "query": _count(
            [{"field": "Has Installed Device", "op": "eq", "value": False}])},
    ),
    NlqMetric(
        id="usage_transactions",
        label="Usage transactions processed",
        category="Meter ops",
        patterns=[r"usage\s+transactions?", r"usage\s+processed"],
        snapshot_id="rpt_usage_txn",
        example="Usage transactions last 30 days",
        default_days=30,
        build=lambda _p: {"kind": "scalar", "date_field": "Start Date/Time",
                          "query": _count()},
    ),
    # ------------------------------------------------------------- Field ops
    NlqMetric(
        id="field_activities",
        label="Field activities",
        category="Field ops",
        patterns=[r"field\s+(activities|activity|work|orders?)", r"truck\s+rolls?"],
        snapshot_id="rpt_field_activity",
        example="Field activities last 30 days",
        default_days=30,
        build=lambda _p: {"kind": "scalar", "date_field": "Event Date/Time",
                          "query": _count(dims=["Activity Type"])},
    ),
    NlqMetric(
        id="open_todos",
        label="Open To Do entries",
        category="Field ops",
        patterns=[r"open\s+to[- ]?dos?", r"to[- ]?do\s+backlog", r"work\s+queue"],
        snapshot_id="rpt_todo",
        example="How many open To Dos?",
        build=lambda _p: {"kind": "scalar", "windowless": True, "query": _count(
            [{"field": "Is Complete", "op": "eq", "value": False}])},
    ),
    NlqMetric(
        id="open_cases",
        label="Open cases",
        category="Field ops",
        patterns=[r"open\s+cases?", r"case\s+backlog"],
        snapshot_id="rpt_case",
        example="How many open cases?",
        build=lambda _p: {"kind": "scalar", "windowless": True, "query": _count(
            [{"field": "Is Closed", "op": "eq", "value": False}])},
    ),
    # --------------------------------------------------------------- Finance
    NlqMetric(
        id="frozen_ft_dollars",
        label="Frozen financial transaction dollars",
        category="Finance",
        patterns=[r"(frozen\s+)?ft\s+dollars", r"financial\s+transactions?\s+(total|dollars)",
                  r"posted\s+dollars"],
        snapshot_id="rpt_financial_txn",
        format="currency",
        example="Frozen FT dollars last 90 days",
        build=lambda _p: {"kind": "scalar", "date_field": "Accounting Date",
                          "query": _sum("Current Amount",
                                        [{"field": "Is Frozen", "op": "eq", "value": True}])},
    ),
    NlqMetric(
        id="adjustments",
        label="Adjustment dollars",
        category="Finance",
        patterns=[r"adjustments?\s+(total|dollars|amount)?", r"write[- ]?offs?\b"],
        snapshot_id="rpt_financial_txn",
        format="currency",
        example="Adjustment dollars last 90 days",
        build=lambda _p: {"kind": "scalar", "date_field": "Accounting Date",
                          "query": _sum("Current Amount",
                                        [{"field": "Is Adjustment", "op": "eq", "value": True}])},
    ),
    NlqMetric(
        id="gl_by_account",
        label="GL dollars by account",
        category="Finance",
        patterns=[r"gl\s+(distribution|dollars|by\s+account)", r"general\s+ledger"],
        snapshot_id="rpt_gl",
        format="currency",
        example="GL dollars by account last 90 days",
        build=lambda _p: {"kind": "trend", "date_field": "Accounting Date",
                          "query": _sum("GL Amount", dims=["GL Account"])},
    ),
]

_METRIC_BY_ID = {m.id: m for m in METRICS}
_COMPILED = [(m, re.compile("|".join(m.patterns), re.I)) for m in METRICS]


def list_metric_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": m.id,
            "label": m.label,
            "category": m.category,
            "snapshot_id": m.snapshot_id,
            "default_days": m.default_days,
            "format": m.format,
            "param_keys": m.param_keys,
            "example": m.example or m.label,
        }
        for m in METRICS
    ]


def match_metric(question: str, metric_id: str | None = None) -> NlqMetric | None:
    if metric_id and metric_id in _METRIC_BY_ID:
        return _METRIC_BY_ID[metric_id]
    q = (question or "").strip()
    if not q:
        return None
    for metric, pattern in _COMPILED:
        if pattern.search(q):
            return metric
    return None


def run_metric_nlq(
    question: str,
    *,
    metric_id: str | None = None,
    params: dict[str, Any] | None = None,
    organization_id: str,
) -> dict[str, Any] | None:
    metric = match_metric(question, metric_id)
    if not metric:
        return None
    merged = parse_params(question, params)
    if merged.get("days") is None:
        merged["days"] = metric.default_days
    return _run_metric(metric, merged, organization_id=organization_id)
