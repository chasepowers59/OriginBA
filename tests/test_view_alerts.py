"""An alert can watch a saved view, not only a home KPI.

It watches the view's first measure as ONE total (no breakdown) over the view's saved
filters and a trailing window, through the same query a schedule of that view runs, with
its creator's current access. It fires when the total rises above or falls below the
threshold, once per breach, on the same hourly runner as the KPI alerts. Period-over-period
conditions stay KPI-only. Only someone who can see the view can alert on it.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import kpi_alerts as ka  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402

NOW = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)
VIEW = {"id": "v1", "title": "Past due by cycle", "snapshot_id": "rpt_sa_aged_balance", "visibility": "organization",
        "owner_id": "ana", "dimensions": ["Bill Cycle"], "measures": [{"field": "Past Due Amount", "agg": "sum"},
                                                                      {"field": "*", "agg": "count"}],
        "filters": [{"field": "SA Status", "op": "eq", "value": "Active"}]}


def _ctx(uid="ana"):
    return AuthContext(id=uid, email=f"{uid}@utility.gov", display_name=uid, role="editor", client_id="dev",
                       organization_id="dev", organization_name="Dev",
                       permissions={"portal:read", "saved_views:write"}, workstreams=["*"])


class ViewAlertTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [mock.patch.object(ka, "ALERTS_PATH", Path(self.tmp.name) / "a.json"),
                        mock.patch("api.report_schedules._find_view", return_value=VIEW)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _alert(self, **kw):
        return ka.create_alert({"saved_view_id": "v1", "condition": "above", "threshold": 1000,
                                "window_days": 30, "recipients": ["ana@utility.gov"], **kw},
                               organization_id="dev", created_by="ana@utility.gov")

    def test_an_alert_names_the_view_and_its_measure(self):
        a = self._alert()
        self.assertEqual(a["saved_view_id"], "v1")
        self.assertEqual(a["kpi_label"], "Past due by cycle: Total Past Due Amount")

    def test_period_over_period_stays_kpi_only(self):
        with self.assertRaises(ka.AlertError):
            self._alert(condition="pct_change_above")

    def test_it_watches_one_total_through_the_schedule_query(self):
        self._alert()
        seen = {}

        def render(schedule, view):
            seen["schedule"], seen["view"] = schedule, view
            return ["m0"], {"m0": "Total Past Due Amount"}, [{"m0": 1500.0}]
        sent = []
        with mock.patch("api.report_schedules.render_schedule", side_effect=render):
            out = ka.run_kpi_alerts(now=NOW, send=sent.append)
        self.assertEqual(out[0]["status"], "breached-notified")
        self.assertEqual(seen["view"]["dimensions"], [])
        self.assertEqual(seen["view"]["measures"], [{"field": "Past Due Amount", "agg": "sum"}])
        self.assertEqual(seen["view"]["filters"], VIEW["filters"])
        self.assertEqual((seen["schedule"]["created_by"], seen["schedule"]["window_days"]), ("ana@utility.gov", 30))
        self.assertIn("Past due by cycle", sent[0]["Subject"])
        self.assertIn("1500", sent[0].get_content())

    def test_a_database_decimal_is_stored_as_a_number(self):
        """The warehouse returns Decimal; the alert store is JSON. A real run failed where a float passed."""
        from decimal import Decimal
        self._alert()
        with mock.patch("api.report_schedules.render_schedule",
                        return_value=(["m0"], {}, [{"m0": Decimal("76992.39")}])):
            out = ka.run_kpi_alerts(now=NOW, send=lambda m: None)
        self.assertEqual(out[0]["status"], "breached-notified")
        self.assertEqual(ka.list_alerts("dev")[0]["last_value"], 76992.39)

    def test_a_deleted_view_is_an_error_not_an_all_clear(self):
        self._alert()
        with mock.patch("api.report_schedules._find_view", return_value=None):
            out = ka.run_kpi_alerts(now=NOW, send=lambda m: None)
        self.assertTrue(out[0]["status"].startswith("error"))

    def test_only_someone_who_can_see_the_view_alerts_on_it(self):
        from api import kpi_alert_routes as kr
        private = {**VIEW, "visibility": "private", "owner_id": "ana"}
        with mock.patch("api.report_schedules._find_view", return_value=private), \
             mock.patch.object(kr, "require_org_for_data", return_value="dev"):
            with self.assertRaises(HTTPException) as err:
                kr.create_alert(kr.AlertCreateRequest(saved_view_id="v1", condition="above", threshold=1,
                                                      recipients=["bob@utility.gov"]), ctx=_ctx("bob"))
            self.assertEqual(err.exception.status_code, 404)
            self.assertTrue(kr.create_alert(kr.AlertCreateRequest(saved_view_id="v1", condition="above", threshold=1,
                                                                  recipients=["ana@utility.gov"]), ctx=_ctx("ana")))


if __name__ == "__main__":
    unittest.main()
