"""patch_write_offs_domain on the Origin_DEV export of the Standard Offering Write Offs domain:
the payment aggregate loses its hard-coded 2025-09-01 floor and its cross-id join, two derived
tables and a running-arrears calculation arrive, and nothing a view already binds to moves."""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "jaspersoft"))
import patch_write_offs_domain as pw  # noqa: E402

SOURCE = ROOT / "domains/manual_imports/write_offs_domain/schema.reference.xml"
NS = "{http://www.jaspersoft.com/2007/SL/XMLSchema}"
ITEM = re.compile(r'<item [^>]*id="([^"]+)"[^>]*resourceId="([^"]+)"')


@unittest.skipUnless(SOURCE.exists(), "reference schema not present")
class Patched(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = SOURCE.read_text(encoding="utf-8")
        cls.after = pw.patch(cls.before)
        cls.root = ET.fromstring(cls.after)
        cls.queries = {q.get("id"): (q.find(NS + "query").text or "") for q in cls.root.iter(NS + "jdbcQuery")}

    def test_payment_aggregate_window_is_relative_and_the_chain_is_right(self):
        q = self.queries["WO_PAY_AGG"].lower()
        self.assertNotIn("date '", q, "a literal date survived")
        self.assertNotIn("2025", q)
        self.assertIn("pe.pay_dt >= trunc(w.cre_dttm)", q)
        self.assertIn("p.pay_id = ps.pay_id", q)
        self.assertIn("pe.pay_event_id = p.pay_event_id", q)
        self.assertNotIn("pay_tender_id = ps.pay_id", q)
        self.assertIn("p.pay_status_flg = '50'", q)

    def test_payment_aggregate_keeps_its_seven_columns(self):
        before = re.search(r'<jdbcQuery id="WO_PAY_AGG".*?</fieldList>', self.before, re.S).group(0)
        after = re.search(r'<jdbcQuery id="WO_PAY_AGG".*?</fieldList>', self.after, re.S).group(0)
        self.assertEqual(before, after)

    def test_two_derived_tables_joined_from_the_process_row(self):
        for qid in ("WO_ACCT_BAL", "WO_PROC_ARS"):
            self.assertIn(qid, self.queries)
        self.assertIn("ft.redundant_sw = 'n'", self.queries["WO_ACCT_BAL"].lower())
        self.assertIn("ft.freeze_sw = 'y'", self.queries["WO_ACCT_BAL"].lower())
        self.assertNotIn("sa_type_cd = 'pa'", self.queries["WO_PROC_ARS"].lower(), "a client-configured SA type must not be carried")
        joins = {(j.get("right"), j.get("type")) for j in self.root.iter(NS + "join")}
        self.assertIn(("WO_ACCT_BAL", "leftOuter"), joins)
        self.assertIn(("WO_PROC_ARS", "leftOuter"), joins)
        refs = {r.get("tableId") for r in self.root.iter(NS + "tableRef")}
        self.assertTrue({"WO_ACCT_BAL", "WO_PROC_ARS"} <= refs)

    def test_every_new_item_resolves_to_a_join_tree_field(self):
        jt = next(t for t in self.root.iter(NS + "jdbcTable") if t.get("id") == "JoinTree_1")
        fields = {f.get("id") for f in jt.iter(NS + "field")}
        for _, _, rid in pw.ROW_ITEMS + pw.MEASURE_ITEMS:
            self.assertIn(rid.removeprefix("JoinTree_1."), fields, rid)
        calc = next(f for f in jt.iter(NS + "field") if f.get("id") == "RUNNING_ARS_ROW")
        self.assertIn("WO_PROC_ARS.ARS_AMT", calc.get("dataSetExpression"))
        self.assertIn("WO_PAY_AGG.PAY_SEG_AMT_TOTAL", calc.get("dataSetExpression"))

    def test_nothing_a_view_binds_to_moved(self):
        before = dict(ITEM.findall(self.before))
        after = dict(ITEM.findall(self.after))
        for iid, rid in before.items():
            self.assertEqual(after.get(iid), rid, f"item {iid} changed")
        self.assertEqual(len(after), len(before) + len(pw.ROW_ITEMS) + len(pw.MEASURE_ITEMS))
        self.assertEqual(len(set(after)), len(after), "duplicate item id")
        jt_before = re.findall(r'<join expr="[^"]+"', self.before)
        self.assertTrue(all(j in self.after for j in jt_before))

    def test_idempotent_and_one_datasource(self):
        self.assertEqual(pw.patch(self.after), self.after)
        self.assertEqual(len(set(re.findall(r'datasourceId="([^"]+)"', self.after))), 1)

    def test_validator_accepts_the_result(self):
        out = ROOT / "backups" / "jaspersoft" / "write_offs_domain_patched_for_test.xml"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.after, encoding="utf-8")
        r = subprocess.run([sys.executable, str(ROOT / "scripts/jaspersoft/validate_domain_schema.py"), str(out)],
                           capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
