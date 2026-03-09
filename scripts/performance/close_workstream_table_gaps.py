#!/usr/bin/env python3
"""
Close workstream table coverage gaps using domain metadata as a pre-DB baseline.

This script:
1. Finds tables present in output/domain_designs_metadata.json but missing from
   output/workstream_reporting_dictionary.json.
2. Assigns each missing table to a workstream using deterministic rules.
3. Optionally writes updates back to workstream_reporting_dictionary.json.
4. Optionally emits a provisional output/cisadm_dictionary/tables.csv seed so
   coverage_summary can be generated before live DB discovery.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKSTREAM_DICT = ROOT / "output" / "workstream_reporting_dictionary.json"
DEFAULT_DOMAIN_META = ROOT / "output" / "domain_designs_metadata.json"
DEFAULT_PROVISIONAL_DIR = ROOT / "output" / "cisadm_dictionary"


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_fields(domain_table: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    fields = domain_table.get("fields") or []
    out: Dict[str, Dict[str, str]] = {}
    if isinstance(fields, list):
        for f in fields:
            name = (f.get("name") or "").strip().upper()
            if not name:
                continue
            desc = (f.get("description") or "").strip()
            out[name] = {"description": desc if desc else name}
    elif isinstance(fields, dict):
        # Defensive fallback if source format changes.
        for name, value in fields.items():
            n = (name or "").strip().upper()
            if not n:
                continue
            if isinstance(value, dict):
                desc = (value.get("description") or "").strip()
            else:
                desc = str(value).strip()
            out[n] = {"description": desc if desc else n}
    return out


def _clean_justification(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    marker = "Justification |"
    if marker in t:
        return t.split(marker, 1)[1].strip()
    return t


def _pick_workstream(table_name: str) -> str:
    t = table_name.upper()

    manual = {
        "C1_PA_RQST": "debt_mgmt",
        "C1_PA_RQST_REL_OBJ": "debt_mgmt",
        "C1_REPRESENTATIVE": "customer_ops",
        "C1_USAGE": "meter_ops",
        "CI_ADJ": "finance",
        "CI_APPR_REQ": "customer_ops",
        "CI_LANDLORD": "customer_ops",
        "CI_PAY_SEG": "cashiering",
        "CI_PER": "customer_ops",
        "CI_PREM_CHAR": "common",
        "CI_PREM_GEO": "common",
        "D1_CONTACT_IDENTIFIER": "customer_ops",
        "D1_US_CONTACT": "customer_ops",
        "F1_BNDL": "common",
        "F1_BNDL_ENTTY": "common",
        "F1_MIGR_DATA_ST": "common",
        "F1_MIGR_TRANS": "common",
    }
    if t in manual:
        return manual[t]

    if t.startswith("CI_BILL") or t.startswith("CI_BSEG"):
        return "billing"
    if t.startswith("CI_PAY"):
        return "cashiering"
    if t.startswith("C1_PA"):
        return "debt_mgmt"
    if t.startswith("D1_ACTIVITY"):
        return "field_ops"
    if t.startswith("D1_") or t == "C1_USAGE":
        return "meter_ops"
    if t.startswith("F1_"):
        return "common"
    if t in {"CI_PER", "CI_LANDLORD", "C1_REPRESENTATIVE"}:
        return "customer_ops"

    return "common"


def _ensure_workstream_shape(workstream_entry: Dict[str, Any]) -> None:
    if "tables" not in workstream_entry or not isinstance(workstream_entry["tables"], dict):
        workstream_entry["tables"] = {}


def _build_new_table_payload(table_name: str, domain_table: Dict[str, Any], assigned_ws: str) -> Dict[str, Any]:
    justification = _clean_justification((domain_table or {}).get("justification") or "")
    fields = _normalize_fields(domain_table or {})
    desc = justification if justification else f"Auto-added coverage table for {table_name}"
    return {
        "description": desc,
        "designer_notes": f"Auto-added by close_workstream_table_gaps.py to {assigned_ws}; review and refine.",
        "business_impact": None,
        "fields": fields,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _emit_provisional_tables_csv(path: Path, table_names: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["OWNER", "TABLE_NAME"])
        for t in sorted(set(table_names)):
            writer.writerow(["CISADM", t])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workstream-dict", default=str(DEFAULT_WORKSTREAM_DICT))
    parser.add_argument("--domain-meta", default=str(DEFAULT_DOMAIN_META))
    parser.add_argument("--write", action="store_true", help="Write updates back to workstream dictionary.")
    parser.add_argument(
        "--emit-provisional-dictionary-seed",
        action="store_true",
        help="Emit provisional output/cisadm_dictionary/tables.csv from domain metadata.",
    )
    parser.add_argument(
        "--provisional-dir",
        default=str(DEFAULT_PROVISIONAL_DIR),
        help="Directory for provisional dictionary seed output.",
    )
    args = parser.parse_args()

    ws_path = Path(args.workstream_dict).resolve()
    dm_path = Path(args.domain_meta).resolve()
    provisional_dir = Path(args.provisional_dir).resolve()
    if not provisional_dir.exists():
        provisional_dir = ROOT / "output" / "cisadm_dictionary"

    ws_payload = _load_json(ws_path)
    dm_payload = _load_json(dm_path)

    ws_tables: Dict[str, str] = {}
    for ws_name, ws_entry in ws_payload.items():
        _ensure_workstream_shape(ws_entry)
        for table_name in ws_entry["tables"].keys():
            ws_tables[table_name.upper()] = ws_name

    dm_tables = dm_payload.get("tables") or {}
    dm_table_names = sorted({t.upper() for t in dm_tables.keys()})

    missing = [t for t in dm_table_names if t not in ws_tables]
    if not missing:
        print("[PASS] No workstream table gaps found between domain metadata and workstream dictionary.")
    else:
        print(f"[INFO] Missing tables to add: {len(missing)}")

    additions: List[Tuple[str, str]] = []
    for table_name in missing:
        ws = _pick_workstream(table_name)
        ws_entry = ws_payload.get(ws)
        if not isinstance(ws_entry, dict):
            ws_entry = {"tables": {}}
            ws_payload[ws] = ws_entry
        _ensure_workstream_shape(ws_entry)

        domain_table = dm_tables.get(table_name) or dm_tables.get(table_name.upper()) or {}
        ws_entry["tables"][table_name] = _build_new_table_payload(table_name, domain_table, ws)
        additions.append((table_name, ws))

    if args.write and additions:
        _write_json(ws_path, ws_payload)
        print(f"[PASS] Updated workstream dictionary: {ws_path}")

    if additions:
        for table_name, ws in additions:
            print(f"[ADD] {table_name} -> {ws}")

    if args.emit_provisional_dictionary_seed:
        seed_path = provisional_dir / "tables.csv"
        _emit_provisional_tables_csv(seed_path, dm_table_names)
        print(f"[PASS] Wrote provisional dictionary seed: {seed_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
