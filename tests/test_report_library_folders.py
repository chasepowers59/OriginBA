"""The report library is a folder tree (catalog["report_library"]), scoped to the caller.

Each folder's {snapshot_id, report_id} references resolve into the same card the packs
carry, plus `essential`. Folders keep catalog order; a folder with nothing left to show --
empty in the catalog, unresolvable, or emptied by the caller's access -- is not sent,
because an empty folder in the rail reads as a broken one.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import report_library as rl  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402
from api.snapshot_catalog import CatalogError  # noqa: E402


def _premade(rid):
    return {"id": rid, "title": f"Title {rid}", "description": f"Why {rid}", "chart_type": "bar",
            "dimensions": ["Bill Cycle"], "measures": [{"field": "*", "agg": "count"}], "filters": []}


CATALOG = {
    "client": "test",
    "workstream_labels": {"billing": "Billing", "finance": "Finance"},
    "snapshots": {
        "rpt_bill_segment": {"label": "Bill Segment", "workstream": "billing",
                             "grain_description": "One row per bill segment",
                             "fields": [{"id": "Service Type"}],
                             "premade_reports": [_premade("billed"), _premade("rebilled"), _premade("late")]},
        "rpt_gl": {"label": "GL Distribution", "workstream": "finance", "grain_description": "One row per GL line",
                   "fields": [{"id": "GL Account"}],
                   "premade_reports": [_premade("gl_total")]},
    },
    "report_library_packs": [
        {"id": "pack", "title": "Pack", "description": "", "audience": "",
         "reports": [{"snapshot_id": "rpt_bill_segment", "report_id": "billed"}]},
    ],
    "report_library": [
        {"id": "billing_revenue", "title": "Billing & Revenue", "description": "What was billed.",
         "reports": [{"snapshot_id": "rpt_bill_segment", "report_id": "billed", "essential": True},
                     {"snapshot_id": "rpt_bill_segment", "report_id": "rebilled", "essential": True},
                     {"snapshot_id": "rpt_bill_segment", "report_id": "late", "essential": False},
                     {"snapshot_id": "rpt_bill_segment", "report_id": "no_such_report", "essential": False}]},
        {"id": "budget_billing", "title": "Budget Billing", "description": "Fills later.", "reports": []},
        {"id": "ghosts", "title": "Ghosts", "description": "Nothing here resolves.",
         "reports": [{"snapshot_id": "rpt_missing", "report_id": "x", "essential": True}]},
        {"id": "finance_adjustments", "title": "Finance & Adjustments", "description": "The ledger.",
         "reports": [{"snapshot_id": "rpt_gl", "report_id": "gl_total", "essential": True}]},
    ],
}


class FolderResolutionTests(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(rl, "load_catalog", return_value=CATALOG)
        p.start()
        self.addCleanup(p.stop)
        self.lib = rl.get_report_library("dev")

    def test_folders_keep_catalog_order_and_skip_empty_ones(self):
        self.assertEqual([f["id"] for f in self.lib["folders"]], ["billing_revenue", "finance_adjustments"])

    def test_a_folder_carries_its_title_description_and_count(self):
        f = self.lib["folders"][0]
        self.assertEqual((f["title"], f["description"], f["report_count"]),
                         ("Billing & Revenue", "What was billed.", 3))

    def test_cards_are_the_library_card_plus_essential(self):
        cards = self.lib["folders"][0]["reports"]
        self.assertEqual([(c["report_id"], c["essential"]) for c in cards],
                         [("billed", True), ("rebilled", True), ("late", False)])
        card = cards[0]
        self.assertEqual(card["explore_url"], "/explore/rpt_bill_segment?report=billed")
        self.assertEqual(card["snapshot_label"], "Bill Segment")
        self.assertEqual(card["workstream"], "billing")
        self.assertEqual(card["workstream_label"], "Billing")
        self.assertEqual(card["dimensions"], ["Bill Cycle"])
        self.assertEqual(card["grain_description"], "One row per bill segment")

    def test_the_library_total_counts_the_folders(self):
        self.assertEqual(self.lib["report_count"], 4)

    def test_a_catalog_error_returns_an_empty_tree(self):
        with mock.patch.object(rl, "load_catalog", side_effect=CatalogError("gone")):
            lib = rl.get_report_library("dev")
        self.assertEqual(lib["folders"], [])
        self.assertIn("error", lib)


def _ctx(workstreams, rules=()):
    return AuthContext(id="u", email="u@utility.gov", display_name="u", role="viewer", client_id="dev",
                       organization_id="dev", organization_name="Dev", permissions={"report_library:read"},
                       workstreams=workstreams, row_rules=tuple(rules))


class FolderAccessTests(unittest.TestCase):
    """The route scopes folders exactly as it scopes packs: never a report on a workstream
    or canvas the caller cannot reach, and never a folder that scoping emptied."""

    def setUp(self):
        for target in ("api.report_library.load_catalog", "api.snapshot_catalog.load_catalog"):
            p = mock.patch(target, return_value=CATALOG)
            p.start()
            self.addCleanup(p.stop)
        from api import portal_routes
        self.route = portal_routes.report_library

    def _ids(self, lib):
        return {f["id"]: [c["report_id"] for c in f["reports"]] for f in lib["folders"]}

    def test_full_access_and_an_empty_grant_see_every_folder(self):
        for grant in (["*"], []):
            self.assertEqual(list(self._ids(self.route(ctx=_ctx(grant)))),
                             ["billing_revenue", "finance_adjustments"], grant)

    def test_a_workstream_grant_drops_other_workstreams_and_the_folders_they_emptied(self):
        lib = self.route(ctx=_ctx(["finance"]))
        self.assertEqual(self._ids(lib), {"finance_adjustments": ["gl_total"]})
        self.assertEqual(lib["folders"][0]["report_count"], 1)
        self.assertEqual(lib["report_count"], 1)
        self.assertEqual(lib["packs"], [])

    def test_row_rules_drop_canvases_that_do_not_carry_the_column(self):
        lib = self.route(ctx=_ctx(["*"], [{"field": "Service Type", "values": ["Water"]}]))
        self.assertEqual(self._ids(lib), {"billing_revenue": ["billed", "rebilled", "late"]})
        self.assertEqual(lib["report_count"], 3)

    def test_both_rules_apply_together(self):
        # finance alone keeps the ledger folder; the Service Type rule alone keeps billing;
        # together nothing is readable, so nothing -- not even a folder name -- is returned
        lib = self.route(ctx=_ctx(["finance"], [{"field": "Service Type", "values": ["Water"]}]))
        self.assertEqual((lib["folders"], lib["report_count"]), ([], 0))


if __name__ == "__main__":
    unittest.main()
