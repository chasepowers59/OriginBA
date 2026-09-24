"""build_adjustment_domain: the comprehensive Adjustment domain is structurally sound before it goes
near a server -- one row per adjustment (root CI_ADJ, every join outer), every item resolves, ids
are unique, labels join on their full key at ENG, no secret column reaches an item, only
base-product lifecycle codes are literal, and the validator accepts it."""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "jaspersoft"))
import build_adjustment_domain as b  # noqa: E402

NS = "{http://www.jaspersoft.com/2007/SL/XMLSchema}"
SECRETS = {"ALERT_INFO", "WEB_PASSWD", "WEB_PASSWD_ANS", "WEB_PWD_HINT_FLG", "MICR_ID"}


class Schema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.xml = b.schema("Origin_DEV_DS")
        cls.root = ET.fromstring(cls.xml)
        cls.jt = next(t for t in cls.root.iter(NS + "jdbcTable") if t.get("id") == "JoinTree_1")
        cls.jt_fields = {f.get("id") for f in cls.jt.iter(NS + "field")}
        cls.items = list(cls.root.iter(NS + "item"))

    def test_every_item_resolves_and_ids_are_unique(self):
        ids = [i.get("id") for i in self.items]
        self.assertEqual(len(ids), len(set(ids)), "duplicate item id")
        for i in self.items:
            rid = i.get("resourceId")
            self.assertTrue(rid.startswith("JoinTree_1."), rid)
            self.assertIn(rid.removeprefix("JoinTree_1."), self.jt_fields, rid)

    def test_join_tree_fields_come_from_declared_tables_queries_or_calculations(self):
        declared = {t.get("id"): {f.get("id") for f in t.iter(NS + "field")}
                    for t in list(self.root.iter(NS + "jdbcTable")) + list(self.root.iter(NS + "jdbcQuery")) if t.get("id") != "JoinTree_1"}
        calc = {f.get("id") for f in self.jt.iter(NS + "field") if f.get("dataSetExpression")}
        for fid in self.jt_fields:
            if fid in calc:
                continue
            table, col = fid.split(".", 1)
            self.assertIn(col, declared[table], fid)

    def test_root_is_the_adjustment_and_every_join_is_outer(self):
        self.assertIn('<joinInfo alias="CI_ADJ" referenceId="CI_ADJ">', self.xml)
        tables = {t.get("id") for t in self.root.iter(NS + "jdbcTable")} | {q.get("id") for q in self.root.iter(NS + "jdbcQuery")}
        refs = {r.get("tableId") for r in self.root.iter(NS + "tableRef")}
        reached = {"CI_ADJ"}
        for j in self.root.iter(NS + "join"):
            self.assertEqual(j.get("type"), "leftOuter", f"{j.get('left')} -> {j.get('right')}: one row per adjustment means nothing may drop it")
            self.assertIn(j.get("left"), tables); self.assertIn(j.get("right"), tables)
            self.assertIn(j.get("left"), reached, f"{j.get('right')} joined before its left side {j.get('left')} is reachable from CI_ADJ")
            reached.add(j.get("right"))
        self.assertEqual(reached, refs, "every referenced table is joined exactly once from the root")
        self.assertEqual(len(refs), len(b.TABLES) + len(b.DERIVED))

    def test_label_and_lookup_joins_carry_their_full_key(self):
        for e, _, r, _ in b.JOINS:
            if r.endswith("_L") or r in b.LOOKUPS:
                self.assertIn("LANGUAGE_CD == 'ENG'", e, e)
            if r in b.LOOKUPS:
                self.assertIn(f"{r}.FIELD_NAME == '{b.LOOKUPS[r]}'", e, e)
            if r == "CI_SA_TYPE_L":
                self.assertIn("CIS_DIVISION", e, "SA type labels are division-qualified")
            if r == "APPR_STAT_L":
                self.assertIn("BUS_OBJ_CD", e, "BO status labels are per business object")

    def test_the_customer_chain_is_the_main_customer_primary_name(self):
        joins = {r: e for e, _, r, _ in b.JOINS}
        self.assertIn("MAIN_CUST_SW == 'Y'", joins["CI_ACCT_PER"])
        self.assertIn("NAME_TYPE_FLG == 'PRIM'", joins["CI_PER_NAME"])

    def test_no_secret_column_is_declared_anywhere(self):
        cols = {f.get("id").rsplit(".", 1)[-1] for f in self.root.iter(NS + "field")}
        self.assertFalse(cols & SECRETS, cols & SECRETS)

    def test_only_base_product_codes_are_literal(self):
        literals = set(re.findall(r"== '([^']*)'", " ".join(x for _, x, _ in b.CALCULATED)))
        self.assertTrue(literals <= b.BASE_PRODUCT_LITERALS, literals - b.BASE_PRODUCT_LITERALS)

    def test_derived_tables_aggregate_to_one_row_per_adjustment(self):
        for qid, (sql, fields) in b.DERIVED.items():
            one_per_adj = re.search(r"group by\s+\w+\.(sibling_id|adj_id)(, a\.cre_dt)?\s*$", sql.lower()) or re.search(r"from cisadm\.ci_adj a\s*$", sql.lower())
            self.assertTrue(one_per_adj, f"{qid}: not one row per adjustment")
            self.assertNotIn("sysdate", " ".join(x for _, x, _ in b.CALCULATED).lower()); self.assertNotIn("Today(", " ".join(x for _, x, _ in b.CALCULATED))
            self.assertEqual(fields[0][0], "ADJ_ID", qid)
            self.assertNotIn("$P{", sql)

    def test_every_table_column_the_sets_expose_is_labelled_distinctly_within_its_set(self):
        for sid, _, items in b.SETS:
            labels = [l for _, l, _ in items]
            self.assertEqual(len(labels), len(set(labels)), f"{sid}: repeated label")

    def test_one_datasource_and_the_validator_accepts_it(self):
        self.assertEqual(set(re.findall(r'datasourceId="([^"]+)"', self.xml)), {"Origin_DEV_DS"})
        out = ROOT / "backups" / "jaspersoft" / "adjustment_domain_for_test.xml"
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(self.xml, encoding="utf-8")
        r = subprocess.run([sys.executable, str(ROOT / "scripts/jaspersoft/validate_domain_schema.py"), str(out)], capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("/>", self.xml)
        self.assertNotIn("<filterString></filterString>", self.xml)


if __name__ == "__main__":
    unittest.main()
