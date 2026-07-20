"""Executive KPI definitions and query runner for the analytics portal."""

from __future__ import annotations

from typing import Any

from api.demo_db import demo_configured
from api.kpi_runner import date_windows, execute_kpi_definition


EXECUTIVE_KPIS: list[dict[str, Any]] = [
    {
        "id": "billed_revenue",
        "label": "Billed revenue",
        "subtitle": "Completed bill segments",
        "snapshot_id": "BSEG_BILLED_USAGE_RPT_CURR",
        "format": "currency",
        "workstream": "billing",
        "explore_report_id": "amount_by_class",
        "value": {
            "dimensions": [],
            "measures": [{"field": "TOTAL_CALC_AMT", "agg": "sum"}],
            "filters": [],
        },
        "trend": {
            "dimensions": ["CUST_CL_DESC"],
            "measures": [{"field": "TOTAL_CALC_AMT", "agg": "sum"}],
            "filters": [],
            "limit": 6,
        },
    },
    {
        "id": "transaction_volume",
        "label": "Transaction dollars",
        "subtitle": "Financial transactions",
        "snapshot_id": "FT_RPT_CURR",
        "format": "currency",
        "workstream": "finance",
        "explore_report_id": "ft_by_type",
        "value": {
            "dimensions": [],
            "measures": [{"field": "CUR_AMT", "agg": "sum"}],
            "filters": [],
        },
        "trend": {
            "dimensions": ["FT_TYPE_FLG_DESC"],
            "measures": [{"field": "CUR_AMT", "agg": "sum"}],
            "filters": [],
            "limit": 6,
        },
    },
    {
        "id": "open_exceptions",
        "label": "Open exceptions",
        "subtitle": "Billing & meter validation backlog",
        "snapshot_id": "OPS_EXCEPTION_RPT_CURR",
        "format": "number",
        "workstream": "common",
        "explore_report_id": "excp_open",
        "value": {
            "dimensions": [],
            "measures": [{"field": "*", "agg": "count"}],
            "filters": [{"field": "OPEN_CLOSE_FLG", "op": "eq", "value": "O"}],
        },
        "trend": {
            "dimensions": ["EXCP_SEVERITY_DESC"],
            "measures": [{"field": "*", "agg": "count"}],
            "filters": [{"field": "OPEN_CLOSE_FLG", "op": "eq", "value": "O"}],
            "limit": 6,
        },
    },
    {
        "id": "case_volume",
        "label": "Customer cases",
        "subtitle": "Cases opened",
        "snapshot_id": "CASE_PREM_CONTACT_RPT_CURR",
        "format": "number",
        "workstream": "customer_ops",
        "explore_report_id": "cases_by_type",
        "value": {
            "dimensions": [],
            "measures": [{"field": "*", "agg": "count"}],
            "filters": [],
        },
        "trend": {
            "dimensions": ["CASE_TYPE_DESC"],
            "measures": [{"field": "*", "agg": "count"}],
            "filters": [],
            "limit": 6,
        },
    },
    {
        "id": "open_todos",
        "label": "Open to-do items",
        "subtitle": "Staff work queue backlog",
        "snapshot_id": "WORKFLOW_QUEUE_RPT_CURR",
        "format": "number",
        "workstream": "common",
        "explore_report_id": "todo_by_status",
        "value": {
            "dimensions": [],
            "measures": [{"field": "*", "agg": "count"}],
            "filters": [{"field": "QUEUE_SOURCE", "op": "eq", "value": "TODO"}],
        },
        "trend": {
            "dimensions": ["ENTRY_STATUS_DESC"],
            "measures": [{"field": "*", "agg": "count"}],
            "filters": [{"field": "QUEUE_SOURCE", "op": "eq", "value": "TODO"}],
            "limit": 6,
        },
    },
    {
        "id": "total_debt",
        "label": "Total SA debt",
        "subtitle": "Service agreement arrears snapshot",
        "snapshot_id": "SA_AGED_BAL_RPT_CURR",
        "format": "currency",
        "workstream": "debt",
        "explore_report_id": "debt_by_class",
        "value": {
            "dimensions": [],
            "measures": [{"field": "TOTAL_DEBT", "agg": "sum"}],
            "filters": [],
        },
        "trend": {
            "dimensions": ["CUST_CL_DESC"],
            "measures": [{"field": "TOTAL_DEBT", "agg": "sum"}],
            "filters": [],
            "limit": 6,
        },
    },
]


def _kpis_for_workstreams(allowed_workstreams: list[str] | None) -> list[dict[str, Any]]:
    if not allowed_workstreams or "*" in allowed_workstreams:
        return EXECUTIVE_KPIS
    allowed = set(allowed_workstreams)
    return [kpi for kpi in EXECUTIVE_KPIS if kpi.get("workstream") in allowed]


def build_executive_summary(
    days: int = 30,
    *,
    compare: bool = False,
    extra_filters: list[dict[str, Any]] | None = None,
    allowed_workstreams: list[str] | None = None,
    organization_id: str | None = None,
) -> dict[str, Any]:
    (date_start, date_end), (prior_start, prior_end) = date_windows(days)
    period_label = f"Last {days} days"
    client_id = organization_id or "demo"
    kpi_defs = _kpis_for_workstreams(allowed_workstreams)

    if not organization_id or not demo_configured(organization_id):
        return {
            "client": client_id,
            "db_configured": False,
            "compare_enabled": compare,
            "period": {
                "start": date_start,
                "end": date_end,
                "label": period_label,
                "days": days,
            },
            "prior_period": {
                "start": prior_start,
                "end": prior_end,
                "label": f"Prior {days} days",
                "days": days,
            },
            "kpis": [
                {
                    **{
                        k: kpi[k]
                        for k in (
                            "id",
                            "label",
                            "subtitle",
                            "snapshot_id",
                            "format",
                            "workstream",
                            "explore_report_id",
                        )
                    },
                    "value": None,
                    "prior_value": None,
                    "change_pct": None,
                    "trend": [],
                    "error": "Demo database not configured",
                }
                for kpi in kpi_defs
            ],
        }

    kpis = [
        execute_kpi_definition(
            kpi,
            days=days,
            compare=compare,
            extra_filters=extra_filters,
            organization_id=organization_id,
        )
        for kpi in kpi_defs
    ]
    return {
        "client": client_id,
        "db_configured": True,
        "compare_enabled": compare,
        "period": {
            "start": date_start,
            "end": date_end,
            "label": period_label,
            "days": days,
        },
        "prior_period": {
            "start": prior_start,
            "end": prior_end,
            "label": f"Prior {days} days",
            "days": days,
        },
        "kpis": kpis,
    }
