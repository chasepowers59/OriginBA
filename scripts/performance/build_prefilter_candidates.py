#!/usr/bin/env python3
"""
Build domain pre-filter candidates from read-only CISADM dictionary extracts.

Inputs:
  - output/cisadm_dictionary/indexes.csv
  - output/cisadm_dictionary/index_columns.csv
  - output/cisadm_dictionary/columns.csv (optional but recommended)
  - output/cisadm_dictionary/workstream_coverage.csv (optional)
  - output/domain_designs_metadata.json (optional)

Outputs:
  - output/cisadm_dictionary/index_columns_enriched.csv
  - output/cisadm_dictionary/prefilter_candidates.csv
  - output/cisadm_dictionary/prefilter_candidates_summary.md
  - output/cisadm_dictionary/prefilter_top_by_table.md
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DICTIONARY_DIR = ROOT / "output" / "cisadm_dictionary"
DEFAULT_DOMAIN_META = ROOT / "output" / "domain_designs_metadata.json"


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required CSV file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _row_get_ci(row: Dict[str, str], key: str) -> str:
    key_upper = key.upper()
    for k, v in row.items():
        if (k or "").strip().upper() == key_upper:
            return (v or "").strip()
    return ""


def _to_int(value: str) -> int:
    try:
        return int((value or "").strip())
    except Exception:
        return 0


def _write_csv(path: Path, rows: Iterable[Dict[str, str]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _load_domain_tables(path: Path) -> set[str]:
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    tables = (payload or {}).get("tables", {}) or {}
    return {str(t).upper() for t in tables.keys()}


def _is_date_like(data_type: str) -> bool:
    dt = (data_type or "").strip().upper()
    return dt.startswith("DATE") or dt.startswith("TIMESTAMP")


def _build_index_lookup(indexes_rows: List[Dict[str, str]]) -> Dict[Tuple[str, str], Dict[str, str]]:
    out: Dict[Tuple[str, str], Dict[str, str]] = {}
    for row in indexes_rows:
        table_name = _row_get_ci(row, "TABLE_NAME").upper()
        index_name = _row_get_ci(row, "INDEX_NAME").upper()
        if not table_name or not index_name:
            continue
        out[(table_name, index_name)] = {
            "index_type": _row_get_ci(row, "INDEX_TYPE").upper(),
            "index_status": _row_get_ci(row, "STATUS").upper(),
            "index_visibility": _row_get_ci(row, "VISIBILITY").upper(),
            "index_partitioned": _row_get_ci(row, "PARTITIONED").upper(),
            "index_uniqueness": _row_get_ci(row, "UNIQUENESS").upper(),
        }
    return out


def _build_data_type_lookup(columns_rows: List[Dict[str, str]]) -> Dict[Tuple[str, str], str]:
    out: Dict[Tuple[str, str], str] = {}
    for row in columns_rows:
        table_name = _row_get_ci(row, "TABLE_NAME").upper()
        column_name = _row_get_ci(row, "COLUMN_NAME").upper()
        data_type = _row_get_ci(row, "DATA_TYPE").upper()
        if not table_name or not column_name:
            continue
        out[(table_name, column_name)] = data_type
    return out


def _build_workstream_lookup(rows: List[Dict[str, str]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for row in rows:
        table_name = _row_get_ci(row, "TABLE_NAME").upper() or _row_get_ci(row, "table_name").upper()
        workstreams = _row_get_ci(row, "WORKSTREAMS") or _row_get_ci(row, "workstreams")
        if table_name:
            out[table_name] = workstreams
    return out


def _priority(
    is_leading: bool,
    is_valid_visible: bool,
    is_date: bool,
    index_type: str,
) -> str:
    idx = (index_type or "").upper()
    if is_leading and is_valid_visible and is_date and "NORMAL" in idx:
        return "HIGH"
    if is_leading and is_valid_visible and "NORMAL" in idx:
        return "MEDIUM"
    if is_leading and is_valid_visible:
        return "MEDIUM"
    return "LOW"


def _guidance(is_leading: bool, is_date: bool, is_valid_visible: bool) -> str:
    if is_leading and is_valid_visible and is_date:
        return "Primary candidate for mandatory rolling window pre-filter."
    if is_leading and is_valid_visible:
        return "Good candidate for equality or IN pre-filter."
    if is_leading and not is_valid_visible:
        return "Leading column found but index is not VALID/VISIBLE; verify with DBA."
    return "Not a leading indexed column; avoid as first pre-filter predicate."


def _write_summary(
    path: Path,
    enriched_rows: List[Dict[str, str]],
    candidate_rows: List[Dict[str, str]],
) -> None:
    total_rows = len(enriched_rows)
    leading_rows = sum(1 for r in enriched_rows if r["is_leading_column"] == "Y")
    valid_visible_rows = sum(1 for r in enriched_rows if r["is_valid_visible"] == "Y")
    candidate_date_rows = sum(1 for r in candidate_rows if r["is_date_like"] == "Y")
    domain_candidate_rows = sum(1 for r in candidate_rows if r["in_domain_metadata"] == "Y")

    per_table: Dict[str, int] = {}
    for row in candidate_rows:
        table_name = row["table_name"]
        per_table[table_name] = per_table.get(table_name, 0) + 1
    top_tables = sorted(per_table.items(), key=lambda kv: (-kv[1], kv[0]))[:20]

    lines = [
        "# Prefilter Candidate Summary",
        "",
        "## Totals",
        f"- Indexed column rows analyzed: {total_rows}",
        f"- Leading indexed columns: {leading_rows}",
        f"- Valid + visible index column rows: {valid_visible_rows}",
        f"- Recommended prefilter candidates: {len(candidate_rows)}",
        f"- Candidate columns that are date-like: {candidate_date_rows}",
        f"- Candidate columns in domain metadata: {domain_candidate_rows}",
        "",
        "## Top Tables By Candidate Count",
    ]
    if not top_tables:
        lines.append("- None")
    else:
        lines.extend([f"- {table}: {count}" for table, count in top_tables])

    lines.extend(
        [
            "",
            "## Usage Notes",
            "- Use leading indexed date columns first for rolling-window domain pre-filters.",
            "- For non-date candidates, use equality/IN pre-filters and pair with a date window when possible.",
            "- After pre-filtering on indexed columns, include additional business fields freely in the report.",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_top_by_table(
    path: Path,
    candidate_rows: List[Dict[str, str]],
    top_per_table: int,
) -> None:
    by_table: Dict[str, List[Dict[str, str]]] = {}
    for row in candidate_rows:
        by_table.setdefault(row["table_name"], []).append(row)

    lines: List[str] = [
        "# Top Prefilters By Table",
        "",
        "Leading indexed columns only (VALID + VISIBLE indexes).",
        "",
    ]

    if not by_table:
        lines.append("No candidates found.")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    for table_name in sorted(by_table.keys()):
        rows = sorted(
            by_table[table_name],
            key=lambda r: (
                priority_order.get(r["prefilter_priority"], 9),
                0 if r["is_date_like"] == "Y" else 1,
                r["column_name"],
                r["index_name"],
            ),
        )
        selected = rows[: max(top_per_table, 1)]

        workstream = next((r["workstreams"] for r in rows if r.get("workstreams")), "")
        lines.extend(
            [
                f"## {table_name}",
                f"- Workstreams: {workstream or 'N/A'}",
                f"- Total candidates: {len(rows)}",
                f"- Top {len(selected)} candidate(s):",
            ]
        )

        for i, row in enumerate(selected, start=1):
            dtype = row.get("data_type") or "UNKNOWN"
            priority = row.get("prefilter_priority") or "LOW"
            idx = row.get("index_name") or ""
            guidance = row.get("design_guidance") or ""
            lines.append(
                f"- {i}. {row['column_name']} ({dtype}) [{priority}] via {idx} - {guidance}"
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dictionary-dir",
        default=str(DEFAULT_DICTIONARY_DIR),
        help="Directory containing dictionary extraction CSV files.",
    )
    parser.add_argument(
        "--domain-meta",
        default=str(DEFAULT_DOMAIN_META),
        help="Path to domain_designs_metadata.json (optional).",
    )
    parser.add_argument(
        "--enriched-out",
        default="index_columns_enriched.csv",
        help="Enriched index-column output CSV filename.",
    )
    parser.add_argument(
        "--candidates-out",
        default="prefilter_candidates.csv",
        help="Candidate output CSV filename.",
    )
    parser.add_argument(
        "--summary-out",
        default="prefilter_candidates_summary.md",
        help="Summary markdown filename.",
    )
    parser.add_argument(
        "--top-by-table-out",
        default="prefilter_top_by_table.md",
        help="Top-candidates markdown grouped by table.",
    )
    parser.add_argument(
        "--top-per-table",
        type=int,
        default=3,
        help="Maximum number of candidates to list per table in grouped markdown.",
    )
    args = parser.parse_args()

    dictionary_dir = Path(args.dictionary_dir).resolve()
    dictionary_dir.mkdir(parents=True, exist_ok=True)

    indexes_csv = dictionary_dir / "indexes.csv"
    index_columns_csv = dictionary_dir / "index_columns.csv"
    columns_csv = dictionary_dir / "columns.csv"
    workstream_coverage_csv = dictionary_dir / "workstream_coverage.csv"
    domain_meta = Path(args.domain_meta).resolve()

    indexes_rows = _read_csv_rows(indexes_csv)
    index_columns_rows = _read_csv_rows(index_columns_csv)
    columns_rows = _read_csv_rows(columns_csv) if columns_csv.exists() else []
    workstream_rows = _read_csv_rows(workstream_coverage_csv) if workstream_coverage_csv.exists() else []

    index_lookup = _build_index_lookup(indexes_rows)
    data_type_lookup = _build_data_type_lookup(columns_rows)
    workstream_lookup = _build_workstream_lookup(workstream_rows)
    domain_tables = _load_domain_tables(domain_meta)

    enriched_rows: List[Dict[str, str]] = []
    candidate_rows: List[Dict[str, str]] = []

    for row in index_columns_rows:
        table_name = _row_get_ci(row, "TABLE_NAME").upper()
        index_name = _row_get_ci(row, "INDEX_NAME").upper()
        column_name = _row_get_ci(row, "COLUMN_NAME").upper()
        pos = _to_int(_row_get_ci(row, "COLUMN_POSITION"))
        if not table_name or not index_name or not column_name:
            continue

        idx = index_lookup.get((table_name, index_name), {})
        index_type = idx.get("index_type", "")
        index_status = idx.get("index_status", "")
        index_visibility = idx.get("index_visibility", "")
        index_partitioned = idx.get("index_partitioned", "")
        index_uniqueness = idx.get("index_uniqueness", "")

        is_leading = pos == 1
        is_valid = index_status == "VALID"
        is_visible = index_visibility in {"", "VISIBLE"}
        is_valid_visible = is_valid and is_visible
        data_type = data_type_lookup.get((table_name, column_name), "")
        is_date = _is_date_like(data_type)
        priority = _priority(is_leading, is_valid_visible, is_date, index_type)

        record = {
            "table_name": table_name,
            "column_name": column_name,
            "data_type": data_type,
            "index_name": index_name,
            "column_position": str(pos),
            "index_type": index_type,
            "index_status": index_status,
            "index_visibility": index_visibility or "VISIBLE",
            "index_partitioned": index_partitioned,
            "index_uniqueness": index_uniqueness,
            "is_leading_column": "Y" if is_leading else "N",
            "is_valid_visible": "Y" if is_valid_visible else "N",
            "is_date_like": "Y" if is_date else "N",
            "in_domain_metadata": "Y" if table_name in domain_tables else "N",
            "workstreams": workstream_lookup.get(table_name, ""),
            "prefilter_priority": priority,
            "design_guidance": _guidance(is_leading, is_date, is_valid_visible),
        }
        enriched_rows.append(record)

        if is_leading and is_valid_visible:
            candidate_rows.append(record)

    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    enriched_rows.sort(
        key=lambda r: (
            r["table_name"],
            priority_order.get(r["prefilter_priority"], 9),
            r["index_name"],
            _to_int(r["column_position"]),
            r["column_name"],
        )
    )
    candidate_rows.sort(
        key=lambda r: (
            r["table_name"],
            priority_order.get(r["prefilter_priority"], 9),
            r["column_name"],
            r["index_name"],
        )
    )

    enriched_out = dictionary_dir / args.enriched_out
    candidates_out = dictionary_dir / args.candidates_out
    summary_out = dictionary_dir / args.summary_out
    top_by_table_out = dictionary_dir / args.top_by_table_out

    fieldnames = [
        "table_name",
        "column_name",
        "data_type",
        "index_name",
        "column_position",
        "index_type",
        "index_status",
        "index_visibility",
        "index_partitioned",
        "index_uniqueness",
        "is_leading_column",
        "is_valid_visible",
        "is_date_like",
        "in_domain_metadata",
        "workstreams",
        "prefilter_priority",
        "design_guidance",
    ]
    _write_csv(enriched_out, enriched_rows, fieldnames)
    _write_csv(candidates_out, candidate_rows, fieldnames)
    _write_summary(summary_out, enriched_rows, candidate_rows)
    _write_top_by_table(top_by_table_out, candidate_rows, args.top_per_table)

    print(f"[PASS] Enriched index columns written: {enriched_out}")
    print(f"[PASS] Prefilter candidates written: {candidates_out}")
    print(f"[PASS] Prefilter summary written: {summary_out}")
    print(f"[PASS] Top prefilters by table written: {top_by_table_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
