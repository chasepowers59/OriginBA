#!/usr/bin/env python3
"""
Smoke test analytics portal API against live demo DB (VPN required).

Usage:
  uvicorn api.app:app --port 8000   # in another terminal
  python3 scripts/local/smoke_analytics_portal.py
  python3 scripts/local/smoke_analytics_portal.py --base http://localhost:8000 --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "output" / "snapshot_explorer_catalog.json"

WORKSTREAM_ORDER = [
    "finance",
    "billing",
    "meter_ops",
    "cashiering",
    "debt",
    "customer_ops",
    "new_services",
    "field_ops",
    "common",
]

NLQ_QUERIES = [
    "top accounts by debt",
    "open exceptions this week",
    "billed revenue last month",
]

# Large snapshots where live sample/query checks are skipped (metadata + stats still run).
SKIP_LIVE_QUERY_SNAPSHOTS = frozenset({"D1_MSRMT_RPT_CURR"})


class SmokeFailure(Exception):
    pass


def http_json(method: str, url: str, body: dict | None = None, timeout: int = 180) -> tuple[int, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return exc.code, detail
    except TimeoutError:
        return 504, "timeout"


def default_date_range(days: int = 180) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def load_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.exists():
        raise SmokeFailure(f"Missing catalog: {CATALOG_PATH}")
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    if not ok:
        raise SmokeFailure(f"{name}{suffix}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    catalog = load_catalog()
    snapshots = catalog["snapshots"]
    failures: list[str] = []

    print(f"\n=== Analytics Portal Smoke Test ===\nBase: {base}\n")

    # Health / index
    try:
        code, idx = http_json("GET", f"{base}/snapshots")
        check("GET /snapshots", code == 200 and isinstance(idx, dict))
        check("DB configured", bool(idx.get("db_configured")), str(idx.get("db_configured")))
        check(
            "Snapshot count",
            len(idx.get("snapshots", [])) == 19,
            f"got {len(idx.get('snapshots', []))}",
        )
        check(
            "Workstream count",
            len(idx.get("workstreams", [])) == 9,
            f"got {len(idx.get('workstreams', []))}",
        )
    except SmokeFailure as exc:
        print(exc)
        return 1

    code, portal = http_json("GET", f"{base}/portal/config")
    check("GET /portal/config", code == 200)

    code, views = http_json("GET", f"{base}/portal/saved-views")
    check("GET /portal/saved-views", code == 200)

    code, dashboards = http_json("GET", f"{base}/portal/dashboards")
    check("GET /portal/dashboards", code == 200)

    code, library = http_json("GET", f"{base}/portal/report-library")
    check(
        "GET /portal/report-library",
        code == 200 and int(library.get("pack_count", 0)) >= 5,
        f"packs={library.get('pack_count')} reports={library.get('report_count')}",
    )

    code, exec_sum = http_json("GET", f"{base}/snapshots/executive-summary?days=30")
    check("GET /snapshots/executive-summary", code == 200 and "kpis" in exec_sum)
    if args.verbose:
        print(f"  executive KPIs: {len(exec_sum.get('kpis', []))}")

    for ws in WORKSTREAM_ORDER:
        code, ws_sum = http_json("GET", f"{base}/snapshots/workstream-summary/{ws}?days=30")
        try:
            check(f"GET workstream-summary/{ws}", code == 200 and "kpis" in ws_sum)
        except SmokeFailure as exc:
            failures.append(str(exc))

    for q in NLQ_QUERIES:
        code, nlq = http_json("POST", f"{base}/portal/analytics-nlq", {"query": q})
        try:
            check(f"NLQ: {q!r}", code == 200 and bool(nlq.get("narrative")))
            if args.verbose:
                table_rows = (nlq.get("table") or {}).get("rows") or []
                print(f"  narrative ok, table rows={len(table_rows)} source={nlq.get('source')}")
        except SmokeFailure as exc:
            failures.append(str(exc))

    start, end = default_date_range(180)
    ws_results: dict[str, list[str]] = {ws: [] for ws in WORKSTREAM_ORDER}

    for snap_id, meta in snapshots.items():
        ws = meta["workstream"]
        label = meta["label"]
        prefix = f"{snap_id} ({label})"

        code, md = http_json("GET", f"{base}/snapshots/{snap_id}/metadata")
        try:
            check(f"{prefix} metadata", code == 200)
            dm = md.get("data_model") or {}
            check(
                f"{prefix} data_model",
                bool(dm.get("snapshot_table")) and len(dm.get("source_tables") or []) > 0,
                f"{len(dm.get('source_tables') or [])} tables, {len(dm.get('join_paths') or [])} joins",
            )
            check(
                f"{prefix} fields",
                len(md.get("fields") or []) > 0,
                str(len(md.get("fields") or [])),
            )
        except SmokeFailure as exc:
            failures.append(str(exc))
            ws_results[ws].append("metadata")
            continue

        code, stats = http_json("GET", f"{base}/snapshots/{snap_id}/stats")
        try:
            check(
                f"{prefix} stats",
                code == 200 and int(stats.get("row_count", -1)) >= 0,
                f"rows={stats.get('row_count')}",
            )
        except SmokeFailure as exc:
            failures.append(str(exc))
            ws_results[ws].append("stats")

        if snap_id in SKIP_LIVE_QUERY_SNAPSHOTS:
            print(f"[SKIP] {prefix} sample-rows + premade query (large snapshot — metadata/stats only)")
            continue

        code, sample = http_json("GET", f"{base}/snapshots/{snap_id}/sample-rows?limit=5", timeout=60)
        try:
            check(
                f"{prefix} sample-rows",
                code == 200 and isinstance(sample.get("rows"), list),
                f"sample={len(sample.get('rows') or [])}",
            )
        except SmokeFailure as exc:
            failures.append(str(exc))
            ws_results[ws].append("sample-rows")

        premade = (meta.get("premade_reports") or [{}])[0]
        date_field = meta.get("required_date_field")
        filters: list[dict[str, Any]] = []
        if date_field:
            filters.append({"field": date_field, "op": "between", "value": [start, end]})
        filters.extend(premade.get("filters") or [])

        query_body = {
            "dimensions": premade.get("dimensions") or [],
            "measures": premade.get("measures") or [{"field": "*", "agg": "count"}],
            "filters": filters,
            "time_dimensions": [],
            "limit": 50,
        }
        code, result = http_json("POST", f"{base}/snapshots/{snap_id}/query", query_body, timeout=90)
        ok = False
        try:
            ok = code == 200 and isinstance(result.get("rows"), list)
            detail = f"categories={result.get('row_count')}" if ok else str(result)[:120]
            check(f"{prefix} premade query", ok, detail)
        except SmokeFailure as exc:
            failures.append(str(exc))
            ws_results[ws].append("query")

        if args.verbose and ok:
            print(f"  SQL: {(result.get('sql') or '')[:100]}…")

    print("\n=== Workstream summary ===")
    for ws in WORKSTREAM_ORDER:
        issues = ws_results.get(ws) or []
        if issues:
            print(f"[REVIEW] {ws}: failures on {', '.join(sorted(set(issues)))}")
        else:
            snap_count = sum(1 for s in snapshots.values() if s["workstream"] == ws)
            print(f"[PASS] {ws}: {snap_count} snapshots OK")

    print("\n=== Result ===")
    if failures:
        print(f"FAILED — {len(failures)} check(s)")
        for item in failures[:20]:
            print(f"  • {item}")
        if len(failures) > 20:
            print(f"  … and {len(failures) - 20} more")
        return 1

    print("ALL CHECKS PASSED (18 live + 1 metadata-only snapshot, 9 workstreams, portal routes, NLQ)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
