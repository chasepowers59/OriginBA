"""
Build a workstream-aware reporting dictionary from Domain Designs metadata.

Reads output/domain_designs_metadata.json and writes
output/workstream_reporting_dictionary.json with, for each workstream:
  - tables: description, business_impact, designer_notes
  - fields: field-level descriptions from the workbook when available.

Run from repo root:
  python scripts/build_reporting_dictionary.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META_PATH = ROOT / "output" / "domain_designs_metadata.json"
OUT_PATH = ROOT / "output" / "workstream_reporting_dictionary.json"


def main() -> None:
    if not META_PATH.exists():
        print(f"Metadata not found: {META_PATH}. Run scripts/refresh_domain_metadata.py first.", file=sys.stderr)
        sys.exit(1)

    with open(META_PATH, encoding="utf-8") as f:
        meta = json.load(f)

    table_desc = meta.get("table_descriptions") or {}
    tables_block = meta.get("tables") or {}

    # Workstream -> tables mapping (aligned with domain_context)
    workstream_tables = {
        "billing": ["CI_BILL", "CI_BSEG", "CI_FT", "CI_RS_L"],
        "cashiering": ["CI_PAY_EVENT", "CI_PAY_TNDR", "CI_DEP_CTL"],
        "meter_ops": ["D1_DVC", "D1_DVC_CFG", "D1_INSTALL_EVT", "CI_SP"],
        "customer_ops": ["CI_ACCT", "CI_PER_NAME", "CI_ACCT_ALERT"],
        "new_services": ["CI_SA", "CI_SP_CHAR"],
        "finance": ["CI_FT_GL", "CI_FT_PROC", "CI_FT"],
        "common": ["CI_PREM", "CI_LOOKUP_VAL"],
        "debt_mgmt": ["CI_ACCT", "CI_FT", "CI_COLL_PROC"],
        "field_ops": ["CI_SP", "D1_ACTIVITY"],
        "field_tasks": ["F1_TSK", "F1_TSK_LOG", "CI_SP"],  # OCX & Field Tasks (F1 metadata + CI functional)
    }

    reporting_dict: dict[str, dict] = {}

    # Strategic Priority tags per workstream
    strategic_priority = {
        "billing": ["Revenue Assurance"],
        "cashiering": ["Revenue Assurance"],
        "meter_ops": ["Technical Stability"],
        "customer_ops": ["Customer Adoption"],
        "new_services": ["Customer Adoption"],
        "finance": ["Revenue Assurance"],
        "common": [],
        "debt_mgmt": ["Revenue Assurance"],
        "field_ops": ["Technical Stability"],
        "field_tasks": ["Technical Stability"],  # OCX & Field Tasks
    }

    for ws_name, tables in workstream_tables.items():
        ws_entry: dict[str, dict] = {
            "tables": {},
            "strategic_priority": strategic_priority.get(ws_name, []),
        }
        for t in tables:
            t_meta = table_desc.get(t) or {}
            if isinstance(t_meta, dict):
                desc = t_meta.get("description")
                designer_notes = t_meta.get("designer_notes")
                business_impact = t_meta.get("business_impact")
            else:
                desc = t_meta if isinstance(t_meta, str) else None
                designer_notes = None
                business_impact = None

            # Field-level info from "tables" block when present
            field_info = {}
            t_table_block = tables_block.get(t) or {}
            if isinstance(t_table_block, dict):
                fields = t_table_block.get("fields") or []
                for fld in fields:
                    name = fld.get("name")
                    if not name:
                        continue
                    field_info[name] = {
                        "description": fld.get("description"),
                    }

            ws_entry["tables"][t] = {
                "description": desc,
                "designer_notes": designer_notes,
                "business_impact": business_impact,
                "fields": field_info,
            }
        reporting_dict[ws_name] = ws_entry

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(reporting_dict, f, indent=2, ensure_ascii=False)
    print(f"Wrote {OUT_PATH} (workstreams: {len(reporting_dict)})")


if __name__ == "__main__":
    main()

