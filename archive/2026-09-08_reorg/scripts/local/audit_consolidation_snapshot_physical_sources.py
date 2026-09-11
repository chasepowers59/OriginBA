#!/usr/bin/env python3
"""
Static audit: consolidation snapshot 02a procedures vs physical-table policy.

Flags custom views (CMS_*, *_VW) and documents physical driving tables.

Usage:
  python3 scripts/local/audit_consolidation_snapshot_physical_sources.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

SNAPSHOTS = [
    ("customer_ops/acct_customer", "CI_ACCT", "customer_ops"),
    ("customer_ops/case_prem_contact", "CI_CASE", "customer_ops"),
    ("new_services/pipeline", "CI_SA", "new_services"),
    ("field_ops/field_activity", "D1_ACTIVITY", "field_ops"),
    ("field_ops/crew_ops", "C1_REPRESENTATIVE", "field_ops"),
    ("meter_ops/device_sp", "D1_DVC", "meter_ops"),
    ("payments_cashiering/pay_event", "CI_PAY", "cashiering"),
    ("finance/billable_charge", "CI_B_CHG_LINE", "finance"),
    ("debt_mgmt/sa_aged_bal", "CI_FT", "debt_mgmt"),
    ("debt_mgmt/wo_proc", "CI_WO_PROC", "debt_mgmt"),
    ("common/ops_exception", "UNION", "common"),
    ("common/workflow_queue", "CI_TD_ENTRY", "common"),
]

VIEW_PATTERN = re.compile(r"cisadm\.([a-z0-9_]+)", re.I)


def _load_catalog() -> dict:
    path = ROOT / "output" / "workstream_physical_catalog.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def audit() -> list[dict]:
    catalog = _load_catalog()
    results = []
    for rel_path, driver, ws in SNAPSHOTS:
        sql_path = ROOT / "sql" / "performance" / "snapshots" / rel_path / "02a_full_history_refresh_procedure.sql"
        text = sql_path.read_text(encoding="utf-8")
        tables = {m.group(1).upper() for m in VIEW_PATTERN.finditer(text)}
        views = sorted(
            t
            for t in tables
            if t.startswith("CMS_") or t.endswith("_VW") or t.startswith("X1_")
        )
        physical = sorted(t for t in tables if t not in views)
        ws_tables = set((catalog.get("workstreams", {}).get(ws) or {}).get("tables") or [])
        unknown = sorted(t for t in physical if ws_tables and t not in ws_tables and not t.endswith("_L"))
        results.append(
            {
                "snapshot": rel_path.split("/")[-1],
                "path": str(sql_path.relative_to(ROOT)),
                "workstream": ws,
                "expected_driver": driver,
                "custom_views": views,
                "physical_table_count": len(physical),
                "tables_not_in_workstream_catalog": unknown[:15],
            }
        )
    return results


def main() -> int:
    rows = audit()
    print("[INFO] Consolidation snapshot physical-source audit\n")
    for row in rows:
        status = "PASS" if not row["custom_views"] else "REVIEW"
        print(f"[{status}] {row['snapshot']}")
        print(f"  driver: {row['expected_driver']} | workstream: {row['workstream']}")
        if row["custom_views"]:
            print(f"  custom views (LEFT enrichment): {', '.join(row['custom_views'])}")
        if row["tables_not_in_workstream_catalog"]:
            print(f"  extra physical tables: {', '.join(row['tables_not_in_workstream_catalog'][:8])}")
        print()
    view_count = sum(1 for r in rows if r["custom_views"])
    print(f"[SUMMARY] {len(rows)} snapshots | {view_count} with custom view enrichment | population uses physical drivers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
