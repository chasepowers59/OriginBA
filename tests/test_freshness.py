"""When were this organization's reporting tables last built, and is that too long ago?

Ellensburg 2026-09-29: the tables dated 2026-09-10 because a stranded swap table blocked every
scheduled build, and no page said so; the home page's "data refreshed" line reads the Postgres
landing watermarks and is silent for Oracle organizations. Builds run every six hours with a
daily full refresh, so more than 36 hours since the last one means at least a day of missed
refreshes, and every page says so.
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import freshness as fr  # noqa: E402

NOW = datetime(2026, 9, 29, 17, 0, tzinfo=timezone.utc)   # 11:00 MDT


class BuiltAtTests(unittest.TestCase):
    def test_the_oracle_stamp_gives_the_build_time_in_the_servers_clock(self):
        self.assertEqual(fr.built_at("20260929163000:20260929123907:39:-0400", "oracle"), "2026-09-29T12:39:07-04:00")
        self.assertEqual(fr.built_at("20260928180601:20260910084138:39", "oracle"), "2026-09-10T08:41:38")
        self.assertIsNone(fr.built_at("none", "oracle"))
        self.assertIsNone(fr.built_at("garbage", "oracle"))

    def test_the_postgres_watermark_is_the_build_time(self):
        self.assertEqual(fr.built_at("2026-09-28 06:31:02", "postgres"), "2026-09-28T06:31:02")


class FreshnessTests(unittest.TestCase):
    def _fresh(self, stamp, engine="oracle"):
        fr.clear()
        with mock.patch.object(fr, "org_backend", return_value=(engine, "dbt")), \
             mock.patch.object(fr, "data_version", return_value=stamp):
            return fr.freshness("ellensburg", now=NOW)

    def test_a_build_this_morning_is_fresh(self):
        out = self._fresh("20260929163000:20260929123907:39:-0400")
        self.assertEqual(out, {"built_at": "2026-09-29T12:39:07-04:00", "age_hours": 0.3, "stale": False, "scheduled": True})

    def test_nineteen_days_is_stale(self):
        out = self._fresh("20260928180601:20260910084138:39:-0400")
        self.assertTrue(out["stale"])
        self.assertEqual(round(out["age_hours"] / 24), 19)

    def test_the_line_is_a_day_and_a_half(self):
        self.assertFalse(self._fresh("x:20260928060000:39:+0000")["stale"])   # 35 hours
        self.assertTrue(self._fresh("x:20260928040000:39:+0000")["stale"])    # 37 hours

    def test_unknown_is_not_stale(self):
        self.assertEqual(self._fresh(None), {"built_at": None, "age_hours": None, "stale": False, "scheduled": True})

    def test_postgres_reads_the_built_reporting_table_not_the_staging_view(self):
        # review 2026-09-29: staging is a VIEW over landing, so CDC kept it current through a
        # failed dbt build and no page said stale
        cur = mock.MagicMock()
        cur.fetchone.return_value = ["2026-09-28 06:31:02"]
        conn = mock.MagicMock()
        conn.cursor.return_value = cur
        pool = mock.MagicMock()
        pool.__enter__.return_value = conn
        with mock.patch.object(fr, "warehouse_connection", return_value=pool):
            self.assertEqual(fr.refresh_marker("demo25", "postgres"), "2026-09-28 06:31:02")
        sql = cur.execute.call_args.args[0]
        self.assertIn('reporting.rpt_financial_txn', sql)
        self.assertIn('"Load Date/Time"', sql)

    def test_the_answer_is_kept_for_a_minute(self):
        fr.clear()
        with mock.patch.object(fr, "org_backend", return_value=("oracle", "dbt")), \
             mock.patch.object(fr, "data_version", return_value="x:20260929123907:39:-0400") as dv:
            fr.freshness("ellensburg")
            fr.freshness("ellensburg")
        self.assertEqual(dv.call_count, 1)

    def test_a_database_without_scheduled_builds_is_never_stale(self):
        # demo25 was loaded once (2026-09-01) and has no nightly: "the scheduled refresh has not
        # completed" would be false there
        fr.clear()
        with mock.patch.object(fr, "org_backend", return_value=("postgres", "dbt")), \
             mock.patch.object(fr, "refresh_marker", return_value="2026-09-01 10:11:22"), \
             mock.patch.object(fr, "get_organization", return_value={"id": "demo25", "scheduled_builds": False}):
            out = fr.freshness("demo25", now=NOW)
        self.assertEqual(out["built_at"], "2026-09-01T10:11:22")
        self.assertFalse(out["stale"])
        # System health said "Fresh" beside a 28-day-old load; it is "not scheduled", not fresh
        self.assertFalse(out["scheduled"])

    def test_the_route_answers_for_the_callers_organization(self):
        from api.auth.dependencies import AuthContext
        ctx = AuthContext(id="u", email="u@x.gov", display_name="u", role="viewer", client_id="ellensburg",
                          organization_id="ellensburg", organization_name="Ellensburg", permissions={"portal:read"},
                          workstreams=["*"], row_rules=())
        with mock.patch.object(fr, "require_org_for_data", return_value="ellensburg"), \
             mock.patch.object(fr, "freshness", return_value={"built_at": None, "age_hours": None, "stale": False, "scheduled": True}) as f:
            self.assertEqual(fr.freshness_route(ctx=ctx)["stale"], False)
        f.assert_called_once_with("ellensburg")


if __name__ == "__main__":
    unittest.main()
