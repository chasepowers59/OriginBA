"""An org whose warehouse is not built yet gets ONE sentence, not nine error cards.

Since 2026-09-02 every org reads the dbt catalog, so `available_kpis` -- which checks
the CATALOG -- resolves every KPI everywhere. On an Oracle org whose in-database
warehouse has not been built yet (five of them at the time of writing), every KPI then
runs against a schema that does not exist, and the home page renders a grid of nine
cards each saying "Query failed: ORA-00942: table or view does not exist".

That is worse than empty. The guard that shows a single explanation exists for exactly
this situation; it just keyed off the wrong thing. When EVERY KPI fails with a
missing-relation error -- ORA-00942 on Oracle, `relation ... does not exist` (42P01)
on Postgres -- the summary now collapses to one `catalog_note` and no cards, the same
shape the front-end already renders for a catalog that lacks the canvases.

A partial failure is left alone: one KPI erroring while eight succeed is a real
per-KPI problem the reader should see per KPI.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _errored(kpi, **_):
    return {"id": kpi["id"], "label": kpi["label"], "snapshot_id": kpi["snapshot_id"],
            "value": None, "prior_value": None, "change_pct": None, "trend": [],
            "error": "Query failed: ORA-00942: table or view does not exist"}


def _ok(kpi, **_):
    return {"id": kpi["id"], "label": kpi["label"], "snapshot_id": kpi["snapshot_id"],
            "value": 1.0, "prior_value": None, "change_pct": None, "trend": [], "error": None}


class UnbuiltWarehouseTests(unittest.TestCase):
    def setUp(self):
        self._env = mock.patch.dict(os.environ, {"PORTAL_AUTH_DISABLED": "true",
                                                 "PORTAL_DEV_ORGANIZATION": "dev"})
        self._env.start()

    def tearDown(self):
        self._env.stop()

    def _summary(self, runner):
        from api.executive_dashboard import build_executive_summary
        with mock.patch("api.executive_dashboard.execute_kpi_definition", side_effect=runner), \
             mock.patch("api.executive_dashboard.warehouse_configured", return_value=True), \
             mock.patch("api.executive_dashboard.demo_configured", return_value=False), \
             mock.patch("api.executive_dashboard._refresh_insight", return_value=None):
            return build_executive_summary(30, organization_id="newark")

    def test_every_kpi_missing_its_table_collapses_to_one_note(self):
        out = self._summary(_errored)
        self.assertEqual(out["kpis"], [], "nine error cards is worse than empty")
        self.assertIsNotNone(out.get("catalog_note"))
        self.assertIn("not been built", out["catalog_note"].lower())

    def test_the_note_never_shows_the_driver_error(self):
        out = self._summary(_errored)
        self.assertNotIn("ORA-", out["catalog_note"])

    def test_postgres_missing_relation_is_the_same_case(self):
        def pg(kpi, **_):
            d = _errored(kpi); d["error"] = 'Query failed: relation "reporting.rpt_bill" does not exist'
            return d
        out = self._summary(pg)
        self.assertEqual(out["kpis"], [])
        self.assertIn("not been built", out["catalog_note"].lower())

    def test_a_partial_failure_stays_per_kpi(self):
        calls = {"n": 0}
        def mixed(kpi, **_):
            calls["n"] += 1
            return _errored(kpi) if calls["n"] == 1 else _ok(kpi)
        out = self._summary(mixed)
        self.assertGreater(len(out["kpis"]), 1)
        self.assertIsNone(out.get("catalog_note"))
        self.assertTrue(any(k["error"] for k in out["kpis"]))

    def test_a_different_error_on_every_kpi_is_not_mistaken_for_unbuilt(self):
        def timeout(kpi, **_):
            d = _errored(kpi); d["error"] = "Query failed: ORA-01013: user requested cancel"
            return d
        out = self._summary(timeout)
        self.assertGreater(len(out["kpis"]), 1, "a timeout is not a missing warehouse")
        self.assertIsNone(out.get("catalog_note"))


class WorkstreamSummaryTests(unittest.TestCase):
    """The workstream page had the same nine-cards shape and no note to collapse into."""

    def setUp(self):
        self._env = mock.patch.dict(os.environ, {"PORTAL_AUTH_DISABLED": "true",
                                                 "PORTAL_DEV_ORGANIZATION": "dev"})
        self._env.start()

    def tearDown(self):
        self._env.stop()

    def _summary(self, runner):
        from api.workstream_dashboard import build_workstream_summary
        with mock.patch("api.workstream_dashboard.execute_kpi_definition", side_effect=runner), \
             mock.patch("api.workstream_dashboard.warehouse_configured", return_value=True), \
             mock.patch("api.workstream_dashboard.demo_configured", return_value=False):
            return build_workstream_summary("finance", 30, organization_id="newark")

    def test_an_unbuilt_warehouse_collapses_to_one_note(self):
        out = self._summary(_errored)
        self.assertEqual(out["kpis"], [])
        self.assertIn("not been built", (out.get("note") or "").lower())

    def test_a_working_warehouse_has_no_note(self):
        out = self._summary(_ok)
        self.assertGreater(len(out["kpis"]), 0)
        self.assertIsNone(out.get("note"))

    def test_kpis_run_concurrently_not_one_after_another(self):
        """At client volume over the VPN a sequential fan-out is ~20s; the executive
        dashboard already runs its KPIs in a pool, and this page had not caught up."""
        import threading, time
        seen = set()
        def slow(kpi, **_):
            seen.add(threading.get_ident()); time.sleep(0.05); return _ok(kpi)
        t = time.time(); out = self._summary(slow); elapsed = time.time() - t
        self.assertGreater(len(out["kpis"]), 1)
        self.assertGreater(len(seen), 1, "every KPI ran on the same thread")
        self.assertLess(elapsed, 0.05 * len(out["kpis"]) * 0.8)


class QueryRouteTests(unittest.TestCase):
    """The same class on the builder/explorer path: a human sentence, not the driver."""

    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.auth.bootstrap import init_auth_database
        from api.snapshot_explorer import router
        cls._env = mock.patch.dict(os.environ, {
            "PORTAL_AUTH_DISABLED": "true", "PORTAL_DEV_ORGANIZATION": "dev",
            "WAREHOUSE_DATABASE_URL": "postgresql://test@localhost/test"})
        cls._env.start()
        init_auth_database()
        app = FastAPI(); app.include_router(router); cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()

    def _post(self, exc):
        with mock.patch("api.warehouse_db.execute_query", side_effect=exc), \
             mock.patch("api.warehouse_db.warehouse_configured", return_value=True):
            return self.client.post("/snapshots/rpt_bill_segment/query",
                                    json={"dimensions": ["Bill Cycle"],
                                          "measures": [{"field": "*", "agg": "count"}]})

    def test_a_missing_table_reads_as_not_built_yet(self):
        r = self._post(RuntimeError('relation "reporting.rpt_bill_segment" does not exist'))
        self.assertEqual(r.status_code, 502)
        self.assertIn("not been built", r.json()["detail"].lower())
        self.assertNotIn("relation", r.json()["detail"])

    def test_the_canvas_overview_routes_say_the_same(self):
        """Stats, sample rows and the value picker all run on the canvas; on an unbuilt
        org each of them failed with the driver's text too."""
        exc = RuntimeError('relation "reporting.rpt_bill_segment" does not exist')
        for path in ("/snapshots/rpt_bill_segment/stats",
                     "/snapshots/rpt_bill_segment/sample-rows?limit=3",
                     "/snapshots/rpt_bill_segment/scope-options/Bill%20Cycle"):
            with self.subTest(path=path), \
                 mock.patch("api.warehouse_db.execute_query", side_effect=exc), \
                 mock.patch("api.warehouse_db.warehouse_configured", return_value=True):
                r = self.client.get(path)
            self.assertEqual(r.status_code, 502, path)
            self.assertIn("not been built", r.json()["detail"].lower(), path)
            self.assertNotIn("relation", r.json()["detail"], path)

    def test_any_other_failure_still_says_what_happened(self):
        r = self._post(RuntimeError("connection refused"))
        self.assertEqual(r.status_code, 502)
        self.assertIn("connection refused", r.json()["detail"])


if __name__ == "__main__":
    unittest.main()
