"""A dropped Oracle connection reads as one plain sentence on every page, never a driver error.

Probed 2026-09-29 by simulating the VPN dropping mid-request (DPY-4011) on every Oracle-backed
route. The explorer answered 502 "Demo query failed: DPY-4011: ..." (driver text can name hosts),
data quality listed 22 rule errors, and the home page told a configured organization to "connect
it under Settings". Now: 503 "cannot be reached right now" wherever the database is configured
but unreachable; "not connected yet" only when nothing is configured.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from api import demo_db, freshness, summary_cache  # noqa: E402
from api.executive_dashboard import DATABASE_UNREACHABLE_NOTE  # noqa: E402

H = {"X-Organization-Id": "ellensburg"}


def _dropped(*_a, **_k):
    raise RuntimeError("DPY-4011: the database or network closed the connection (host=db.example.internal)")


class OracleOutageTests(unittest.TestCase):
    def setUp(self):
        summary_cache.clear()
        freshness.clear()
        patches = [mock.patch.dict(os.environ, {"PORTAL_AUTH_DISABLED": "true", "ENVIRONMENT": "test"}),
                   mock.patch.object(demo_db, "_oracle_pool", side_effect=_dropped),
                   mock.patch("api.org_db.demo_configured", return_value=True),
                   mock.patch("api.demo_db.demo_configured", return_value=True),
                   mock.patch("api.data_version.data_version", return_value=None)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        from api.app import app
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_no_route_shows_driver_text(self):
        for path in ("/snapshots/executive-summary?days=30", "/snapshots/workstream-summary/billing?days=30",
                     "/snapshots/rpt_bill/stats", "/snapshots/rpt_bill/sample-rows", "/dq/findings",
                     "/portal/letters?from=2026-05-01&to=2026-05-31"):
            with self.subTest(path=path):
                body = self.client.get(path, headers=H).text
                self.assertNotIn("DPY-", body)
                self.assertNotIn("example.internal", body)

    def test_the_explorer_says_the_database_cannot_be_reached(self):
        r = self.client.post("/snapshots/rpt_bill/query", headers=H, json={
            "dimensions": [], "measures": [{"field": "*", "agg": "count"}], "filters": [], "time_dimensions": [], "limit": 10})
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"], DATABASE_UNREACHABLE_NOTE)
        self.assertEqual(self.client.get("/snapshots/rpt_bill/stats", headers=H).status_code, 503)

    def test_pages_say_unreachable_not_unconfigured(self):
        home = self.client.get("/snapshots/executive-summary?days=30", headers=H).json()
        self.assertEqual(home["catalog_note"], DATABASE_UNREACHABLE_NOTE)
        ws = self.client.get("/snapshots/workstream-summary/billing?days=30", headers=H).json()
        self.assertEqual(ws["note"], DATABASE_UNREACHABLE_NOTE)

    def test_data_quality_says_so_once(self):
        dq = self.client.get("/dq/findings", headers=H).json()
        self.assertEqual(dq["rules"], [])
        self.assertEqual(dq["error"], DATABASE_UNREACHABLE_NOTE)


if __name__ == "__main__":
    unittest.main()
