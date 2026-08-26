"""Per-workstream KPI dashboard definitions."""

from __future__ import annotations

from typing import Any

from api.demo_db import demo_configured
from api.warehouse_db import warehouse_configured
from api.kpi_runner import date_windows, execute_kpi_definition
from api.snapshot_catalog import load_catalog


WORKSTREAM_KPIS: dict[str, list[dict[str, Any]]] = {
    # DBT-CANVAS section dashboards (2026-08-26): every snapshot is a governed
    # reporting canvas (schema=reporting -> per-tenant warehouse routing). These are
    # the curated end-user sections: Billing & Revenue (billing), Payments
    # (cashiering), Collections (debt), Usage & Devices (meter_ops), Service Orders
    # (field_ops), Customer Operations (customer_ops), Finance (finance). Filters
    # use base-product constants or canvas flags only -- never client config.
    "billing": [
        {"id": "billed_amount", "label": "Billed amount", "subtitle": "Frozen bill segments",
         "snapshot_id": "rpt_bill_segment", "format": "currency", "workstream": "billing",
         "explore_report_id": None, "date_field": "Bill Date",
         "value": {"dimensions": [], "measures": [{"field": "Billed Amount", "agg": "sum"}],
                   "filters": [{"field": "Is Frozen", "op": "eq", "value": True}]},
         "trend": {"dimensions": ["SA Type"], "measures": [{"field": "Billed Amount", "agg": "sum"}],
                   "filters": [{"field": "Is Frozen", "op": "eq", "value": True}], "limit": 6}},
        {"id": "bills_completed", "label": "Bills completed", "subtitle": "Cycled throughput",
         "snapshot_id": "rpt_bill", "format": "number", "workstream": "billing",
         "explore_report_id": None, "date_field": "Window Start Date",
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Completed", "op": "eq", "value": True}]},
         "trend": {"dimensions": ["Bill Cycle"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Completed", "op": "eq", "value": True}], "limit": 6}},
        {"id": "stuck_bills", "label": "Bills stuck open", "subtitle": "Window open over 30 days",
         "snapshot_id": "rpt_bill", "format": "number", "workstream": "billing",
         "explore_report_id": None, "windowless": True,
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Days Bill Open", "op": "gte", "value": 30}]},
         "trend": {"dimensions": ["Bill Cycle"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Days Bill Open", "op": "gte", "value": 30}], "limit": 6}},
        {"id": "cancelled_segments", "label": "Cancelled segments", "subtitle": "Cancel/rebill activity",
         "snapshot_id": "rpt_bill_segment", "format": "number", "workstream": "billing",
         "explore_report_id": None, "date_field": "Bill Date",
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Cancelled", "op": "eq", "value": True}]},
         "trend": {"dimensions": ["SA Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Cancelled", "op": "eq", "value": True}], "limit": 6}},
    ],
    "cashiering": [
        {"id": "payments_collected", "label": "Payments collected", "subtitle": "Frozen pay segments",
         "snapshot_id": "rpt_payment", "format": "currency", "workstream": "cashiering",
         "explore_report_id": None, "date_field": "Payment Date",
         "value": {"dimensions": [], "measures": [{"field": "Pay Segment Amount", "agg": "sum"}], "filters": []},
         "trend": {"dimensions": ["Payment Status"], "measures": [{"field": "Pay Segment Amount", "agg": "sum"}],
                   "filters": [], "limit": 6}},
        {"id": "tender_amount", "label": "Tenders received", "subtitle": "By tender type",
         "snapshot_id": "rpt_payment_tender", "format": "currency", "workstream": "cashiering",
         "explore_report_id": None, "date_field": "Payment Date",
         "value": {"dimensions": [], "measures": [{"field": "Tender Amount", "agg": "sum"}], "filters": []},
         "trend": {"dimensions": ["Tender Type"], "measures": [{"field": "Tender Amount", "agg": "sum"}],
                   "filters": [], "limit": 6}},
        {"id": "unbalanced_events", "label": "Unbalanced pay events", "subtitle": "Cashiering exceptions",
         "snapshot_id": "rpt_payment", "format": "number", "workstream": "cashiering",
         "explore_report_id": None, "windowless": True,
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Event Is Balanced", "op": "eq", "value": False}]},
         "trend": {"dimensions": ["Payment Status"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Event Is Balanced", "op": "eq", "value": False}], "limit": 6}},
        {"id": "cancelled_tenders", "label": "Cancelled tenders", "subtitle": "Reversals in window",
         "snapshot_id": "rpt_payment_tender", "format": "number", "workstream": "cashiering",
         "explore_report_id": None, "date_field": "Payment Date",
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Cancelled", "op": "eq", "value": True}]},
         "trend": {"dimensions": ["Tender Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Cancelled", "op": "eq", "value": True}], "limit": 6}},
    ],
    "debt": [
        {"id": "accounts_receivable", "label": "Accounts receivable", "subtitle": "Total SA balances",
         "snapshot_id": "rpt_sa_aged_balance", "format": "currency", "workstream": "debt",
         "explore_report_id": None, "windowless": True,
         "value": {"dimensions": [], "measures": [{"field": "Total Balance", "agg": "sum"}], "filters": []},
         "trend": {"dimensions": ["Oldest Debt Band"], "measures": [{"field": "Total Balance", "agg": "sum"}],
                   "filters": [], "limit": 6}},
        {"id": "past_due", "label": "Past-due balance", "subtitle": "SAs past due",
         "snapshot_id": "rpt_sa_aged_balance", "format": "currency", "workstream": "debt",
         "explore_report_id": None, "windowless": True,
         "value": {"dimensions": [], "measures": [{"field": "Total Balance", "agg": "sum"}],
                   "filters": [{"field": "Is Past Due", "op": "eq", "value": True}]},
         "trend": {"dimensions": ["Oldest Debt Band"], "measures": [{"field": "Total Balance", "agg": "sum"}],
                   "filters": [{"field": "Is Past Due", "op": "eq", "value": True}], "limit": 6}},
        {"id": "collection_processes", "label": "Collection processes", "subtitle": "Started in window",
         "snapshot_id": "rpt_debt_process", "format": "number", "workstream": "debt",
         "explore_report_id": None, "date_field": "Process Created",
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
         "trend": {"dimensions": ["Process Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [], "limit": 6}},
        {"id": "active_pay_plans", "label": "Active pay plans", "subtitle": "Currently in force",
         "snapshot_id": "rpt_pay_plan", "format": "number", "workstream": "debt",
         "explore_report_id": None, "windowless": True,
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Active", "op": "eq", "value": True}]},
         "trend": {"dimensions": ["Pay Plan Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Active", "op": "eq", "value": True}], "limit": 6}},
        {"id": "broken_pay_plans", "label": "Broken pay plans", "subtitle": "Kept vs broken watch",
         "snapshot_id": "rpt_pay_plan", "format": "number", "workstream": "debt",
         "explore_report_id": None, "windowless": True,
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Broken", "op": "eq", "value": True}]},
         "trend": {"dimensions": ["Pay Plan Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Broken", "op": "eq", "value": True}], "limit": 6}},
    ],
    "meter_ops": [
        {"id": "measurements", "label": "Measurements", "subtitle": "All conditions, in window",
         "snapshot_id": "rpt_measurement", "format": "number", "workstream": "meter_ops",
         "explore_report_id": None, "date_field": "Measurement Date/Time",
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
         "trend": {"dimensions": ["Device Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [], "limit": 6}},
        {"id": "estimated_measurements", "label": "Estimated measurements", "subtitle": "Estimation pressure",
         "snapshot_id": "rpt_measurement", "format": "number", "workstream": "meter_ops",
         "explore_report_id": None, "date_field": "Measurement Date/Time",
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Estimated Measurement", "op": "eq", "value": True}]},
         "trend": {"dimensions": ["Device Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Estimated Measurement", "op": "eq", "value": True}], "limit": 6}},
        {"id": "usage_transactions", "label": "Usage transactions", "subtitle": "Bill determinants processed",
         "snapshot_id": "rpt_usage_txn", "format": "number", "workstream": "meter_ops",
         "explore_report_id": None, "date_field": "Start Date/Time",
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
         "trend": {"dimensions": ["Usage Status Code"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [], "limit": 6}},
        {"id": "never_registered", "label": "Never registered at head-end", "subtitle": "AMI rollout worklist",
         "snapshot_id": "rpt_device_asset", "format": "number", "workstream": "meter_ops",
         "explore_report_id": None, "windowless": True,
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Never Registered At Head-End", "op": "eq", "value": True}]},
         "trend": {"dimensions": ["Device Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Never Registered At Head-End", "op": "eq", "value": True}], "limit": 6}},
        {"id": "devices_dark_60d", "label": "Devices off 60+ days", "subtitle": "Reconnect aging",
         "snapshot_id": "rpt_device_asset", "format": "number", "workstream": "meter_ops",
         "explore_report_id": None, "windowless": True,
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Days Switched Off", "op": "gte", "value": 60}]},
         "trend": {"dimensions": ["Device Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Days Switched Off", "op": "gte", "value": 60}], "limit": 6}},
    ],
    "field_ops": [
        {"id": "field_activities", "label": "Field activities", "subtitle": "MDM activity volume",
         "snapshot_id": "rpt_field_activity", "format": "number", "workstream": "field_ops",
         "explore_report_id": None, "date_field": "Event Date/Time",
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
         "trend": {"dimensions": ["Activity Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [], "limit": 6}},
        {"id": "open_todos", "label": "Open To Do entries", "subtitle": "The operational queue",
         "snapshot_id": "rpt_todo", "format": "number", "workstream": "field_ops",
         "explore_report_id": None, "windowless": True,
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Complete", "op": "eq", "value": False}]},
         "trend": {"dimensions": ["To Do Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Complete", "op": "eq", "value": False}], "limit": 6}},
        {"id": "open_cases", "label": "Open cases", "subtitle": "Not at a final status",
         "snapshot_id": "rpt_case", "format": "number", "workstream": "field_ops",
         "explore_report_id": None, "windowless": True,
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Closed", "op": "eq", "value": False}]},
         "trend": {"dimensions": ["Case Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Is Closed", "op": "eq", "value": False}], "limit": 6}},
    ],
    "customer_ops": [
        {"id": "customer_contacts", "label": "Customer contacts", "subtitle": "All channels",
         "snapshot_id": "rpt_customer_contact", "format": "number", "workstream": "customer_ops",
         "explore_report_id": None, "date_field": "Contact Date/Time",
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
         "trend": {"dimensions": ["Contact Class"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [], "limit": 6}},
        {"id": "new_service_agreements", "label": "New service agreements", "subtitle": "Started in window",
         "snapshot_id": "rpt_service_agreement", "format": "number", "workstream": "customer_ops",
         "explore_report_id": None, "date_field": "SA Start Date",
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
         "trend": {"dimensions": ["SA Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [], "limit": 6}},
        {"id": "estimate_streaks", "label": "Estimate streaks (3+)", "subtitle": "Complaint-zone SAs",
         "snapshot_id": "rpt_service_agreement", "format": "number", "workstream": "customer_ops",
         "explore_report_id": None, "windowless": True,
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Consecutive Estimated Bills", "op": "gte", "value": 3}]},
         "trend": {"dimensions": ["SA Type"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [{"field": "Consecutive Estimated Bills", "op": "gte", "value": 3}], "limit": 6}},
        {"id": "total_customers", "label": "Total customers", "subtitle": "Accounts in CIS",
         "snapshot_id": "rpt_customer_account", "format": "number", "workstream": "customer_ops",
         "explore_report_id": None, "windowless": True,
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
         "trend": {"dimensions": ["Customer Class"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [], "limit": 6}},
    ],
    "finance": [
        {"id": "frozen_charge_fts", "label": "Frozen charge FTs", "subtitle": "Bill segments + adjustments",
         "snapshot_id": "rpt_financial_txn", "format": "currency", "workstream": "finance",
         "explore_report_id": None, "date_field": "Accounting Date",
         "value": {"dimensions": [], "measures": [{"field": "Current Amount", "agg": "sum"}],
                   "filters": [{"field": "Is Frozen", "op": "eq", "value": True}]},
         "trend": {"dimensions": ["FT Type"], "measures": [{"field": "Current Amount", "agg": "sum"}],
                   "filters": [{"field": "Is Frozen", "op": "eq", "value": True}], "limit": 6}},
        {"id": "adjustments", "label": "Adjustment dollars", "subtitle": "AD/AX in window",
         "snapshot_id": "rpt_financial_txn", "format": "currency", "workstream": "finance",
         "explore_report_id": None, "date_field": "Accounting Date",
         "value": {"dimensions": [], "measures": [{"field": "Current Amount", "agg": "sum"}],
                   "filters": [{"field": "Is Adjustment", "op": "eq", "value": True}]},
         "trend": {"dimensions": ["SA Type"], "measures": [{"field": "Current Amount", "agg": "sum"}],
                   "filters": [{"field": "Is Adjustment", "op": "eq", "value": True}], "limit": 6}},
        {"id": "gl_lines", "label": "GL distribution lines", "subtitle": "Posting detail rows",
         "snapshot_id": "rpt_gl", "format": "number", "workstream": "finance",
         "explore_report_id": None, "date_field": "Accounting Date",
         "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
         "trend": {"dimensions": ["GL Account"], "measures": [{"field": "*", "agg": "count"}],
                   "filters": [], "limit": 6}},
    ],
}

def build_workstream_summary(
    workstream_id: str,
    days: int = 30,
    *,
    compare: bool = False,
    compare_mode: str = "prior_period",
    extra_filters: list[dict[str, Any]] | None = None,
    organization_id: str | None = None,
) -> dict[str, Any]:
    catalog = load_catalog()
    labels = catalog.get("workstream_labels", {})
    ws = workstream_id.lower()
    kpis_def = WORKSTREAM_KPIS.get(ws, [])

    (date_start, date_end), (prior_start, prior_end), compare_label = date_windows(days, compare_mode)
    period_label = f"Last {days} days" if compare_mode != "mom" else "Month to date"
    client_id = organization_id or catalog.get("client", "demo")

    if ws not in WORKSTREAM_KPIS:
        return {"error": f"Unknown workstream: {workstream_id}"}

    # dbt-canvas KPIs run on the warehouse; either backend being configured is
    # enough (same widening as the executive summary, 2026-08-26)
    if not organization_id or not (
            demo_configured(organization_id) or warehouse_configured(organization_id)):
        return {
            "client": client_id,
            "db_configured": False,
            "compare_enabled": compare,
            "compare_mode": compare_mode,
            "compare_label": compare_label,
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
            compare_mode=compare_mode,
            extra_filters=extra_filters,
            organization_id=organization_id,
        )
        for kpi in kpis_def
    ]
    return {
        "client": client_id,
        "db_configured": True,
        "compare_enabled": compare,
        "compare_mode": compare_mode,
        "compare_label": compare_label,
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


# ---------------------------------------------------------------------------
# "About this workstream" -- what a section INCLUDES, what it deliberately does
# NOT, and how it cross-links to its neighbors. Included canvases and KPIs are
# GENERATED (catalog + WORKSTREAM_KPIS, so they cannot drift); the summaries,
# exclusions, and id-chain links are authored BASE-PRODUCT semantics -- the same
# at every client, which is why they live here and not in per-tenant config.
# The exclusions are the point: they are what analysts guess wrong.
# ---------------------------------------------------------------------------

WORKSTREAM_ABOUT: dict[str, dict[str, Any]] = {
    "billing": {
        "summary": "Bill production: segments, calc-line itemization, billed usage "
                   "per unit of measure, and rate/bill-factor pricing -- each at its "
                   "own grain, lifecycle stated on every amount (frozen vs cancelled).",
        "not_included": [
            "Payments and tenders -- Cashiering & Payments (money received is not money billed)",
            "The accounting view of the same dollars (FTs, GL) -- Finance",
            "Raw/unbilled usage and measurements -- Meter Operations (usage joins billing only once a segment bills it)",
            "Aged balances and arrears -- Collections & Debt",
        ],
        "related": [
            {"workstream": "finance", "via": "Bill Segment ID -> frozen bill-segment FTs (the revenue tie the reconciliation canvas asserts)"},
            {"workstream": "cashiering", "via": "Account ID / Bill ID -> payments applied against billed balances"},
            {"workstream": "meter_ops", "via": "Bill Segment ID -> the usage and service-quantity lines behind each segment"},
            {"workstream": "customer_ops", "via": "SA ID -> the agreement and customer context on every segment"},
        ],
    },
    "cashiering": {
        "summary": "Money received: payments, tenders, and tender-control balancing "
                   "-- the cash-drawer view, with cancellation and NSF lifecycle flags.",
        "not_included": [
            "Pay plans and collection activity -- Collections & Debt",
            "The ledger effect of a payment (PS/PX FTs) -- Finance",
            "What was billed -- Billing & Rates",
        ],
        "related": [
            {"workstream": "finance", "via": "Payment ID -> payment FTs posting to the ledger"},
            {"workstream": "debt", "via": "Account ID -> payments that cure arrears and feed pay-plan compliance"},
            {"workstream": "customer_ops", "via": "Account ID -> who paid"},
        ],
    },
    "debt": {
        "summary": "What is owed and what is being done about it: aged balances "
                   "(rederived from raw FTs and verified 100% against the client's own "
                   "snapshot), collection/severance processes, pay plans, credit rating.",
        "not_included": [
            "Current bill production -- Billing & Rates",
            "The cash drawer itself -- Cashiering & Payments",
            "Write-off accounting detail (GL) -- Finance",
        ],
        "related": [
            {"workstream": "field_ops", "via": "severance -> the cut/reconnect field activities it dispatches"},
            {"workstream": "cashiering", "via": "Account ID -> payments reducing the aged position"},
            {"workstream": "customer_ops", "via": "SA ID / Account ID -> whose debt it is"},
        ],
    },
    "customer_ops": {
        "summary": "Who the utility serves: accounts, linked persons, contacts, "
                   "notifications, and cases -- the customer master with flattened "
                   "contact points, alerts, autopay, and characteristics on the row.",
        "not_included": [
            "Balances and arrears detail -- Collections & Debt",
            "Bills and segments -- Billing & Rates",
            "Premises/service points/devices -- Meter Operations (the service side of the same customers)",
        ],
        "related": [
            {"workstream": "billing", "via": "Account ID / SA ID -> everything billed to the customer"},
            {"workstream": "debt", "via": "Account ID -> the aged position behind the account"},
            {"workstream": "field_ops", "via": "Case ID / Account ID -> field work the customer generated"},
        ],
    },
    "meter_ops": {
        "summary": "The metering estate and what it measures: devices, service "
                   "points, install/on-off history, measurements (with estimation "
                   "flags), processed usage, and asset locations.",
        "not_included": [
            "Billed usage -- Billing & Rates (same quantities, but only once a bill segment claims them)",
            "Field visit workflow -- Field Operations (the activity that touches the meter lives there)",
            "Customer identity -- Customer Operations",
        ],
        "related": [
            {"workstream": "billing", "via": "usage transactions -> the bill segments that bill them"},
            {"workstream": "field_ops", "via": "Service Point ID -> activities executed at the point"},
            {"workstream": "customer_ops", "via": "Premise ID / SP ID -> the customer at the point"},
        ],
    },
    "field_ops": {
        "summary": "Work in the field: activities with their event lifecycle, and "
                   "operational exceptions -- the dispatch-and-outcome view.",
        "not_included": [
            "The device/meter master -- Meter Operations",
            "To Do queues -- Operations & Shared Services (back-office work, not truck rolls)",
            "Cases -- Customer Operations",
        ],
        "related": [
            {"workstream": "meter_ops", "via": "Service Point ID / Device ID -> what the activity touched"},
            {"workstream": "debt", "via": "severance cut/reconnect activities dispatched by collections"},
        ],
    },
    "finance": {
        "summary": "The ledger view: every financial transaction (bill segments, "
                   "payments, adjustments) net of cancellation, GL distribution "
                   "lines, and the revenue reconciliation control canvas.",
        "not_included": [
            "Tender-level cash detail -- Cashiering & Payments",
            "Calc-line pricing itemization -- Billing & Rates",
            "Aged debt bands -- Collections & Debt (same FTs, aged rather than posted)",
        ],
        "related": [
            {"workstream": "billing", "via": "Bill Segment ID -> BS/BX FTs (calc lines must tie, asserted per bill)"},
            {"workstream": "cashiering", "via": "Payment ID -> PS/PX FTs"},
            {"workstream": "debt", "via": "the same FTs aged into arrears bands"},
        ],
    },
    "common": {
        "summary": "Shared infrastructure every workstream reads: the bill "
                   "lifecycle header, batch runs, To Do queues, and characteristics "
                   "for every entity type.",
        "not_included": [
            "Domain detail -- each canvas here cross-links into its owning workstream by id",
        ],
        "related": [
            {"workstream": "billing", "via": "Bill ID -> the segments inside each bill"},
            {"workstream": "field_ops", "via": "To Do drill keys -> the work the queues point at"},
        ],
    },
}


def build_workstream_about(
    workstream_id: str, *, organization_id: str | None = None
) -> dict[str, Any]:
    from api.snapshot_catalog import list_snapshots

    catalog = load_catalog(organization_id=organization_id)
    labels = catalog.get("workstream_labels", {})
    ws = workstream_id.lower()
    about = WORKSTREAM_ABOUT.get(ws, {})
    canvases = [
        {"id": s["id"], "label": s["label"], "grain": s.get("grain_description") or s.get("grain")}
        for s in list_snapshots(organization_id=organization_id)
        if s["workstream"] == ws
    ]
    kpis = [
        {"id": k["id"], "label": k["label"], "subtitle": k.get("subtitle", "")}
        for k in WORKSTREAM_KPIS.get(ws, [])
    ]
    return {
        "workstream": ws,
        "label": labels.get(ws, ws),
        "summary": about.get("summary", ""),
        "canvases": canvases,
        "kpis": kpis,
        "not_included": about.get("not_included", []),
        "related": [
            {**r, "label": labels.get(r["workstream"], r["workstream"])}
            for r in about.get("related", [])
        ],
    }
