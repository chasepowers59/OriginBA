"""build_adj_ap_request_domain: the schema it emits is structurally sound before it goes near a
server -- every item resolves to a join-tree field, ids are unique, joins name real tables, the
request-to-adjustment join is the only inner one, and the validator accepts it."""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "jaspersoft"))
import build_adj_ap_request_domain as b  # noqa: E402

NS = "{http://www.jaspersoft.com/2007/SL/XMLSchema}"


class Schema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.xml = b.schema("Origin_DEV_DS")
        cls.root = ET.fromstring(cls.xml)
        cls.jt = next(t for t in cls.root.iter(NS + "jdbcTable") if t.get("id") == "JoinTree_1")
        cls.jt_fields = {f.get("id") for f in cls.jt.iter(NS + "field")}

    def test_every_item_resolves_and_ids_are_unique(self):
        items = list(self.root.iter(NS + "item"))
        ids = [i.get("id") for i in items]
        self.assertEqual(len(ids), len(set(ids)), "duplicate item id")
        for i in items:
            rid = i.get("resourceId")
            self.assertTrue(rid.startswith("JoinTree_1."), rid)
            self.assertIn(rid.removeprefix("JoinTree_1."), self.jt_fields, rid)

    def test_join_tree_fields_come_from_declared_tables_or_calculations(self):
        tables = {t.get("id"): {f.get("id") for f in t.iter(NS + "field")} for t in self.root.iter(NS + "jdbcTable") if t.get("id") != "JoinTree_1"}
        calc = {f.get("id") for f in self.jt.iter(NS + "field") if f.get("dataSetExpression")}
        for fid in self.jt_fields:
            if fid in calc:
                continue
            table, col = fid.split(".", 1)
            self.assertIn(col, tables[table], fid)

    def test_joins_name_real_tables_and_only_the_request_link_is_inner(self):
        tables = {t.get("id") for t in self.root.iter(NS + "jdbcTable")}
        refs = {r.get("tableId") for r in self.root.iter(NS + "tableRef")}
        for j in self.root.iter(NS + "join"):
            self.assertIn(j.get("left"), tables); self.assertIn(j.get("right"), tables)
            self.assertIn(j.get("right"), refs)
            if j.get("type") == "inner":
                self.assertEqual((j.get("left"), j.get("right")), ("CI_ADJ_APREQ", "CI_ADJ"),
                                 "SA/account/customer must be outer: 2 of 16 Odessa adjustments point at a missing SA")
        self.assertEqual(len(refs), len(b.TABLES))

    def test_label_joins_carry_a_language_and_lookups_a_field_name(self):
        for e, l, r, _ in b.JOINS:
            if r.endswith("_L"):
                self.assertIn("LANGUAGE_CD == 'ENG'", e, e)
            if r in ("REQ_STAT_L", "ADJ_STAT_L"):
                self.assertIn("FIELD_NAME ==", e, e)

    def test_only_lifecycle_codes_are_literal(self):
        literals = set(re.findall(r"== '([^']+)'", " ".join(x for _, x, _ in b.CALCULATED)))
        self.assertTrue(literals <= {"X", "P", "30", "50", "60"}, literals)

    def test_one_datasource_and_the_validator_accepts_it(self):
        self.assertEqual(set(re.findall(r'datasourceId="([^"]+)"', self.xml)), {"Origin_DEV_DS"})
        out = ROOT / "backups" / "jaspersoft" / "adj_ap_request_domain_for_test.xml"
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(self.xml, encoding="utf-8")
        r = subprocess.run([sys.executable, str(ROOT / "scripts/jaspersoft/validate_domain_schema.py"), str(out)], capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("/>", self.xml, "JRS exports use explicit close tags")


if __name__ == "__main__":
    unittest.main()
