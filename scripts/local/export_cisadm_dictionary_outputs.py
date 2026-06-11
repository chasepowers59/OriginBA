#!/usr/bin/env python3
"""
Export CISADM dictionary discovery SQL results to CSV for a named client.

Usage:
  python3 scripts/local/export_cisadm_dictionary_outputs.py --client demo
  python3 scripts/local/export_cisadm_dictionary_outputs.py --client demo --only 14_fk_join_map
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "local"))

from run_client_oracle_sql import (  # noqa: E402
    CLIENTS,
    client_connection,
    expand_includes,
    init_oracle_client,
    load_config,
    split_sql_script,
)

import oracledb  # noqa: E402


DISCOVERY_SCRIPTS = {
    "03_constraints": "constraints.csv",
    "07_views": "views.csv",
    "08_view_dependencies": "view_dependencies.csv",
    "09_mviews": "mviews.csv",
    "10_synonyms_to_cisadm": "synonyms_to_cisadm.csv",
    "11_table_partitions": "table_partitions.csv",
    "12_table_stats": "table_stats.csv",
    "13_column_stats": "column_stats.csv",
    "14_fk_join_map": "fk_join_map.csv",
    "15_keyword_table_map": "keyword_table_map.csv",
}


def export_sql(client: str, sql_path: Path, out_csv: Path, max_rows: int) -> int:
    config = load_config(ROOT)
    init_oracle_client(config)
    user, password, dsn = client_connection(config, client)
    sql_text = expand_includes(sql_path)
    sql_text = sql_text.replace("&schema_owner", "CISADM")
    statements = split_sql_script(sql_text)
    if len(statements) != 1:
        raise RuntimeError(f"Expected one statement in {sql_path}, found {len(statements)}")

    with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
        with conn.cursor() as cursor:
            cursor.arraysize = 500
            cursor.execute(statements[0])
            if cursor.description is None:
                raise RuntimeError(f"No result set from {sql_path}")
            columns = [col[0] for col in cursor.description]
            out_csv.parent.mkdir(parents=True, exist_ok=True)
            row_count = 0
            with out_csv.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(columns)
                while True:
                    batch = cursor.fetchmany(max_rows)
                    if not batch:
                        break
                    for row in batch:
                        writer.writerow(["" if v is None else v for v in row])
                        row_count += 1
    print(f"[PASS] {out_csv.name}: {row_count} rows")
    return row_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", choices=sorted(CLIENTS), default="demo")
    parser.add_argument("--only", action="append", help="Export only named script stem(s), e.g. 14_fk_join_map")
    parser.add_argument("--max-rows", type=int, default=500000)
    parser.add_argument(
        "--out-dir",
        default=str(ROOT / "output" / "cisadm_dictionary"),
        help="Output directory for CSV files",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    sql_dir = ROOT / "sql" / "diagnostics" / "cisadm_dictionary"
    selected = args.only or list(DISCOVERY_SCRIPTS.keys())

    for stem in selected:
        if stem not in DISCOVERY_SCRIPTS:
            raise SystemExit(f"Unknown discovery script: {stem}")
        sql_path = sql_dir / f"{stem}.sql"
        out_csv = out_dir / DISCOVERY_SCRIPTS[stem]
        export_sql(args.client, sql_path, out_csv, args.max_rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
