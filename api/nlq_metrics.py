"""Governed everyday metric questions mapped to snapshot queries."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable

from api.kpi_runner import run_kpi_query, trend_from_rows
from api.snapshot_catalog import get_snapshot


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


def _extra(params: dict[str, Any]) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = []
    if params.get("bill_cycle"):
        filters.append({"field": "BILL_CYC_DESC", "op": "eq", "value": params["bill_cycle"]})
    if params.get("customer_class"):
        filters.append({"field": "CUST_CL_DESC", "op": "eq", "value": params["customer_class"]})
    if params.get("payment_type"):
        filters.append({"field": "SOLE_TENDER_TYPE_DESC", "op": "eq", "value": params["payment_type"]})
    if params.get("rate_code"):
        filters.append({"field": "SOLE_RS_DESC", "op": "eq", "value": params["rate_code"]})
    if params.get("uom"):
        filters.append({"field": "UOM_DESC", "op": "eq", "value": params["uom"]})
    return filters


def _scalar(
    snapshot_id: str,
    query: dict[str, Any],
    params: dict[str, Any],
    *,
    organization_id: str,
    date_field: str | None = None,
) -> tuple[float, list[dict[str, Any]]]:
    snap = get_snapshot(snapshot_id)
    field_name = date_field or snap.get("required_date_field")
    if not field_name:
        raise ValueError(f"No date field for {snapshot_id}")
    days = int(params.get("days") or 90)
    start, end = _window(days)
    extra = _extra(params)
    filters = list(query.get("filters") or [])
    filters.extend(extra)
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
) -> list[dict[str, Any]]:
    snap = get_snapshot(snapshot_id)
    field_name = date_field or snap.get("required_date_field")
    days = int(params.get("days") or 90)
    start, end = _window(days)
    extra = _extra(params)
    filters = list(query.get("filters") or [])
    filters.extend(extra)
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
    narrative = (
        f"{metric.label}: {_fmt(value, metric.format)} "
        f"(last {days} days on {metric.snapshot_id.replace('_RPT_CURR', '').replace('_', ' ').title()})."
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
    if kind == "bucket_table":
        rows: list[dict[str, Any]] = []
        total = 0.0
        for bucket in spec.get("buckets") or []:
            label = str(bucket.get("label", "Bucket"))
            query = bucket["query"]
            value, _ = _scalar(
                metric.snapshot_id,
                query,
                params,
                organization_id=organization_id,
                date_field=spec.get("date_field"),
            )
            rows.append({"label": label, "value": value})
            total += value
        return _result(
            metric, params, total, rows, narrative_extra=spec.get("note", ""), spec=spec
        )
    if kind == "trend":
        table = _trend(metric.snapshot_id, spec["query"], params, organization_id=organization_id)
        total = sum(float(r["value"]) for r in table)
        return _result(
            metric, params, total, table, narrative_extra=spec.get("note", ""), spec=spec
        )
    value, table = _scalar(metric.snapshot_id, spec["query"], params, organization_id=organization_id)
    return _result(
        metric, params, value, table or None, narrative_extra=spec.get("note", ""), spec=spec
    )


METRICS: list[NlqMetric] = [
    NlqMetric(
        id="total_premises",
        label="Total premises (distinct)",
        category="Premises & accounts",
        patterns=[r"total\s+#?\s*(?:of\s+)?premises?", r"how many premises"],
        snapshot_id="CASE_PREM_CONTACT_RPT_CURR",
        default_days=365,
        param_keys=["days", "bill_cycle", "customer_class"],
        example="Total premises by customer class",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["CUST_CL_DESC"],
                "measures": [{"field": "PREM_ID", "agg": "count_distinct"}],
                "filters": [],
                "limit": 20,
            },
        },
    ),
    NlqMetric(
        id="total_accounts",
        label="Total accounts",
        category="Premises & accounts",
        patterns=[r"total\s+#?\s*(?:of\s+)?accounts?(?!\s+billed)", r"how many accounts"],
        snapshot_id="ACCT_CUSTOMER_RPT_CURR",
        default_days=365,
        param_keys=["days", "bill_cycle", "customer_class"],
        example="Total accounts by bill cycle",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["BILL_CYC_DESC"],
                "measures": [{"field": "ACCT_ID", "agg": "count_distinct"}],
                "filters": [],
                "limit": 24,
            },
        },
    ),
    NlqMetric(
        id="active_service_agreements",
        label="Active service agreements",
        category="Premises & accounts",
        patterns=[r"active\s+service", r"premises?\s+with\s+active\s+service"],
        snapshot_id="NEW_SERVICE_PIPELINE_RPT_CURR",
        default_days=365,
        param_keys=["days", "customer_class"],
        example="Premises with active service",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "SA_ID", "agg": "count_distinct"}],
                "filters": [{"field": "SA_STATUS_DESC", "op": "eq", "value": "Active"}],
            },
            "note": "Active SA status (20) on new service pipeline snapshot.",
        },
    ),
    NlqMetric(
        id="billed_revenue_total",
        label="Total dollars billed",
        category="Billing",
        patterns=[
            r"total\s+\$?\s*(?:of\s+)?accounts?\s+billed",
            r"billed\s+revenue",
            r"billing\s+total",
        ],
        snapshot_id="BSEG_BILLED_USAGE_RPT_CURR",
        default_days=180,
        format="currency",
        param_keys=["days", "bill_cycle", "customer_class"],
        example="Total billed revenue last 6 months",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "TOTAL_CALC_AMT", "agg": "sum"}],
                "filters": [],
            },
        },
    ),
    NlqMetric(
        id="accounts_billed_count",
        label="Accounts billed (distinct)",
        category="Billing",
        patterns=[r"total\s+#?\s*(?:of\s+)?accounts?\s+billed", r"how many accounts billed"],
        snapshot_id="BSEG_BILLED_USAGE_RPT_CURR",
        default_days=180,
        param_keys=["days", "bill_cycle", "customer_class"],
        example="Total accounts billed",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "ACCT_ID", "agg": "count_distinct"}],
                "filters": [],
            },
        },
    ),
    NlqMetric(
        id="billed_by_customer_class",
        label="Billed revenue by customer class",
        category="Billing",
        patterns=[r"billed.*customer\s+class", r"revenue\s+by\s+class"],
        snapshot_id="BSEG_BILLED_USAGE_RPT_CURR",
        default_days=180,
        format="currency",
        param_keys=["days", "customer_class"],
        example="Billed revenue by customer class",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["CUST_CL_DESC"],
                "measures": [{"field": "TOTAL_CALC_AMT", "agg": "sum"}],
                "filters": [],
                "limit": 12,
            },
        },
    ),
    NlqMetric(
        id="billed_by_bill_cycle",
        label="Billed revenue by bill cycle",
        category="Billing",
        patterns=[r"by\s+bill\s+cycle", r"billed.*bill\s+cycle"],
        snapshot_id="BSEG_BILLED_USAGE_RPT_CURR",
        default_days=180,
        format="currency",
        param_keys=["days", "bill_cycle"],
        example="Billed amount by bill cycle",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["BILL_CYC_DESC"],
                "measures": [{"field": "TOTAL_CALC_AMT", "agg": "sum"}],
                "filters": [],
                "limit": 24,
            },
        },
    ),
    NlqMetric(
        id="kwh_billed",
        label="Total kWh billed",
        category="Billing",
        patterns=[r"total\s+kwh", r"kilowatt", r"kwh\s+billed"],
        snapshot_id="BSEG_SQ_USAGE_RPT_CURR",
        default_days=180,
        param_keys=["days", "customer_class"],
        example="Total kWh billed",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "TOTAL_BILL_SQ", "agg": "sum"}],
                "filters": [{"field": "UOM_DESC", "op": "eq", "value": "KWH"}],
            },
            "note": "Filtered to KWH unit of measure on billed determinant snapshot.",
        },
    ),
    NlqMetric(
        id="billing_todos",
        label="Billing to-do items",
        category="Billing",
        patterns=[r"billing\s+todo", r"todo.*billing"],
        snapshot_id="WORKFLOW_QUEUE_RPT_CURR",
        default_days=30,
        param_keys=["days"],
        example="Billing todos generated",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [{"field": "QUEUE_SOURCE", "op": "eq", "value": "TODO"}],
            },
        },
    ),
    NlqMetric(
        id="open_exceptions",
        label="Open exceptions",
        category="Operations",
        patterns=[r"open\s+exceptions?", r"exception\s+backlog", r"total\s+#?\s*(?:of\s+)?exceptions?"],
        snapshot_id="OPS_EXCEPTION_RPT_CURR",
        default_days=30,
        param_keys=["days"],
        example="Open exceptions this month",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["EXCP_SEVERITY_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [{"field": "OPEN_CLOSE_FLG", "op": "eq", "value": "O"}],
                "limit": 8,
            },
        },
    ),
    NlqMetric(
        id="workflow_todos",
        label="Open workflow to-dos",
        category="Operations",
        patterns=[r"workflow\s+todo", r"work\s+queue", r"staff\s+todo"],
        snapshot_id="WORKFLOW_QUEUE_RPT_CURR",
        default_days=30,
        param_keys=["days"],
        example="Open to-do workload",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["ENTRY_STATUS_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [{"field": "QUEUE_SOURCE", "op": "eq", "value": "TODO"}],
                "limit": 10,
            },
        },
    ),
    NlqMetric(
        id="payments_count",
        label="Payments processed",
        category="Payments",
        patterns=[r"total\s+#?\s*(?:of\s+)?payments?\s+processed", r"how many payments"],
        snapshot_id="PAY_EVENT_RPT_CURR",
        default_days=90,
        param_keys=["days", "payment_type"],
        example="Payments processed last quarter",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
        },
    ),
    NlqMetric(
        id="payments_dollars",
        label="Payment dollars processed",
        category="Payments",
        patterns=[
            r"total\s+\$?\s*(?:of\s+)?payments?\s+processed",
            r"payment\s+dollars",
            r"payments?\s+amount",
        ],
        snapshot_id="PAY_EVENT_RPT_CURR",
        default_days=90,
        format="currency",
        param_keys=["days", "payment_type"],
        example="Total payment dollars",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "PAY_AMT", "agg": "sum"}],
                "filters": [],
            },
        },
    ),
    NlqMetric(
        id="payments_by_type",
        label="Payments by tender type",
        category="Payments",
        patterns=[r"payment\s+type", r"payments?\s+by\s+(?:payment\s+)?type", r"ebpp|kiosk|usps"],
        snapshot_id="PAY_EVENT_RPT_CURR",
        default_days=90,
        format="currency",
        param_keys=["days", "payment_type"],
        example="Payments by payment type",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["SOLE_TENDER_TYPE_DESC"],
                "measures": [{"field": "PAY_AMT", "agg": "sum"}],
                "filters": [],
                "limit": 12,
            },
        },
    ),
    NlqMetric(
        id="field_activities_created",
        label="Field activities created",
        category="Field operations",
        patterns=[r"field\s+activit(?:y|ies)\s+created", r"total\s+#?\s*(?:of\s+)?field\s+activit"],
        snapshot_id="FIELD_ACTIVITY_RPT_CURR",
        default_days=90,
        param_keys=["days"],
        example="Field activities created",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
        },
    ),
    NlqMetric(
        id="field_activities_pending",
        label="Pending field activities",
        category="Field operations",
        patterns=[r"field\s+activit.*pending", r"pending\s+field"],
        snapshot_id="FIELD_ACTIVITY_RPT_CURR",
        default_days=90,
        param_keys=["days"],
        example="Field activities pending",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [{"field": "BO_STATUS_DESC", "op": "neq", "value": "Complete"}],
            },
        },
    ),
    NlqMetric(
        id="debt_total",
        label="Total SA debt",
        category="Collections",
        patterns=[r"total\s+debt", r"accounts?\s+by\s+debt", r"top\s+accounts?\s+by\s+debt"],
        snapshot_id="SA_AGED_BAL_RPT_CURR",
        default_days=730,
        format="currency",
        param_keys=["days", "customer_class"],
        example="Top accounts by debt",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["ACCT_ID"],
                "measures": [{"field": "TOTAL_DEBT", "agg": "sum"}],
                "filters": [{"field": "TOTAL_DEBT", "op": "gte", "value": 0.01}],
                "limit": 10,
            },
        },
    ),
    NlqMetric(
        id="debt_by_age",
        label="Debt by aging bucket",
        category="Collections",
        patterns=[r"accounts?\s+by\s+age", r"debt\s+by\s+age", r"aging"],
        snapshot_id="SA_AGED_BAL_RPT_CURR",
        default_days=730,
        format="currency",
        param_keys=["days"],
        example="Total debt by age bucket",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["CUST_CL_DESC"],
                "measures": [{"field": "TOTAL_DEBT", "agg": "sum"}],
                "filters": [],
                "limit": 12,
            },
            "note": "Grouped by customer class; use explorer for 0-30/31-60 bucket fields.",
        },
    ),
    NlqMetric(
        id="new_connections",
        label="New service connections",
        category="New connections",
        patterns=[r"total\s+#?\s*(?:of\s+)?connects?", r"new\s+connections?", r"new\s+service"],
        snapshot_id="NEW_SERVICE_PIPELINE_RPT_CURR",
        default_days=180,
        param_keys=["days"],
        example="New connects in pipeline",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "SA_ID", "agg": "count_distinct"}],
                "filters": [],
            },
        },
    ),
    NlqMetric(
        id="meter_reads_in_cycle",
        label="Measurements in period",
        category="Meter operations",
        patterns=[r"meters?\s+.*reads?", r"meter\s+reading", r"measurements?\s+in"],
        snapshot_id="D1_MSRMT_RPT_CURR",
        default_days=30,
        param_keys=["days"],
        example="Meter reads last 30 days",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "note": "Large domain — uses 30-day window by default.",
        },
    ),
    NlqMetric(
        id="premises_by_bill_cycle",
        label="Premises by bill cycle",
        category="Premises & accounts",
        patterns=[r"premises?\s+by\s+bill\s+cycle"],
        snapshot_id="SA_AGED_BAL_RPT_CURR",
        default_days=365,
        param_keys=["days", "bill_cycle"],
        example="Total premises by bill cycle",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["BILL_CYC_DESC"],
                "measures": [{"field": "PREM_ID", "agg": "count_distinct"}],
                "filters": [],
                "limit": 24,
            },
        },
    ),
    NlqMetric(
        id="premises_by_customer_class",
        label="Premises by customer class",
        category="Premises & accounts",
        patterns=[r"premises?\s+by\s+customer\s+class"],
        snapshot_id="SA_AGED_BAL_RPT_CURR",
        default_days=365,
        param_keys=["days", "customer_class"],
        example="Premises by customer class",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["CUST_CL_DESC"],
                "measures": [{"field": "PREM_ID", "agg": "count_distinct"}],
                "filters": [],
                "limit": 12,
            },
        },
    ),
    NlqMetric(
        id="accounts_by_customer_class",
        label="Accounts by customer class",
        category="Premises & accounts",
        patterns=[r"accounts?\s+by\s+customer\s+class"],
        snapshot_id="ACCT_CUSTOMER_RPT_CURR",
        default_days=365,
        param_keys=["days", "customer_class"],
        example="Accounts by customer class",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["CUST_CL_DESC"],
                "measures": [{"field": "ACCT_ID", "agg": "count_distinct"}],
                "filters": [],
                "limit": 12,
            },
        },
    ),
    NlqMetric(
        id="premises_active_service",
        label="Premises with active service",
        category="Premises & accounts",
        patterns=[r"premises?\s+with\s+active\s+service", r"active\s+service\s+premises?"],
        snapshot_id="NEW_SERVICE_PIPELINE_RPT_CURR",
        default_days=365,
        param_keys=["days", "customer_class", "bill_cycle"],
        example="Premises with active service",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "PREM_ID", "agg": "count_distinct"}],
                "filters": [{"field": "SA_STATUS_DESC", "op": "eq", "value": "Active"}],
            },
        },
    ),
    NlqMetric(
        id="premises_no_active_service",
        label="Premises with no active service",
        category="Premises & accounts",
        patterns=[r"no\s+active\s+service", r"premises?\s+without\s+active"],
        snapshot_id="ACCT_CUSTOMER_RPT_CURR",
        default_days=365,
        param_keys=["days", "customer_class"],
        example="Accounts with no active service agreements",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "ACCT_ID", "agg": "count_distinct"}],
                "filters": [{"field": "ACTIVE_SA_COUNT", "op": "lte", "value": 0}],
            },
            "note": "Account grain — ACTIVE_SA_COUNT = 0.",
        },
    ),
    NlqMetric(
        id="premises_disconnected",
        label="Premises with disconnected service",
        category="Premises & accounts",
        patterns=[r"disconnected\s+service", r"service\s+disconnected"],
        snapshot_id="NEW_SERVICE_PIPELINE_RPT_CURR",
        default_days=365,
        param_keys=["days"],
        example="Service agreements in stopped status",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "PREM_ID", "agg": "count_distinct"}],
                "filters": [{"field": "SA_STATUS_DESC", "op": "eq", "value": "Stopped"}],
            },
            "note": "Distinct premises on stopped service agreements.",
        },
    ),
    NlqMetric(
        id="accounts_billed_by_rate",
        label="Accounts billed by rate schedule",
        category="Billing",
        patterns=[r"accounts?\s+billed\s+by\s+rate", r"billed\s+accounts?\s+by\s+rate"],
        snapshot_id="BSEG_BILLED_USAGE_RPT_CURR",
        default_days=180,
        param_keys=["days", "rate_code"],
        example="Accounts billed by rate code",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["SOLE_RS_DESC"],
                "measures": [{"field": "ACCT_ID", "agg": "count_distinct"}],
                "filters": [],
                "limit": 15,
            },
        },
    ),
    NlqMetric(
        id="billed_dollars_by_rate",
        label="Billed dollars by rate schedule",
        category="Billing",
        patterns=[r"\$\s*.*billed\s+by\s+rate", r"revenue\s+by\s+rate\s+code"],
        snapshot_id="BSEG_BILLED_USAGE_RPT_CURR",
        default_days=180,
        format="currency",
        param_keys=["days", "rate_code"],
        example="Total dollars billed by rate code",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["SOLE_RS_DESC"],
                "measures": [{"field": "TOTAL_CALC_AMT", "agg": "sum"}],
                "filters": [],
                "limit": 15,
            },
        },
    ),
    NlqMetric(
        id="estimated_bills",
        label="Estimated bills",
        category="Billing",
        patterns=[r"estimated\s+bills?", r"total\s+#?\s*(?:of\s+)?estimated"],
        snapshot_id="BSEG_BILLED_USAGE_RPT_CURR",
        default_days=180,
        param_keys=["days", "bill_cycle"],
        example="Estimated bill segments",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "BSEG_ID", "agg": "count_distinct"}],
                "filters": [{"field": "EST_SW", "op": "eq", "value": "Y"}],
            },
        },
    ),
    NlqMetric(
        id="closing_cycle_segments",
        label="Closing-cycle bill segments",
        category="Billing",
        patterns=[r"closing\s+cycle", r"eligible.*closing"],
        snapshot_id="BSEG_BILLED_USAGE_RPT_CURR",
        default_days=90,
        param_keys=["days", "bill_cycle"],
        example="Accounts eligible on closing cycle",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "ACCT_ID", "agg": "count_distinct"}],
                "filters": [{"field": "CLOSING_BSEG_SW", "op": "eq", "value": "Y"}],
            },
            "note": "Distinct accounts on closing bill segments.",
        },
    ),
    NlqMetric(
        id="opening_cycle_segments",
        label="Opening-cycle bill segments",
        category="Billing",
        patterns=[r"opening\s+cycle", r"eligible.*opening"],
        snapshot_id="BSEG_BILLED_USAGE_RPT_CURR",
        default_days=90,
        param_keys=["days", "bill_cycle"],
        example="Accounts on opening cycle segments",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "ACCT_ID", "agg": "count_distinct"}],
                "filters": [{"field": "CLOSING_BSEG_SW", "op": "neq", "value": "Y"}],
            },
            "note": "Distinct accounts on non-closing bill segments.",
        },
    ),
    NlqMetric(
        id="accounts_on_hold",
        label="Accounts with bill print intercept",
        category="Billing",
        patterns=[r"accounts?\s+on\s+hold", r"bill\s+hold", r"intercept"],
        snapshot_id="NEW_SERVICE_PIPELINE_RPT_CURR",
        default_days=365,
        param_keys=["days"],
        example="Accounts on billing hold (print intercept)",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "ACCT_ID", "agg": "count_distinct"}],
                "filters": [{"field": "BILL_PRT_INTERCEPT", "op": "neq", "value": " "}],
            },
            "note": "Accounts with a non-blank bill print intercept flag.",
        },
    ),
    NlqMetric(
        id="meter_read_todos",
        label="Meter reading to-do items",
        category="Meter operations",
        patterns=[r"meter\s+reading\s+todo", r"mr\s+todo"],
        snapshot_id="WORKFLOW_QUEUE_RPT_CURR",
        default_days=30,
        param_keys=["days"],
        example="Meter reading todos in workflow queue",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [
                    {"field": "QUEUE_SOURCE", "op": "eq", "value": "TODO"},
                    {"field": "TD_TYPE_DESC", "op": "in", "value": ["Meter Read", "Meter Reading"]},
                ],
            },
            "note": "Open to-dos whose type description matches meter reading.",
        },
    ),
    NlqMetric(
        id="meters_with_reads",
        label="Bill segments with meter reads",
        category="Meter operations",
        patterns=[r"meters?\s+.*with\s+reads?", r"segments?\s+with\s+reads?"],
        snapshot_id="BSEG_BILLED_USAGE_RPT_CURR",
        default_days=90,
        param_keys=["days", "bill_cycle"],
        example="Bill segments with read lines",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "BSEG_ID", "agg": "count_distinct"}],
                "filters": [{"field": "READ_LINE_COUNT", "op": "gte", "value": 1}],
            },
        },
    ),
    NlqMetric(
        id="meters_without_reads",
        label="Bill segments with no reads",
        category="Meter operations",
        patterns=[r"meters?\s+.*no\s+reads?", r"without\s+reads?", r"no\s+read\s+lines?"],
        snapshot_id="BSEG_BILLED_USAGE_RPT_CURR",
        default_days=90,
        param_keys=["days", "bill_cycle"],
        example="Bill segments missing read lines",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "BSEG_ID", "agg": "count_distinct"}],
                "filters": [{"field": "READ_LINE_COUNT", "op": "lte", "value": 0}],
            },
        },
    ),
    NlqMetric(
        id="field_activities_scheduled",
        label="Scheduled field activities",
        category="Field operations",
        patterns=[r"field\s+activit.*scheduled", r"scheduled\s+for\s+(?:7|9)\s*am"],
        snapshot_id="FIELD_ACTIVITY_RPT_CURR",
        default_days=30,
        param_keys=["days"],
        example="Field activities with appointment windows",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [{"field": "APPOINTMENT_FLG", "op": "eq", "value": "Y"}],
            },
            "note": "Use explorer on START_DTTM for 7am/9am slot drill-down.",
        },
    ),
    NlqMetric(
        id="disconnects",
        label="Disconnect field activities",
        category="Field operations",
        patterns=[r"total\s+#?\s*(?:of\s+)?disconnects?", r"\bdisconnects?\b"],
        snapshot_id="FIELD_ACTIVITY_RPT_CURR",
        default_days=90,
        param_keys=["days"],
        example="Disconnect field activities",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [{"field": "ACTIVITY_TYPE_DESC", "op": "eq", "value": "Disconnect"}],
            },
        },
    ),
    NlqMetric(
        id="reconnects",
        label="Reconnect field activities",
        category="Field operations",
        patterns=[r"total\s+#?\s*(?:of\s+)?reconnects?", r"\breconnects?\b"],
        snapshot_id="FIELD_ACTIVITY_RPT_CURR",
        default_days=90,
        param_keys=["days"],
        example="Reconnect field activities",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [{"field": "ACTIVITY_TYPE_DESC", "op": "eq", "value": "Reconnect"}],
            },
        },
    ),
    NlqMetric(
        id="connects",
        label="Connect field activities",
        category="Field operations",
        patterns=[r"total\s+#?\s*(?:of\s+)?connects?(?!\s+ion)", r"\bconnects?\b"],
        snapshot_id="FIELD_ACTIVITY_RPT_CURR",
        default_days=90,
        param_keys=["days"],
        example="Connect field activities",
        build=lambda _p: {
            "query": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [{"field": "ACTIVITY_TYPE_DESC", "op": "eq", "value": "Connect"}],
            },
        },
    ),
    NlqMetric(
        id="work_requests_manual",
        label="Open to-dos needing attention",
        category="Operations",
        patterns=[r"work\s+request.*manual", r"manual\s+intervention", r"waiting\s+for\s+staff"],
        snapshot_id="WORKFLOW_QUEUE_RPT_CURR",
        default_days=30,
        param_keys=["days"],
        example="Open workflow to-dos not complete",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["TD_TYPE_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [
                    {"field": "QUEUE_SOURCE", "op": "eq", "value": "TODO"},
                    {"field": "TD_ENTRY_STATUS_DESC", "op": "neq", "value": "Complete"},
                ],
                "limit": 12,
            },
        },
    ),
    NlqMetric(
        id="payments_count_by_type",
        label="Payment count by tender type",
        category="Payments",
        patterns=[r"payments?\s+processed\s+by\s+(?:payment\s+)?type", r"#\s*payments?\s+by\s+type"],
        snapshot_id="PAY_EVENT_RPT_CURR",
        default_days=90,
        param_keys=["days", "payment_type"],
        example="Number of payments by payment type",
        build=lambda _p: {
            "kind": "trend",
            "query": {
                "dimensions": ["SOLE_TENDER_TYPE_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 12,
            },
        },
    ),
    NlqMetric(
        id="accounts_by_age",
        label="Accounts with debt by aging bucket",
        category="Collections",
        patterns=[r"accounts?\s+by\s+age", r"#\s*accounts?\s+by\s+age"],
        snapshot_id="SA_AGED_BAL_RPT_CURR",
        default_days=730,
        param_keys=["days"],
        example="Accounts with debt by age bucket",
        build=lambda _p: {
            "kind": "bucket_table",
            "buckets": [
                {
                    "label": "0-30 days",
                    "query": {
                        "dimensions": [],
                        "measures": [{"field": "ACCT_ID", "agg": "count_distinct"}],
                        "filters": [{"field": "DEBT_0_30", "op": "gte", "value": 0.01}],
                    },
                },
                {
                    "label": "31-60 days",
                    "query": {
                        "dimensions": [],
                        "measures": [{"field": "ACCT_ID", "agg": "count_distinct"}],
                        "filters": [{"field": "DEBT_31_60", "op": "gte", "value": 0.01}],
                    },
                },
                {
                    "label": "61-90 days",
                    "query": {
                        "dimensions": [],
                        "measures": [{"field": "ACCT_ID", "agg": "count_distinct"}],
                        "filters": [{"field": "DEBT_61_90", "op": "gte", "value": 0.01}],
                    },
                },
                {
                    "label": "Over 90 days",
                    "query": {
                        "dimensions": [],
                        "measures": [{"field": "ACCT_ID", "agg": "count_distinct"}],
                        "filters": [{"field": "DEBT_OVER_90", "op": "gte", "value": 0.01}],
                    },
                },
            ],
        },
    ),
    NlqMetric(
        id="debt_dollars_by_age",
        label="Debt dollars by aging bucket",
        category="Collections",
        patterns=[r"\$\s*.*accounts?\s+by\s+age", r"debt\s+dollars\s+by\s+age"],
        snapshot_id="SA_AGED_BAL_RPT_CURR",
        default_days=730,
        format="currency",
        param_keys=["days"],
        example="Total debt dollars by age bucket",
        build=lambda _p: {
            "kind": "bucket_table",
            "buckets": [
                {
                    "label": "0-30 days",
                    "query": {
                        "dimensions": [],
                        "measures": [{"field": "DEBT_0_30", "agg": "sum"}],
                        "filters": [],
                    },
                },
                {
                    "label": "31-60 days",
                    "query": {
                        "dimensions": [],
                        "measures": [{"field": "DEBT_31_60", "agg": "sum"}],
                        "filters": [],
                    },
                },
                {
                    "label": "61-90 days",
                    "query": {
                        "dimensions": [],
                        "measures": [{"field": "DEBT_61_90", "agg": "sum"}],
                        "filters": [],
                    },
                },
                {
                    "label": "Over 90 days",
                    "query": {
                        "dimensions": [],
                        "measures": [{"field": "DEBT_OVER_90", "agg": "sum"}],
                        "filters": [],
                    },
                },
            ],
        },
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
