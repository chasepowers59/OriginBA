"""KPI threshold alerts: tests written before the code.

Contract under test (api/kpi_alerts.py + api/kpi_alert_routes.py):
  - An alert watches ONE executive KPI with a condition (value above/below a
    threshold, or percent-change above/below) over a trailing window; creation
    validates the KPI exists, the condition is sane, and recipients are real.
  - evaluate_condition() is pure: value/pct_change in, breached out; a KPI with
    no data never breaches.
  - run_kpi_alerts() notifies ONLY on the transition into breach (no daily spam
    while a KPI stays red), records recovery silently, and one failing alert
    never blocks the rest.
  - Routes are org-scoped.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.pop("PORTAL_STATE_DATABASE_URL", None)
os.environ.pop("PORTAL_AUTH_DATABASE_URL", None)

from api import kpi_alerts as ka  # noqa: E402

UTC = timezone.utc


def _payload(**over):
    base = {
        "kpi_id": "field_activities",
        "condition": "below",
        "threshold": 100,
        "window_days": 7,
        "recipients": ["ops@utility.gov"],
    }
    base.update(over)
    return base


class AlertStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._path = mock.patch.object(
            ka, "ALERTS_PATH", Path(self._tmp.name) / "kpi_alerts.json")
        self._path.start()

    def tearDown(self):
        self._path.stop()
        self._tmp.cleanup()

    def test_create_and_list_org_scoped(self):
        entry = ka.create_alert(_payload(), organization_id="dev", created_by="a@b.gov")
        self.assertTrue(entry["id"])
        self.assertEqual(entry["kpi_label"], "Field activities")
        self.assertEqual([a["id"] for a in ka.list_alerts("dev")], [entry["id"]])
        self.assertEqual(ka.list_alerts("ellensburg"), [])
        self.assertFalse(ka.delete_alert(entry["id"], "ellensburg"))
        self.assertTrue(ka.delete_alert(entry["id"], "dev"))

    def test_create_rejects_bad_input(self):
        with self.assertRaises(ka.AlertError):
            ka.create_alert(_payload(kpi_id="not-a-kpi"),
                            organization_id="dev", created_by="a@b.gov")
        with self.assertRaises(ka.AlertError):
            ka.create_alert(_payload(condition="sideways"),
                            organization_id="dev", created_by="a@b.gov")
        with self.assertRaises(ka.AlertError):
            ka.create_alert(_payload(recipients=["nope"]),
                            organization_id="dev", created_by="a@b.gov")
        with self.assertRaises(ka.AlertError):
            ka.create_alert(_payload(threshold="high"),
                            organization_id="dev", created_by="a@b.gov")


class ConditionTests(unittest.TestCase):
    def test_value_above_and_below(self):
        self.assertTrue(ka.evaluate_condition("above", 150, value=200, pct_change=None))
        self.assertFalse(ka.evaluate_condition("above", 150, value=150, pct_change=None))
        self.assertTrue(ka.evaluate_condition("below", 100, value=42, pct_change=None))
        self.assertFalse(ka.evaluate_condition("below", 100, value=100, pct_change=None))

    def test_pct_change(self):
        # fell more than 20% period over period
        self.assertTrue(ka.evaluate_condition("pct_change_below", -20, value=1, pct_change=-35.0))
        self.assertFalse(ka.evaluate_condition("pct_change_below", -20, value=1, pct_change=-5.0))
        self.assertTrue(ka.evaluate_condition("pct_change_above", 50, value=1, pct_change=80.0))

    def test_no_data_never_breaches(self):
        self.assertFalse(ka.evaluate_condition("below", 100, value=None, pct_change=None))
        self.assertFalse(ka.evaluate_condition("pct_change_below", -20, value=10, pct_change=None))


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._path = mock.patch.object(
            ka, "ALERTS_PATH", Path(self._tmp.name) / "kpi_alerts.json")
        self._path.start()
        self.alert = ka.create_alert(_payload(), organization_id="dev", created_by="a@b.gov")

    def tearDown(self):
        self._path.stop()
        self._tmp.cleanup()

    def _run(self, value, pct=None, sent=None):
        fake = {"value": value, "pct_change": pct, "label": "Field activities"}
        with mock.patch.object(ka, "_kpi_result", return_value=fake):
            return ka.run_kpi_alerts(
                now=datetime(2026, 9, 1, 13, 0, tzinfo=UTC),
                send=(lambda m: sent.append(m)) if sent is not None else (lambda m: None))

    def test_notifies_on_transition_into_breach_only(self):
        sent: list = []
        results = self._run(value=42, sent=sent)          # below 100 -> breach
        self.assertEqual(results[0]["status"], "breached-notified")
        self.assertEqual(len(sent), 1)
        self.assertIn("Field activities", sent[0]["Subject"])
        self.assertIn("ops@utility.gov", sent[0]["To"])

        results = self._run(value=40, sent=sent)          # still breached -> quiet
        self.assertEqual(results[0]["status"], "breached-quiet")
        self.assertEqual(len(sent), 1)

        results = self._run(value=500, sent=sent)         # recovered -> quiet
        self.assertEqual(results[0]["status"], "ok")
        self.assertEqual(len(sent), 1)

        results = self._run(value=10, sent=sent)          # breach again -> notify again
        self.assertEqual(results[0]["status"], "breached-notified")
        self.assertEqual(len(sent), 2)

    def test_kpi_failure_recorded_not_fatal(self):
        sent: list = []
        with mock.patch.object(ka, "_kpi_result", side_effect=RuntimeError("warehouse down")):
            results = ka.run_kpi_alerts(
                now=datetime(2026, 9, 1, 13, 0, tzinfo=UTC), send=lambda m: sent.append(m))
        self.assertTrue(results[0]["status"].startswith("error"))
        self.assertEqual(sent, [])


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.kpi_alert_routes import router

        cls._tmp = tempfile.TemporaryDirectory()
        cls._path = mock.patch.object(
            ka, "ALERTS_PATH", Path(cls._tmp.name) / "kpi_alerts.json")
        cls._path.start()
        cls._env = mock.patch.dict(os.environ, {
            "PORTAL_AUTH_DISABLED": "true", "PORTAL_DEV_ORGANIZATION": "dev",
            # dev needs a data source: require_org_for_data no longer accepts
            # the global credential fallback (audit H2).
            "WAREHOUSE_DATABASE_URL": "postgresql://test@localhost/test",
        })
        cls._env.start()
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()
        cls._path.stop()
        cls._tmp.cleanup()

    def test_crud_roundtrip_and_validation(self):
        r = self.client.post("/kpi-alerts", json=_payload())
        self.assertEqual(r.status_code, 200, r.text)
        aid = r.json()["id"]
        r = self.client.get("/kpi-alerts")
        self.assertIn(aid, [a["id"] for a in r.json()["alerts"]])
        # the route also lists which KPIs can be watched
        self.assertTrue(any(k["id"] == "field_activities" for k in r.json()["available_kpis"]))
        r = self.client.post("/kpi-alerts", json=_payload(kpi_id="nope"))
        self.assertEqual(r.status_code, 400)
        r = self.client.delete(f"/kpi-alerts/{aid}")
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
