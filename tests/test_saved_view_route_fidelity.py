"""What a saved view loses on the way through the HTTP route.

test_saved_views_multimeasure.py calls sv.create_saved_view() DIRECTLY, so it proves
the store keeps `measures` -- and it does. The request schema is where they were lost:
SavedViewCreate never declared `measures`, and Pydantic drops undeclared fields, so
model_dump() handed the store a payload without it. Measured against the running API
on 2026-09-02, POSTing two measures and one filter:

    POST /portal/saved-views  ->  measures: None
                                  filters:  absent from the response entirely

Consequences in the builder: a multi-measure view silently reopens with only its first
measure (the restore reads v.measures, gets null, falls back to measure_field), and a
view scoped with filters reopens showing EVERY row -- different numbers, no warning.

So these tests go through the route, not the store function. A store-level test cannot
see a field the schema already dropped.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import api.saved_views as sv  # noqa: E402


class SavedViewRouteFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.portal_routes import router

        # Pinned per class, not at import: the suite shares one interpreter and another
        # module had already set PORTAL_AUTH_DISABLED, so a setdefault here lost the
        # race and every request came back 401 — but only when run with the full suite.
        cls._env = mock.patch.dict(os.environ, {
            "PORTAL_AUTH_DISABLED": "true", "PORTAL_DEV_ORGANIZATION": "dev"})
        cls._env.start()
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._orig = sv.VIEWS_PATH
        sv.VIEWS_PATH = Path(self._tmp.name)
        Path(self._tmp.name).write_text('{"views": []}')

    def tearDown(self):
        sv.VIEWS_PATH = self._orig
        Path(self._tmp.name).unlink(missing_ok=True)

    BASE = {
        "snapshot_id": "rpt_bill_segment",
        "snapshot_label": "Bill Segment",
        "title": "Billed revenue by SA type",
        "kind": "custom",
        "dimensions": ["SA Type"],
        "measure_field": "Billed Amount",
        "measure_agg": "sum",
        "chart_type": "bar",
    }

    def _post(self, **extra) -> dict:
        response = self.client.post("/portal/saved-views", json={**self.BASE, **extra})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _reload(self, view_id: str) -> dict:
        response = self.client.get("/portal/saved-views")
        self.assertEqual(response.status_code, 200, response.text)
        match = [v for v in response.json()["views"] if v["id"] == view_id]
        self.assertTrue(match, "view vanished between POST and GET")
        return match[0]

    def test_measures_survive_the_route(self):
        measures = [
            {"field": "Billed Amount", "agg": "sum"},
            {"field": "Billed Usage", "agg": "sum"},
        ]
        created = self._post(measures=measures)
        self.assertEqual(created["measures"], measures)
        self.assertEqual(self._reload(created["id"])["measures"], measures)

    def test_filters_survive_the_route(self):
        """The scoping a user applied is the difference between the numbers they saved
        and every row in the canvas."""
        filters = [
            {"field": "SA Type", "op": "eq", "value": "E-RES"},
            {"field": "Bill Date", "op": "between", "value": ["2025-01-01", "2025-12-31"]},
        ]
        created = self._post(filters=filters)
        self.assertEqual(created["filters"], filters)
        self.assertEqual(self._reload(created["id"])["filters"], filters)

    def test_a_view_without_them_stays_null_rather_than_inventing_a_scope(self):
        created = self._post()
        self.assertIsNone(created["measures"])
        self.assertIsNone(created["filters"])

    def test_the_fields_that_already_worked_still_do(self):
        created = self._post()
        reloaded = self._reload(created["id"])
        self.assertEqual(reloaded["dimensions"], ["SA Type"])
        self.assertEqual(reloaded["measure_field"], "Billed Amount")
        self.assertEqual(reloaded["chart_type"], "bar")
        # Ids are stored as written; uppercasing them was a previous bug.
        self.assertEqual(reloaded["snapshot_id"], "rpt_bill_segment")

    def test_bulk_import_keeps_them_too(self):
        """Import shares SavedViewCreate, so it inherited the same gap."""
        measures = [{"field": "Billed Amount", "agg": "sum"}]
        filters = [{"field": "SA Type", "op": "eq", "value": "E-RES"}]
        response = self.client.post(
            "/portal/saved-views/import",
            json={"views": [{**self.BASE, "measures": measures, "filters": filters}]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        imported = response.json()["views"][0]
        self.assertEqual(imported["measures"], measures)
        self.assertEqual(imported["filters"], filters)


if __name__ == "__main__":
    unittest.main()
