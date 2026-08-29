#!/usr/bin/env python3
"""Tenant readiness check — prove an organization end-to-end before users touch it.

The portal scales by ROUTING, not by code: every tenant is one entry in
config/portal_organizations.json (engine + catalog + warehouse env key) and one
database. This script is the acceptance gate for that entry. It exercises the same
in-process paths the portal serves — catalog, canvases, executive summary, all
workstream summaries, the database workspace — and exits nonzero if any of it fails,
so onboarding (and every migration flip) ends with a proof, not a hope.

    python3 scripts/check_tenant.py dev
    python3 scripts/check_tenant.py --all            # every org in the registry

Empty canvases are REPORTED, not failed: "no rows" is a finding whose explanation
lives with the client's data (a demo DB with no pay plans is honest; a production
client with zero bills is not). The check prints them so a human decides.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


def _p(status: str, name: str, detail: str = "") -> bool:
    print(f"  {status:4} {name}" + (f" — {detail}" if detail else ""))
    return status != FAIL


def check_org(org_id: str) -> bool:
    from api.organizations import get_organization

    print(f"== {org_id} ==")
    org = get_organization(org_id)
    if not org:
        return _p(FAIL, "registry", f"no entry for '{org_id}' in portal_organizations.json")
    catalog_name = str(org.get("catalog") or "dbt")
    engine = str(org.get("engine") or ("postgres" if catalog_name == "dbt" else "oracle"))
    ok = _p(PASS, "registry", f"engine={engine} catalog={catalog_name}")

    # 1. The catalog this org is served.
    from api.snapshot_catalog import load_catalog

    try:
        catalog = load_catalog(organization_id=org_id)
        snaps = catalog.get("snapshots", {})
        ok &= _p(PASS, "catalog", f"{len(snaps)} snapshots")
    except Exception as exc:  # noqa: BLE001
        return _p(FAIL, "catalog", str(exc)[:120]) and False

    if catalog_name != "dbt":
        # Legacy tenant: the dbt checks below do not apply; just prove the backend.
        from api.demo_db import demo_configured

        ok &= _p(PASS if demo_configured(org_id) else FAIL, "oracle backend",
                 "demo_configured" if demo_configured(org_id) else "not configured")
        print()
        return bool(ok)

    if engine == "oracle":
        # In-database shape (oracle + dbt): the canvases live in ORIGINBA_REPORTING
        # inside the client's own Oracle instance. Same gates, Oracle introspection.
        return _check_oracle_dbt(org_id, ok, snaps)

    # 2. The warehouse itself.
    from api.warehouse_db import execute_query, warehouse_configured, warehouse_url

    if not warehouse_configured(org_id):
        return _p(FAIL, "warehouse", f"env key {org.get('warehouse_url_env')} not set") and False
    url = warehouse_url(org_id)
    masked = url.split("@")[-1] if "@" in url else url
    try:
        _, rows = execute_query(
            "select count(*) filter (where n_live_tup > 0), count(*) "
            "from pg_stat_user_tables where schemaname = 'reporting'",
            organization_id=org_id)
        populated, total = rows[0]
        ok &= _p(PASS, "warehouse", f"{masked} — {populated}/{total} canvases populated")
        if total == 0:
            ok &= _p(FAIL, "reporting schema", "no canvases — did dbt build run here?")
        elif populated < total:
            _, empty = execute_query(
                "select string_agg(relname, ', ' order by relname) from pg_stat_user_tables "
                "where schemaname = 'reporting' and n_live_tup = 0",
                organization_id=org_id)
            ok &= _p(WARN, "empty canvases", str(empty[0][0])[:160])
    except Exception as exc:  # noqa: BLE001
        return _p(FAIL, "warehouse", str(exc)[:160]) and False

    # 3. Catalog vs warehouse: every cataloged canvas must exist (schema drift gate).
    try:
        _, rows = execute_query(
            "select array_agg(relname) from pg_stat_user_tables where schemaname='reporting'",
            organization_id=org_id)
        live = set(rows[0][0] or [])
        missing = sorted(set(snaps.keys()) - live)
        ok &= _p(FAIL if missing else PASS, "catalog↔warehouse",
                 f"missing: {missing[:5]}" if missing else "every cataloged canvas exists")
    except Exception as exc:  # noqa: BLE001
        ok &= _p(FAIL, "catalog↔warehouse", str(exc)[:120])

    # 4. Executive summary — every KPI must execute.
    from api.executive_dashboard import build_executive_summary

    try:
        summary = build_executive_summary(days=365, compare=False, organization_id=org_id)
        errs = [k["id"] for k in summary.get("kpis", []) if k.get("error")]
        ok &= _p(FAIL if errs else PASS, "executive summary",
                 f"KPI errors: {errs}" if errs else f"{len(summary.get('kpis', []))} KPIs execute")
    except Exception as exc:  # noqa: BLE001
        ok &= _p(FAIL, "executive summary", str(exc)[:120])

    # 5. Every workstream summary — the section dashboards.
    from api.workstream_dashboard import WORKSTREAM_KPIS, build_workstream_summary

    for ws in WORKSTREAM_KPIS:
        try:
            r = build_workstream_summary(ws, days=365, compare=False, organization_id=org_id)
            errs = [k["id"] for k in r.get("kpis", []) if k.get("error")]
            ok &= _p(FAIL if errs else PASS, f"workstream:{ws}",
                     f"KPI errors: {errs}" if errs else f"{len(r.get('kpis', []))} KPIs")
        except Exception as exc:  # noqa: BLE001
            ok &= _p(FAIL, f"workstream:{ws}", str(exc)[:120])

    # 6. Database workspace — list + one governed query through the real path.
    from api.database_routes import _engine, _list_warehouse_tables, _run, _validate

    try:
        eng = _engine(org_id)
        tables = _list_warehouse_tables(org_id, "")
        sql = _validate(eng, 'select count(*) from rpt_financial_txn')
        _, rows = _run(eng, sql, org_id, 1)
        ok &= _p(PASS, "database workspace",
                 f"{len(tables)} canvases listed, rpt_financial_txn count={rows[0][0]}")
    except Exception as exc:  # noqa: BLE001
        ok &= _p(FAIL, "database workspace", str(exc)[:120])

    print()
    return bool(ok)


def _check_oracle_dbt(org_id: str, ok: bool, snaps: dict) -> bool:
    """Gates 2-6 for the in-database deployment shape (2026-08-28)."""
    from api.demo_db import demo_configured, execute_query

    # 2. The in-instance reporting schema.
    if not demo_configured(org_id):
        return _p(FAIL, "oracle backend", "connection not configured (env keys)") and False
    try:
        _, rows = execute_query(
            "select count(case when nvl(num_rows, 0) > 0 then 1 end), count(*) "
            "from all_tables where owner = 'ORIGINBA_REPORTING' "
            "and table_name like 'RPT%'",
            organization_id=org_id)
        populated, total = int(rows[0][0]), int(rows[0][1])
        ok &= _p(PASS, "warehouse (in-database)",
                 f"ORIGINBA_REPORTING — {populated}/{total} canvases with rows (stats-based)")
        if total == 0:
            ok &= _p(FAIL, "reporting schema",
                     "no canvases — did build_oracle_warehouse.sh run here?")
        elif populated < total:
            _, empty = execute_query(
                "select listagg(lower(table_name), ', ') within group (order by table_name) "
                "from all_tables where owner = 'ORIGINBA_REPORTING' "
                "and table_name like 'RPT%' and nvl(num_rows, 0) = 0",
                organization_id=org_id)
            ok &= _p(WARN, "empty canvases (per stats)", str(empty[0][0])[:160])
    except Exception as exc:  # noqa: BLE001
        return _p(FAIL, "warehouse (in-database)", str(exc)[:160]) and False

    # 3. Catalog vs warehouse drift.
    try:
        _, rows = execute_query(
            "select lower(table_name) from all_tables "
            "where owner = 'ORIGINBA_REPORTING' and table_name like 'RPT%'",
            organization_id=org_id, max_rows=500)
        live = {r[0] for r in rows}
        missing = sorted(set(snaps.keys()) - live)
        ok &= _p(FAIL if missing else PASS, "catalog↔warehouse",
                 f"missing: {missing[:5]}" if missing else "every cataloged canvas exists")
    except Exception as exc:  # noqa: BLE001
        ok &= _p(FAIL, "catalog↔warehouse", str(exc)[:120])

    # 4 + 5. Executive and workstream KPIs — identical calls; the runner routes.
    from api.executive_dashboard import build_executive_summary

    try:
        summary = build_executive_summary(days=365, compare=False, organization_id=org_id)
        errs = [k["id"] for k in summary.get("kpis", []) if k.get("error")]
        ok &= _p(FAIL if errs else PASS, "executive summary",
                 f"KPI errors: {errs}" if errs else f"{len(summary.get('kpis', []))} KPIs execute")
    except Exception as exc:  # noqa: BLE001
        ok &= _p(FAIL, "executive summary", str(exc)[:120])

    from api.workstream_dashboard import WORKSTREAM_KPIS, build_workstream_summary

    for ws in WORKSTREAM_KPIS:
        try:
            r = build_workstream_summary(ws, days=365, compare=False, organization_id=org_id)
            errs = [k["id"] for k in r.get("kpis", []) if k.get("error")]
            ok &= _p(FAIL if errs else PASS, f"workstream:{ws}",
                     f"KPI errors: {errs}" if errs else f"{len(r.get('kpis', []))} KPIs")
        except Exception as exc:  # noqa: BLE001
            ok &= _p(FAIL, f"workstream:{ws}", str(exc)[:120])

    # 6. Database workspace through the real path.
    from api.database_routes import _engine, _list_oracle_reporting_tables, _run, _validate

    try:
        eng = _engine(org_id)
        tables = _list_oracle_reporting_tables(org_id, "")
        sql = _validate(eng, "select count(*) from rpt_financial_txn")
        _, rows = _run(eng, sql, org_id, 1)
        ok &= _p(PASS, "database workspace",
                 f"engine={eng}, {len(tables)} canvases listed, "
                 f"rpt_financial_txn count={rows[0][0]}")
    except Exception as exc:  # noqa: BLE001
        ok &= _p(FAIL, "database workspace", str(exc)[:120])

    print()
    return bool(ok)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("org_id", nargs="?", help="organization id from portal_organizations.json")
    ap.add_argument("--all", action="store_true", help="check every registered organization")
    args = ap.parse_args()

    if not args.org_id and not args.all:
        ap.error("give an org id or --all")

    from api.organizations import load_organizations

    org_ids = ([o["id"] for o in load_organizations()] if args.all else [args.org_id])
    results = {oid: check_org(oid) for oid in org_ids}
    bad = [oid for oid, good in results.items() if not good]
    print(f"{len(results) - len(bad)}/{len(results)} tenants ready"
          + (f" — FAILED: {', '.join(bad)}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
