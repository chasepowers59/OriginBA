#!/usr/bin/env python3
"""
Build CISADM dictionary coverage artifacts from read-only extraction outputs.

Inputs:
  - output/cisadm_dictionary/tables.csv (preferred)
  - output/workstream_reporting_dictionary.json
  - output/domain_designs_metadata.json

Outputs:
  - output/cisadm_dictionary/workstream_coverage.csv
  - output/cisadm_dictionary/coverage_summary.md
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DICTIONARY_DIR = ROOT / "output" / "cisadm_dictionary"
DEFAULT_WORKSTREAM_DICT = ROOT / "output" / "workstream_reporting_dictionary.json"
DEFAULT_DOMAIN_META = ROOT / "output" / "domain_designs_metadata.json"


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _row_get_case_insensitive(row: Dict[str, str], key: str) -> str:
    key_upper = key.upper()
    for k, v in row.items():
        if (k or "").strip().upper() == key_upper:
            return (v or "").strip()
    return ""


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required CSV file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _load_table_stats(dictionary_dir: Path) -> Dict[str, Dict[str, Optional[int]]]:
    tables_csv = dictionary_dir / "tables.csv"
    if not tables_csv.exists():
        return {}
    stats: Dict[str, Dict[str, Optional[int]]] = {}
    rows = _read_csv_rows(tables_csv)
    for row in rows:
        name = _row_get_case_insensitive(row, "TABLE_NAME").upper()
        if not name:
            continue
        num_rows_raw = _row_get_case_insensitive(row, "NUM_ROWS")
        try:
            num_rows = int(num_rows_raw) if num_rows_raw else None
        except ValueError:
            num_rows = None
        stats[name] = {
            "num_rows": num_rows,
            "last_analyzed": _row_get_case_insensitive(row, "LAST_ANALYZED") or None,
        }
    return stats


def _stats_population_status(num_rows: Optional[int]) -> str:
    if num_rows is None:
        return "unknown"
    if num_rows == 0:
        return "empty"
    return "populated"


def _stats_stale(last_analyzed: Optional[str], stale_days: int = 30) -> str:
    if not last_analyzed:
        return "unknown"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            analyzed = datetime.strptime(last_analyzed[:19], fmt)
            cutoff = datetime.now() - timedelta(days=stale_days)
            return "stale" if analyzed < cutoff else "fresh"
        except ValueError:
            continue
    return "unknown"


def _load_discovered_tables(dictionary_dir: Path) -> Set[str]:
    tables_csv = dictionary_dir / "tables.csv"
    columns_csv = dictionary_dir / "columns.csv"

    if tables_csv.exists():
        rows = _read_csv_rows(tables_csv)
        values = {_row_get_case_insensitive(r, "TABLE_NAME").upper() for r in rows}
        return {v for v in values if v}

    if columns_csv.exists():
        rows = _read_csv_rows(columns_csv)
        values = {_row_get_case_insensitive(r, "TABLE_NAME").upper() for r in rows}
        return {v for v in values if v}

    raise FileNotFoundError(
        f"Neither {tables_csv} nor {columns_csv} exists. Run dictionary discovery first."
    )


def _load_workstream_tables(path: Path) -> Dict[str, Set[str]]:
    payload = _read_json(path)
    mapping: Dict[str, Set[str]] = {}

    for workstream, details in payload.items():
        tables = (details or {}).get("tables", {}) or {}
        for table_name in tables.keys():
            t = table_name.upper()
            mapping.setdefault(t, set()).add(workstream)
    return mapping


def _load_domain_tables(path: Path) -> Set[str]:
    payload = _read_json(path)
    tables = (payload or {}).get("tables", {}) or {}
    return {t.upper() for t in tables.keys()}


def _write_csv(path: Path, rows: Iterable[Dict[str, str]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_summary_md(
    path: Path,
    discovered: Set[str],
    workstream_map: Dict[str, Set[str]],
    domain_tables: Set[str],
) -> None:
    workstream_tables = set(workstream_map.keys())
    missing_from_discovery = sorted(workstream_tables - discovered)
    discovered_not_in_workstream = sorted(discovered - workstream_tables)
    domain_missing_from_discovery = sorted(domain_tables - discovered)

    lines = [
        "# CISADM Dictionary Coverage Summary",
        "",
        "## Totals",
        f"- Discovered tables (read-only dictionary extract): {len(discovered)}",
        f"- Workstream dictionary tables: {len(workstream_tables)}",
        f"- Domain metadata tables: {len(domain_tables)}",
        f"- Workstream tables found in discovery: {len(workstream_tables & discovered)}",
        f"- Domain tables found in discovery: {len(domain_tables & discovered)}",
        "",
        "## Workstream Tables Missing From Discovery",
        f"- Count: {len(missing_from_discovery)}",
    ]
    lines.extend([f"- {name}" for name in missing_from_discovery[:100]])

    lines.extend(
        [
            "",
            "## Domain Metadata Tables Missing From Discovery",
            f"- Count: {len(domain_missing_from_discovery)}",
        ]
    )
    lines.extend([f"- {name}" for name in domain_missing_from_discovery[:100]])

    lines.extend(
        [
            "",
            "## Discovered Tables Not In Workstream Dictionary",
            f"- Count: {len(discovered_not_in_workstream)}",
        ]
    )
    lines.extend([f"- {name}" for name in discovered_not_in_workstream[:100]])

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dictionary-dir",
        default=str(DEFAULT_DICTIONARY_DIR),
        help="Directory containing tables.csv/columns.csv outputs from dictionary discovery.",
    )
    parser.add_argument(
        "--workstream-dict",
        default=str(DEFAULT_WORKSTREAM_DICT),
        help="Path to workstream_reporting_dictionary.json",
    )
    parser.add_argument(
        "--domain-meta",
        default=str(DEFAULT_DOMAIN_META),
        help="Path to domain_designs_metadata.json",
    )
    parser.add_argument(
        "--out-csv",
        default="workstream_coverage.csv",
        help="Output CSV filename in dictionary directory.",
    )
    parser.add_argument(
        "--out-md",
        default="coverage_summary.md",
        help="Output Markdown filename in dictionary directory.",
    )
    args = parser.parse_args()

    dictionary_dir = Path(args.dictionary_dir).resolve()
    workstream_dict = Path(args.workstream_dict).resolve()
    domain_meta = Path(args.domain_meta).resolve()
    out_csv = dictionary_dir / args.out_csv
    out_md = dictionary_dir / args.out_md

    dictionary_dir.mkdir(parents=True, exist_ok=True)

    discovered = _load_discovered_tables(dictionary_dir)
    table_stats = _load_table_stats(dictionary_dir)
    workstream_map = _load_workstream_tables(workstream_dict)
    domain_tables = _load_domain_tables(domain_meta)

    all_tables = sorted(discovered | set(workstream_map.keys()) | domain_tables)
    rows: List[Dict[str, str]] = []
    empty_workstream = 0
    stale_workstream = 0
    for table in all_tables:
        ws = sorted(workstream_map.get(table, set()))
        stat = table_stats.get(table, {})
        num_rows = stat.get("num_rows")
        last_analyzed = stat.get("last_analyzed")
        population_status = _stats_population_status(num_rows if isinstance(num_rows, int) else None)
        stats_freshness = _stats_stale(last_analyzed if isinstance(last_analyzed, str) else None)
        if table in workstream_map:
            if population_status == "empty":
                empty_workstream += 1
            if stats_freshness == "stale":
                stale_workstream += 1
        rows.append(
            {
                "table_name": table,
                "discovered_in_cisadm_dictionary": "Y" if table in discovered else "N",
                "in_workstream_dictionary": "Y" if table in workstream_map else "N",
                "workstreams": "|".join(ws),
                "in_domain_metadata": "Y" if table in domain_tables else "N",
                "num_rows": "" if num_rows is None else str(num_rows),
                "last_analyzed": last_analyzed or "",
                "stats_population_status": population_status,
                "stats_freshness": stats_freshness,
            }
        )

    _write_csv(
        out_csv,
        rows,
        [
            "table_name",
            "discovered_in_cisadm_dictionary",
            "in_workstream_dictionary",
            "workstreams",
            "in_domain_metadata",
            "num_rows",
            "last_analyzed",
            "stats_population_status",
            "stats_freshness",
        ],
    )
    _write_summary_md(out_md, discovered, workstream_map, domain_tables)
    print(f"[INFO] Workstream tables with NUM_ROWS=0: {empty_workstream}")
    print(f"[INFO] Workstream tables with stale stats: {stale_workstream}")

    print(f"[PASS] Coverage CSV written: {out_csv}")
    print(f"[PASS] Coverage summary written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
