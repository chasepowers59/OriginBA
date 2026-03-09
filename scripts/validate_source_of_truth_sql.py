"""
Validate SQL table references against source-of-truth metadata:
  - output/workstream_reporting_dictionary.json
  - output/domain_designs_metadata.json

Usage:
  python scripts/validate_source_of_truth_sql.py
  python scripts/validate_source_of_truth_sql.py sql/smartcity_9_workstream_kpis.sql
  python scripts/validate_source_of_truth_sql.py sql/performance/bill_cycle/bill_cycle_active_validation.sql
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQL_DIR = ROOT / "sql"
WORKSTREAM_DICT = ROOT / "output" / "workstream_reporting_dictionary.json"
DOMAIN_META = ROOT / "output" / "domain_designs_metadata.json"

TABLE_REF_RE = re.compile(r"\b(?:FROM|JOIN)\s+([A-Z0-9_]+(?:\.[A-Z0-9_]+)?)\b", re.IGNORECASE)
IGNORE_TABLES = {"DUAL", "TABLE"}
SUPPLEMENTAL_ALLOWED_TABLES = {
    # Used in governed SQL but not always present in exported metadata snapshots.
    "CI_CC",
    "CI_LETTER_TMPL",
    "CI_PAY",
    "CI_TNDR_CTL",
    "CI_COLL_CL_L",
    "CI_CC_CL_L",
    "CI_CC_TYPE_L",
    "CI_DEBT_CL_L",
    "CI_SA_TYPE",
    "CI_ALERT_TYPE_L",
    "CI_TENDER_TYPE_L",
    # Core usage/reporting tables may be absent from partial metadata snapshots.
    "CI_ACCT",
    "CI_SA",
    "C1_USAGE",
    "D1_USAGE",
    "D1_USAGE_SCALAR_DTL",
    "CI_CUST_CL_L",
    "CI_BILL_CYC_L",
    "CI_LOOKUP_VAL_L",
    "CI_SA_SP",
    "CI_ACCT_PER",
    "CI_TNDR_SRCE_L",
    # Oracle dictionary views used by read-only preflight checks.
    "SESSION_PRIVS",
    "USER_TAB_PRIVS_RECD",
    # Oracle dictionary views used by discovery workflows.
    "ALL_TABLES",
    "ALL_TAB_COMMENTS",
    "ALL_TAB_COLUMNS",
    "ALL_COL_COMMENTS",
    "ALL_CONSTRAINTS",
    "ALL_CONS_COLUMNS",
    "ALL_INDEXES",
    "ALL_IND_COLUMNS",
}


def _load_known_tables() -> set[str]:
    known: set[str] = set()

    if WORKSTREAM_DICT.exists():
        d = json.loads(WORKSTREAM_DICT.read_text(encoding="utf-8"))
        for ws in d.values():
            tables = ws.get("tables", {})
            for t in tables.keys():
                known.add(t.upper())

    if DOMAIN_META.exists():
        d = json.loads(DOMAIN_META.read_text(encoding="utf-8"))
        tables = d.get("tables", {})
        for t in tables.keys():
            known.add(t.upper())

    known.update(SUPPLEMENTAL_ALLOWED_TABLES)
    return known


def _iter_sql_files(args: list[str]) -> list[Path]:
    if not args:
        return sorted(DEFAULT_SQL_DIR.rglob("*.sql"))

    files: list[Path] = []
    for a in args:
        p = Path(a).resolve()
        if p.is_file() and p.suffix.lower() == ".sql":
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.sql")))
    return files


def _extract_table_refs(sql_text: str) -> set[str]:
    # Strip SQL comments so "FROM" and "JOIN" in comments do not generate false positives.
    sql_text = re.sub(r"/\*.*?\*/", " ", sql_text, flags=re.DOTALL)
    sql_text = re.sub(r"--[^\r\n]*", " ", sql_text)

    # Capture CTE names declared in a WITH clause so we do not flag them as base tables.
    cte_names = {m.group(1).upper() for m in re.finditer(r"\b([A-Z0-9_]+)\s+AS\s*\(", sql_text, re.IGNORECASE)}

    refs: set[str] = set()
    for m in TABLE_REF_RE.finditer(sql_text):
        token = m.group(1).upper()
        table = token.split(".")[-1]
        if table in IGNORE_TABLES:
            continue
        if table in cte_names:
            continue
        refs.add(table)
    return refs


def main() -> int:
    known = _load_known_tables()
    files = _iter_sql_files(sys.argv[1:])
    if not files:
        print("[FAIL] No SQL files found.")
        return 2

    failures = []
    for f in files:
        if not f.exists():
            failures.append((str(f), "file_not_found"))
            continue
        refs = _extract_table_refs(f.read_text(encoding="utf-8", errors="ignore"))
        unknown = sorted([t for t in refs if t not in known])
        if unknown:
            failures.append((str(f), ", ".join(unknown)))
            print(f"[FAIL] {f}: unknown table(s): {', '.join(unknown)}")
        else:
            print(f"[PASS] {f}: all table refs found in source-of-truth metadata.")

    if failures:
        print(f"[FAIL] Source-of-truth SQL validation failed for {len(failures)} file(s).")
        return 1

    print("[PASS] Source-of-truth SQL validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
