"""patch_budget_domain on the real Origin_DEV export of the Budget domain (Standard Offering >
Billing and Rates > Budget Billing): nothing existing changes, the two new join trees are whole
(every item resolves inside its own tree, every table is the tree's own copy), the derived SQL
obeys the domain parser's rules, and the budget rule is C2M's own flags, never a client code.

Measured on College Station TEST 2026-09-30 before any of this was written: 965 accounts on budget
(ELIG_BUDGET_SW + Active/Pending Stop + current recurring charge > 0), 594 of them with a frozen
LPC adjustment in 12 months, 4,330 fees, $28,884.35; the budget plan code alone matches 104,826.
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "jaspersoft"))
import domain_schema  # noqa: E402
import patch_budget_domain as p  # noqa: E402

NS = "{http://www.jaspersoft.com/2007/SL/XMLSchema}"
# the Origin_DEV schema as exported before the patch (2026-09-30), and as the server holds it after
SNAP = ROOT / "domains/manual_imports/budget_domain/schema.reference.xml"
PATCHED = ROOT / "domains/manual_imports/budget_domain/schema.patched.xml"


@unittest.skipUnless(SNAP.exists(), "needs the pre-patch reference schema")
class Patch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = SNAP.read_text(encoding="utf-8")
        cls.after = p.patch_schema(cls.before)
        cls.root = ET.fromstring(cls.after)

    def tree(self, tid):
        return next(t for t in self.root.iter(NS + "jdbcTable") if t.get("id") == tid)

    def test_the_patch_is_additive_only(self):
        self.assertEqual(domain_schema.additions_only(self.before, self.after), [])

    def test_the_server_holds_exactly_this_patch(self):
        self.assertEqual(PATCHED.read_text(encoding="utf-8"), self.after)

    def test_refuses_to_patch_twice(self):
        with self.assertRaises(ValueError):
            p.patch_schema(self.after)

    def test_every_tree_is_a_data_island(self):
        islands = {g.get("id"): g.get("resourceId") for g in self.root.find(NS + "dataIslands")}
        self.assertEqual(islands, {"JoinTree_1": "JoinTree_1", "JoinTree_2": "JoinTree_2", "JoinTree_3": "JoinTree_3"})

    def test_every_item_resolves_inside_its_own_tree(self):
        for g in self.root.find(NS + "itemGroups"):
            tid = g.get("resourceId")
            fields = {f.get("id") for f in self.tree(tid).iter(NS + "field")}
            for i in g.iter(NS + "item"):
                rid = i.get("resourceId")
                self.assertTrue(rid.startswith(tid + "."), (g.get("id"), i.get("id"), rid))
                self.assertIn(rid[len(tid) + 1:], fields, (g.get("id"), i.get("id")))

    def test_item_ids_are_unique_across_the_domain(self):
        ids = [i.get("id") for i in self.root.iter(NS + "item")]
        self.assertEqual(len(ids), len(set(ids)))

    def test_a_table_belongs_to_one_tree(self):
        owner = {}
        for tid in ("JoinTree_1", "JoinTree_2", "JoinTree_3"):
            for r in self.tree(tid).iter(NS + "tableRef"):
                self.assertNotIn(r.get("tableId"), owner, f"{r.get('tableId')} in {owner.get(r.get('tableId'))} and {tid}")
                owner[r.get("tableId")] = tid

    def test_the_population_table_is_always_in_the_query(self):
        # each tree roots on its account copy; the ONE inner join is to the derived table that defines
        # the population (budget accounts / budget changes), and it is always included, or an Ad Hoc
        # view with only account fields would drop the join and list every account in C2M
        for tid, root, population in (("JoinTree_2", "BA_ACCT", "BA_BUDGET"), ("JoinTree_3", "BC_ACCT", "BC_CHANGE")):
            t = self.tree(tid)
            self.assertEqual(t.find(NS + "joinInfo").get("alias"), root)
            inner = [j.get("right") for j in t.iter(NS + "join") if j.get("type") == "inner"]
            self.assertEqual(inner, [population], tid)
            always = [r.get("tableId") for r in t.iter(NS + "tableRef") if r.get("alwaysIncludeTable") == "true"]
            self.assertEqual(always, [population], tid)
            self.assertTrue(all(j.get("type") in ("inner", "leftOuter") for j in t.iter(NS + "join")))

    def test_label_joins_carry_their_key(self):
        for tid in ("JoinTree_2", "JoinTree_3"):
            for j in self.tree(tid).iter(NS + "join"):
                if j.get("right").endswith("_L"):
                    self.assertIn("LANGUAGE_CD == 'ENG'", j.get("expr"), j.get("right"))
                if j.get("right") == "BC_SA_TYPE_L":
                    self.assertIn("CIS_DIVISION", j.get("expr"))   # SA type labels are division-qualified

    def test_derived_sql_obeys_the_domain_parser(self):
        for q in self.root.iter(NS + "jdbcQuery"):
            sql = (q.find(NS + "query").text or "").strip()
            self.assertTrue(sql.upper().startswith("SELECT"), q.get("id"))
            self.assertNotIn(";", sql, q.get("id"))
            self.assertNotIn(" WITH ", sql.upper(), q.get("id"))
            self.assertIsNone(re.search(r":\w|\$P\{", sql), q.get("id"))

    def test_the_budget_rule_is_c2m_flags_not_client_codes(self):
        sql = p.DERIVED["BA_BUDGET"][0]
        for part in ("ELIG_BUDGET_SW = 'Y'", "SA_STATUS_FLG IN ('20', '30')", "RCR_CHG_AMT > 0", "EFFDT <= TRUNC(SYSDATE)"):
            self.assertIn(part, sql)
        self.assertNotIn("BUD_PLAN_CD", sql)       # 104,826 accounts carry a plan code; 965 are on budget
        added = " ".join([q for q, _ in p.DERIVED.values()] + [e for e, *_ in p.BA_JOINS + p.BC_JOINS])
        self.assertNotIn("LPC", added)   # the late-fee code is the view's filter, per client

    def test_adjustments_are_net_of_cancellation_by_status(self):
        sql = p.DERIVED["BA_ADJ_12M"][0]
        self.assertIn("ADJ_STATUS_FLG = '50'", sql)
        self.assertIn("ADJ_STATUS_FLG = '60'", sql)
        self.assertNotIn("CI_FT", sql)   # summing ADJ_AMT over CI_FT counted a cancelled fee twice

    def test_validator_accepts(self):
        out = ROOT / "backups" / "jaspersoft" / "budget_patch_for_test.xml"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.after, encoding="utf-8")
        r = subprocess.run([sys.executable, str(ROOT / "scripts/jaspersoft/validate_domain_schema.py"), str(out)],
                           capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_probe_reads_one_tree(self):
        # jrs_domain_patch_apply probes the first ten items of SETS in ONE query; items from two
        # trees cannot be combined, so the first set must hold ten items of a single tree
        first = p.SETS[0]
        self.assertGreaterEqual(len(first[2]), 10)


if __name__ == "__main__":
    unittest.main()
