#!/usr/bin/env python3
"""
Build 9-workstream physical CISADM table catalog and join paths (no custom views).

Sources:
  - output/standard_offering_domain_inventory/domain_tables_master.csv
  - output/standard_offering_domain_inventory/domain_joins_master.csv
  - docs/cisadm_relationship_map.md (canonical chains)

Outputs:
  - output/workstream_physical_catalog.json
  - output/workstream_physical_join_paths.json
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
DOMAIN_TABLES = ROOT / "output" / "standard_offering_domain_inventory" / "domain_tables_master.csv"
DOMAIN_JOINS = ROOT / "output" / "standard_offering_domain_inventory" / "domain_joins_master.csv"
OUT_CATALOG = ROOT / "output" / "workstream_physical_catalog.json"
OUT_JOIN_PATHS = ROOT / "output" / "workstream_physical_join_paths.json"

# Nine reporting workstreams (Standard Offering folders; excludes Development).
WS_LABEL_TO_KEY = {
    "Billing and Rates": "billing",
    "Cashiering": "cashiering",
    "Common": "common",
    "Customer Operations": "customer_ops",
    "Debt Management": "debt_mgmt",
    "Field Operations": "field_ops",
    "Finance": "finance",
    "Meter Operations": "meter_ops",
    "New Services and Planning": "new_services",
}

# Canonical physical chains for learning + AI (no views).
CANONICAL_CHAINS: Dict[str, List[dict]] = {
    "billing": [
        {
            "name": "billing_fact_chain",
            "grain": "bill_segment",
            "driver_table": "CI_BSEG",
            "tables": ["CI_ACCT", "CI_SA", "CI_BSEG", "CI_BILL"],
            "join_sql": [
                "CI_ACCT.ACCT_ID = CI_SA.ACCT_ID",
                "CI_SA.SA_ID = CI_BSEG.SA_ID",
                "CI_BSEG.BILL_ID = CI_BILL.BILL_ID",
            ],
        },
        {
            "name": "billing_detail_enrichment",
            "grain": "bill_segment",
            "driver_table": "CI_BSEG",
            "tables": ["CI_BSEG_SQ", "CI_BSEG_READ", "CI_BSEG_CALC", "CI_BSEG_CALC_LN", "CI_BSEG_ITEM", "CI_BSEG_EXCP"],
            "join_sql": ["CI_BSEG.BSEG_ID = <child>.BSEG_ID"],
            "enrichment": True,
        },
    ],
    "cashiering": [
        {
            "name": "payment_event_chain",
            "grain": "payment_event",
            "driver_table": "CI_PAY_EVENT",
            "tables": ["CI_ACCT", "CI_PAY", "CI_PAY_EVENT", "CI_PAY_TNDR", "CI_PAY_SEG", "CI_DEP_CTL"],
            "join_sql": [
                "CI_PAY_EVENT.PAY_EVENT_ID = CI_PAY.PAY_EVENT_ID",
                "CI_PAY.ACCT_ID = CI_ACCT.ACCT_ID",
            ],
            "enrichment": True,
        },
    ],
    "finance": [
        {
            "name": "financial_transaction_chain",
            "grain": "ft",
            "driver_table": "CI_FT",
            "tables": ["CI_ACCT", "CI_SA", "CI_FT", "CI_FT_GL", "CI_FT_PROC"],
            "join_sql": [
                "CI_ACCT.ACCT_ID = CI_SA.ACCT_ID",
                "CI_SA.SA_ID = CI_FT.SA_ID",
                "CI_FT.FT_ID = CI_FT_GL.FT_ID",
            ],
        },
    ],
    "meter_ops": [
        {
            "name": "usage_chain",
            "grain": "usage",
            "driver_table": "D1_USAGE",
            "tables": ["CI_ACCT", "CI_SA", "C1_USAGE", "D1_USAGE", "D1_USAGE_SCALAR_DTL", "D1_USAGE_PERIOD_SQ"],
            "join_sql": [
                "CI_SA.SA_ID = C1_USAGE.SA_ID",
                "C1_USAGE.USAGE_ID = D1_USAGE.USG_EXT_ID",
                "D1_USAGE.D1_USAGE_ID = D1_USAGE_SCALAR_DTL.D1_USAGE_ID",
            ],
        },
        {
            "name": "device_install_chain",
            "grain": "install_event",
            "driver_table": "D1_INSTALL_EVT",
            "tables": ["CI_SP", "D1_INSTALL_EVT", "D1_DVC_CFG", "D1_DVC", "D1_MEASR_COMP"],
            "join_sql": [
                "D1_INSTALL_EVT.D1_DEVICE_ID = D1_DVC.D1_DEVICE_ID",
            ],
            "enrichment": True,
        },
    ],
    "customer_ops": [
        {
            "name": "account_customer_chain",
            "grain": "account",
            "driver_table": "CI_ACCT",
            "tables": ["CI_ACCT", "CI_ACCT_PER", "CI_PER", "CI_PER_NAME", "CI_PREM"],
            "join_sql": [
                "CI_ACCT.ACCT_ID = CI_ACCT_PER.ACCT_ID AND CI_ACCT_PER.MAIN_CUST_SW = 'Y'",
                "CI_ACCT_PER.PER_ID = CI_PER.PER_ID",
                "CI_ACCT_PER.PER_ID = CI_PER_NAME.PER_ID AND CI_PER_NAME.NAME_TYPE_FLG = 'PRIM'",
            ],
        },
        {
            "name": "case_chain",
            "grain": "case",
            "driver_table": "CI_CASE",
            "tables": ["CI_CASE", "CI_CC", "CI_ACCT", "CI_PREM", "CI_PER"],
            "join_sql": [
                "CI_CASE.ACCT_ID = CI_ACCT.ACCT_ID",
                "CI_CASE.PREM_ID = CI_PREM.PREM_ID",
            ],
            "enrichment": True,
        },
    ],
    "new_services": [
        {
            "name": "service_agreement_chain",
            "grain": "sa",
            "driver_table": "CI_SA",
            "tables": ["CI_ACCT", "CI_SA", "CI_SA_SP", "CI_SP", "CI_SA_TYPE", "CI_ENRL"],
            "join_sql": [
                "CI_ACCT.ACCT_ID = CI_SA.ACCT_ID",
                "CI_SA.SA_ID = CI_SA_SP.SA_ID",
                "CI_SA_SP.SP_ID = CI_SP.SP_ID",
            ],
        },
    ],
    "debt_mgmt": [
        {
            "name": "debt_chain",
            "grain": "sa",
            "driver_table": "CI_FT",
            "tables": ["CI_ACCT", "CI_SA", "CI_FT", "CI_COLL_PROC", "C1_PA_RQST", "C1_PA_RQST_REL_OBJ"],
            "join_sql": [
                "CI_ACCT.ACCT_ID = CI_SA.ACCT_ID",
                "CI_SA.SA_ID = CI_FT.SA_ID",
            ],
        },
    ],
    "field_ops": [
        {
            "name": "field_activity_chain",
            "grain": "activity",
            "driver_table": "D1_ACTIVITY",
            "tables": ["CI_SP", "D1_ACTIVITY", "D1_ACTIVITY_TYPE", "D1_ACTIVITY_CHAR", "D1_ACTIVITY_REL", "D1_ACTIVITY_REL_OBJ", "C1_REPRESENTATIVE", "F1_TSK", "F1_TSK_LOG"],
            "join_sql": [
                "D1_ACTIVITY.D1_ACTIVITY_ID = D1_ACTIVITY_CHAR.D1_ACTIVITY_ID",
                "D1_ACTIVITY.ACTIVITY_TYPE_CD = D1_ACTIVITY_TYPE.ACTIVITY_TYPE_CD",
            ],
            "enrichment": True,
        },
    ],
    "common": [
        {
            "name": "workflow_queue_chain",
            "grain": "todo_entry",
            "driver_table": "CI_TD_ENTRY",
            "tables": ["CI_TD_ENTRY", "CI_BATCH_INST", "CI_PREM", "CI_ACCT"],
            "join_sql": [],
            "enrichment": True,
        },
        {
            "name": "premise_chain",
            "grain": "premise",
            "driver_table": "CI_PREM",
            "tables": ["CI_PREM", "CI_PREM_CHAR", "CI_PREM_GEO", "CI_SP"],
            "join_sql": ["CI_SP.PREM_ID = CI_PREM.PREM_ID"],
            "enrichment": True,
        },
    ],
}


def is_physical_base_table(name: str) -> bool:
    n = (name or "").strip().upper()
    if not n:
        return False
    if n.startswith("JOINTREE") or n.startswith("JOIN"):
        return False
    if n.startswith("CMS_"):
        return False
    if "_VW" in n:
        return False
    if n.startswith("C1_BI_"):
        return False
    return True


def _parse_join_expression(expr: str) -> List[Tuple[str, str, str, str]]:
    """Parse 'A.COL == B.COL and ...' into (left_table, left_col, right_table, right_col)."""
    pairs: List[Tuple[str, str, str, str]] = []
    if not expr:
        return pairs
    for clause in re.split(r"\band\b", expr, flags=re.I):
        clause = clause.strip()
        m = re.match(r"([A-Z0-9_]+)\.([A-Z0-9_]+)\s*==\s*([A-Z0-9_]+)\.([A-Z0-9_]+)", clause, re.I)
        if m:
            pairs.append(tuple(x.upper() for x in m.groups()))
    return pairs


def _load_domain_tables() -> Dict[str, Set[str]]:
    by_ws: Dict[str, Set[str]] = defaultdict(set)
    with DOMAIN_TABLES.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            label = row.get("workstream") or ""
            ws_key = WS_LABEL_TO_KEY.get(label)
            if not ws_key:
                continue
            pt = (row.get("physical_table") or "").upper()
            if is_physical_base_table(pt):
                by_ws[ws_key].add(pt)
    # Merge field-task physical tables into field_ops
    by_ws["field_ops"].update({"F1_TSK", "F1_TSK_LOG"})
    return by_ws


def _load_domain_joins(workstream_tables: Dict[str, Set[str]]) -> List[dict]:
    all_ws_tables = set().union(*workstream_tables.values())
    joins: List[dict] = []
    seen: Set[Tuple[str, str, str, str]] = set()
    with DOMAIN_JOINS.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            left = (row.get("left_table") or "").upper()
            right = (row.get("right_table") or "").upper()
            if not is_physical_base_table(left) or not is_physical_base_table(right):
                continue
            if left not in all_ws_tables and right not in all_ws_tables:
                continue
            for lt, lc, rt, rc in _parse_join_expression(row.get("join_expression") or ""):
                if not is_physical_base_table(lt) or not is_physical_base_table(rt):
                    continue
                key = (lt, lc, rt, rc)
                if key in seen:
                    continue
                seen.add(key)
                joins.append(
                    {
                        "child_table": lt,
                        "child_column": lc,
                        "parent_table": rt,
                        "parent_column": rc,
                        "join_type": row.get("join_type"),
                        "domain_name": row.get("domain_name"),
                        "workstream": row.get("workstream"),
                        "source": "domain_join_inventory",
                    }
                )
    return joins


def main() -> int:
    workstream_tables = _load_domain_tables()
    domain_joins = _load_domain_joins(workstream_tables)

    # Ensure canonical chain tables are in catalog even if absent from a domain export.
    for ws_key, chains in CANONICAL_CHAINS.items():
        for chain in chains:
            for t in chain.get("tables") or []:
                base = t.split(".")[0].upper()
                if is_physical_base_table(base):
                    workstream_tables[ws_key].add(base)

    catalog = {
        "version": "1.0",
        "workstream_count": len(WS_LABEL_TO_KEY),
        "rules": {
            "physical_tables_only": True,
            "exclude_patterns": ["CMS_*", "*_VW", "C1_BI_*"],
            "enrichment_join": "LEFT JOIN",
            "preserve_driving_population": True,
        },
        "workstreams": {},
    }
    for label, ws_key in WS_LABEL_TO_KEY.items():
        tables = sorted(workstream_tables.get(ws_key, set()))
        catalog["workstreams"][ws_key] = {
            "label": label,
            "table_count": len(tables),
            "tables": tables,
        }

    join_paths = {
        "version": "1.0",
        "sql_rules": {
            "driving_population": "Choose the table that matches business grain; do not filter exploratory populations in SQL when building ad hoc snapshots.",
            "enrichment": "LEFT JOIN lookup (_L), char, and optional child detail tables.",
            "language_cd": "Lookup labels: LANGUAGE_CD = 'ENG'",
            "blank_strings": "Use NULLIF(TRIM(col),'') for C2M blank-string codes.",
        },
        "workstreams": {},
        "domain_inferred_joins": domain_joins,
        "domain_inferred_join_count": len(domain_joins),
    }
    for ws_key in WS_LABEL_TO_KEY.values():
        join_paths["workstreams"][ws_key] = {
            "label": WS_LABEL_TO_KEY.get(ws_key, ws_key),
            "canonical_chains": CANONICAL_CHAINS.get(ws_key, []),
            "tables": sorted(workstream_tables.get(ws_key, set())),
        }

    OUT_CATALOG.parent.mkdir(parents=True, exist_ok=True)
    OUT_CATALOG.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    OUT_JOIN_PATHS.write_text(json.dumps(join_paths, indent=2) + "\n", encoding="utf-8")

    total_tables = sum(w["table_count"] for w in catalog["workstreams"].values())
    print(f"[PASS] Physical catalog: {OUT_CATALOG}")
    print(f"       Workstreams: {catalog['workstream_count']} | Table assignments: {total_tables}")
    print(f"[PASS] Join paths: {OUT_JOIN_PATHS}")
    print(f"       Domain-inferred joins: {len(domain_joins)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
