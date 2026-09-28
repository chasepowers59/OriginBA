"""A canvas page's record count never scans the canvas on Oracle, and is not re-counted per visit.

The explorer header showed "Records in domain" from COUNT(*) over the whole canvas on every
page view: ~10 s for Ellensburg's rpt_gl (6.08M rows) and rpt_financial_txn (5.39M), and the
crawl measured those pages at 41-45 s end to end (2026-09-28). A canvas changes only when the
warehouse is rebuilt, and the build gathers statistics after every table, so on Oracle the
count is ALL_TABLES.NUM_ROWS; COUNT(*) is the fallback when statistics are missing.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import snapshot_explorer as se  # noqa: E402


class Ctx:
    def require_permission(self, _):
        return None


class StatsTests(unittest.TestCase):
    def setUp(self):
        se._STATS_CACHE.clear()
        self.patches = [
            mock.patch.object(se, "require_org_for_data", return_value="ellensburg"),
            mock.patch.object(se, "_require_snapshot_access", return_value={"table_name": "rpt_gl"}),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        se._STATS_CACHE.clear()

    def _stats(self, engine, answers):
        sqls = []

        def run(snapshot, sql, binds=None, **_):
            sqls.append(sql)
            return ["ROW_COUNT"], [[answers.pop(0)]]

        with mock.patch.object(se, "snapshot_backend", return_value=(engine, engine, "ORIGINBA_REPORTING")), \
             mock.patch.object(se, "_run", side_effect=run):
            out = se.snapshot_stats("rpt_gl", ctx=Ctx())
        return out, sqls

    def test_oracle_reads_the_gathered_statistics_not_a_count(self):
        out, sqls = self._stats("oracle", [6077613])
        self.assertEqual(out["row_count"], 6077613)
        self.assertIn("ALL_TABLES", sqls[0].upper())
        self.assertNotIn("COUNT(*)", " ".join(sqls).upper())

    def test_oracle_counts_when_statistics_are_missing(self):
        out, sqls = self._stats("oracle", [None, 42])
        self.assertEqual(out["row_count"], 42)
        self.assertIn("COUNT(*)", sqls[-1].upper())

    def test_a_second_visit_is_served_from_the_cache(self):
        self._stats("postgres", [7])
        out, sqls = self._stats("postgres", [])
        self.assertEqual(out["row_count"], 7)
        self.assertEqual(sqls, [])


if __name__ == "__main__":
    unittest.main()
