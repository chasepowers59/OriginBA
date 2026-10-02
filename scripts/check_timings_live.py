#!/usr/bin/env python3
"""How long each demo surface takes through the RUNNING API, per organization, against a budget.
The performance skill quotes numbers; this is how they are re-measured. One request per surface:
Home (every chip, with and without Compare), each workstream summary, Ori's findings and
trends, Data Quality, the report library, and a 12-month monthly count on the largest data
sets (the ones with a pre-aggregate, plus the biggest without). Each is asked TWICE, so the
cold and the warm path both show. Read-only; it writes nothing and runs no model call.
    python3 scripts/check_timings_live.py --org ellensburg [--budget 5]
Exit 1 when any warm answer is over the budget (seconds): a warm surface that slow is a
regression, not a cold start.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LARGEST = ["rpt_bill_segment", "rpt_billed_charge", "rpt_financial_txn", "rpt_gl", "rpt_payment",
           "rpt_measurement", "rpt_billed_usage", "rpt_bill_segment_read"]
WORKSTREAMS = ["billing", "finance", "debt", "cashiering", "meter_ops", "field_ops", "customer_ops",
               "assets", "common"]


def _timed(api: str, org: str, path: str, body: dict | None = None) -> tuple[int, float]:
    req = urllib.request.Request(f"{api}{path}", data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", "X-Organization-Id": org})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            r.read()
            return r.status, time.time() - t
    except urllib.error.HTTPError as e:
        return e.code, time.time() - t


def surfaces(org: str) -> list[tuple[str, str, dict | None]]:
    cat = json.loads((ROOT / "output" / "catalog_dbt.json").read_text())["snapshots"]
    out: list[tuple[str, str, dict | None]] = []
    for days in (30, 90, 180):
        for compare in ("false", "true"):
            out.append((f"home {days}d compare={compare}", f"/snapshots/executive-summary?days={days}&compare={compare}", None))
    out += [(f"workstream {ws}", f"/snapshots/workstream-summary/{ws}?days=30", None) for ws in WORKSTREAMS]
    out += [("ori findings", "/portal/ori/findings", None), ("ori trends", "/portal/ori/trends", None),
            ("data quality", "/dq/findings", None), ("report library", "/portal/report-library", None)]
    for c in LARGEST:
        if c not in cat:
            continue
        d = cat[c].get("default_date_field")
        body = {"dimensions": [], "measures": [{"field": "*", "agg": "count"}], "limit": 50,
                "filters": [{"field": d, "op": "between", "value": ["2025-07-01", "2026-06-30"]}] if d else [],
                "time_dimensions": [{"field": d, "grain": "month"}] if d else []}
        out.append((f"explore {c} monthly count", f"/snapshots/{c}/query", body))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", default="ellensburg")
    ap.add_argument("--api", default=os.environ.get("PORTAL_API", "http://localhost:8010"))
    ap.add_argument("--budget", type=float, default=5.0, help="seconds a WARM answer may take")
    a = ap.parse_args()
    slow = 0
    print(f"{'first':>8} {'again':>8}  {'code':>4}  surface   (org {a.org})")
    for name, path, body in surfaces(a.org):
        code, first = _timed(a.api, a.org, path, body)
        code2, again = _timed(a.api, a.org, path, body)
        flag = "" if code == 200 and code2 == 200 else "  <- not 200"
        if code2 == 200 and again > a.budget:
            flag = f"  <- warm over {a.budget:g}s"
            slow += 1
        print(f"{first:7.2f}s {again:7.2f}s  {code:>4}  {name}{flag}")
    print(f"\n{slow} surface(s) over budget on {a.org}")
    return 1 if slow else 0


if __name__ == "__main__":
    sys.exit(main())
