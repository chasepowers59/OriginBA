"""An unfiltered canvas query windows on a real date, and says that it did.

`snapshot_explorer` decided its default window from `required_date_field` ALONE. That
one read produced two opposite bugs at once, both measured 2026-09-02:

    catalog_cisadm   19/19 canvases   silent BETWEEN today-90 AND today
    catalog_dbt       0/38 canvases   no window at all

Legacy orgs -- six of nine -- ask for all time and get a quarter, with nothing in the
response saying so. The response returns `sql`, so it is technically discoverable, but
no caller reads SQL to find out what question it asked. Canvas-backed orgs get the
mirror image: an unfiltered aggregate scans the whole table, and the row cap does NOT
save it, because FETCH FIRST applies AFTER GROUP BY.

WHAT THE WINDOW IS AND IS NOT WORTH, because the obvious claim is wrong. A default
window pays ONLY where it is selective, and that is a property of the client's data,
not of the query. Measured both ways:

    Ellensburg RPT_GL, 6.08M rows, years of history   4,062 ms -> 825 ms  (3 months)
    demo25 rpt_measurement, 3.57M rows                  198 ms -> 256 ms

demo25 is SLOWER windowed, and no smaller window rescues it: its dates are clumped so
tightly that even a 7-day window still holds 1,255,830 rows -- 35% of the table -- so
the filter costs evaluation and saves no scan. Do not quote this change as a general
speedup. It bounds the worst case on client data that spans years, it is neutral-to-
slightly-negative on a compressed demo set, and consistency between the two shapes is
the reason it applies everywhere rather than only where it happens to pay.

`required_date_field` alone is a CISADM-era read: no dbt canvas sets one. kpi_runner,
nlq_metrics and report_schedules ALL already fall back to `default_date_field` --
report_schedules' own docstring describes this exact bug, found and fixed there and
never carried across to the explorer. This is the fourth caller of one rule, so the
rule moved to api/reporting_dates.py rather than being written a fourth time.

DISCLOSURE IS WHAT MAKES THE DEFAULT SAFE. A window the server chose and did not
mention is the bug the legacy shape already had; widening it to 38 more canvases
without saying so would spread it rather than fix it. When the server adds the filter
itself the response carries `applied_window`, and a filter the CALLER sent is left
alone and never described as ours.
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.auth.bootstrap import init_auth_database  # noqa: E402


class WindowDateFieldTests(unittest.TestCase):
    """One rule, one home, one source: the measured default."""

    def test_a_canvas_windows_on_its_measured_default(self):
        from api.reporting_dates import window_date_field
        self.assertEqual(window_date_field({"default_date_field": "Bill Date"}), "Bill Date")

    def test_a_canvas_with_no_date_windows_on_nothing(self):
        from api.reporting_dates import window_date_field
        self.assertIsNone(window_date_field({}))

    def test_report_schedules_uses_the_shared_rule(self):
        """It had the only correct copy; it must not keep a private one."""
        from api.report_schedules import schedule_date_field
        from api.reporting_dates import window_date_field
        self.assertIs(schedule_date_field, window_date_field)


class WindowDateLabelTests(unittest.TestCase):
    """The note is user-facing copy, so it must never print a raw column name."""

    def test_a_declared_date_field_label_is_used(self):
        from api.reporting_dates import window_date_label
        self.assertEqual(
            window_date_label({"date_fields": [{"id": "Bill Date", "label": "Bill Date"}]},
                              "Bill Date"), "Bill Date")

    def test_an_unlabelled_field_falls_back_to_itself_rather_than_vanishing(self):
        from api.reporting_dates import window_date_label
        self.assertEqual(window_date_label({}, "SOME_DT"), "SOME_DT")


class DefaultFilterTests(unittest.TestCase):
    def test_a_dbt_canvas_now_gets_a_window(self):
        from api.snapshot_explorer import _default_date_filter
        f = _default_date_filter({"default_date_field": "Bill Date"})
        self.assertIsNotNone(f, "a canvas with a measured date must window by default")
        self.assertEqual(f.field, "Bill Date")
        self.assertEqual(f.op, "between")
        self.assertEqual(f.value[1], date.today().isoformat())
        self.assertEqual(f.value[0], (date.today() - timedelta(days=90)).isoformat())

    def test_a_canvas_with_no_date_column_is_left_alone(self):
        """rpt_account_person, rpt_asset_location and rpt_revenue_reconciliation carry
        no date. Inventing one would filter on a column that does not exist."""
        from api.snapshot_explorer import _default_date_filter
        self.assertIsNone(_default_date_filter({"default_date_field": None}))


class QueryRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.snapshot_explorer import router

        cls._env = mock.patch.dict(os.environ, {
            "PORTAL_AUTH_DISABLED": "true", "PORTAL_DEV_ORGANIZATION": "dev",
            "WAREHOUSE_DATABASE_URL": "postgresql://test@localhost/test"})
        cls._env.start()
        init_auth_database()
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()

    def _query(self, body):
        with mock.patch("api.warehouse_db.execute_query",
                        return_value=(["Bill Cycle"], [["CYCLE1"]])), \
             mock.patch("api.warehouse_db.warehouse_configured", return_value=True):
            r = self.client.post("/snapshots/rpt_bill_segment/query", json=body)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    BODY = {"dimensions": ["Bill Cycle"], "measures": [{"field": "*", "agg": "count"}]}

    def test_an_unfiltered_query_is_bounded(self):
        """Without this the aggregate scans the table; the row cap runs after GROUP BY."""
        out = self._query(dict(self.BODY))
        self.assertIn("Bill Date", out["sql"],
                      "an unfiltered canvas query must window on its default date")

    def test_the_window_the_server_chose_is_disclosed(self):
        out = self._query(dict(self.BODY))
        applied = out.get("applied_window")
        self.assertIsNotNone(applied, "a server-chosen window must not be silent")
        self.assertEqual(applied["field"], "Bill Date")
        self.assertEqual(applied["days"], 90)
        self.assertIn("Bill Date", applied["note"])

    def test_the_note_never_shows_a_raw_column_name(self):
        """The field stays machine-readable; only the sentence is humanised."""
        out = self._query(dict(self.BODY))
        applied = out["applied_window"]
        self.assertEqual(applied["label"], "Bill Date")
        self.assertNotRegex(applied["note"], r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b",
                            "a database column name reached user-facing copy")

    def test_a_caller_supplied_filter_is_never_relabelled_as_ours(self):
        """Filtering on a NON-date field: the server must neither claim a window nor
        quietly add its own date predicate on top of the caller's question. Dates ride
        as bind parameters, so the absence of the column name is the observable."""
        out = self._query({**self.BODY, "filters": [
            {"field": "Bill Cycle", "op": "eq", "value": "CYCLE1"}]})
        self.assertIsNone(out.get("applied_window"),
                          "the caller chose the filters; the server must not claim one")
        where = out["sql"].split("WHERE", 1)[1].split("GROUP BY", 1)[0]
        self.assertIn("Bill Cycle", where)
        self.assertNotIn("Bill Date", where,
                         "a caller who filtered deliberately must not get a hidden window")


if __name__ == "__main__":
    unittest.main()


class TheWindowIsForBigCanvases(unittest.TestCase):
    """"How many accounts, by customer class?" rendered ONE bar on demo25: the default
    90-day window on Account Setup Date kept 56 of 562 accounts, so a stock question was
    silently answered as a flow question (2026-09-04). The window exists to keep a
    multi-million-row aggregate interactive -- measured: Ellensburg RPT_GL 6.08M rows
    4,062ms -> 825ms -- and on 562 rows it buys nothing and changes the answer. So it is
    applied only when the engine's own row estimate says the canvas is big; an estimate
    that cannot be read fails TOWARD the window, never toward an unbounded scan.
    """

    def test_a_small_canvas_gets_no_default_window(self):
        from api import snapshot_explorer as se
        with mock.patch.object(se, "_row_estimate", return_value=562):
            self.assertIsNone(se._default_date_filter({"default_date_field": "Account Setup Date"}, "dev"))

    def test_a_big_canvas_still_gets_the_window(self):
        from api import snapshot_explorer as se
        with mock.patch.object(se, "_row_estimate", return_value=6_080_000):
            f = se._default_date_filter({"default_date_field": "Accounting Date"}, "dev")
        self.assertEqual(f.field, "Accounting Date")

    def test_an_unreadable_estimate_keeps_the_window(self):
        from api import snapshot_explorer as se
        with mock.patch.object(se, "_row_estimate", return_value=None):
            self.assertIsNotNone(se._default_date_filter({"default_date_field": "Bill Date"}, "dev"))

    def test_the_threshold_is_where_the_measurements_put_it(self):
        from api.reporting_dates import DEFAULT_WINDOW_MIN_ROWS
        self.assertEqual(DEFAULT_WINDOW_MIN_ROWS, 100_000)

    def test_the_estimate_reads_the_engine_statistics_not_a_count(self):
        from api import snapshot_explorer as se
        seen = {}
        def fake_run(snapshot, sql, organization_id=None, max_rows=None):
            seen["sql"] = sql
            return ["n"], [[562]]
        with mock.patch.object(se, "_run", side_effect=fake_run), \
             mock.patch.object(se, "snapshot_backend", return_value=("postgres", "postgres", "reporting")):
            se._ESTIMATES.clear()
            self.assertEqual(se._row_estimate({"table_name": "rpt_customer_account"}, "dev"), 562)
        self.assertIn("pg_class", seen["sql"])
        self.assertNotIn("count(*)", seen["sql"].lower())
