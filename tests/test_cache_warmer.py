"""After a warehouse rebuild, the home page and each workstream page are built once in the
background, so the first person each morning is not the one who waits.

The warmer notices a new build stamp (api/data_version.py), then builds the summaries a page
asks for by default (30 days, no comparison, no filters) for a reader with every workstream
and no row rules, through the SAME cache keys the routes use. Nothing happens while the stamp
is unchanged or unknown; a failed build is logged and never stops the rest. It does not run
under tests, and PORTAL_WARM_CACHE=false switches it off.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import cache_warmer as cw  # noqa: E402
from api import snapshot_explorer as se  # noqa: E402
from api import summary_cache as sc  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402

CTX = AuthContext(id="u", email="u@utility.gov", display_name="u", role="editor", client_id="demo25",
                  organization_id="demo25", organization_name="Demo", permissions={"snapshots:read", "snapshots:query"},
                  workstreams=["*"])


class WarmerTests(unittest.TestCase):
    def setUp(self):
        sc.clear()
        cw.reset()
        self.version = ["v1"]
        self.home = mock.patch.object(se, "build_executive_summary", side_effect=lambda *a, **k: {"kpis": [], "who": "home"})
        self.ws = mock.patch.object(se, "build_workstream_summary", side_effect=lambda ws, *a, **k: {"kpis": [], "ws": ws})
        self.patches = [self.home, self.ws,
                        mock.patch.object(cw, "data_version", side_effect=lambda org: self.version[0]),
                        mock.patch.object(se, "data_version", side_effect=lambda org: self.version[0]),
                        mock.patch.object(cw, "_workstreams", return_value=["billing", "finance"]),
                        mock.patch.object(se, "require_org_for_data", return_value="demo25"),
                        mock.patch.object(se, "assert_workstream_access")]
        self.mocks = [p.start() for p in self.patches]

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_a_new_stamp_warms_what_the_pages_ask_for(self):
        self.assertEqual(cw.warm_once("demo25"), ["home", "billing", "finance"])
        home, ws = self.mocks[0], self.mocks[1]
        home.reset_mock(), ws.reset_mock()
        # the pages' default requests are now answered from memory
        se.executive_summary(days=30, compare=False, compare_mode="prior_period", cross_field=None,
                             cross_value=None, lens=[], ctx=CTX)
        se.workstream_summary("billing", days=30, compare=False, compare_mode="prior_period",
                              cross_field=None, cross_value=None, ctx=CTX)
        home.assert_not_called()
        ws.assert_not_called()

    def test_an_unchanged_stamp_does_nothing(self):
        cw.warm_once("demo25")
        self.assertEqual(cw.warm_once("demo25"), [])
        self.version[0] = "v2"
        self.assertEqual(cw.warm_once("demo25"), ["home", "billing", "finance"])

    def test_an_unknown_stamp_does_nothing(self):
        self.version[0] = None
        self.assertEqual(cw.warm_once("demo25"), [])

    def test_a_failed_build_does_not_stop_the_rest(self):
        self.mocks[0].side_effect = RuntimeError("ORA-03113")
        with self.assertLogs("originba.api", level="WARNING"):
            self.assertEqual(cw.warm_once("demo25"), ["billing", "finance"])


BIG = {"id": "rpt_billed_charge", "label": "Billed Charge", "table_name": "rpt_billed_charge",
       "fields": [{"id": f} for f in ("Bill Date", "Customer Class", "Billed Amount", "Is Frozen")],
       "trusted_measures": ["Billed Amount"], "default_date_field": "Bill Date",
       "default_date_preset": "last_12_months", "max_rows": 500,
       "premade_reports": [{"id": "by_class", "dimensions": ["Customer Class"],
                            "measures": [{"field": "Billed Amount", "agg": "sum"}],
                            "filters": [{"field": "Is Frozen", "op": "eq", "value": True}]}]}
SMALL = {**BIG, "id": "rpt_bill", "table_name": "rpt_bill"}


class ReportWarmingTests(unittest.TestCase):
    """A large canvas's opening report (the first ready-to-run report over the canvas's default
    window, which the explorer runs when the page opens) is run after a rebuild too."""

    def setUp(self):
        sc.clear()
        cw.reset()
        self.runs = []
        catalog = {"snapshots": {"rpt_billed_charge": BIG, "rpt_bill": SMALL}}
        self.patches = [
            mock.patch.object(cw, "data_version", return_value="v1"),
            mock.patch.object(se, "data_version", return_value="v1"),
            mock.patch.object(cw, "_workstreams", return_value=[]),
            mock.patch.object(se, "build_executive_summary", return_value={"kpis": []}),
            mock.patch("api.snapshot_catalog.load_catalog", return_value=catalog),
            mock.patch.object(se, "_row_estimate", side_effect=lambda snap, org: 3_160_000 if snap is BIG else 40_000),
            mock.patch.object(se, "snapshot_backend", return_value=("postgres", "postgres", "reporting")),
            mock.patch.object(cw, "data_as_of", return_value="2026-09-29"),
            mock.patch("api.warehouse_db.execute_query",
                       side_effect=lambda sql, binds=None, **k: self.runs.append(sql) or (["Customer Class", "m0"], [["R", 1.0]])),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_the_opening_report_of_a_large_canvas_is_warm(self):
        self.assertEqual(cw.warm_once("demo25"), ["home", "report rpt_billed_charge"])
        self.assertEqual(len(self.runs), 1)
        # what the explorer sends when the page opens (ExplorerPanel.runPremade): the canvas's
        # window first (last_12_months as of 2026-09-29), then the report's own filters
        body = se.QueryRequest(dimensions=["Customer Class"], measures=[{"field": "Billed Amount", "agg": "sum"}],
                               filters=[{"field": "Bill Date", "op": "between", "value": ["2025-09-29", "2026-09-29"]},
                                        {"field": "Is Frozen", "op": "eq", "value": True}],
                               time_dimensions=[], limit=500)
        with mock.patch.object(se, "require_org_for_data", return_value="demo25"), \
             mock.patch.object(se, "_require_snapshot_access", return_value=BIG), \
             mock.patch("api.access_audit.record_access_event"):
            se.snapshot_query("rpt_billed_charge", body, ctx=CTX)
        self.assertEqual(len(self.runs), 1)


class SwitchTests(unittest.TestCase):
    def test_off_under_tests_and_when_switched_off(self):
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            self.assertFalse(cw.enabled())
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "production", "PORTAL_WARM_CACHE": "false"}):
            self.assertFalse(cw.enabled())
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "production", "PORTAL_WARM_CACHE": ""}):
            self.assertTrue(cw.enabled())


if __name__ == "__main__":
    unittest.main()
