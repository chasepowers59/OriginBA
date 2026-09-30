"""The characteristics patch (scripts/jaspersoft/patch_domain_characteristics.py) on the
Service Agreement 360 schema: the derived tables replace the raw characteristic tables and
their labels under the SAME ids, every reference still resolves, one datasource, and the
derived SQL is parser-safe. Runs on the schema the builder produces (Origin_DEV_DS)."""
from __future__ import annotations

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "jaspersoft"))
import patch_domain_characteristics as pdc  # noqa: E402

SOURCE = ROOT / "domains/manual_imports/service_agreement_360_prem_char/Service_Agreement___Domain_files/schema.data"
NS = "{http://www.jaspersoft.com/2007/SL/XMLSchema}"


def _resources(root):
    out = {}
    for tag in ("jdbcTable", "jdbcQuery"):
        for r in root.iter(NS + tag):
            out[r.get("id")] = {f.get("id") for f in r.iter(NS + "field")}
    return out


class Patched(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = SOURCE.read_text(encoding="utf-8")
        if "<jdbcQuery" in raw:   # the builder already applied it; recover the raw shape is not needed
            cls.schema = raw
        else:
            cls.schema = pdc.patch(raw)
        cls.root = ET.fromstring(cls.schema)
        cls.res = _resources(cls.root)

    def test_the_characteristic_tables_are_derived_under_their_original_ids(self):
        queries = {q.get("id"): q for q in self.root.iter(NS + "jdbcQuery")}
        self.assertEqual(set(queries), {"CI_SA_CHAR", "CI_PREM_CHAR"})
        for tid, q in queries.items():
            sql = q.find(NS + "query").text
            self.assertTrue(sql.startswith("SELECT "), "a derived table query must start with SELECT")
            self.assertNotIn(";", sql)
            self.assertNotIn("$P{", sql)
            self.assertIn("IS_CURRENT_SW", sql)
            self.assertIn("CHAR_VALUE", sql)
            self.assertIn(f"CISADM.{tid} c", sql)
        for gone in ("CI_CHAR_TYPE_L", "CI_CHAR_VAL_L", "CI_CHAR_TYPE_L_2", "CI_CHAR_VAL_L_2"):
            self.assertNotIn(gone, self.res, f"{gone} should no longer be a table")

    def test_one_datasource_everywhere(self):
        ids = set(re.findall(r'datasourceId="([^"]+)"', self.schema)) | set(re.findall(r'<jdbcDataSource id="([^"]+)"', self.schema))
        self.assertEqual(len(ids), 1, ids)

    def test_every_reference_resolves(self):
        tree = self.res["JoinTree_1"]
        for f in tree:
            if "." in f:
                alias, col = f.split(".", 1)
                self.assertIn(alias, self.res, f)
                self.assertIn(col, self.res[alias], f)
        for m in re.finditer(r'resourceId="JoinTree_1\.([^"]+)"', self.schema):
            self.assertIn(m.group(1), tree, m.group(0))
        refs = re.findall(r'tableId="([^"]+)"', self.schema)
        for r in refs:
            self.assertIn(r, self.res, r)
        for j in self.root.iter(NS + "join"):
            self.assertIn(j.get("left"), refs); self.assertIn(j.get("right"), refs)
            self.assertNotIn("CHAR_TYPE_L", j.get("right")); self.assertNotIn("CHAR_VAL_L", j.get("right"))

    def test_the_groups_keep_their_item_ids_and_gain_the_resolved_columns(self):
        for table in ("CI_SA_CHAR", "CI_PREM_CHAR"):
            g = next(g for g in self.root.iter(NS + "itemGroup") if g.get("id") == table)
            items = {i.get("id"): i.get("resourceId") for i in g.iter(NS + "item")}
            self.assertIn(f"{table}_CHAR_TYPE_CD", items)
            self.assertEqual(items[f"{table}_CHAR_VALUE"], f"JoinTree_1.{table}.CHAR_VALUE")
            self.assertEqual(items[f"{table}_IS_CURRENT_SW"], f"JoinTree_1.{table}.IS_CURRENT_SW")
            descr = [v for k, v in items.items() if k.endswith("TYPE_L_DESCR") or k.endswith("TYPE_L_2_DESCR")]
            self.assertEqual(descr, [f"JoinTree_1.{table}.CHAR_TYPE_DESCR"])

    def test_distinct_sa_counts_sas(self):
        self.assertIn("CountDistinct(CI_SA.SA_ID, 'Current')", self.schema)
        self.assertNotIn("CountDistinct(CI_SA_CONTERM.SA_ID, 'Current')", self.schema)

    def test_patching_twice_is_refused(self):
        with self.assertRaises(SystemExit):
            pdc.patch(self.schema)


class AnyCharacteristicTable(unittest.TestCase):
    def test_a_target_spec_names_table_key_and_the_two_label_aliases(self):
        self.assertEqual(pdc.parse_target("CI_ACCT_CHAR:ACCT_ID:CI_CHAR_TYPE_L_3:CI_CHAR_VAL_L_3"),
                         ("CI_ACCT_CHAR", {"key": "ACCT_ID", "type_l": "CI_CHAR_TYPE_L_3", "val_l": "CI_CHAR_VAL_L_3"}))
        with self.assertRaises(SystemExit):
            pdc.parse_target("CI_ACCT_CHAR:ACCT_ID")

    def test_the_derived_sql_is_generic_over_the_entity_key(self):
        sql = pdc.derived_sql("CI_ACCT_CHAR", "ACCT_ID")
        self.assertIn("FROM CISADM.CI_ACCT_CHAR c", sql)
        self.assertIn("PARTITION BY c.ACCT_ID, c.CHAR_TYPE_CD", sql)
        self.assertTrue(sql.startswith("SELECT ACCT_ID, CHAR_TYPE_CD"))


class DerivedSql(unittest.TestCase):
    def test_value_resolution_covers_all_three_kinds(self):
        sql = pdc.derived_sql("CI_PREM_CHAR", "PREM_ID")
        self.assertIn("WHEN 'ADV' THEN c.ADHOC_CHAR_VAL", sql)
        self.assertIn("WHEN 'FKV' THEN c.CHAR_VAL_FK1", sql)
        self.assertIn("ELSE COALESCE(cvl.DESCR, c.CHAR_VAL)", sql)
        self.assertIn("PARTITION BY c.PREM_ID, c.CHAR_TYPE_CD", sql)
        self.assertIn("c.EFFDT <= CURRENT_DATE", sql, "a future-dated version is not current")


if __name__ == "__main__":
    unittest.main()
