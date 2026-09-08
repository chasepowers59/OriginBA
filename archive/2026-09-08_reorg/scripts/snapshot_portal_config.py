"""Portal UX config: date presets, large domains, workstream featured links."""

from __future__ import annotations

from typing import Any

LARGE_SNAPSHOTS = frozenset({"D1_MSRMT_RPT_CURR"})

PORTAL_DEFAULT_DATE: dict[str, Any] = {"kind": "days", "days": 180, "label": "Last 6 months"}

DEFAULT_DATE_PRESETS: dict[str, dict[str, Any]] = {
    "FT_RPT_CURR": {"kind": "days", "days": 180, "label": "Last 6 months"},
    "FT_GL_DISTRIBUTION_RPT_CURR": {"kind": "days", "days": 180, "label": "Last 6 months"},
    "BILLABLE_CHARGE_RPT_CURR": {"kind": "days", "days": 365, "label": "Last 12 months"},
    "BSEG_BILLED_USAGE_RPT_CURR": {"kind": "days", "days": 365, "label": "Last 12 months"},
    "BSEG_SQ_USAGE_RPT_CURR": {"kind": "days", "days": 365, "label": "Last 12 months"},
    "D1_MSRMT_RPT_CURR": {"kind": "days", "days": 30, "label": "Last 30 days"},
    "D1_USAGE_RPT_CURR": {"kind": "days", "days": 180, "label": "Last 6 months"},
    "D1_USAGE_SCALAR_DTL_RPT_CURR": {"kind": "days", "days": 180, "label": "Last 6 months"},
    "DEVICE_SP_RPT_CURR": {"kind": "days", "days": 365, "label": "Last 12 months"},
    "PAY_EVENT_RPT_CURR": {"kind": "days", "days": 180, "label": "Last 6 months"},
    "SA_AGED_BAL_RPT_CURR": {"kind": "days", "days": 730, "label": "Last 24 months"},
    "WO_PROC_RPT_CURR": {"kind": "days", "days": 365, "label": "Last 12 months"},
    "ACCT_CUSTOMER_RPT_CURR": {"kind": "days", "days": 365, "label": "Last 12 months"},
    "CASE_PREM_CONTACT_RPT_CURR": {"kind": "days", "days": 365, "label": "Last 12 months"},
    "NEW_SERVICE_PIPELINE_RPT_CURR": {"kind": "days", "days": 365, "label": "Last 12 months"},
    "FIELD_ACTIVITY_RPT_CURR": {"kind": "days", "days": 90, "label": "Last quarter"},
    "CREW_OPS_RPT_CURR": {"kind": "days", "days": 180, "label": "Last 6 months"},
    "OPS_EXCEPTION_RPT_CURR": {"kind": "days", "days": 90, "label": "Last quarter"},
    "WORKFLOW_QUEUE_RPT_CURR": {"kind": "days", "days": 90, "label": "Last quarter"},
}

WORKSTREAM_FEATURED: dict[str, list[dict[str, str]]] = {
    "finance": [
        {"snapshot_id": "FT_RPT_CURR", "report_id": "ft_by_type"},
        {"snapshot_id": "BILLABLE_CHARGE_RPT_CURR", "report_id": "volume_by_dimension"},
    ],
    "billing": [
        {"snapshot_id": "BSEG_BILLED_USAGE_RPT_CURR", "report_id": "amount_by_class"},
        {"snapshot_id": "BSEG_SQ_USAGE_RPT_CURR", "report_id": "volume_by_dimension"},
    ],
    "meter_ops": [
        {"snapshot_id": "D1_USAGE_RPT_CURR", "report_id": "volume_by_dimension"},
        {"snapshot_id": "DEVICE_SP_RPT_CURR", "report_id": "volume_by_dimension"},
    ],
    "cashiering": [
        {"snapshot_id": "PAY_EVENT_RPT_CURR", "report_id": "payments_by_method"},
    ],
    "debt": [
        {"snapshot_id": "SA_AGED_BAL_RPT_CURR", "report_id": "debt_by_class"},
        {"snapshot_id": "WO_PROC_RPT_CURR", "report_id": "volume_by_dimension"},
    ],
    "customer_ops": [
        {"snapshot_id": "ACCT_CUSTOMER_RPT_CURR", "report_id": "volume_by_dimension"},
        {"snapshot_id": "CASE_PREM_CONTACT_RPT_CURR", "report_id": "cases_by_type"},
    ],
    "new_services": [
        {"snapshot_id": "NEW_SERVICE_PIPELINE_RPT_CURR", "report_id": "volume_by_dimension"},
    ],
    "field_ops": [
        {"snapshot_id": "FIELD_ACTIVITY_RPT_CURR", "report_id": "volume_by_dimension"},
        {"snapshot_id": "CREW_OPS_RPT_CURR", "report_id": "volume_by_dimension"},
    ],
    "common": [
        {"snapshot_id": "OPS_EXCEPTION_RPT_CURR", "report_id": "excp_open"},
        {"snapshot_id": "WORKFLOW_QUEUE_RPT_CURR", "report_id": "todo_by_status"},
    ],
}

