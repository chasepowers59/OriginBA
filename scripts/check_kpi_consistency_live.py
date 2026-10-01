#!/usr/bin/env python3
"""Every Home and workstream KPI card shows what the explorer would answer to the same question.

The cards are computed by api/workstream_dashboard.py, a different path from the explorer's
/snapshots/{id}/query. A card that says one number while the same question in the explorer says
another breaks trust in both. For each card on each workstream, over the card's own period, this
asks the explorer path the card's declared question (WORKSTREAM_KPIS value query + its date
window) and compares. Read-only, on the organization's real warehouse.

    python3 scripts/check_kpi_consistency_live.py --org citycorp
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from api.workstream_dashboard import WORKSTREAM_KPIS  # noqa: E402


def _call(api: str, org: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(f"{api}{path}", data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", "X-Organization-Id": org})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp)


def close(a, b) -> bool:
    a, b = float(a or 0), float(b or 0)
    return abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", default="ellensburg")
    ap.add_argument("--api", default=os.environ.get("PORTAL_API", "http://localhost:8010"))
    ap.add_argument("--days", type=int, default=365)
    a = ap.parse_args()
    failures = checked = 0
    for ws, kpis in WORKSTREAM_KPIS.items():
        summary = _call(a.api, a.org, f"/snapshots/workstream-summary/{ws}?days={a.days}")
        start, end = summary["period"]["start"], summary["period"]["end"]
        by_id = {k["id"]: k for k in summary["kpis"]}
        for kpi in kpis:
            card = by_id.get(kpi["id"]) or {}
            if card.get("error") or card.get("value") is None:
                print(f"skip {ws:12} {kpi['id']:34} card shows {card.get('error') or 'nothing'}")
                continue
            q = kpi["value"]
            filters = list(q.get("filters") or [])
            if kpi.get("date_field"):
                filters.append({"field": kpi["date_field"], "op": "between", "value": [start, end]})
            body = {"dimensions": q.get("dimensions") or [], "measures": q["measures"], "filters": filters,
                    "time_dimensions": [], "all_dates": True, "limit": 5}
            try:
                rows = _call(a.api, a.org, f"/snapshots/{kpi['snapshot_id']}/query", body)["rows"]
                explorer = rows[0].get("m0") if rows else None
            except Exception as exc:  # noqa: BLE001
                explorer = f"ERROR {str(exc)[:80]}"
            ok = not isinstance(explorer, str) and close(card["value"], explorer)
            failures += not ok
            checked += 1
            print(f"{'ok  ' if ok else 'FAIL'} {ws:12} {kpi['id']:34} card {card['value']!s:>16}  explorer {explorer!s:>16}", flush=True)
    print(f"\n{checked} cards on {a.org} ({start} to {end}), {failures} disagree with the explorer")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
