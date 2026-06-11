#!/usr/bin/env python3
"""
Build comprehensive FK/join map for workstream physical tables.

Merges:
  - Oracle FK rows from output/cisadm_dictionary/constraint_columns.csv (type R)
  - Domain join inventory (physical tables only)
  - output/workstream_physical_join_paths.json canonical chains

Output:
  - output/cisadm_dictionary/fk_join_map_full.csv
  - output/cisadm_dictionary/fk_join_map_summary.md
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
CONSTRAINT_COLS = ROOT / "output" / "cisadm_dictionary" / "constraint_columns.csv"
JOIN_PATHS = ROOT / "output" / "workstream_physical_join_paths.json"
PHYSICAL_CATALOG = ROOT / "output" / "workstream_physical_catalog.json"
OUT_CSV = ROOT / "output" / "cisadm_dictionary" / "fk_join_map_full.csv"
OUT_MD = ROOT / "output" / "cisadm_dictionary" / "fk_join_map_summary.md"


def _load_workstream_tables() -> Set[str]:
    payload = json.loads(PHYSICAL_CATALOG.read_text(encoding="utf-8"))
    tables: Set[str] = set()
    for ws in (payload.get("workstreams") or {}).values():
        for t in ws.get("tables") or []:
            tables.add(t.upper())
    return tables


def _load_oracle_fks(ws_tables: Set[str]) -> List[dict]:
    if not CONSTRAINT_COLS.exists():
        return []
    # Need parent table from constraints - parse from constraint_columns only has child side
    # For R constraints, we have child table/column; parent requires constraints.csv or fk_join_map.csv
    fk_map = ROOT / "output" / "cisadm_dictionary" / "fk_join_map.csv"
    rows: List[dict] = []
    if fk_map.exists():
        with fk_map.open("r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                child = (row.get("CHILD_TABLE_NAME") or row.get("child_table_name") or "").upper()
                parent = (row.get("PARENT_TABLE_NAME") or row.get("parent_table_name") or "").upper()
                if child not in ws_tables and parent not in ws_tables:
                    continue
                rows.append(
                    {
                        "child_table": child,
                        "child_column": (row.get("CHILD_COLUMN_NAME") or row.get("child_column_name") or "").upper(),
                        "parent_table": parent,
                        "parent_column": (row.get("PARENT_COLUMN_NAME") or row.get("parent_column_name") or "").upper(),
                        "fk_name": row.get("FK_NAME") or row.get("fk_name") or "",
                        "source": "oracle_all_constraints",
                    }
                )
    return rows


def _load_domain_joins(ws_tables: Set[str]) -> List[dict]:
    payload = json.loads(JOIN_PATHS.read_text(encoding="utf-8"))
    rows = []
    for j in payload.get("domain_inferred_joins") or []:
        child = j.get("child_table", "").upper()
        parent = j.get("parent_table", "").upper()
        if child not in ws_tables and parent not in ws_tables:
            continue
        rows.append({**j, "fk_name": ""})
    return rows


def _load_canonical_joins(ws_tables: Set[str]) -> List[dict]:
    payload = json.loads(JOIN_PATHS.read_text(encoding="utf-8"))
    rows: List[dict] = []
    for ws_key, ws_data in (payload.get("workstreams") or {}).items():
        for chain in ws_data.get("canonical_chains") or []:
            for expr in chain.get("join_sql") or []:
                if "<child>" in expr:
                    continue
                for clause in re.split(r"\band\b", expr, flags=re.I):
                    m = re.match(
                        r"([A-Z0-9_]+)\.([A-Z0-9_]+)\s*=\s*([A-Z0-9_]+)\.([A-Z0-9_]+)",
                        clause.strip(),
                        re.I,
                    )
                    if not m:
                        continue
                    lt, lc, rt, rc = (x.upper() for x in m.groups())
                    if lt not in ws_tables and rt not in ws_tables:
                        continue
                    rows.append(
                        {
                            "child_table": lt,
                            "child_column": lc,
                            "parent_table": rt,
                            "parent_column": rc,
                            "fk_name": chain.get("name", ""),
                            "source": f"canonical_chain:{ws_key}",
                            "workstream": ws_key,
                        }
                    )
    return rows


def _dedupe(rows: List[dict]) -> List[dict]:
    seen: Set[Tuple[str, str, str, str]] = set()
    out: List[dict] = []
    for row in rows:
        key = (
            row.get("child_table", "").upper(),
            row.get("child_column", "").upper(),
            row.get("parent_table", "").upper(),
            row.get("parent_column", "").upper(),
        )
        if not key[0] or not key[2]:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return sorted(out, key=lambda r: (r["child_table"], r["child_column"], r["parent_table"]))


def main() -> int:
    if not PHYSICAL_CATALOG.exists():
        raise SystemExit("Run scripts/build_workstream_physical_catalog.py first.")

    ws_tables = _load_workstream_tables()
    merged = _dedupe(
        _load_oracle_fks(ws_tables) + _load_domain_joins(ws_tables) + _load_canonical_joins(ws_tables)
    )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "child_table",
        "child_column",
        "parent_table",
        "parent_column",
        "join_sql",
        "source",
        "fk_name",
        "workstream",
        "domain_name",
        "join_type",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in merged:
            row = dict(row)
            row["join_sql"] = (
                f"{row['child_table']}.{row['child_column']} = "
                f"{row['parent_table']}.{row['parent_column']}"
            )
            writer.writerow(row)

    by_source: Dict[str, int] = {}
    for row in merged:
        by_source[row.get("source", "unknown")] = by_source.get(row.get("source", "unknown"), 0) + 1

    lines = [
        "# FK / Join Map Summary (Physical Workstream Tables)",
        "",
        f"- Workstream physical tables: {len(ws_tables)}",
        f"- Total deduped join rows: {len(merged)}",
        "",
        "## By Source",
    ]
    for src, cnt in sorted(by_source.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- {src}: {cnt}")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[PASS] FK join map: {OUT_CSV} ({len(merged)} rows)")
    print(f"[PASS] Summary: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
