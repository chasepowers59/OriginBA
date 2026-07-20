#!/usr/bin/env python3
"""
Export full CREATE VIEW DDL for every view in a schema (default CISADM).

Writes:
  output/cisadm_views/<client>/
    index.csv
    README.md
    ddl/<VIEW_NAME>.sql
    all_views_ddl.sql
    view_select_logic/<VIEW_NAME>.sql   -- AS clause / select only
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import oracledb

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from oracle_client import ensure_oracle_client, load_env_file, normalize_oracle_dsn  # noqa: E402
from run_client_oracle_sql import client_connection  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export CISADM view DDL from Oracle.")
    parser.add_argument("--client", default="demo", help="Client alias from .env (default: demo).")
    parser.add_argument("--schema", default="CISADM", help="Schema owner (default: CISADM).")
    parser.add_argument(
        "--output-dir",
        default="output/cisadm_views",
        help="Base output directory.",
    )
    return parser.parse_args()


def list_views(cursor: oracledb.Cursor, schema: str) -> list[dict[str, object]]:
    cursor.execute(
        """
        SELECT view_name, text_length
        FROM all_views
        WHERE owner = :owner
        ORDER BY view_name
        """,
        {"owner": schema.upper()},
    )
    return [
        {"view_name": row[0], "text_length": row[1]}
        for row in cursor.fetchall()
    ]


def fetch_view_ddl(cursor: oracledb.Cursor, schema: str, view_name: str) -> str:
    cursor.execute(
        """
        SELECT DBMS_METADATA.GET_DDL('VIEW', :view_name, :owner) AS ddl
        FROM dual
        """,
        {"view_name": view_name, "owner": schema.upper()},
    )
    row = cursor.fetchone()
    if not row or row[0] is None:
        raise RuntimeError(f"No DDL returned for {schema}.{view_name}")
    ddl = row[0]
    if hasattr(ddl, "read"):
        ddl = ddl.read()
    return str(ddl).strip()


def extract_select_logic(ddl: str) -> str:
    """Return the SELECT portion (everything after the outer AS keyword)."""
    match = re.search(r"\sAS\s+", ddl, flags=re.IGNORECASE)
    if not match:
        return ddl
    return ddl[match.end() :].strip().rstrip(";")


def main() -> int:
    args = parse_args()
    config = load_env_file(ROOT / ".env")
    ensure_oracle_client(config)
    user, password, dsn = client_connection(config, args.client)
    schema = args.schema.upper()

    out_root = (ROOT / args.output_dir / args.client.lower()).resolve()
    ddl_dir = out_root / "ddl"
    select_dir = out_root / "view_select_logic"
    ddl_dir.mkdir(parents=True, exist_ok=True)
    select_dir.mkdir(parents=True, exist_ok=True)

    exported_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    index_rows: list[dict[str, str]] = []
    failures: list[str] = []

    with oracledb.connect(user=user, password=password, dsn=normalize_oracle_dsn(dsn)) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                BEGIN
                  DBMS_METADATA.SET_TRANSFORM_PARAM(
                    DBMS_METADATA.SESSION_TRANSFORM, 'SQLTERMINATOR', TRUE);
                  DBMS_METADATA.SET_TRANSFORM_PARAM(
                    DBMS_METADATA.SESSION_TRANSFORM, 'PRETTY', TRUE);
                END;
                """
            )
            views = list_views(cursor, schema)
            combined_parts: list[str] = [
                f"-- CISADM view DDL export",
                f"-- Client: {args.client}",
                f"-- Schema: {schema}",
                f"-- Exported: {exported_at}",
                f"-- View count: {len(views)}",
                "",
            ]

            for idx, view in enumerate(views, start=1):
                view_name = str(view["view_name"])
                print(f"[{idx}/{len(views)}] {view_name}", flush=True)
                try:
                    ddl = fetch_view_ddl(cursor, schema, view_name)
                    select_logic = extract_select_logic(ddl)
                    ddl_path = ddl_dir / f"{view_name}.sql"
                    select_path = select_dir / f"{view_name}.sql"
                    ddl_path.write_text(ddl + "\n", encoding="utf-8")
                    select_path.write_text(
                        f"-- SELECT logic for {schema}.{view_name}\n{select_logic}\n",
                        encoding="utf-8",
                    )
                    combined_parts.append(f"-- ----- {view_name} -----")
                    combined_parts.append(ddl)
                    combined_parts.append("")
                    index_rows.append(
                        {
                            "owner": schema,
                            "view_name": view_name,
                            "text_length": str(view["text_length"] or ""),
                            "ddl_file": f"ddl/{view_name}.sql",
                            "select_file": f"view_select_logic/{view_name}.sql",
                            "ddl_chars": str(len(ddl)),
                            "status": "ok",
                        }
                    )
                except oracledb.Error as exc:
                    msg = f"{view_name}: {exc}"
                    failures.append(msg)
                    index_rows.append(
                        {
                            "owner": schema,
                            "view_name": view_name,
                            "text_length": str(view["text_length"] or ""),
                            "ddl_file": "",
                            "select_file": "",
                            "ddl_chars": "",
                            "status": f"error: {exc}",
                        }
                    )

    combined_path = out_root / "all_views_ddl.sql"
    combined_path.write_text("\n".join(combined_parts) + "\n", encoding="utf-8")

    index_path = out_root / "index.csv"
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "owner",
                "view_name",
                "text_length",
                "ddl_chars",
                "ddl_file",
                "select_file",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(index_rows)

    readme = out_root / "README.md"
    readme.write_text(
        "\n".join(
            [
                f"# CISADM view DDL export ({args.client})",
                "",
                f"- **Schema:** `{schema}`",
                f"- **Exported:** {exported_at}",
                f"- **Views:** {len(views)}",
                f"- **Succeeded:** {len(views) - len(failures)}",
                f"- **Failed:** {len(failures)}",
                "",
                "## Files",
                "",
                "| Path | Description |",
                "| --- | --- |",
                "| `index.csv` | View inventory with file paths |",
                "| `all_views_ddl.sql` | Combined `CREATE OR REPLACE VIEW` statements |",
                "| `ddl/<VIEW_NAME>.sql` | Full DDL per view |",
                "| `view_select_logic/<VIEW_NAME>.sql` | SELECT logic only (after `AS`) |",
                "",
                "## Regenerate",
                "",
                "```bash",
                f"python3 scripts/local/export_cisadm_view_ddl.py --client {args.client}",
                "```",
                "",
            ]
            + (
                ["## Failures", ""]
                + [f"- `{line}`" for line in failures]
                + [""]
                if failures
                else []
            )
        ),
        encoding="utf-8",
    )

    print(f"\nExport root: {out_root}")
    print(f"Views exported: {len(views) - len(failures)} / {len(views)}")
    if failures:
        print(f"Failures: {len(failures)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
