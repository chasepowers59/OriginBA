#!/usr/bin/env python3
"""Compare consolidation snapshot table columns to legacy domain field inventory."""

from __future__ import annotations

import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INVENTORY = REPO / "output/standard_offering_domain_inventory"
SNAPSHOT_ROOT = REPO / "sql/performance/snapshots"

SNAPSHOT_DOMAIN_MAP = {
    "customer_ops/acct_customer": [
        "Customer_Operations_Customer_Customer.csv",
    ],
    "customer_ops/case_prem_contact": [
        "Customer_Operations_Case_Case.csv",
        "Customer_Operations_Premise_Premise.csv",
        "Customer_Operations_Customer_Contact_Customer_Contact.csv",
    ],
    "new_services/pipeline": ["New_Services_Planning_New_Services_New_Services.csv"],
    "field_ops/field_activity": ["Field_Operations_Field_Activity_Field_Activity.csv"],
    "field_ops/crew_ops": ["Field_Operations_Crew_Crew.csv"],
    "meter_ops/device_sp": [
        "Meter_Operations_Device_Device.csv",
        "Meter_Operations_Asset_Asset.csv",
    ],
    "payments_cashiering/pay_event": [
        "Cashiering_Payment_Header_Payment_Header.csv",
        "Cashiering_Deposit_Control_Deposit_Control.csv",
    ],
    "finance/billable_charge": ["Finance_Billable_Charge_Billable_Charge.csv"],
    "debt_mgmt/sa_aged_bal": ["Debt_Management_SA_Snapshot_Aged_Balance_SA_Snapshot_Aged_Balance.csv"],
    "debt_mgmt/wo_proc": [
        "Debt_Management_Write_Off_Process_1_Write_Off_Process.csv",
        "Debt_Management_Write_Off_Process_1_Write_Offs.csv",
    ],
    "common/ops_exception": [
        "Common_Exception_Bill_Segment_Exception.csv",
        "Common_Exception_Usage_Transaction_Exception.csv",
        "Common_Exception_VEE_Exception.csv",
    ],
    "common/workflow_queue": [
        "Common_To_Do_To_Do.csv",
        "Common_Batch_Process_Batch_Process.csv",
    ],
}


def snapshot_columns(path: Path) -> set[str]:
    ddl = (SNAPSHOT_ROOT / path / "01_create_snapshot_table.sql").read_text(encoding="utf-8")
    cols: set[str] = set()
    for line in ddl.splitlines():
        m = re.match(r"\s+([a-z0-9_]+)\s+", line, re.I)
        if m and not line.strip().upper().startswith(("CONSTRAINT", "PRIMARY", "FOREIGN", "CREATE", ")")):
            cols.add(m.group(1).lower())
    return cols


def domain_fields(csv_name: str) -> set[str]:
    path = INVENTORY / "by_domain" / csv_name
    if not path.exists():
        return set()
    fields: set[str] = set()
    in_fields = False
    with path.open(encoding="utf-8", newline="") as fh:
        for line in fh:
            if line.startswith("EXPOSED_FIELDS"):
                in_fields = True
                next(fh, None)
                continue
            if not in_fields:
                continue
            if not line.strip() or line.startswith("section,"):
                break
            row = next(csv.reader([line]))
            if len(row) >= 4 and row[0] != "item_group_label":
                col = row[3].strip().lower()
                if col:
                    fields.add(col)
    return fields


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower())


def main() -> int:
    print("Consolidation snapshot field parity (static DDL vs domain inventory)\n")
    report_lines = [
        "# Consolidation Snapshot Field Parity (Static)",
        "",
        "Compares snapshot DDL columns to legacy domain `source_column` values.",
        "",
        "| Snapshot | Snapshot cols | Domain cols | Overlap |",
        "|---|---:|---:|---:|",
    ]
    for snap_path, domain_csvs in SNAPSHOT_DOMAIN_MAP.items():
        snap_cols = snapshot_columns(Path(snap_path))
        domain_cols: set[str] = set()
        for csv_name in domain_csvs:
            domain_cols |= domain_fields(csv_name)
        overlap = snap_cols & domain_cols
        table = snap_path.split("/")[-1].upper()
        overlap_pct = (len(overlap) / len(domain_cols) * 100) if domain_cols else 0
        print(f"=== {table} ===")
        print(f"  snapshot columns: {len(snap_cols)}")
        print(f"  legacy domain source columns: {len(domain_cols)}")
        print(f"  overlap: {len(overlap)} ({overlap_pct:.0f}%)")
        print()
        report_lines.append(
            f"| `{table}` | {len(snap_cols)} | {len(domain_cols)} | {len(overlap)} ({overlap_pct:.0f}%) |"
        )

    report_path = REPO / "deploy/snapshot_rollout_logs/demo/consolidation/field_parity_static.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
