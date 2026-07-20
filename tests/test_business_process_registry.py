"""Validate business process field guides against the explorer catalog."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from business_process_registry import BUSINESS_PROCESSES  # noqa: E402


class BusinessProcessRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        catalog_path = ROOT / "output" / "snapshot_explorer_catalog.json"
        if not catalog_path.exists():
            raise unittest.SkipTest("Run scripts/build_snapshot_explorer_catalog.py first")
        cls.catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    def test_process_dimensions_and_measures_exist(self) -> None:
        snapshots = self.catalog["snapshots"]
        for process in BUSINESS_PROCESSES:
            for entry in process["entries"]:
                snap_id = entry["snapshot_id"]
                self.assertIn(snap_id, snapshots, f"{process['id']} references unknown snapshot {snap_id}")
                allowed = {f["id"].upper() for f in snapshots[snap_id]["fields"]}
                for field_id in entry.get("dimensions", []):
                    self.assertIn(
                        field_id.upper(),
                        allowed,
                        f"{process['id']} dimension {field_id} missing on {snap_id}",
                    )
                for field_id in entry.get("measures", []):
                    if field_id == "*":
                        continue
                    self.assertIn(
                        field_id.upper(),
                        allowed,
                        f"{process['id']} measure {field_id} missing on {snap_id}",
                    )
                report_id = entry.get("report_id")
                if report_id:
                    premade_ids = {r["id"] for r in snapshots[snap_id].get("premade_reports", [])}
                    self.assertIn(
                        report_id,
                        premade_ids,
                        f"{process['id']} report {report_id} missing on {snap_id}",
                    )

    def test_catalog_includes_business_processes(self) -> None:
        processes = self.catalog.get("business_processes", [])
        self.assertGreaterEqual(len(processes), 15)
        cashiering = [p for p in processes if p["workstream"] == "cashiering"]
        labels = {p["label"] for p in cashiering}
        self.assertIn("Tender", labels)
        self.assertIn("Deposit & tender control", labels)


if __name__ == "__main__":
    unittest.main()
