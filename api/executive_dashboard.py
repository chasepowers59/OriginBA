"""Executive KPI definitions and query runner for the analytics portal."""

from __future__ import annotations

from typing import Any

from api.demo_db import demo_configured
from api.warehouse_db import warehouse_configured
from api.kpi_runner import date_windows, execute_kpi_definition, public_lenses, select_lens


EXECUTIVE_KPIS: list[dict[str, Any]] = [
    # DBT-CANVAS KPIs (2026-08-25): every snapshot below is a governed reporting
    # canvas with schema=reporting, so the runner routes it to the per-tenant
    # Postgres warehouse. Filters use base-product constants only (never client
    # config); stock metrics are windowless; flow metrics window on the canvas's
    # own date field.
    {
        "id": "total_customers",
        "label": "Billing accounts",
        "subtitle": "Accounts in CIS",
        "snapshot_id": "rpt_customer_account",
        "format": "number",
        "workstream": "customer",
        "explore_report_id": None,
        "windowless": True,
        "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
        "trend": {"dimensions": ["Customer Class"],
                  "measures": [{"field": "*", "agg": "count"}], "filters": [], "limit": 6},
        # "Total customers / Accounts in CIS" counted EVERY account -- 562 on Demo 25.4
        # -- where a reader hears "customers we bill" (496). Both are legitimate, so the
        # card names which one it is showing. "Active SA Count" is a coalesced count, so
        # <= 0 reaches the accounts with no service agreement at all; while it was NULL
        # that comparison silently excluded 27 of the 66.
        "lenses": [
            {"id": "active", "label": "Active", "subtitle": "At least one active service agreement",
             "filters": [{"field": "Active SA Count", "op": "gte", "value": 1}]},
            {"id": "all", "label": "All", "subtitle": "Every account in CIS", "filters": []},
            {"id": "inactive", "label": "Inactive", "subtitle": "No active service agreement",
             "filters": [{"field": "Active SA Count", "op": "lte", "value": 0}]},
        ],
    },
    {
        "id": "active_service_agreements",
        "label": "Service agreements",
        "subtitle": "Status Active or Reactivated",
        "snapshot_id": "rpt_service_agreement",
        "format": "number",
        "workstream": "customer",
        "explore_report_id": None,
        "windowless": True,
        # The lens supplies the status filter; `value`/`trend` carry none of their own,
        # so "All" really is every SA rather than the active ones re-counted.
        "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
        "trend": {"dimensions": ["SA Type"],
                  "measures": [{"field": "*", "agg": "count"}], "filters": [], "limit": 6},
        # SA_STATUS_FLG is a base-product lookup, not client config, so testing its codes
        # is safe (the same licence the Active/Reactivated pair already relied on).
        # Verified against Demo 25.4, which carries all seven: 20 Active 1485,
        # 70 Canceled 45, 60 Closed 38, 10 Pending Start 33, 30 Pending Stop 15,
        # 40 Stopped 14, 50 Reactivated 1. Active+Reactivated = 1,486 = the old headline.
        "lenses": [
            {"id": "active", "label": "Active", "subtitle": "Status Active or Reactivated",
             "filters": [{"field": "SA Status Code", "op": "in", "value": ["20", "50"]}]},
            {"id": "pending", "label": "Pending", "subtitle": "Pending start or pending stop",
             "filters": [{"field": "SA Status Code", "op": "in", "value": ["10", "30"]}]},
            {"id": "stopped", "label": "Stopped", "subtitle": "Stopped or closed",
             "filters": [{"field": "SA Status Code", "op": "in", "value": ["40", "60"]}]},
            {"id": "canceled", "label": "Canceled", "subtitle": "Cancelled service agreements",
             "filters": [{"field": "SA Status Code", "op": "in", "value": ["70"]}]},
            {"id": "all", "label": "All", "subtitle": "Every service agreement, any status",
             "filters": []},
        ],
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
        "label": "Payments",
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
        # This card SAID "Frozen pay segments" and filtered on nothing, so it summed
        # cancelled payments into collections: $1,010,508.27 against a true frozen
        # $1,003,883.05 on Demo 25.4 -- $6,570.22 of it cancelled. The Frozen lens is
        # first, so the default now matches the claim the subtitle was already making.
        # PAY_STATUS_FLG is a base-product lookup (30 Freezable, 50 Frozen, 60 Cancelled).
        "lenses": [
            {"id": "frozen", "label": "Frozen", "subtitle": "Frozen pay segments — collected",
             "filters": [{"field": "Payment Status Code", "op": "eq", "value": "50"}]},
            {"id": "canceled", "label": "Canceled", "subtitle": "Cancelled payments",
             "filters": [{"field": "Payment Status Code", "op": "eq", "value": "60"}]},
            {"id": "freezable", "label": "Freezable", "subtitle": "Not yet frozen",
             "filters": [{"field": "Payment Status Code", "op": "eq", "value": "30"}]},
            {"id": "all", "label": "All", "subtitle": "Every pay segment, any status",
             "filters": []},
        ],
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
        # The card summed every row and reported the NET: -$6,333.30 on Demo 25.4, which
        # is arithmetically right and reads as broken. "Accounts receivable" means what
        # customers owe -- 130 SAs at +$23,854.69 -- and netting 66 credit balances of
        # -$30,187.99 against it turns a receivable into a liability nobody asked for.
        # Gross receivable is the default; credits are their own line, as in any ledger.
        #
        # rpt_sa_aged_balance anticipated exactly this. Its header says credit balances
        # are deliberately kept as rows because "who do we owe" is a real finance
        # question, and that the choice "belongs to the Ad Hoc user, which is why
        # 'Is In Arrears' and 'Has Credit Balance' exist as flags instead". The card
        # simply never made the choice; these lenses are it, using that same flag.
        # The flag reads Current Balance while the measure sums Total Balance, so the
        # subtitles name the flag rather than implying a clean sign split.
        "lenses": [
            {"id": "owing", "label": "Owing",
             "subtitle": "Service agreements not in credit",
             "filters": [{"field": "Has Credit Balance", "op": "eq", "value": False}]},
            {"id": "credit", "label": "In credit",
             "subtitle": "Credit balances — what the utility owes",
             "filters": [{"field": "Has Credit Balance", "op": "eq", "value": True}]},
            {"id": "net", "label": "Net", "subtitle": "Every balance, credits netted off",
             "filters": []},
        ],
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
        "label": "Bills",
        "subtitle": "Cycled billing throughput",
        "snapshot_id": "rpt_bill",
        "format": "number",
        "workstream": "billing",
        "explore_report_id": None,
        # NOT "Window Start Date": that column is empty at two of the three client
        # databases on this machine (0 of 1,978 on Demo 25.4, 0 of 87 on INT_DEV) and
        # only 53% populated on Ellensburg, so the card read 0 whatever the window.
        # "Created Date/Time" is 100% populated at all three, and it is the only date a
        # PENDING bill has -- a bill that is not yet billed has no bill date, so windowing
        # on Bill Date would make the Pending lens permanently empty.
        "date_field": "Created Date/Time",
        # The lens supplies the status; the base query carries none, so "All" is really
        # every bill rather than the completed ones re-counted.
        "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
        "trend": {"dimensions": ["Bill Cycle"],
                  "measures": [{"field": "*", "agg": "count"}], "filters": [], "limit": 6},
        # Phrased against the canvas's derived BOOLEAN rather than BILL_STAT_FLG's
        # 'C'/'P', so no code is written down at all -- the model already owns that
        # mapping and is tested on it. Demo 25.4: 1,963 complete, 15 pending.
        "lenses": [
            {"id": "complete", "label": "Complete", "subtitle": "Completed bills",
             "filters": [{"field": "Is Completed", "op": "eq", "value": True}]},
            {"id": "pending", "label": "Pending", "subtitle": "Bills not yet completed",
             "filters": [{"field": "Is Completed", "op": "eq", "value": False}]},
            {"id": "all", "label": "All", "subtitle": "Every bill, any status", "filters": []},
        ],
    },
    {
        "id": "field_activities",
        "label": "Field activities",
        "subtitle": "MDM activity volume",
        "snapshot_id": "rpt_field_activity",
        "format": "number",
        "workstream": "operations",
        "explore_report_id": None,
        # NOT "Event Date/Time": an activity only gets one once it has actually been
        # executed in the field, so it is 17% populated on Demo 25.4 (57 of 330), 54% on
        # Ellensburg and 56% on INT_DEV -- the card silently dropped the rest while
        # calling itself "activity volume". "Created Date/Time" is 100% at all three and
        # is the date every activity has, whatever became of it.
        "date_field": "Created Date/Time",
        "value": {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": []},
        "trend": {"dimensions": ["Activity Type"],
                  "measures": [{"field": "*", "agg": "count"}], "filters": [], "limit": 6},
        # DISCOVERED, not declared. An activity's status is a business-object lifecycle
        # state a client can extend, unlike the base-product _FLG lookups above -- Demo
        # 25.4 alone carries COMPLETED, DISCARDED, WAITEFFTDT, COMINPROG, VALERROR,
        # COMERROR and WAITAPPT. Writing those down would be wrong at the next client,
        # so the lenses are read from the tenant's own data, most common first.
        # The canvas carries the code without a description (no ENG label table for BO
        # states), so the code IS the label -- which is also what the analyst sees in CIS.
        "lens_field": {"field": "Activity Status Code", "noun": "Activity status",
                       "all_subtitle": "Every activity, any status", "limit": 8},
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
        # Broken down by TYPE, lensed by CLASS -- pick a category, see what it is made of.
        # Lensing on the trend's own axis would leave a one-bar chart; this way "Credit
        # and collection contacts" resolves to NSF letter 12, auto-dialer call 8, debt
        # reminder 8, which is the shape of the question someone actually asks.
        "trend": {"dimensions": ["Contact Type"],
                  "measures": [{"field": "*", "agg": "count"}], "filters": [], "limit": 6},
        # Contact class is CI_CC_CL -- client configuration, so DISCOVERED. Demo 25.4
        # carries nine ("General contacts", "Credit and collection contacts",
        # "Record of Digital Notifications" ...), and the next client's will be its own.
        #
        # Status was the obvious axis and is unusable: "Contact Status" is NULL on all
        # 170 rows here and at Ellensburg and INT_DEV too. "Contact Source" is likewise
        # empty and "Contact Method" reaches only 6 of 170, so class is the one
        # well-populated axis a lens can stand on.
        "lens_field": {"field": "Contact Class", "noun": "Contact class",
                       "all_subtitle": "Every contact, all classes", "limit": 8},
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

    The executive KPIs read the governed dbt canvases (rpt_*). An org whose warehouse
    is not built yet resolves none of them, and running the set there produced a grid of
    'Unknown snapshot' error cards. Skip the missing ones instead; when nothing is left,
    return a single human note for the dashboard to show.
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
    lenses: dict[str, str] | None = None,
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
                    "lenses": public_lenses(kpi),
                    "lens": (select_lens(kpi, (lenses or {}).get(str(kpi.get("id")))) or {}).get("id"),
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
            lens_id=(lenses or {}).get(str(kpi.get("id"))),
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
