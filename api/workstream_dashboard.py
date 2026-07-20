"""Per-workstream KPI dashboard definitions."""

from __future__ import annotations

from typing import Any

from api.demo_db import demo_configured
from api.kpi_runner import date_windows, execute_kpi_definition
from api.snapshot_catalog import load_catalog


WORKSTREAM_KPIS: dict[str, list[dict[str, Any]]] = {
    "finance": [
        {
            "id": "ft_dollars",
            "label": "Transaction dollars",
            "subtitle": "Sum of financial transaction amounts",
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
                "limit": 5,
            },
        },
        {
            "id": "gl_lines",
            "label": "GL distribution lines",
            "subtitle": "Posting detail row count",
            "snapshot_id": "FT_GL_DISTRIBUTION_RPT_CURR",
            "format": "number",
            "workstream": "finance",
            "explore_report_id": None,
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["GL_DISTRIB_STATUS_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
        {
            "id": "billable_charges",
            "label": "Billable charge dollars",
            "subtitle": "Charge line amounts",
            "snapshot_id": "BILLABLE_CHARGE_RPT_CURR",
            "format": "currency",
            "workstream": "finance",
            "explore_report_id": None,
            "value": {
                "dimensions": [],
                "measures": [{"field": "CHARGE_AMT", "agg": "sum"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["BILL_STAT_DESC"],
                "measures": [{"field": "CHARGE_AMT", "agg": "sum"}],
                "filters": [],
                "limit": 5,
            },
        },
    ],
    "billing": [
        {
            "id": "billed_revenue",
            "label": "Billed revenue",
            "subtitle": "Segment-level billed dollars",
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
                "limit": 5,
            },
        },
        {
            "id": "billed_segments",
            "label": "Bill segments",
            "subtitle": "Completed segment count",
            "snapshot_id": "BSEG_BILLED_USAGE_RPT_CURR",
            "format": "number",
            "workstream": "billing",
            "explore_report_id": "amount_by_cycle",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["BILL_BILL_CYC_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
        {
            "id": "sq_usage_rows",
            "label": "Usage determinant rows",
            "subtitle": "SQ detail population — filter UOM for totals",
            "snapshot_id": "BSEG_SQ_USAGE_RPT_CURR",
            "format": "number",
            "workstream": "billing",
            "explore_report_id": "usage_by_uom",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["UOM_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
    ],
    "meter_ops": [
        {
            "id": "measurements",
            "label": "Measurements",
            "subtitle": "Processed measurement count",
            "snapshot_id": "D1_MSRMT_RPT_CURR",
            "format": "number",
            "workstream": "meter_ops",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["MSRMT_COND_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
        {
            "id": "usage_records",
            "label": "Usage records",
            "subtitle": "Interval usage population",
            "snapshot_id": "D1_USAGE_RPT_CURR",
            "format": "number",
            "workstream": "meter_ops",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["BO_STATUS_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
        {
            "id": "scalar_quantity",
            "label": "Scalar quantity total",
            "subtitle": "Summed final quantity at scalar grain",
            "snapshot_id": "D1_USAGE_SCALAR_DTL_RPT_CURR",
            "format": "number",
            "workstream": "meter_ops",
            "value": {
                "dimensions": [],
                "measures": [{"field": "FINAL_QUANTITY", "agg": "sum"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["UOM_DESC"],
                "measures": [{"field": "FINAL_QUANTITY", "agg": "sum"}],
                "filters": [],
                "limit": 5,
            },
        },
        {
            "id": "devices",
            "label": "Devices tracked",
            "subtitle": "Device asset population",
            "snapshot_id": "DEVICE_SP_RPT_CURR",
            "format": "number",
            "workstream": "meter_ops",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["DVC_STATUS_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
    ],
    "cashiering": [
        {
            "id": "payment_dollars",
            "label": "Payment dollars",
            "subtitle": "Total payment amount",
            "snapshot_id": "PAY_EVENT_RPT_CURR",
            "format": "currency",
            "workstream": "cashiering",
            "explore_report_id": "payments_by_method",
            "value": {
                "dimensions": [],
                "measures": [{"field": "PAY_AMT", "agg": "sum"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["PAY_METHOD_DESC"],
                "measures": [{"field": "PAY_AMT", "agg": "sum"}],
                "filters": [],
                "limit": 5,
            },
        },
        {
            "id": "payment_events",
            "label": "Payment events",
            "subtitle": "Count of payment transactions",
            "snapshot_id": "PAY_EVENT_RPT_CURR",
            "format": "number",
            "workstream": "cashiering",
            "explore_report_id": "payments_by_status",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["PAY_STATUS_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
    ],
    "debt": [
        {
            "id": "total_debt",
            "label": "Total SA debt",
            "subtitle": "Arrears dollars on service agreements",
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
                "limit": 5,
            },
        },
        {
            "id": "debt_accounts",
            "label": "Accounts with debt",
            "subtitle": "Service agreements in arrears population",
            "snapshot_id": "SA_AGED_BAL_RPT_CURR",
            "format": "number",
            "workstream": "debt",
            "explore_report_id": "debt_by_sa_type",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["SA_TYPE_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
        {
            "id": "writeoff_processes",
            "label": "Write-off processes",
            "subtitle": "Active write-off pipeline",
            "snapshot_id": "WO_PROC_RPT_CURR",
            "format": "number",
            "workstream": "debt",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["WO_PROC_STATUS_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
    ],
    "customer_ops": [
        {
            "id": "cases_opened",
            "label": "Cases opened",
            "subtitle": "Customer case volume",
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
                "dimensions": ["CASE_STATUS_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
        {
            "id": "accounts",
            "label": "Accounts",
            "subtitle": "Account master population",
            "snapshot_id": "ACCT_CUSTOMER_RPT_CURR",
            "format": "number",
            "workstream": "customer_ops",
            "explore_report_id": "accounts_by_class",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["CUST_CL_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
    ],
    "new_services": [
        {
            "id": "pipeline_count",
            "label": "Pipeline SAs",
            "subtitle": "New connection service agreements",
            "snapshot_id": "NEW_SERVICE_PIPELINE_RPT_CURR",
            "format": "number",
            "workstream": "new_services",
            "explore_report_id": "pipeline_by_status",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["SA_STATUS_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
        {
            "id": "pipeline_by_type",
            "label": "By SA type",
            "subtitle": "Pipeline mix",
            "snapshot_id": "NEW_SERVICE_PIPELINE_RPT_CURR",
            "format": "number",
            "workstream": "new_services",
            "explore_report_id": "pipeline_by_type",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["SA_TYPE_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
    ],
    "field_ops": [
        {
            "id": "field_activities",
            "label": "Field activities",
            "subtitle": "BODA field work volume",
            "snapshot_id": "FIELD_ACTIVITY_RPT_CURR",
            "format": "number",
            "workstream": "field_ops",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["FA_STATUS_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
        {
            "id": "crews",
            "label": "Crew records",
            "subtitle": "Crew operations population",
            "snapshot_id": "CREW_OPS_RPT_CURR",
            "format": "number",
            "workstream": "field_ops",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
            },
            "trend": {
                "dimensions": ["CREW_STATUS_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "limit": 5,
            },
        },
    ],
    "common": [
        {
            "id": "open_exceptions",
            "label": "Open exceptions",
            "subtitle": "Operational exception backlog",
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
                "limit": 5,
            },
        },
        {
            "id": "open_todos",
            "label": "Open to-do items",
            "subtitle": "Staff work queue",
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
                "limit": 5,
            },
        },
        {
            "id": "batch_jobs",
            "label": "Batch threads",
            "subtitle": "Overnight batch monitor",
            "snapshot_id": "WORKFLOW_QUEUE_RPT_CURR",
            "format": "number",
            "workstream": "common",
            "explore_report_id": "batch_by_status",
            "value": {
                "dimensions": [],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [{"field": "QUEUE_SOURCE", "op": "eq", "value": "BATCH"}],
            },
            "trend": {
                "dimensions": ["BATCH_RUN_STATUS_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [{"field": "QUEUE_SOURCE", "op": "eq", "value": "BATCH"}],
                "limit": 5,
            },
        },
    ],
}


def build_workstream_summary(
    workstream_id: str,
    days: int = 30,
    *,
    compare: bool = False,
    extra_filters: list[dict[str, Any]] | None = None,
    organization_id: str | None = None,
) -> dict[str, Any]:
    catalog = load_catalog()
    labels = catalog.get("workstream_labels", {})
    ws = workstream_id.lower()
    kpis_def = WORKSTREAM_KPIS.get(ws, [])

    (date_start, date_end), (prior_start, prior_end) = date_windows(days)
    period_label = f"Last {days} days"
    client_id = organization_id or catalog.get("client", "demo")

    if ws not in WORKSTREAM_KPIS:
        return {"error": f"Unknown workstream: {workstream_id}"}

    if not organization_id or not demo_configured(organization_id):
        return {
            "client": client_id,
            "db_configured": False,
            "compare_enabled": compare,
            "workstream": ws,
            "workstream_label": labels.get(ws, ws),
            "period": {"start": date_start, "end": date_end, "label": period_label, "days": days},
            "prior_period": {
                "start": prior_start,
                "end": prior_end,
                "label": f"Prior {days} days",
                "days": days,
            },
            "kpis": [
                {
                    **{k: kpi[k] for k in ("id", "label", "subtitle", "snapshot_id", "format", "explore_report_id")},
                    "workstream": ws,
                    "value": None,
                    "prior_value": None,
                    "change_pct": None,
                    "trend": [],
                    "error": "Demo database not configured",
                }
                for kpi in kpis_def
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
        for kpi in kpis_def
    ]
    return {
        "client": client_id,
        "db_configured": True,
        "compare_enabled": compare,
        "workstream": ws,
        "workstream_label": labels.get(ws, ws),
        "period": {"start": date_start, "end": date_end, "label": period_label, "days": days},
        "prior_period": {
            "start": prior_start,
            "end": prior_end,
            "label": f"Prior {days} days",
            "days": days,
        },
        "kpis": kpis,
    }
