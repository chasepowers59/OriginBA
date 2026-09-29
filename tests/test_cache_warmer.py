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
                  organization_id="demo25", organization_name="Demo", permissions={"snapshots:read"},
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
