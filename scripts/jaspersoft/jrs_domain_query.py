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


def query(env: str, org: str, domain: str, fields: list[str], limit: int, page: int, timeout: int) -> list[list]:
    os.environ["JRS_ENV"] = env; sw._AUTH.header = sw._auth_for(org)
    q = {"select": {"fields": [{"id": f"f{i}", "field": f} for i, f in enumerate(fields)]}}
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
    ap.add_argument("--domain", required=True); ap.add_argument("--fields", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--limit", type=int, default=20000); ap.add_argument("--page", type=int, default=2000)
    ap.add_argument("--timeout", type=int, default=300)
    a = ap.parse_args()
    fields = [f.strip() for f in a.fields.split(",") if f.strip()]
    rows = query(a.env, a.org, a.domain, fields, a.limit, a.page, a.timeout)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"env": a.env, "org": a.org, "domain": a.domain, "fields": fields, "rows": rows}, indent=0))
    print(f"{a.env}/{a.org}: {len(rows)} rows x {len(fields)} fields -> {a.out}")
    for r in rows[:5]:
        print("   ", json.dumps(r)[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
