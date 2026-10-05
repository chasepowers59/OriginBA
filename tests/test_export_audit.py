"""Exports are in the audit trail (production-readiness ledger item 7, 2026-10-05).

Nothing recorded that customer rows left the portal as a file. PDFs are built by the API and
are recorded there; CSV and Excel files are built in the browser, which reports each one to
POST /portal/export/record. Both land in portal_audit_log as action "export" under the
organization the person was viewing (an administrator switched to a client is recorded
against that client, not against no client at all).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import export_routes as er  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402


def _ctx(role="user", org="citycorp", active=None):
    return AuthContext(id="u1", email="ann@citycorp.test", display_name="Ann", role=role, client_id="dev",
                       organization_id=org, organization_name="CityCorp", permissions={"portal:read"},
                       workstreams=["*"], active_organization_id=active)


class ExportAudit(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.patch = mock.patch.object(er, "record_access_event", side_effect=lambda **kw: self.events.append(kw))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_a_pdf_export_is_recorded_with_its_rows_and_client(self):
        body = er.PdfExportRequest(title="Aged debt", columns=["A"], rows=[{"A": 1}, {"A": 2}])
        er.export_pdf(body, ctx=_ctx())
        (event,) = self.events
        self.assertEqual(event["action"], "export")
        self.assertEqual(event["organization_id"], "citycorp")
        self.assertIn("format=pdf", event["detail"])
        self.assertIn("rows=2", event["detail"])

    def test_a_browser_built_file_is_recorded(self):
        er.record_export(er.ExportRecord(format="xlsx", file="Aged debt.xlsx", rows=1234), ctx=_ctx())
        (event,) = self.events
        self.assertEqual((event["action"], event["organization_id"]), ("export", "citycorp"))
        self.assertIn("format=xlsx", event["detail"])
        self.assertIn("rows=1234", event["detail"])
        self.assertIn("Aged debt.xlsx", event["detail"])

    def test_an_admin_switched_to_a_client_is_recorded_against_it(self):
        er.record_export(er.ExportRecord(format="csv", file="x.csv", rows=1), ctx=_ctx(role="admin", org=None, active="ellensburg"))
        self.assertEqual(self.events[0]["organization_id"], "ellensburg")

    def test_only_csv_and_excel_are_reported_by_the_browser(self):
        with self.assertRaises(Exception):
            er.ExportRecord(format="exe", file="x", rows=1)


class TheBrowserReportsEveryDownload(unittest.TestCase):
    def test_both_download_helpers_report(self):
        web = ROOT / "apps" / "analytics-portal" / "src" / "lib"
        for name in ("format.ts", "exportXlsx.ts"):
            self.assertTrue("noteExport(" in (web / name).read_text(), f"{name} downloads without reporting it")


if __name__ == "__main__":
    unittest.main()
