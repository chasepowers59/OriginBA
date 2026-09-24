"""patch_field_activity_domain on the real Origin_DEV export: additive only, validator accepts, items
resolve, joins outer and reachable from the activity, no Today() in DomEL."""
from __future__ import annotations

import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "jaspersoft"))
import domain_schema  # noqa: E402
import patch_field_activity_domain as p  # noqa: E402

NS = "{http://www.jaspersoft.com/2007/SL/XMLSchema}"
SNAP = ROOT / "jaspersoft/inventory/test/Origin_DEV/resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Standard_Offering/Field_Operations/Field_Activity/Field_Activity___Domain_files/schema.data"


@unittest.skipUnless(SNAP.exists(), "needs the Origin_DEV inventory snapshot")
class Patch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = SNAP.read_text(encoding="utf-8"); cls.after = p.patch_schema(cls.before)
        cls.root = ET.fromstring(cls.after)

    def test_additive_only_and_items_resolve(self):
        self.assertEqual(domain_schema.additions_only(self.before, self.after), [])
        jt = next(t for t in self.root.iter(NS + "jdbcTable") if t.get("id") == "JoinTree_1")
        fields = {f.get("id") for f in jt.iter(NS + "field")}
        for g in self.root.iter(NS + "itemGroup"):
            if g.get("id") in {s[0] for s in p.SETS}:
                for i in g.iter(NS + "item"):
                    self.assertIn(i.get("resourceId").removeprefix("JoinTree_1."), fields, i.get("id"))

    def test_joins_outer_and_reachable_and_typed(self):
        existing = {t.get("id") for t in ET.fromstring(self.before).iter(NS + "jdbcTable")}
        self.assertFalse(set(p.TABLES) & existing, "new table ids must not collide")
        reached = set(existing)
        for j in self.root.iter(NS + "join"):
            if j.get("right") in p.TABLES:
                self.assertEqual(j.get("type"), "leftOuter"); self.assertIn(j.get("left"), reached); reached.add(j.get("right"))
        self.assertTrue(set(p.TABLES) <= reached)
        self.assertIn("ACTIVITY_ID_TYPE_FLG == 'D1RI'", p.JOINS[0][0], "the bridge is the typed identifier")
        self.assertNotIn("Today(", " ".join(x for _, x, _ in p.CALCULATED))

    def test_validator_accepts_and_refuses_twice(self):
        out = ROOT / "backups" / "jaspersoft" / "field_activity_patch_for_test.xml"
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(self.after, encoding="utf-8")
        r = subprocess.run([sys.executable, str(ROOT / "scripts/jaspersoft/validate_domain_schema.py"), str(out)], capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with self.assertRaises(ValueError):
            p.patch_schema(self.after)


if __name__ == "__main__":
    unittest.main()
