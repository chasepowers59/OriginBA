#!/usr/bin/env python3
"""
Build unified AI context bundle for Oracle C2M CISADM SQL and Jaspersoft work.

Merges workstream dictionary, physical stats, domain joins, lookup hints,
core join patterns, and optional per-client table health results.

Usage:
  python3 scripts/build_ai_cisadm_context.py
  python3 scripts/build_ai_cisadm_context.py --client demo
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_WORKSTREAM_DICT = ROOT / "output" / "workstream_reporting_dictionary.json"
DEFAULT_DOMAIN_META = ROOT / "output" / "domain_designs_metadata.json"
DEFAULT_TABLES_CSV = ROOT / "output" / "cisadm_dictionary" / "tables.csv"
DEFAULT_DOMAIN_JOINS = ROOT / "output" / "standard_offering_domain_inventory" / "domain_joins_master.csv"
DEFAULT_FK_JOIN_MAP = ROOT / "output" / "cisadm_dictionary" / "fk_join_map_full.csv"
DEFAULT_FK_JOIN_MAP_LEGACY = ROOT / "output" / "cisadm_dictionary" / "fk_join_map.csv"
DEFAULT_PHYSICAL_CATALOG = ROOT / "output" / "workstream_physical_catalog.json"
DEFAULT_JOIN_PATHS = ROOT / "output" / "workstream_physical_join_paths.json"
DEFAULT_CD_INVENTORY = ROOT / "output" / "cd_field_inventory.json"
DEFAULT_OUT = ROOT / "output" / "ai_cisadm_context.json"

CORE_JOIN_PATTERNS = [
    {
        "description": "Account to service agreement",
        "child_table": "CI_SA",
        "parent_table": "CI_ACCT",
        "join_sql": "CI_ACCT.ACCT_ID = CI_SA.ACCT_ID",
    },
    {
        "description": "Service agreement to SA/SP link (detect missing SP)",
        "child_table": "CI_SA_SP",
        "parent_table": "CI_SA",
        "join_sql": "CI_SA.SA_ID = CI_SA_SP.SA_ID",
    },
    {
        "description": "Usage transaction envelope",
        "child_table": "C1_USAGE",
        "parent_table": "CI_SA",
        "join_sql": "CI_SA.SA_ID = C1_USAGE.SA_ID",
    },
    {
        "description": "MDM usage detail",
        "child_table": "D1_USAGE",
        "parent_table": "C1_USAGE",
        "join_sql": "C1_USAGE.USAGE_ID = D1_USAGE.USG_EXT_ID",
    },
    {
        "description": "Scalar usage detail",
        "child_table": "D1_USAGE_SCALAR_DTL",
        "parent_table": "D1_USAGE",
        "join_sql": "D1_USAGE.D1_USAGE_ID = D1_USAGE_SCALAR_DTL.D1_USAGE_ID",
    },
    {
        "description": "Bill to bill segment",
        "child_table": "CI_BSEG",
        "parent_table": "CI_BILL",
        "join_sql": "CI_BILL.BILL_ID = CI_BSEG.BILL_ID",
    },
    {
        "description": "Account to primary customer",
        "child_table": "CI_ACCT_PER",
        "parent_table": "CI_ACCT",
        "join_sql": "CI_ACCT.ACCT_ID = CI_ACCT_PER.ACCT_ID AND CI_ACCT_PER.MAIN_CUST_SW = 'Y'",
    },
    {
        "description": "Primary customer name",
        "child_table": "CI_PER_NAME",
        "parent_table": "CI_ACCT_PER",
        "join_sql": "CI_ACCT_PER.PER_ID = CI_PER_NAME.PER_ID AND CI_PER_NAME.NAME_TYPE_FLG = 'PRIM'",
    },
]

SLICE_HINTS = {
    "CI_SA": {
        "all_rows": "Full SA population",
        "active_only": "SA_STATUS_FLG = '20'",
    },
    "CI_FT": {
        "frozen_billing": "FREEZE_SW = 'Y'",
        "governed_arrears": (
            "FREEZE_SW = 'Y' AND NOT_IN_ARS_SW = 'N' "
            "AND FT_TYPE_FLG NOT IN ('PS','PX') AND ARS_DT IS NOT NULL"
        ),
    },
    "D1_USAGE": {
        "sent_usage": "BO_STATUS_CD = 'SENT'",
    },
    "C1_USAGE": {
        "processed": "BO_STATUS_CD = 'BD-PROC'",
    },
}


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _row_get(row: Dict[str, str], key: str) -> str:
    key_upper = key.upper()
    for k, v in row.items():
        if (k or "").strip().upper() == key_upper:
            return (v or "").strip()
    return ""


def _load_table_stats(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {}
    stats: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            name = _row_get(row, "TABLE_NAME").upper()
            if not name:
                continue
            num_rows_raw = _row_get(row, "NUM_ROWS")
            try:
                num_rows = int(num_rows_raw) if num_rows_raw else None
            except ValueError:
                num_rows = None
            stats[name] = {
                "num_rows": num_rows,
                "last_analyzed": _row_get(row, "LAST_ANALYZED") or None,
                "stats_population_status": _stats_status(num_rows),
            }
    return stats


def _stats_status(num_rows: Optional[int]) -> str:
    if num_rows is None:
        return "unknown"
    if num_rows == 0:
        return "empty"
    return "populated"


def _is_physical_table(name: str) -> bool:
    n = (name or "").upper()
    if n.startswith("CMS_") or "_VW" in n or n.startswith("C1_BI_"):
        return False
    return bool(n)


def _load_domain_joins(path: Path) -> Dict[str, List[dict]]:
    if not path.exists():
        return {}
    by_table: Dict[str, List[dict]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            left = (row.get("left_table") or "").upper()
            right = (row.get("right_table") or "").upper()
            if not _is_physical_table(left) or not _is_physical_table(right):
                continue
            entry = {
                "domain_name": row.get("domain_name"),
                "workstream": row.get("workstream"),
                "join_type": row.get("join_type"),
                "left_table": left,
                "right_table": right,
                "join_expression": row.get("join_expression"),
            }
            for table in (left, right):
                if table:
                    by_table.setdefault(table, []).append(entry)
    return by_table


def _load_fk_joins(path: Path, legacy_path: Path, workstream_tables: Set[str]) -> Dict[str, List[dict]]:
    by_child: Dict[str, List[dict]] = {}
    paths = [path, legacy_path]
    for fk_path in paths:
        if not fk_path.exists():
            continue
        with fk_path.open("r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                child = (_row_get(row, "child_table") or _row_get(row, "CHILD_TABLE_NAME")).upper()
                parent = (_row_get(row, "parent_table") or _row_get(row, "PARENT_TABLE_NAME")).upper()
                if child not in workstream_tables and parent not in workstream_tables:
                    continue
                entry = {
                    "child_table": child,
                    "child_column": _row_get(row, "child_column") or _row_get(row, "CHILD_COLUMN_NAME"),
                    "parent_table": parent,
                    "parent_column": _row_get(row, "parent_column") or _row_get(row, "PARENT_COLUMN_NAME"),
                    "join_sql": _row_get(row, "join_sql"),
                    "source": _row_get(row, "source"),
                    "fk_name": _row_get(row, "fk_name") or _row_get(row, "FK_NAME"),
                }
                by_child.setdefault(child, []).append(entry)
    return by_child


def _load_cd_hints(path: Path) -> Dict[str, dict]:
    payload = _read_json(path)
    fields = payload.get("fields") or {}
    return {k.upper(): v for k, v in fields.items() if isinstance(v, dict)}


def _table_cd_fields(table_name: str, table_fields: dict, cd_hints: Dict[str, dict]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for field_name in (table_fields or {}).keys():
        hint = cd_hints.get(field_name.upper())
        if hint and (hint.get("lookup") or field_name.upper().endswith(("_CD", "_FLG"))):
            out[field_name] = hint
    return out


def _load_client_health(client: Optional[str]) -> dict:
    if not client:
        return {}
    health_path = ROOT / "deploy" / "snapshot_rollout_logs" / client / "table_health.json"
    if not health_path.exists():
        return {}
    return json.loads(health_path.read_text(encoding="utf-8"))


def _merge_client_health(table_entry: dict, table_name: str, client_health: dict) -> None:
    rows = client_health.get("tables") or {}
    info = rows.get(table_name.upper())
    if not info:
        return
    population_status = info.get("population_status") or "unknown"
    table_entry["client_health"] = {
        "row_count": info.get("row_count"),
        "population_status": population_status,
        "checked_at": client_health.get("checked_at"),
        "client": client_health.get("client"),
    }


def build_context(client: Optional[str] = None) -> dict:
    workstream_dict = _read_json(DEFAULT_WORKSTREAM_DICT)
    physical_catalog = _read_json(DEFAULT_PHYSICAL_CATALOG)
    join_paths = _read_json(DEFAULT_JOIN_PATHS)
    domain_meta = _read_json(DEFAULT_DOMAIN_META)
    table_stats = _load_table_stats(DEFAULT_TABLES_CSV)
    domain_joins = _load_domain_joins(DEFAULT_DOMAIN_JOINS)
    cd_hints = _load_cd_hints(DEFAULT_CD_INVENTORY)
    client_health = _load_client_health(client)

    workstream_tables: Set[str] = set()
    catalog_workstreams = (physical_catalog.get("workstreams") or {}) if physical_catalog else {}
    if catalog_workstreams:
        for ws_data in catalog_workstreams.values():
            for table_name in ws_data.get("tables") or []:
                workstream_tables.add(table_name.upper())
    else:
        for ws_details in workstream_dict.values():
            for table_name in ((ws_details or {}).get("tables") or {}).keys():
                workstream_tables.add(table_name.upper())

    fk_joins = _load_fk_joins(DEFAULT_FK_JOIN_MAP, DEFAULT_FK_JOIN_MAP_LEGACY, workstream_tables)

    workstreams_out: Dict[str, Any] = {}
    ws_keys = list(catalog_workstreams.keys()) if catalog_workstreams else list(workstream_dict.keys())
    for workstream in ws_keys:
        if workstream == "field_tasks":
            continue
        catalog_tables = (catalog_workstreams.get(workstream) or {}).get("tables") or []
        dict_tables = ((workstream_dict.get(workstream) or {}).get("tables") or {})
        if workstream == "field_ops":
            dict_tables = {
                **dict_tables,
                **((workstream_dict.get("field_tasks") or {}).get("tables") or {}),
            }
        table_names = sorted(
            set(t.upper() for t in catalog_tables)
            | {t.upper() for t in dict_tables.keys()}
        )
        tables_out: Dict[str, Any] = {}
        for t_upper in table_names:
            table_details = dict_tables.get(t_upper) or dict_tables.get(t_upper.lower()) or {}
            physical = table_stats.get(t_upper, {
                "num_rows": None,
                "last_analyzed": None,
                "stats_population_status": "unknown",
            })
            entry = {
                "description": (table_details or {}).get("description"),
                "designer_notes": (table_details or {}).get("designer_notes"),
                "fields": (table_details or {}).get("fields") or {},
                "physical": physical,
                "domain_joins_physical": domain_joins.get(t_upper, [])[:15],
                "fk_joins_as_child": fk_joins.get(t_upper, [])[:25],
                "lookup_field_hints": _table_cd_fields(
                    t_upper,
                    (table_details or {}).get("fields") or {},
                    cd_hints,
                ),
            }
            if t_upper in SLICE_HINTS:
                entry["population_slices"] = SLICE_HINTS[t_upper]
            _merge_client_health(entry, t_upper, client_health)
            tables_out[t_upper] = entry
        ws_join = (join_paths.get("workstreams") or {}).get(workstream) or {}
        workstreams_out[workstream] = {
            "label": (catalog_workstreams.get(workstream) or {}).get("label"),
            "canonical_chains": ws_join.get("canonical_chains") or [],
            "tables": tables_out,
        }

    domain_tables = (domain_meta.get("tables") or {})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "2.0",
        "sources": [
            str(DEFAULT_PHYSICAL_CATALOG.relative_to(ROOT)) if DEFAULT_PHYSICAL_CATALOG.exists() else None,
            str(DEFAULT_JOIN_PATHS.relative_to(ROOT)) if DEFAULT_JOIN_PATHS.exists() else None,
            str(DEFAULT_WORKSTREAM_DICT.relative_to(ROOT)),
            str(DEFAULT_DOMAIN_META.relative_to(ROOT)),
            str(DEFAULT_TABLES_CSV.relative_to(ROOT)),
            str(DEFAULT_DOMAIN_JOINS.relative_to(ROOT)),
            str(DEFAULT_FK_JOIN_MAP.relative_to(ROOT)) if DEFAULT_FK_JOIN_MAP.exists() else None,
            str(DEFAULT_CD_INVENTORY.relative_to(ROOT)),
            "knowledge_base/c2m_cisadm/cisadm_core_model.md",
            "knowledge_base/c2m_cisadm/workstream_physical_join_paths.md",
        ],
        "ai_rules": {
            "physical_tables_only": True,
            "exclude_custom_views": "Do not reference CMS_* views or *_VW in generated SQL; use base CISADM tables.",
            "enrichment_joins": "LEFT JOIN optional lookup (_L), char, and detail tables; preserve driving population.",
            "population_check": (
                "Before recommending a table, check physical.stats_population_status "
                "and client_health.population_status when available"
            ),
            "datasource_aliases": ["ORIGIN_DEV_DS", "C2M_QA_DS", "C2M_PROD_DS"],
        },
        "core_join_patterns": CORE_JOIN_PATTERNS,
        "workstream_join_paths": join_paths.get("sql_rules") or {},
        "workstreams": workstreams_out,
        "domain_metadata_table_count": len(domain_tables),
        "curated_workstream_table_count": len(workstream_tables),
        "workstream_count": len(workstreams_out),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--client",
        help="Optional client id to merge deploy/snapshot_rollout_logs/<client>/table_health.json",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="Output JSON path",
    )
    args = parser.parse_args()

    payload = build_context(client=args.client)
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[PASS] AI CISADM context written: {out_path}")
    print(f"       Workstreams: {len(payload['workstreams'])}")
    print(f"       Curated tables: {payload['curated_workstream_table_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