# Curated utility report packs — surfaced on /reports (no ad-hoc clutter).
REPORT_LIBRARY_PACKS: list[dict[str, Any]] = [
    {
        "id": "billing_cycle",
        "title": "Billing & cycle close",
        "description": "Revenue, usage, and segment-level billing for cycle review.",
        "audience": "Billing & rates",
        "reports": [
            {"snapshot_id": "BSEG_BILLED_USAGE_RPT_CURR", "report_id": "amount_by_class"},
            {"snapshot_id": "BSEG_BILLED_USAGE_RPT_CURR", "report_id": "amount_by_cycle"},
            {"snapshot_id": "BSEG_SQ_USAGE_RPT_CURR", "report_id": "usage_by_uom"},
            {"snapshot_id": "BSEG_SQ_USAGE_RPT_CURR", "report_id": "usage_by_class"},
        ],
    },
    {
        "id": "payments",
        "title": "Payments & cashiering",
        "description": "Payment volume and tender mix for cashiering oversight.",
        "audience": "Cashiering",
        "reports": [
            {"snapshot_id": "PAY_EVENT_RPT_CURR", "report_id": "payments_by_method"},
            {"snapshot_id": "PAY_EVENT_RPT_CURR", "report_id": "payments_by_status"},
        ],
    },
    {
        "id": "operations",
        "title": "Operations control",
        "description": "Exceptions, staff to-dos, and batch health.",
        "audience": "Operations",
        "reports": [
            {"snapshot_id": "OPS_EXCEPTION_RPT_CURR", "report_id": "excp_by_source"},
            {"snapshot_id": "OPS_EXCEPTION_RPT_CURR", "report_id": "excp_open"},
            {"snapshot_id": "WORKFLOW_QUEUE_RPT_CURR", "report_id": "todo_by_status"},
            {"snapshot_id": "WORKFLOW_QUEUE_RPT_CURR", "report_id": "batch_by_status"},
        ],
    },
    {
        "id": "customer_operations",
        "title": "Customer operations",
        "description": "Account populations and customer case workload.",
        "audience": "Customer operations",
        "reports": [
            {"snapshot_id": "ACCT_CUSTOMER_RPT_CURR", "report_id": "accounts_by_class"},
            {"snapshot_id": "CASE_PREM_CONTACT_RPT_CURR", "report_id": "cases_by_type"},
            {"snapshot_id": "CASE_PREM_CONTACT_RPT_CURR", "report_id": "cases_by_status"},
        ],
    },
    {
        "id": "collections",
        "title": "Collections & debt",
        "description": "Aged balances and write-off pipeline.",
        "audience": "Collections",
        "reports": [
            {"snapshot_id": "SA_AGED_BAL_RPT_CURR", "report_id": "debt_by_class"},
            {"snapshot_id": "SA_AGED_BAL_RPT_CURR", "report_id": "debt_by_sa_type"},
        ],
    },
    {
        "id": "field_ops",
        "title": "Field operations",
        "description": "Field activity volume and new service pipeline.",
        "audience": "Field operations",
        "reports": [
            {"snapshot_id": "FIELD_ACTIVITY_RPT_CURR", "report_id": "volume_by_dimension"},
            {"snapshot_id": "NEW_SERVICE_PIPELINE_RPT_CURR", "report_id": "pipeline_by_status"},
            {"snapshot_id": "NEW_SERVICE_PIPELINE_RPT_CURR", "report_id": "pipeline_by_type"},
        ],
    },
    {
        "id": "finance",
        "title": "Finance",
        "description": "Transaction mix and GL posting status.",
        "audience": "Finance",
        "reports": [
            {"snapshot_id": "FT_RPT_CURR", "report_id": "ft_by_type"},
            {"snapshot_id": "FT_RPT_CURR", "report_id": "ft_gl_status"},
        ],
    },
]
