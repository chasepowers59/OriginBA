#!/usr/bin/env python3
"""Every Library report an organization is offered agrees with itself, on its real warehouse.

tests/test_report_invariants.py proves these on the fabricated fixture warehouse; this asks the
RUNNING API the same questions the way the explorer does, for every report the organization is
offered, on its own data (Ellensburg, CityCorp: Chase 2026-10-01, the proof-of-concept pair):

  1. the breakdown adds up to the total            (sum and count)
  2. the month trend adds up to the total          (sum and count, on the data set's date)
  3. clicking the top bar reproduces that bar       (every aggregation)
  4. a share lies in 0-100

Each report is asked over the same window the explorer opens on (the last 12 months to the
data-as-of date) unless the report or data set says all dates. Read-only.

    python3 scripts/check_report_invariants_live.py --org citycorp [--out invariants.json]
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
LIMIT = 5000
ADDITIVE = {"sum", "count"}


def _post(api: str, org: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(f"{api}{path}", data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", "X-Organization-Id": org})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp)


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def close(a, b) -> bool:
    a, b = _num(a), _num(b)
    return abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", default="ellensburg")
    ap.add_argument("--api", default=os.environ.get("PORTAL_API", "http://localhost:8010"))
    ap.add_argument("--out")
    a = ap.parse_args()

    catalog = json.loads((ROOT / "output" / "catalog_dbt.json").read_text())
    library = _post(a.api, a.org, "/portal/report-library")
    offered = [(c["snapshot_id"], c["report_id"]) for f in library["folders"] for c in f["reports"]]
    meta_cache: dict[str, dict] = {}
    results, failures = [], 0
    for sid, rid in offered:
        snap = catalog["snapshots"][sid]
        report = next(r for r in snap["premade_reports"] if r["id"] == rid)
        meta = meta_cache.setdefault(sid, _post(a.api, a.org, f"/snapshots/{sid}/metadata"))
        date = snap.get("default_date_field")
        all_dates = not date or snap.get("default_date_preset") == "all_dates" or bool(report.get("all_dates"))
        filters = list(report["filters"])
        if not all_dates:
            end = dt.date.fromisoformat(meta["data_as_of"]) if meta.get("data_as_of") else dt.date.today()
            filters.append({"field": date, "op": "between",
                            "value": [(end - dt.timedelta(days=365)).isoformat(), end.isoformat()]})
        measure, dims = report["measures"][0], report["dimensions"]

        def q(filters=filters, dimensions=dims, measures=(measure,), time_dimensions=()):
            body = {"dimensions": list(dimensions), "measures": list(measures), "filters": filters,
                    "time_dimensions": list(time_dimensions), "all_dates": True, "limit": LIMIT}
            out = _post(a.api, a.org, f"/snapshots/{sid}/query", body)
            seen["truncated"], seen["totals"] = out.get("truncated"), out.get("totals")
            return out["rows"]

        problems, checked, seen = [], [], {}
        try:
            grouped = q()
            if seen.get("truncated"):
                # cut to its top groups: the API's own total must be the unbroken answer
                reported = (seen.get("totals") or {}).get("m0")
                total = (q(dimensions=()) or [{}])[0].get("m0")
                if not close(reported, total):
                    problems.append(f"cut breakdown reports total {reported}, the unbroken answer is {total}")
                checked.append("cut: true total")
            elif len(grouped) >= LIMIT:
                checked.append("truncated: not judged")
            else:
                values = {tuple(r.get(d) for d in dims): r.get("m0") for r in grouped}
                if measure["agg"] in ADDITIVE:
                    total = (q(dimensions=()) or [{}])[0].get("m0")
                    if not close(sum(_num(v) for v in values.values()), total):
                        problems.append(f"breakdown {sum(_num(v) for v in values.values())} != total {total}")
                    checked.append("breakdown")
                    if date:
                        trend = q(dimensions=(), time_dimensions=[{"field": date, "grain": "month"}])
                        if not close(sum(_num(r.get("m0")) for r in trend), total):
                            problems.append(f"month trend {sum(_num(r.get('m0')) for r in trend)} != total {total}")
                        checked.append("trend")
                if measure["agg"] == "share" and not all(0 <= _num(v) <= 100 for v in values.values()):
                    problems.append("a share outside 0-100")
                top = next((k for k, v in sorted(values.items(), key=lambda kv: -_num(kv[1])) if k[0] is not None), None)
                if top is not None and dims:
                    clicked = (q(filters=[*filters, {"field": dims[0], "op": "eq", "value": top[0]}],
                                 dimensions=dims[1:]) or [{}])
                    clicked_total = sum(_num(r.get("m0")) for r in clicked) if measure["agg"] in ADDITIVE else clicked[0].get("m0")
                    expect = sum(_num(v) for k, v in values.items() if k[0] == top[0]) if measure["agg"] in ADDITIVE else values[top]
                    if len(dims) == 1 or measure["agg"] in ADDITIVE:
                        if not close(clicked_total, expect):
                            problems.append(f"clicking {top[0]!r} gives {clicked_total}, the bar says {expect}")
                        checked.append("cross-filter")
        except Exception as exc:  # noqa: BLE001 -- a report that errors is a finding
            problems.append(f"ERROR {str(exc)[:120]}")
        failures += bool(problems)
        print(f"{'FAIL' if problems else 'ok  '} {sid:28} {rid:34} {', '.join(checked) or '-':32} {'; '.join(problems)}", flush=True)
        results.append({"snapshot": sid, "report": rid, "checked": checked, "problems": problems})
    if a.out:
        Path(a.out).write_text(json.dumps(results, indent=1))
    print(f"\n{len(results)} reports on {a.org}, {failures} disagree with themselves")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
