"""Results are kept until the warehouse data behind them changes, not just five minutes.

The canvases change only when dbt rebuilds them (nightly, weekly full refresh), so a
five-minute cache made every visitor after the fifth minute wait again: 25 seconds for a
ready-to-run report over rpt_billed_charge at Ellensburg volume (2026-09-28). The
warehouse's build stamp (api/data_version.py) changes whenever a canvas is rebuilt or merged
into; a result keyed by it is kept up to twelve hours and dropped the moment the stamp
moves. Without a stamp (it could not be read) the old five-minute rule applies.

The stamp: Postgres, each reporting table's identity plus its insert/update/delete counters
(a dbt table rebuild is a new table; an incremental merge moves the counters). Oracle, the
reporting tables' last-analyzed and last-DDL times (every model build gathers statistics).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import data_version as dv  # noqa: E402
from api import summary_cache as sc  # noqa: E402


class StampTests(unittest.TestCase):
    def setUp(self):
        dv.clear()

    def test_postgres_reads_table_identity_and_write_counters(self):
        with mock.patch.object(dv, "org_backend", return_value=("postgres", "dbt")), \
             mock.patch("api.warehouse_db.execute_query", return_value=(["v"], [["abc"]])) as q:
            self.assertEqual(dv.data_version("demo25"), "abc")
        sql = q.call_args.args[0]
        for part in ("pg_class", "relfilenode", "n_tup_ins", "n_tup_upd", "n_tup_del"):
            self.assertIn(part, sql)

    def test_oracle_reads_analyzed_and_ddl_times(self):
        with mock.patch.object(dv, "org_backend", return_value=("oracle", "dbt")), \
             mock.patch("api.demo_db.execute_query", return_value=(["v"], [["20260929:40"]])) as q:
            self.assertEqual(dv.data_version("ellensburg"), "20260929:40")
        sql = q.call_args.args[0].upper()
        self.assertIn("LAST_ANALYZED", sql)
        self.assertIn("LAST_DDL_TIME", sql)
        self.assertIn("ORIGINBA_REPORTING", str(q.call_args))

    def test_the_stamp_is_read_at_most_once_a_minute(self):
        with mock.patch.object(dv, "org_backend", return_value=("postgres", "dbt")), \
             mock.patch("api.warehouse_db.execute_query", return_value=(["v"], [["abc"]])) as q:
            for _ in range(5):
                dv.data_version("demo25")
        self.assertEqual(q.call_count, 1)

    def test_an_unreadable_stamp_is_none_not_an_error(self):
        with mock.patch.object(dv, "org_backend", return_value=("postgres", "dbt")), \
             mock.patch("api.warehouse_db.execute_query", side_effect=RuntimeError("down")):
            self.assertIsNone(dv.data_version("demo25"))


class CacheLifetimeTests(unittest.TestCase):
    def setUp(self):
        sc.clear()
        self.now = [1000.0]
        self.clock = mock.patch.object(sc.time, "monotonic", side_effect=lambda: self.now[0])
        self.clock.start()
        self.calls = 0

    def tearDown(self):
        self.clock.stop()

    def _build(self):
        self.calls += 1
        return {"n": self.calls}

    def test_a_versioned_result_outlives_five_minutes(self):
        sc.cached(("k",), self._build, version="v1")
        self.now[0] += 2 * 3600
        self.assertEqual(sc.cached(("k",), self._build, version="v1"), {"n": 1})

    def test_a_new_version_is_rebuilt(self):
        sc.cached(("k",), self._build, version="v1")
        self.assertEqual(sc.cached(("k",), self._build, version="v2"), {"n": 2})

    def test_even_a_versioned_result_is_rebuilt_after_twelve_hours(self):
        sc.cached(("k",), self._build, version="v1")
        self.now[0] += 12 * 3600 + 1
        self.assertEqual(sc.cached(("k",), self._build, version="v1"), {"n": 2})

    def test_without_a_version_five_minutes_still_applies(self):
        sc.cached(("k",), self._build)
        self.now[0] += 301
        self.assertEqual(sc.cached(("k",), self._build), {"n": 2})


if __name__ == "__main__":
    unittest.main()
