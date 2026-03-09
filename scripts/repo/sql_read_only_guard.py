#!/usr/bin/env python3
"""
Guard that designated SQL validation folders stay read-only.

Fails if SQL files contain write-capable statements/keywords.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

DEFAULT_PATHS = [
    "sql/performance/billed_usage/validation",
    "sql/diagnostics/cisadm_dictionary",
]

# Conservative blocklist for write/DDL/admin operations.
BANNED = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "CREATE",
    "ALTER",
    "DROP",
    "TRUNCATE",
    "RENAME",
    "GRANT",
    "REVOKE",
    "COMMENT",
    "ANALYZE",
    "EXPLAIN PLAN",
    "DBMS_STATS",
    "COMMIT",
    "ROLLBACK",
    "SAVEPOINT",
    "LOCK TABLE",
}

def strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\r\n]*", " ", sql)
    return sql


def strip_string_literals(sql: str) -> str:
    # Replace quoted literals with spaces so keywords in strings do not trigger false positives.
    return re.sub(r"'(?:''|[^'])*'", " ", sql)


def scan_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = strip_comments(text)
    text = strip_string_literals(text)
    upper = text.upper()

    hits: list[str] = []
    for banned in sorted(BANNED):
        # Phrase keywords (e.g. EXPLAIN PLAN)
        if " " in banned:
            if banned in upper:
                hits.append(banned)
            continue

        # Single token keywords
        pattern = rf"\b{re.escape(banned)}\b"
        if re.search(pattern, upper):
            hits.append(banned)

    # Deduplicate while preserving order
    uniq: list[str] = []
    seen: set[str] = set()
    for h in hits:
        if h not in seen:
            uniq.append(h)
            seen.add(h)
    return uniq


def iter_sql_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_file() and p.suffix.lower() == ".sql":
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.sql")))
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", help="Files or directories to scan")
    args = parser.parse_args()

    raw_paths = args.paths if args.paths else DEFAULT_PATHS
    paths = [Path(p).resolve() for p in raw_paths]
    files = iter_sql_files(paths)

    if not files:
        print("[FAIL] No SQL files found for read-only scan.")
        return 2

    failed = 0
    for file in files:
        hits = scan_file(file)
        if hits:
            failed += 1
            print(f"[FAIL] {file}: banned keyword(s): {', '.join(hits)}")
        else:
            print(f"[PASS] {file}: read-only keyword scan clean.")

    if failed:
        print(f"[FAIL] Read-only SQL guard failed for {failed} file(s).")
        return 1

    print("[PASS] Read-only SQL guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
