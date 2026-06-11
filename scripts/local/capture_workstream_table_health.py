#!/usr/bin/env python3
"""
Capture live workstream table health counts and write table_health.json for AI context.

Usage:
  python3 scripts/local/capture_workstream_table_health.py --client demo
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "local"))

from run_client_oracle_sql import (  # noqa: E402
    CLIENTS,
    client_connection,
    init_oracle_client,
    load_config,
    normalize_oracle_dsn,
)

import oracledb  # noqa: E402


def _workstream_tables() -> list[str]:
    catalog = ROOT / "output" / "workstream_physical_catalog.json"
    if catalog.exists():
        payload = json.loads(catalog.read_text(encoding="utf-8"))
        tables = set()
        for ws in (payload.get("workstreams") or {}).values():
            for t in ws.get("tables") or []:
                tables.add(t.upper())
        return sorted(tables)
    payload = json.loads((ROOT / "output" / "workstream_reporting_dictionary.json").read_text(encoding="utf-8"))
    return sorted(
        {
            table_name.upper()
            for ws_name, ws in payload.items()
            for table_name in ((ws or {}).get("tables") or {}).keys()
            if ws_name != "field_tasks"
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", choices=sorted(CLIENTS), default="demo")
    args = parser.parse_args()

    config = load_config(ROOT)
    init_oracle_client(config)
    user, password, dsn = client_connection(config, args.client)
    tables = _workstream_tables()

    tables_out: dict = {}
    with oracledb.connect(user=user, password=password, dsn=normalize_oracle_dsn(dsn)) as conn:
        with conn.cursor() as cursor:
            for table in tables:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM ALL_TABLES
                    WHERE owner = 'CISADM' AND table_name = :table_name
                    """,
                    {"table_name": table},
                )
                exists = int(cursor.fetchone()[0]) > 0
                if not exists:
                    tables_out[table] = {
                        "row_count": None,
                        "population_status": "missing",
                    }
                    continue
                cursor.execute(f"SELECT COUNT(*) FROM cisadm.{table.lower()}")
                count = int(cursor.fetchone()[0])
                tables_out[table] = {
                    "row_count": count,
                    "population_status": "empty" if count == 0 else "populated",
                }

    payload = {
        "client": args.client,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "tables": tables_out,
        "summary": {
            "workstream_table_count": len(tables_out),
            "missing_table_count": sum(1 for t in tables_out.values() if t["population_status"] == "missing"),
            "empty_table_count": sum(1 for t in tables_out.values() if t["population_status"] == "empty"),
            "populated_table_count": sum(1 for t in tables_out.values() if t["population_status"] == "populated"),
        },
    }

    out_dir = ROOT / "deploy" / "snapshot_rollout_logs" / args.client
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "table_health.json"
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[PASS] table_health.json written: {out_json}")
    print(
        f"       populated={payload['summary']['populated_table_count']} "
        f"empty={payload['summary']['empty_table_count']} "
        f"missing={payload['summary']['missing_table_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
