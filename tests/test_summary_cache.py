"""The home and workstream summaries are not recomputed on every visit.

Ellensburg's home page summary took ~3 s warm (nine KPI queries against Oracle) on every
load, and a canvas only changes when the warehouse is rebuilt. A summary is kept for five
minutes per everything it depends on; one with any failed card is never kept, so a
transient error is not served back to the next visitor.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import snapshot_explorer as se  # noqa: E402
from api import summary_cache  # noqa: E402


class Ctx:
    workstreams = ["*"]

    def require_permission(self, _):
        return None


class SummaryCacheTests(unittest.TestCase):
    def setUp(self):
        summary_cache.clear()
        self.p = mock.patch.object(se, "require_org_for_data", return_value="ellensburg")
        self.p.start()

    def tearDown(self):
        self.p.stop()
        summary_cache.clear()

    def _home(self, built, ctx=None, days=30):
        with mock.patch.object(se, "build_executive_summary", side_effect=built) as b:
            se.executive_summary(days=days, compare=False, compare_mode="prior_period",
                                 cross_field=None, cross_value=None, lens=[], ctx=ctx or Ctx())
        return b.call_count

    def test_a_second_visit_is_served_from_the_cache(self):
        ok = lambda *a, **k: {"kpis": [{"id": "k", "error": None}]}  # noqa: E731
        self.assertEqual(self._home(ok), 1)
        self.assertEqual(self._home(ok), 0)

    def test_a_summary_with_a_failed_card_is_not_kept(self):
        bad = lambda *a, **k: {"kpis": [{"id": "k", "error": "This figure could not be loaded right now."}]}  # noqa: E731
        self._home(bad)
        self.assertEqual(self._home(bad), 1)

    def test_a_different_window_or_grant_is_its_own_entry(self):
        ok = lambda *a, **k: {"kpis": []}  # noqa: E731
        self._home(ok)
        self.assertEqual(self._home(ok, days=90), 1)
        narrow = Ctx(); narrow.workstreams = ["debt"]
        self.assertEqual(self._home(ok, ctx=narrow), 1)


if __name__ == "__main__":
    unittest.main()
