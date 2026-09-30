#!/usr/bin/env python3
"""Ask every Library report its question the way the explorer does, and flag the answers
that say nothing: empty, one "not recorded" bar, all zeros, or a single group.

Every such answer on Ellensburg (2026-09-30) was either a bug no other test could see (a
source column empty at every client, an axis constant on every row, a backlog without an
open-only filter) or a fact about the client. Facts are recorded in KNOWN with the reason;
anything else fails the run. Needs the portal API running (PORTAL_API, default
http://localhost:8010) and the organization's warehouse reachable (VPN for Oracle orgs).

    python3 scripts/check_report_health.py [--org ellensburg] [--out report_health.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOT_RECORDED = (None, "", "Not recorded")

# Answers that are true of the client, not wrong, with the evidence. A verdict that
# changes (or disappears) fails too, so the record cannot go stale unnoticed.
KNOWN = {
    "ellensburg": {
        "billable_charges": ("EMPTY", "newest billable charge 2023-12-07, outside any 12-month window"),
        "bills_by_status": ("ONE-GROUP", "every bill of the last 12 months is Complete; the 4,598 "
                                         "pending bills are older (bills_longest_open shows them)"),
        "meters_not_registered": ("EMPTY", "manually read meters, no head-end: 0 devices flagged"),
        "case_resolution_time": ("EMPTY", "5 cases ever; the 2 closed ones were created 2026-07-09, "
                                          "after the data-as-of date (2026-06-18)"),
        "kpi_exception_rate": ("ALL-ZERO", "none of the 943,090 exceptions created in the year to "
                                           "2026-06-18 is still open; the 9,338 open ones are older or newer"),
    },
}


def verdict(rows: list[dict], dimension: str) -> str | None:
    """What an answer fails to say, or None when it says something."""
    if not rows:
        return "EMPTY"
    if len(rows) == 1 and rows[0].get(dimension) in NOT_RECORDED:
        return "ONLY-NOT-RECORDED"
    if all(not r.get("m0") for r in rows):
        return "ALL-ZERO"
    if len(rows) == 1:
        return "ONE-GROUP"
    return None


def _post(api: str, org: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(f"{api}{path}", data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", "X-Organization-Id": org})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.load(resp)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", default="ellensburg")
    ap.add_argument("--api", default=os.environ.get("PORTAL_API", "http://localhost:8010"))
    ap.add_argument("--out")
    args = ap.parse_args()

    catalog = json.loads((ROOT / "output" / "catalog_dbt.json").read_text())
    known = KNOWN.get(args.org, {})
    results, unexplained = [], []
    meta_cache: dict[str, dict] = {}
    for folder in catalog["report_library"]:
        for entry in folder["reports"]:
            sid, rid = entry["snapshot_id"], entry["report_id"]
            snap = catalog["snapshots"][sid]
            report = next(r for r in snap["premade_reports"] if r["id"] == rid)
            meta = meta_cache.setdefault(sid, _post(args.api, args.org, f"/snapshots/{sid}/metadata"))
            date = snap.get("default_date_field")
            all_dates = not date or snap.get("default_date_preset") == "all_dates" or report.get("all_dates")
            filters = list(report["filters"])
            if not all_dates:
                end = dt.date.fromisoformat(meta["data_as_of"]) if meta.get("data_as_of") else dt.date.today()
                filters.append({"field": date, "op": "between",
                                "value": [(end - dt.timedelta(days=365)).isoformat(), end.isoformat()]})
            body = {"dimensions": report["dimensions"], "measures": report["measures"], "filters": filters,
                    "all_dates": bool(all_dates), "limit": 500}
            try:
                rows = _post(args.api, args.org, f"/snapshots/{sid}/query", body).get("rows", [])
                got = verdict(rows, report["dimensions"][0])
            except Exception as exc:  # noqa: BLE001 -- a report that errors is a finding
                rows, got = [], f"ERROR {str(exc)[:80]}"
            expected = known.get(rid, (None, ""))[0]
            ok = got == expected
            if not ok:
                unexplained.append(rid)
            note = known.get(rid, (None, ""))[1] if got and ok else ""
            print(f"{'ok  ' if ok else 'FAIL'} {folder['id']:20} {rid:32} {got or 'answers':18} {note}", flush=True)
            results.append({"folder": folder["id"], "report": rid, "verdict": got, "expected": expected,
                            "groups": len(rows)})
    stale = sorted(set(known) - {r["report"] for r in results})
    for rid in stale:
        unexplained.append(rid)
        print(f"FAIL {rid}: recorded in KNOWN but no longer in the Library")
    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=1))
    print(f"\n{len(results)} reports, {len(unexplained)} unexplained")
    return 1 if unexplained else 0


if __name__ == "__main__":
    sys.exit(main())
