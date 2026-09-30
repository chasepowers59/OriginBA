"""A dashboard downloads as ONE server-built PDF, the same renderer as the explorer and
schedules: the dashboard's title on every page, then per tile its name, an optional note,
a bar chart when the tile is one label against one number, and its table.

POST /portal/export/dashboard-pdf takes the tiles the person is looking at (at most 12, 5,000
rows in all). Like /portal/export/pdf it renders only what the caller already holds, so it
reads no data; a signed-in reader is still required. It replaces the browser print dialog,
whose output depended on the browser, the window width and the print settings.
"""
from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api import report_schedules as rs  # noqa: E402

NOW = datetime(2026, 9, 29, tzinfo=timezone.utc)
BILLED = {"title": "Billed revenue", "note": "Frozen segments, last 90 days", "columns": ["Category", "Value"],
          "rows": [{"Category": "Residential", "Value": 1200.5}, {"Category": "Commercial", "Value": 300.0}]}
ACCOUNTS = {"title": "Billing accounts", "columns": ["Category", "Value"],
            "rows": [{"Category": "Active", "Value": 496}]}


def _plain(sections, title="Billing Dashboard"):
    """The PDF with page compression off, so its text can be read in the bytes."""
    with mock.patch("reportlab.rl_config.pageCompression", 0):
        return rs.sections_to_pdf(title, "Demo 25.4", sections, NOW)


class SectionsPdfTests(unittest.TestCase):
    def test_every_tile_is_in_one_pdf(self):
        data = _plain([BILLED, ACCOUNTS])
        self.assertTrue(data.startswith(b"%PDF-"))
        for text in (b"Billing Dashboard", b"Billed revenue", b"Frozen segments, last 90 days",
                     b"Residential", b"Billing accounts", b"496"):
            self.assertIn(text, data)

    def test_a_tile_with_no_rows_says_so(self):
        self.assertIn(b"No rows", _plain([{**ACCOUNTS, "rows": []}]))

    def test_a_failed_card_does_not_claim_there_were_no_rows(self):
        data = _plain([{**ACCOUNTS, "rows": [], "failed": True, "note": "This card could not load."}])
        self.assertIn(b"This card could not load.", data)
        self.assertNotIn(b"No rows", data)

    def test_a_chart_is_drawn_for_a_label_against_a_number(self):
        self.assertGreater(len(_plain([BILLED])), len(_plain([{**BILLED, "chart": False}])))

    def test_tile_names_are_text_not_markup(self):
        data = _plain([{**ACCOUNTS, "title": 'A&B <link href="https://evil.test">x</link>'}])
        self.assertNotIn(b"/URI", data)

    def test_one_tile_renders_like_the_single_report(self):
        with mock.patch("reportlab.rl_config.pageCompression", 0):
            single = rs.rows_to_pdf("Billed revenue", "n", ["Category", "Value"], {}, BILLED["rows"], NOW)
        self.assertIn(b"Residential", single)


class DashboardPdfRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = mock.patch.dict(os.environ, {"PORTAL_AUTH_DISABLED": "true", "PORTAL_DEV_ORGANIZATION": "dev"})
        cls.env.start()
        from api.export_routes import router
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()

    def test_the_tiles_on_screen_come_back_as_one_pdf(self):
        r = self.client.post("/portal/export/dashboard-pdf",
                             json={"title": "Billing Dashboard", "note": "Demo 25.4", "sections": [BILLED, ACCOUNTS]})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.headers["content-type"], "application/pdf")
        self.assertIn("Billing_Dashboard", r.headers["content-disposition"])
        self.assertTrue(r.content.startswith(b"%PDF-"))

    def test_limits_are_refused(self):
        too_many = [ACCOUNTS] * 13
        too_big = [{**ACCOUNTS, "rows": [{"Category": "x", "Value": 1}] * 2600}] * 2
        for sections in ([], too_many, too_big):
            r = self.client.post("/portal/export/dashboard-pdf", json={"title": "t", "sections": sections})
            self.assertEqual(r.status_code, 422, len(sections))


if __name__ == "__main__":
    unittest.main()


class ChartAxisTests(unittest.TestCase):
    """A count of 3 drew ticks at 0, 0.5, 1 ... printed as whole numbers: '0 0 1 2 2 2 3'."""

    def _chart(self, values, name="Category"):
        rows = [{name: f"Cycle {i}", "Value": v} for i, v in enumerate(values)]
        return rs._bar_chart([name, "Value"], {}, rows, 500).contents[0]

    def test_small_whole_counts_tick_by_one(self):
        self.assertEqual(self._chart([3, 1]).valueAxis.valueStep, 1)

    def test_small_fractions_keep_their_decimal(self):
        self.assertEqual(self._chart([2.5, 1.25]).valueAxis.labelTextFormat(2.5), "2.5")

    def test_large_values_stay_whole(self):
        self.assertEqual(self._chart([2042.83]).valueAxis.labelTextFormat(1500.0), "1,500")

    def test_a_long_label_is_shortened_visibly(self):
        rows = [{"Category": "Waste Water Residential (monthly)", "Value": 1}]
        names = rs._bar_chart(["Category", "Value"], {}, rows, 500).contents[0].categoryAxis.categoryNames
        self.assertEqual(names, ["Waste Water Residential (mo…"])
