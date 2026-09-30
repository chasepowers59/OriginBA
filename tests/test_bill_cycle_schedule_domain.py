"""build_bill_cycle_schedule_domain: one row per cycle window, every join outer, every item resolves,
the folds group by the window key, no Today() in DomEL, the validator accepts it."""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "jaspersoft"))
import build_bill_cycle_schedule_domain as b  # noqa: E402

NS = "{http://www.jaspersoft.com/2007/SL/XMLSchema}"


class Schema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.xml = b.schema("Origin_DEV_DS"); cls.root = ET.fromstring(cls.xml)
        cls.jt = next(t for t in cls.root.iter(NS + "jdbcTable") if t.get("id") == "JoinTree_1")

    def test_items_resolve_and_ids_unique(self):
        fields = {f.get("id") for f in self.jt.iter(NS + "field")}
        items = list(self.root.iter(NS + "item")); ids = [i.get("id") for i in items]
        self.assertEqual(len(ids), len(set(ids)))
        for i in items:
            self.assertIn(i.get("resourceId").removeprefix("JoinTree_1."), fields, i.get("id"))

    def test_root_and_outer_joins(self):
        self.assertIn('<joinInfo alias="CI_BILL_CYC_SCH" referenceId="CI_BILL_CYC_SCH">', self.xml)
        for j in self.root.iter(NS + "join"):
            self.assertEqual(j.get("type"), "leftOuter"); self.assertEqual(j.get("left"), "CI_BILL_CYC_SCH")
        self.assertEqual(len({r.get("tableId") for r in self.root.iter(NS + "tableRef")}), len(b.TABLES) + len(b.DERIVED))

    def test_folds_group_by_the_window_or_cycle_key_and_carry_no_binds(self):
        for qid, (sql, fields) in b.DERIVED.items():
            self.assertRegex(sql.lower(), r"group by\s+\w+\.bill_cyc_cd(, \w+\.win_start_dt)?\s*$|from cisadm\.ci_bill_cyc_sch s\s*$", qid)
            self.assertEqual(fields[0][0], "BILL_CYC_CD"); self.assertNotIn("$P{", sql)
        self.assertNotIn("Today(", " ".join(x for _, x, _ in b.CALCULATED))

    def test_only_base_product_literals(self):
        lits = set(re.findall(r"== '([^']*)'", " ".join(x for _, x, _ in b.CALCULATED)))
        self.assertTrue(lits <= b.BASE_PRODUCT_LITERALS, lits)
        self.assertTrue({"'C'", "'P'"} <= set(re.findall(r"'[CP]'", b.DERIVED["WINDOW_BILLS"][0])), "bill status P/C is the base-product lifecycle")
        self.assertEqual(set(re.findall(r"'(\d\d)'", b.DERIVED["WINDOW_BSEG"][0])), {"50", "60"}, "segment lifecycle only")

    def test_the_window_key_joins_every_fold(self):
        for e, _, r, _ in b.JOINS:
            if r in ("WINDOW_BILLS", "WINDOW_BSEG", "WINDOW_AGE"):
                self.assertIn("WIN_START_DT == " + r + ".WIN_START_DT", e, r)

    def test_validator_accepts(self):
        out = ROOT / "backups" / "jaspersoft" / "bill_cycle_schedule_for_test.xml"
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(self.xml, encoding="utf-8")
        r = subprocess.run([sys.executable, str(ROOT / "scripts/jaspersoft/validate_domain_schema.py"), str(out)], capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
