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
    row_rules = ()
    workstreams = ["*"]
    email, id = "t@x", "t"

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


class QueryCacheTests(unittest.TestCase):
    """An explorer report on Ellensburg's rpt_billed_charge (589K rows in its six-month
    window, 2.2 GB) took ~25 s, and a canvas changes only when the warehouse is rebuilt.
    The same statement for the same org is answered from memory for five minutes; every
    run is still audited."""

    def setUp(self):
        summary_cache.clear()

    def tearDown(self):
        summary_cache.clear()

    def _query(self, run, start="2025-12-20"):
        body = se.QueryRequest(dimensions=["Customer Class"], measures=[{"field": "Billed Amount", "agg": "sum"}],
                               filters=[{"field": "Bill Date", "op": "between", "value": [start, "2026-06-18"]}],
                               limit=500)
        snap = {"table_name": "rpt_billed_charge", "fields": [], "trusted_measures": ["Billed Amount"]}
        with mock.patch.object(se, "require_org_for_data", return_value="ellensburg"), \
             mock.patch.object(se, "_require_snapshot_access", return_value=snap), \
             mock.patch.object(se, "allowed_fields", return_value={"Customer Class", "Billed Amount", "Bill Date"}), \
             mock.patch.object(se, "snapshot_backend", return_value=("oracle", "oracle_dbt", "ORIGINBA_REPORTING")), \
             mock.patch.object(se, "execute_query", side_effect=run) as ex, \
             mock.patch("api.access_audit.record_access_event") as audit:
            out = se.snapshot_query("rpt_billed_charge", body, ctx=Ctx())
        return out, ex.call_count, audit.call_count

    def test_the_same_report_is_run_once(self):
        run = lambda *a, **k: (["Customer Class", "m0"], [["Residential", 10.0]])  # noqa: E731
        self._query(run)
        out, runs, audits = self._query(run)
        self.assertEqual(runs, 0)
        self.assertEqual(audits, 1, "every run is still audited")
        self.assertEqual(out["rows"], [{"Customer Class": "Residential", "m0": 10.0}])

    def test_a_different_window_runs_again(self):
        run = lambda *a, **k: (["Customer Class", "m0"], [])  # noqa: E731
        self._query(run)
        self.assertEqual(self._query(run, start="2026-01-01")[1], 1)
