"""The inventory tool's offline half: unpacking a real server export into the committed shape
(passwords redacted, everything else verbatim), summarizing it, and diffing two trees while
ignoring what the server changes on every export (dates, versions, the organization path)."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "jaspersoft"))
import jrs_inventory as inv  # noqa: E402

REP8 = ROOT / "domains/manual_imports/newark_rep8_aged_balance_report/REP8_Aged_Balance_staging_client_import.zip"


class Unpack(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_a_real_export_unpacks_with_the_password_redacted_and_content_verbatim(self):
        n = inv.unpack(REP8.read_bytes(), self.dir / "Newark1")
        self.assertGreater(n, 5)
        ds = (self.dir / "Newark1/resources/DataSource/Newark1_DS.xml").read_text()
        self.assertIn("<connectionPassword>REDACTED</connectionPassword>", ds)
        self.assertNotIn("4A5253", ds.split("<connectionPassword>")[1][:20])
        jrxml = (self.dir / "Newark1/resources/SmartCity/Report/Workstreams/Debt_Management/REP8_Aged_Balance_files/main_jrxml.data").read_bytes()
        self.assertIn(b"<jasperReport", jrxml)

    def test_summary_counts_types_and_names_datasources(self):
        inv.unpack(REP8.read_bytes(), self.dir / "Newark1")
        s = inv.summarize(self.dir / "Newark1")
        self.assertEqual(s["resources_by_type"].get("reportUnit"), 1)
        self.assertEqual(s["resources_by_type"].get("jdbcDataSource"), 1)
        self.assertEqual(s["datasources"][0]["user"], "JRS2C2M")
        self.assertTrue(any("Debt_Management" in f for f in s["folders"]))
        self.assertEqual(s["report_units"], ["/SmartCity/Report/Workstreams/Debt_Management/REP8_Aged_Balance"])

    def test_diff_ignores_dates_versions_and_the_org_path(self):
        a, b = self.dir / "test/OrgA", self.dir / "prod/OrgB"
        inv.unpack(REP8.read_bytes(), a); inv.unpack(REP8.read_bytes(), b)
        unit = b / "resources/SmartCity/Report/Workstreams/Debt_Management/REP8_Aged_Balance.xml"
        unit.write_text(unit.read_text().replace("<version>13</version>", "<version>14</version>")
                        .replace("2024-10-30T13:45:17.000Z", "2026-01-01T00:00:00.000Z"))
        with unittest.mock.patch.object(inv, "INVENTORY", self.dir):
            self.assertEqual(inv.diff("test:OrgA", "prod:OrgB", None), 0, "version and date churn is not a difference")
            (b / "resources/SmartCity/Report/Workstreams/Debt_Management/REP8_Aged_Balance_files/main_jrxml.data").write_bytes(b"<jasperReport/>")
            self.assertEqual(inv.diff("test:OrgA", "prod:OrgB", "/SmartCity/Report"), 1, "content is")


import unittest.mock  # noqa: E402

if __name__ == "__main__":
    unittest.main()
