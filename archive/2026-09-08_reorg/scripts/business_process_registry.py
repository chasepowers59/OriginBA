"""
Business processes per workstream — navigation and field guidance for the analytics portal.

Processes group ready-to-run reports and limit ad-hoc builder fields to what is relevant
for that utility workflow (aligned to the Standard Offering catalog).
"""

from __future__ import annotations

from typing import Any

# Each process: workstream, label, description, and guided entries (snapshot + optional report + fields).
BUSINESS_PROCESSES: list[dict[str, Any]] = [
    # ── Finance ──
    {
        "id": "financial_transactions",
        "workstream": "finance",
        "label": "Financial transactions",
        "description": "Transaction mix, posting health, and billed revenue trends at FT header grain.",
        "entries": [
            {
                "snapshot_id": "FT_RPT_CURR",
                "report_id": "ft_by_type",
                "dimensions": [
                    "FT_TYPE_FLG_DESC",
                    "GL_DISTRIB_STATUS_DESC",
                    "ACCT_MGMT_GRP_DESC",
                    "CUST_CL_DESC",
                ],
                "measures": ["CUR_AMT", "*"],
                "scope_fields": ["ACCT_MGMT_GRP_DESC"],
            },
            {
                "snapshot_id": "FT_RPT_CURR",
                "report_id": "ft_gl_status",
                "dimensions": ["GL_DISTRIB_STATUS_DESC", "FT_TYPE_FLG_DESC"],
                "measures": ["*", "CUR_AMT"],
                "scope_fields": ["ACCT_MGMT_GRP_DESC"],
            },
        ],
    },
    {
        "id": "gl_distribution",
        "workstream": "finance",
        "label": "GL distribution",
        "description": "GL account and distribution-code posting detail — not FT header totals.",
        "entries": [
            {
                "snapshot_id": "FT_GL_DISTRIBUTION_RPT_CURR",
                "dimensions": [
                    "GL_DISTRIB_STATUS_DESC",
                    "FT_TYPE_FLG_DESC",
                    "DST_DESC",
                    "GL_DIVISION_DESC",
                ],
                "measures": ["GL_AMOUNT", "*"],
                "scope_fields": ["ACCT_MGMT_GRP_DESC"],
            },
        ],
    },
    {
        "id": "billable_charges",
        "workstream": "finance",
        "label": "Billable charges",
        "description": "Unbilled and billable charge lines before they post to a bill segment.",
        "entries": [
            {
                "snapshot_id": "BILLABLE_CHARGE_RPT_CURR",
                "dimensions": ["BILLABLE_CHG_STAT_DESC", "SA_TYPE_DESC", "CUST_CL_DESC"],
                "measures": ["CHARGE_AMT", "*"],
                "scope_fields": [],
            },
        ],
    },
    # ── Billing ──
    {
        "id": "billed_revenue",
        "workstream": "billing",
        "label": "Billed revenue",
        "description": "Billed dollars at completed bill-segment grain.",
        "entries": [
            {
                "snapshot_id": "BSEG_BILLED_USAGE_RPT_CURR",
                "report_id": "amount_by_class",
                "dimensions": [
                    "CUST_CL_DESC",
                    "BILL_BILL_CYC_DESC",
                    "BSEG_STAT_DESC",
                    "SA_TYPE_DESC",
                ],
                "measures": ["TOTAL_CALC_AMT", "*"],
                "scope_fields": ["ACCT_MGMT_GRP_DESC", "CUST_CL_DESC"],
            },
            {
                "snapshot_id": "BSEG_BILLED_USAGE_RPT_CURR",
                "report_id": "amount_by_cycle",
                "dimensions": ["BILL_BILL_CYC_DESC", "CUST_CL_DESC"],
                "measures": ["TOTAL_CALC_AMT", "*"],
                "scope_fields": ["ACCT_MGMT_GRP_DESC", "CUST_CL_DESC"],
            },
        ],
    },
    {
        "id": "billed_usage",
        "workstream": "billing",
        "label": "Billed usage",
        "description": "Determinant-level billed quantity — filter by unit of measure for accurate totals.",
        "entries": [
            {
                "snapshot_id": "BSEG_SQ_USAGE_RPT_CURR",
                "report_id": "usage_by_uom",
                "dimensions": ["UOM_DESC", "CUST_CL_DESC", "TOU_DESC", "SQI_CD"],
                "measures": ["TOTAL_BILL_SQ", "*"],
                "scope_fields": ["UOM_DESC", "CUST_CL_DESC"],
            },
            {
                "snapshot_id": "BSEG_SQ_USAGE_RPT_CURR",
                "report_id": "usage_by_class",
                "dimensions": ["CUST_CL_DESC", "UOM_DESC"],
                "measures": ["TOTAL_BILL_SQ", "*"],
                "scope_fields": ["UOM_DESC", "CUST_CL_DESC"],
            },
        ],
    },
    # ── Meter operations ──
    {
        "id": "measurements",
        "workstream": "meter_ops",
        "label": "Measurements",
        "description": "Final processed reads — condition, status, and measurement quality.",
        "entries": [
            {
                "snapshot_id": "D1_MSRMT_RPT_CURR",
                "dimensions": ["MSRMT_USE_DESC", "MSRMT_COND_DESC", "MSRMT_BO_STATUS_DESC"],
                "measures": ["*", "MSRMT_VAL"],
                "scope_fields": [],
            },
        ],
    },
    {
        "id": "usage_processing",
        "workstream": "meter_ops",
        "label": "Usage processing",
        "description": "Usage business-object status and service-point context.",
        "entries": [
            {
                "snapshot_id": "D1_USAGE_RPT_CURR",
                "dimensions": ["BO_STATUS_DESC", "D1_USG_CAL_TYPE_DESC", "SA_TYPE_DESC"],
                "measures": ["*"],
                "scope_fields": [],
            },
            {
                "snapshot_id": "D1_USAGE_SCALAR_DTL_RPT_CURR",
                "dimensions": ["D1_UOM_DESC", "D1_TOU_DESC", "BO_STATUS_DESC"],
                "measures": ["QUANTITY", "FINAL_QUANTITY", "*"],
                "scope_fields": [],
            },
        ],
    },
    {
        "id": "device_assets",
        "workstream": "meter_ops",
        "label": "Devices & service points",
        "description": "Meter install, removal, and device lifecycle at service point grain.",
        "entries": [
            {
                "snapshot_id": "DEVICE_SP_RPT_CURR",
                "dimensions": ["BO_STATUS_DESC", "DEVICE_CONFIG_TYPE_CD", "D1_SP_TYPE_DESC"],
                "measures": ["*"],
                "scope_fields": [],
            },
        ],
    },
    # ── Cashiering ──
    {
        "id": "tender",
        "workstream": "cashiering",
        "label": "Tender",
        "description": "Payment tender mix, channel, and tender-type distribution.",
        "entries": [
            {
                "snapshot_id": "PAY_EVENT_RPT_CURR",
                "report_id": "payments_by_method",
                "dimensions": [
                    "SOLE_TENDER_TYPE_DESC",
                    "PRIMARY_TNDR_SOURCE_DESC",
                    "PAY_STATUS_DESC",
                ],
                "measures": ["PAY_AMT", "EVENT_TENDER_AMT", "*"],
                "scope_fields": ["SOLE_TENDER_TYPE_DESC"],
            },
        ],
    },
    {
        "id": "deposit_tender_control",
        "workstream": "cashiering",
        "label": "Deposit & tender control",
        "description": "Daily close, deposit control status, and tender control reconciliation.",
        "entries": [
            {
                "snapshot_id": "PAY_EVENT_RPT_CURR",
                "report_id": "deposit_control_status",
                "dimensions": [
                    "PRIMARY_DEP_CTL_STATUS_DESC",
                    "PRIMARY_TNDR_CTL_STATUS_DESC",
                ],
                "measures": [
                    "PAY_AMT",
                    "EVENT_DEP_AMT",
                    "PRIMARY_DEP_CTL_END_BALANCE",
                    "EVENT_DEP_CTL_COUNT",
                    "EVENT_TNDR_CTL_COUNT",
                    "*",
                ],
                "scope_fields": [],
            },
            {
                "snapshot_id": "PAY_EVENT_RPT_CURR",
                "report_id": "tender_control_status",
                "dimensions": ["PRIMARY_TNDR_CTL_STATUS_DESC", "PRIMARY_TNDR_SOURCE_DESC"],
                "measures": ["PAY_AMT", "EVENT_TENDER_AMT", "EVENT_TNDR_CTL_COUNT", "*"],
                "scope_fields": [],
            },
        ],
    },
    {
        "id": "payment_activity",
        "workstream": "cashiering",
        "label": "Payment activity",
        "description": "Payment event volume and status for cashiering oversight.",
        "entries": [
            {
                "snapshot_id": "PAY_EVENT_RPT_CURR",
                "report_id": "payments_by_status",
                "dimensions": ["PAY_STATUS_DESC", "CAN_RSN_DESC"],
                "measures": ["PAY_AMT", "*"],
                "scope_fields": ["SOLE_TENDER_TYPE_DESC"],
            },
        ],
    },
    {
        "id": "pay_plans",
        "workstream": "cashiering",
        "label": "Pay plans",
        "description": "Payment plan presence and status on payment events.",
        "entries": [
            {
                "snapshot_id": "PAY_EVENT_RPT_CURR",
                "report_id": "pay_plans_by_status",
                "dimensions": ["PRIMARY_PP_STAT_DESC", "PRIMARY_PP_TYPE_DESC"],
                "measures": ["PAY_AMT", "ACTIVE_PP_COUNT", "ACCT_PP_COUNT", "*"],
                "scope_fields": [],
            },
        ],
    },
    # ── Collections & debt ──
    {
        "id": "aged_balances",
        "workstream": "debt",
        "label": "Aged balances",
        "description": "SA-level arrears and aging buckets for collections prioritization.",
        "entries": [
            {
                "snapshot_id": "SA_AGED_BAL_RPT_CURR",
                "report_id": "debt_by_class",
                "dimensions": ["CUST_CL_DESC", "SA_TYPE_DESC", "DEBT_CL_DESC"],
                "measures": [
                    "TOTAL_DEBT",
                    "DEBT_0_30",
                    "DEBT_31_60",
                    "DEBT_61_90",
                    "DEBT_OVER_90",
                    "*",
                ],
                "scope_fields": ["CUST_CL_DESC", "SA_TYPE_DESC"],
            },
            {
                "snapshot_id": "SA_AGED_BAL_RPT_CURR",
                "report_id": "debt_by_sa_type",
                "dimensions": ["SA_TYPE_DESC", "CUST_CL_DESC"],
                "measures": ["TOTAL_DEBT", "*"],
                "scope_fields": ["CUST_CL_DESC", "SA_TYPE_DESC"],
            },
        ],
    },
    {
        "id": "write_offs",
        "workstream": "debt",
        "label": "Write-offs",
        "description": "Write-off process workload, status, and pipeline monitoring.",
        "entries": [
            {
                "snapshot_id": "WO_PROC_RPT_CURR",
                "dimensions": ["WO_STATUS_DESC", "WO_PROC_TMPL_DESC", "UNCOLL_PROC_STAT_DESC"],
                "measures": ["*"],
                "scope_fields": [],
            },
        ],
    },
    # ── Customer operations ──
    {
        "id": "account_population",
        "workstream": "customer_ops",
        "label": "Account population",
        "description": "Account and customer master populations for service operations.",
        "entries": [
            {
                "snapshot_id": "ACCT_CUSTOMER_RPT_CURR",
                "report_id": "accounts_by_class",
                "dimensions": ["CUST_CL_DESC", "ACCT_MGMT_GRP_DESC", "CIS_DIVISION_DESC"],
                "measures": ["*"],
                "scope_fields": [],
            },
            {
                "snapshot_id": "ACCT_CUSTOMER_RPT_CURR",
                "report_id": "accounts_by_bu",
                "dimensions": ["ACCT_MGMT_GRP_DESC", "CUST_CL_DESC"],
                "measures": ["*"],
                "scope_fields": [],
            },
        ],
    },
    {
        "id": "case_management",
        "workstream": "customer_ops",
        "label": "Case management",
        "description": "Customer case volume, status, and service workload.",
        "entries": [
            {
                "snapshot_id": "CASE_PREM_CONTACT_RPT_CURR",
                "report_id": "cases_by_status",
                "dimensions": [
                    "CASE_STATUS_DESC",
                    "CASE_TYPE_DESC",
                    "ACCT_CIS_DIVISION",
                    "ACCT_MGMT_GRP_DESC",
                ],
                "measures": ["*"],
                "scope_fields": ["ACCT_CIS_DIVISION", "ACCT_MGMT_GRP_DESC"],
            },
            {
                "snapshot_id": "CASE_PREM_CONTACT_RPT_CURR",
                "report_id": "cases_by_type",
                "dimensions": ["CASE_TYPE_DESC", "CASE_STATUS_DESC"],
                "measures": ["*"],
                "scope_fields": ["ACCT_CIS_DIVISION", "ACCT_MGMT_GRP_DESC"],
            },
        ],
    },
    # ── New services ──
    {
        "id": "start_service_pipeline",
        "workstream": "new_services",
        "label": "Start-service pipeline",
        "description": "Pending and recent new connection workload by status and SA type.",
        "entries": [
            {
                "snapshot_id": "NEW_SERVICE_PIPELINE_RPT_CURR",
                "report_id": "pipeline_by_status",
                "dimensions": ["SA_STATUS_DESC", "SA_TYPE_DESC"],
                "measures": ["*"],
                "scope_fields": [],
            },
            {
                "snapshot_id": "NEW_SERVICE_PIPELINE_RPT_CURR",
                "report_id": "pipeline_by_type",
                "dimensions": ["SA_TYPE_DESC", "SA_STATUS_DESC"],
                "measures": ["*"],
                "scope_fields": [],
            },
        ],
    },
    # ── Field operations ──
    {
        "id": "field_activities",
        "workstream": "field_ops",
        "label": "Field activities",
        "description": "Field work orders by status, type, and completion.",
        "entries": [
            {
                "snapshot_id": "FIELD_ACTIVITY_RPT_CURR",
                "dimensions": ["FA_INT_STATUS_DESC", "FIELD_TASK_TYPE_DESC", "ACTIVITY_TYPE_DESC"],
                "measures": ["*"],
                "scope_fields": [],
            },
        ],
    },
    {
        "id": "crew_operations",
        "workstream": "field_ops",
        "label": "Crew operations",
        "description": "Crew status and rolled-up field activity metrics.",
        "entries": [
            {
                "snapshot_id": "CREW_OPS_RPT_CURR",
                "dimensions": ["BO_STATUS_DESC", "CREW_TYPE_DESC", "LATEST_FA_STATUS_DESC"],
                "measures": ["*"],
                "scope_fields": [],
            },
        ],
    },
    # ── Common / operations ──
    {
        "id": "billing_meter_exceptions",
        "workstream": "common",
        "label": "Billing & meter exceptions",
        "description": "Unified exception triage across billing, usage, and validation sources.",
        "entries": [
            {
                "snapshot_id": "OPS_EXCEPTION_RPT_CURR",
                "report_id": "excp_by_source",
                "dimensions": [
                    "EXCP_SOURCE",
                    "EXCP_SEVERITY_DESC",
                    "OPEN_CLOSE_DESC",
                    "EXCP_TYPE_DESC",
                ],
                "measures": ["*"],
                "scope_fields": ["SP_DIVISION_DESC", "ACCT_MGMT_GRP_DESC"],
            },
            {
                "snapshot_id": "OPS_EXCEPTION_RPT_CURR",
                "report_id": "excp_open",
                "dimensions": ["EXCP_SEVERITY_DESC", "EXCP_SOURCE"],
                "measures": ["*"],
                "scope_fields": ["SP_DIVISION_DESC", "ACCT_MGMT_GRP_DESC"],
            },
        ],
    },
    {
        "id": "workflow_and_batch",
        "workstream": "common",
        "label": "Workflow & batch",
        "description": "Staff to-do backlog and batch job health monitoring.",
        "entries": [
            {
                "snapshot_id": "WORKFLOW_QUEUE_RPT_CURR",
                "report_id": "todo_by_status",
                "dimensions": ["ENTRY_STATUS_DESC", "TD_TYPE_DESC", "ROLE_DESC"],
                "measures": ["*"],
                "scope_fields": [],
            },
            {
                "snapshot_id": "WORKFLOW_QUEUE_RPT_CURR",
                "report_id": "batch_by_status",
                "dimensions": ["BATCH_RUN_STATUS_DESC", "BATCH_CD"],
                "measures": ["*"],
                "scope_fields": [],
            },
        ],
    },
]
