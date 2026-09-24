"""patch_severance_domain on the real Origin_DEV export of the Severance Process domain: the
validator accepts the result, every new item resolves, every new join is outer, nothing existing
changed, and it refuses to patch twice."""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "jaspersoft"))
import patch_severance_domain as p  # noqa: E402

NS = "{http://www.jaspersoft.com/2007/SL/XMLSchema}"
SNAP = ROOT / "jaspersoft/inventory/test/Origin_DEV/resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Standard_Offering/Debt_Management/Severance_Process/Severance_Process___Domain_files/schema.data"


@unittest.skipUnless(SNAP.exists(), "needs the Origin_DEV inventory snapshot")
class Patch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = SNAP.read_text(encoding="utf-8")
        cls.after = p.patch_schema(cls.before)
        cls.root = ET.fromstring(cls.after)
        cls.jt = next(t for t in cls.root.iter(NS + "jdbcTable") if t.get("id") == "JoinTree_1")

    def test_new_items_resolve_and_nothing_existing_changed(self):
        jt_fields = {f.get("id") for f in self.jt.iter(NS + "field")}
        new = {i.get("id"): i.get("resourceId") for g in self.root.iter(NS + "itemGroup") if g.get("id") in {s[0] for s in p.SETS} for i in g.iter(NS + "item")}
        self.assertEqual(len(new), sum(len(s[2]) for s in p.SETS))
        for i, rid in new.items():
            self.assertIn(rid.removeprefix("JoinTree_1."), jt_fields, i)
        old_items = re.findall(r"<item [^>]*>", self.before)
        self.assertTrue(all(x in self.after for x in old_items))
        self.assertEqual(self.after.count("<jdbcTable "), self.before.count("<jdbcTable ") + len(p.TABLES))

    def test_new_joins_are_outer_and_reach_from_existing_tables(self):
        existing = {t.get("id") for t in ET.fromstring(self.before).iter(NS + "jdbcTable")}
        reached = set(existing)
        for j in self.root.iter(NS + "join"):
            if j.get("right") in p.TABLES:
                self.assertEqual(j.get("type"), "leftOuter", j.get("right"))
                self.assertIn(j.get("left"), reached, j.get("right")); reached.add(j.get("right"))
        self.assertTrue(set(p.TABLES) <= reached)
        refs = {r.get("tableId") for r in self.root.iter(NS + "tableRef")}
        self.assertTrue(set(p.TABLES) <= refs)

    def test_lookup_and_label_joins_carry_their_key(self):
        for e, _, r in p.JOINS:
            if r.endswith("_L"):
                self.assertIn("LANGUAGE_CD == 'ENG'", e)
            if r == "SEV_FA_STAT_L":
                self.assertIn("FIELD_NAME == 'FA_STATUS_FLG'", e)

    def test_validator_accepts_and_no_today_in_calculations(self):
        out = ROOT / "backups" / "jaspersoft" / "severance_patch_for_test.xml"
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(self.after, encoding="utf-8")
        r = subprocess.run([sys.executable, str(ROOT / "scripts/jaspersoft/validate_domain_schema.py"), str(out)], capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("Today(", " ".join(x for _, x, _ in p.CALCULATED))

    def test_refuses_to_patch_twice(self):
        with self.assertRaises(ValueError):
            p.patch_schema(self.after)


if __name__ == "__main__":
    unittest.main()
