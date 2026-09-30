#!/usr/bin/env python3
"""Pull rows out of a domain by item id, the way an Ad Hoc table would, and save them.

A flat query through /rest_v2/queryExecutions with the DOMAIN as the datasource. Fields are
`<set>.<item>` ids as the domain's metadata names them (jrs_debug.py inspect prints them).
Pages through everything up to --limit, writes JSON, prints a count and the first rows. This is
the before/after instrument for a domain change: same fields, same org, two files, diff them.

    scripts/jaspersoft/jrs.sh jrs_domain_query.py --env test --org Origin_DEV \
        --domain /SmartCity/Report/Standard_Offering/Debt_Management/Write_Off_Process_1/Write_Offs___Domain \
        --fields SET_PROCESS.WRITE_OFF_PROCESS_ID,SET_SA_PAYMENT.PAYMENT_EVENT_COUNT_ROW \
        --out /tmp/before.json [--limit 20000] [--page 2000]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jrs_run_sweep as sw  # noqa: E402


def query(env: str, org: str, domain: str, fields: list[str], limit: int, page: int, timeout: int, aggs: list[str] | None = None, where: str = "") -> list[list]:
    """Rows of the fields; with aggs (`set.item:Function`, e.g. SET_METRICS.ADJ_COUNT:CountDistinct) the
    fields become the group-by and each row carries the aggregates -- the only way to a total
    through a domain, since a flat query is row-level whatever the item's default aggregation."""
    os.environ["JRS_ENV"] = env; sw._AUTH.header = None if org == "ROOT" else sw._auth_for(org)   # ROOT: the superuser, absolute /organizations/... uris
    q = {"select": {"fields": [{"id": f"f{i}", "field": f} for i, f in enumerate(fields)]}}
    if aggs:   # a grouped query with detail fields answers one row per DETAIL row (aggregates repeated): group only
        q["select"]["fields"] = []
        # measured shapes (400s otherwise): an aggregation names its item as fieldRef; groupBy is a LIST of
        # typed groups, {"group": {...}} per dimension or {"allGroup": {...}} for the grand total
        q["select"]["aggregations"] = [{"id": f"a{i}", "fieldRef": a.split(":")[0], "functionName": a.split(":")[1]} for i, a in enumerate(aggs)]
        q["groupBy"] = [{"group": {"id": f"g{i}", "field": f}} for i, f in enumerate(fields)] or [{"allGroup": {"id": "all"}}]
    if where:   # DomEL over item ids, e.g. "SET_ADJUSTMENT.ADJ_CRE_DT >= ts'2026-01-01 00:00:00'"
        q["where"] = {"filterExpression": where}
    payload = json.dumps({"dataSource": {"reference": {"uri": domain}}, "query": q}).encode()
    rows: list[list] = []
    offset = 0
    while offset < limit:
        size = min(page, limit - offset)
        c, b, _ = sw._http(f"/rest_v2/queryExecutions?offset={offset}&pageSize={size}", "POST", payload,
                           "application/execution.multiLevelQuery+json", "application/flatData+json", timeout)
        if c != 200:
            raise SystemExit(f"query: HTTP {c}: {sw._message(b)[:300]}")
        j = json.loads(b)
        got = (j.get("dataset") or {}).get("rows") or []
        rows.extend(got)
        total = j.get("totalCounts")
        offset += size
        if not got or len(got) < size or (isinstance(total, int) and offset >= total):
            break
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True); ap.add_argument("--org", required=True)
    ap.add_argument("--domain", required=True); ap.add_argument("--fields", default="")
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--limit", type=int, default=20000); ap.add_argument("--page", type=int, default=2000)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--agg", action="append", default=[], metavar="set.item:Function", help="aggregate over the --fields groups (Sum, CountDistinct, CountAll, Average, Min, Max)")
    ap.add_argument("--where", default="", metavar="DomEL", help="filter expression over item ids; a window keeps a Sum under the server's 300,000-row Ad Hoc cap")
    a = ap.parse_args()
    fields = [f.strip() for f in a.fields.split(",") if f.strip()]
    rows = query(a.env, a.org, a.domain, fields, a.limit, a.page, a.timeout, a.agg, a.where)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"env": a.env, "org": a.org, "domain": a.domain, "fields": fields, "rows": rows}, indent=0))
    print(f"{a.env}/{a.org}: {len(rows)} rows x {len(fields)} fields -> {a.out}")
    for r in rows[:5]:
        print("   ", json.dumps(r)[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
