"""A result on screen downloads as the same formatted PDF a schedule sends.

POST /portal/export/pdf takes the rows the person is looking at (title, window, columns,
labels, rows) and returns the server-built PDF: the Origin mark, the table, page numbers,
and a bar chart when the result is one label against one number. It renders only what the
caller already has, so it reads no data; it still requires a signed-in reader.
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

ROWS = [{"cycle": f"Cycle {i}", "amt": 1000.0 * (10 - i)} for i in range(8)]
LABELS = {"cycle": "Bill Cycle", "amt": "Billed Amount"}
NOW = datetime(2026, 9, 28, tzinfo=timezone.utc)


class PdfChartTests(unittest.TestCase):
    def test_one_label_against_one_number_gets_a_chart(self):
        with_chart = rs.rows_to_pdf("t", "", ["cycle", "amt"], LABELS, ROWS, NOW, chart=True)
        without = rs.rows_to_pdf("t", "", ["cycle", "amt"], LABELS, ROWS, NOW)
        self.assertGreater(len(with_chart), len(without))

    def test_a_table_with_no_number_gets_no_chart(self):
        rows = [{"cycle": "C1", "name": "x"}]
        self.assertEqual(len(rs.rows_to_pdf("t", "", ["cycle", "name"], {}, rows, NOW, chart=True)),
                         len(rs.rows_to_pdf("t", "", ["cycle", "name"], {}, rows, NOW)))


class ExportRouteTests(unittest.TestCase):
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

    def test_the_rows_on_screen_come_back_as_a_pdf(self):
        r = self.client.post("/portal/export/pdf", json={"title": "Billed by cycle", "note": "Last 90 days",
                                                          "columns": ["cycle", "amt"], "labels": LABELS, "rows": ROWS})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["content-type"], "application/pdf")
        self.assertIn("Billed_by_cycle", r.headers["content-disposition"])
        self.assertTrue(r.content.startswith(b"%PDF-"))

    def test_an_oversized_export_is_refused(self):
        r = self.client.post("/portal/export/pdf", json={"title": "t", "columns": ["a"], "rows": [{"a": 1}] * 5001})
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()


class MarkupSafetyTests(unittest.TestCase):
    """reportlab reads Paragraph text as markup: an '&' or '<' in a customer name broke the
    PDF (a scheduled report would fail), and exported text could inject a link."""

    def test_ampersands_and_angle_brackets_render_as_text(self):
        rows = [{"name": "AT&T <Main St> & Sons", "amt": 1.5}]
        data = rs.rows_to_pdf("Owed by A&B <billing>", "note with <b>tags</b> & more", ["name", "amt"],
                              {"name": "Name & Title", "amt": "Amount"}, rows, NOW)
        self.assertTrue(data.startswith(b"%PDF-"))

    def test_injected_markup_does_not_become_a_link(self):
        rows = [{"name": '<link href="https://evil.test">click</link>', "amt": 1.0}]
        data = rs.rows_to_pdf("t", "", ["name", "amt"], {}, rows, NOW)
        self.assertNotIn(b"/URI", data)


class NumberColumnTests(unittest.TestCase):
    def test_a_column_with_any_decimals_shows_two_decimals_throughout(self):
        cells = rs._pdf_cells(["amt", "n"], [{"amt": 1234.5, "n": 3}, {"amt": 99.0, "n": 4}])
        self.assertEqual([r[0] for r in cells], ["1,234.50", "99.00"])
        self.assertEqual([r[1] for r in cells], ["3", "4"])
