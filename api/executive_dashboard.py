"""Executive KPI definitions and query runner for the analytics portal."""

from __future__ import annotations

from typing import Any

from api.demo_db import demo_configured
from api.warehouse_db import warehouse_configured
from api.kpi_runner import date_windows, execute_kpi_definition


EXECUTIVE_KPIS: list[dict[str, Any]] = [
    # DBT-CANVAS KPIs (2026-08-25): every snapshot below is a governed reporting
    # canvas with schema=reporting, so the runner routes it to the per-tenant
    # Postgres warehouse. Filters use base-product constants only (never client
    # config); stock metrics are windowless; flow metrics window on the canvas's
    # own date field.
    {
        "id": "total_customers",
        "label": "Total customers",
        "subtitle": "Accounts in CIS",
        "snapshot_id": "rpt_customer_account",
        "format": "number",
        "workstream": "customer",
        "explore_report_id": None,
        "windowless": True,
        "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
        "trend": {"dimensions": ["Customer Class"],
                  "measures": [{"field": "*", "agg": "count"}], "filters": [], "limit": 6},
    },
    {
        "id": "active_service_agreements",
        "label": "Active service agreements",
        "subtitle": "Status Active or Reactivated",
        "snapshot_id": "rpt_service_agreement",
        "format": "number",
        "workstream": "customer",
        "explore_report_id": None,
        "windowless": True,
        # 20 Active / 50 Reactivated are base-product constants (never client config)
        "value": {"dimensions": [],
                  "measures": [{"field": "*", "agg": "count"}],
                  "filters": [{"field": "SA Status Code", "op": "in", "value": ["20", "50"]}]},
        "trend": {"dimensions": ["SA Type"],
                  "measures": [{"field": "*", "agg": "count"}],
                  "filters": [{"field": "SA Status Code", "op": "in", "value": ["20", "50"]}],
                  "limit": 6},
    },
    {
        "id": "billed_revenue",
        "label": "Billed revenue",
        "subtitle": "Frozen bill-segment FTs",
        "snapshot_id": "rpt_financial_txn",
        "format": "currency",
        "workstream": "billing",
        "explore_report_id": None,
        "date_field": "Accounting Date",
        "value": {"dimensions": [],
                  "measures": [{"field": "Current Amount", "agg": "sum"}],
                  "filters": [{"field": "Is Bill Segment", "op": "eq", "value": True},
                              {"field": "Is Frozen", "op": "eq", "value": True}]},
        "trend": {"dimensions": ["SA Type"],
                  "measures": [{"field": "Current Amount", "agg": "sum"}],
                  "filters": [{"field": "Is Bill Segment", "op": "eq", "value": True},
                              {"field": "Is Frozen", "op": "eq", "value": True}],
                  "limit": 6},
    },
    {
        "id": "payments_collected",
        "label": "Payments collected",
        "subtitle": "Frozen pay segments",
        "snapshot_id": "rpt_payment",
        "format": "currency",
        "workstream": "finance",
        "explore_report_id": None,
        "date_field": "Payment Date",
        "value": {"dimensions": [],
                  "measures": [{"field": "Pay Segment Amount", "agg": "sum"}], "filters": []},
        "trend": {"dimensions": ["Payment Status"],
                  "measures": [{"field": "Pay Segment Amount", "agg": "sum"}],
                  "filters": [], "limit": 6},
    },
    {
        "id": "accounts_receivable",
        "label": "Accounts receivable",
        "subtitle": "Total SA balances",
        "snapshot_id": "rpt_sa_aged_balance",
        "format": "currency",
        "workstream": "finance",
        "explore_report_id": None,
        "windowless": True,
        "value": {"dimensions": [],
                  "measures": [{"field": "Total Balance", "agg": "sum"}], "filters": []},
        "trend": {"dimensions": ["Oldest Debt Band"],
                  "measures": [{"field": "Total Balance", "agg": "sum"}],
                  "filters": [], "limit": 6},
    },
    {
        "id": "past_due_balance",
        "label": "Past-due balance",
        "subtitle": "SAs past due",
        "snapshot_id": "rpt_sa_aged_balance",
        "format": "currency",
        "workstream": "finance",
        "explore_report_id": None,
        "windowless": True,
        "value": {"dimensions": [],
                  "measures": [{"field": "Total Balance", "agg": "sum"}],
                  "filters": [{"field": "Is Past Due", "op": "eq", "value": True}]},
        "trend": {"dimensions": ["Oldest Debt Band"],
                  "measures": [{"field": "Total Balance", "agg": "sum"}],
                  "filters": [{"field": "Is Past Due", "op": "eq", "value": True}],
                  "limit": 6},
    },
    {
        "id": "bills_completed",
        "label": "Bills completed",
        "subtitle": "Cycled billing throughput",
        "snapshot_id": "rpt_bill",
        "format": "number",
        "workstream": "billing",
        "explore_report_id": None,
        "date_field": "Window Start Date",
        "value": {"dimensions": [],
                  "measures": [{"field": "*", "agg": "count"}],
                  "filters": [{"field": "Is Completed", "op": "eq", "value": True}]},
        "trend": {"dimensions": ["Bill Cycle"],
                  "measures": [{"field": "*", "agg": "count"}],
                  "filters": [{"field": "Is Completed", "op": "eq", "value": True}],
                  "limit": 6},
    },
    {
        "id": "field_activities",
        "label": "Field activities",
        "subtitle": "MDM activity volume",
        "snapshot_id": "rpt_field_activity",
        "format": "number",
        "workstream": "operations",
        "explore_report_id": None,
        "date_field": "Event Date/Time",
        "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
        "trend": {"dimensions": ["Activity Type"],
                  "measures": [{"field": "*", "agg": "count"}], "filters": [], "limit": 6},
    },
    {
        "id": "customer_contacts",
        "label": "Customer contacts",
        "subtitle": "All channels",
        "snapshot_id": "rpt_customer_contact",
        "format": "number",
        "workstream": "customer",
        "explore_report_id": None,
        "date_field": "Contact Date/Time",
        "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
        "trend": {"dimensions": ["Contact Class"],
                  "measures": [{"field": "*", "agg": "count"}], "filters": [], "limit": 6},
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

    # the KPI set runs on the dbt WAREHOUSE canvases; the Oracle demo DB is only
    # needed for any legacy-snapshot KPI. Either backend being configured is enough --
    # the runner routes per snapshot and reports per-KPI errors.
    if not organization_id or not (
            demo_configured(organization_id) or warehouse_configured(organization_id)):
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
                    "error": "No reporting backend configured",
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
