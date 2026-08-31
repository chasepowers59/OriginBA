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


def available_kpis(
    kpi_defs: list[dict[str, Any]], organization_id: str | None,
) -> tuple[list[dict[str, Any]], str | None]:
    """Filter the KPI set to snapshots that exist in this org's catalog.

    The executive KPIs read the governed dbt canvases (rpt_*). A legacy-catalog org
    (demo: the CISADM *_RPT_CURR snapshots) has none of them, so running the set there
    produced a grid of 'Unknown snapshot' error cards. Skip the missing ones instead;
    when nothing is left, return a single human note for the dashboard to show.
    """
    from api.snapshot_catalog import CatalogError, get_snapshot

    def _in_catalog(snapshot_id: str) -> bool:
        try:
            get_snapshot(snapshot_id, organization_id)
            return True
        except CatalogError:
            return False

    avail = [k for k in kpi_defs if _in_catalog(str(k.get("snapshot_id")))]
    if avail or not kpi_defs:
        return avail, None
    return [], (
        "Executive KPIs read the governed reporting canvases, which are not part of "
        "this organization's catalog. Its reports are available under Library and "
        "the canvas pages."
    )




def _refresh_insight(organization_id: str) -> dict[str, Any] | None:
    """Change since last refresh, from the landing watermarks -- every row carries
    its CDC load_dttm, so the latest batch IS the change log. Best-effort: a legacy
    org (no warehouse) or a warehouse without the landing schema returns None."""
    try:
        from api.warehouse_db import execute_query as run_warehouse

        # one watermark query per table, kept simple and cheap
        rows_out = []
        last = None
        for name, tbl in [("financial transactions", "ci_ft"), ("bill segments", "ci_bseg"),
                          ("payment tenders", "ci_pay_tndr"), ("measurements", "d1_msrmt")]:
            _, rows = run_warehouse(
                f"select max(load_dttm), count(*) filter (where load_dttm = "
                f"(select max(load_dttm) from cisadm.{tbl})), count(*) from cisadm.{tbl}",
                organization_id=organization_id, max_rows=1)
            if rows and rows[0][0] is not None:
                ts, batch, total = rows[0]
                last = max(last, ts) if last else ts
                rows_out.append({"table": name, "batch_rows": int(batch), "total_rows": int(total)})
        if not rows_out:
            return None
        return {"last_refresh": last.isoformat() if last else None, "tables": rows_out}
    except Exception:  # noqa: BLE001
        return None


def build_executive_summary(
    days: int = 30,
    *,
    compare: bool = False,
    compare_mode: str = "prior_period",
    extra_filters: list[dict[str, Any]] | None = None,
    allowed_workstreams: list[str] | None = None,
    organization_id: str | None = None,
) -> dict[str, Any]:
    (date_start, date_end), (prior_start, prior_end), compare_label = date_windows(days, compare_mode)
    period_label = f"Last {days} days" if compare_mode != "mom" else "Month to date"
    client_id = organization_id or "demo"
    kpi_defs, catalog_note = available_kpis(
        _kpis_for_workstreams(allowed_workstreams), organization_id)

    # the KPI set runs on the dbt WAREHOUSE canvases; the Oracle demo DB is only
    # needed for any legacy-snapshot KPI. Either backend being configured is enough --
    # the runner routes per snapshot and reports per-KPI errors.
    if not organization_id or not (
            demo_configured(organization_id) or warehouse_configured(organization_id)):
        return {
            "client": client_id,
            "db_configured": False,
            "compare_enabled": compare,
        "compare_mode": compare_mode,
        "compare_label": compare_label,
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

    # KPIs are independent and I/O-bound (each is one or more Oracle/Postgres
    # round-trips), so run them CONCURRENTLY rather than in a ~20s sequential
    # loop over the VPN. Workers are capped at the connection-pool size; order is
    # preserved so the dashboard grid stays stable. execute_kpi_definition never
    # raises (it returns an error field), so no future needs a try/except here.
    from concurrent.futures import ThreadPoolExecutor

    def _run(kpi: dict[str, Any]) -> dict[str, Any]:
        return execute_kpi_definition(
            kpi,
            days=days,
            compare=compare,
            compare_mode=compare_mode,
            extra_filters=extra_filters,
            organization_id=organization_id,
        )

    if kpi_defs:
        with ThreadPoolExecutor(max_workers=min(8, len(kpi_defs))) as pool:
            kpis = list(pool.map(_run, kpi_defs))
    else:
        kpis = []
    return {
        "client": client_id,
        "db_configured": True,
        "compare_enabled": compare,
        "compare_mode": compare_mode,
        "compare_label": compare_label,
        "catalog_note": catalog_note,
        # The freshness marker reads the warehouse landing; on a legacy-catalog org
        # (no canvas KPIs ran) it would advertise ANOTHER org's data — suppress it.
        "refresh": _refresh_insight(organization_id) if kpi_defs else None,
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
