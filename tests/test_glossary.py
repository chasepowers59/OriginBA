"""UI-4/UI-5 (Chase, 2026-09-29): what the API says to a reader speaks the portal's glossary --
"data set" and "organization", never canvas, snapshot, domain, tenant, UOM or a table name.
The frontend half is apps/analytics-portal/src/glossary.test.ts. Words the MODEL reads (Ori's
tool descriptions and errors) are not a reader's and are not checked here."""
from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ENVIRONMENT", "test")

from fastapi import HTTPException  # noqa: E402

from api.auth.dependencies import AuthContext  # noqa: E402
from api.auth.workstream_access import assert_snapshot_access  # noqa: E402
from api.executive_dashboard import WAREHOUSE_NOT_BUILT_NOTE, available_kpis  # noqa: E402
from api.report_schedules import window_sentence  # noqa: E402
from api.snapshot_catalog import CatalogError, get_snapshot  # noqa: E402
from api.workstream_dashboard import WORKSTREAM_ABOUT  # noqa: E402

BANNED = re.compile(r"\bcanvas(es)?\b|\breporting tables?\b|\bdomains?\b|\bsnapshots?\b|\btenants?\b|\buom\b|\brpt_\w+",
                    re.IGNORECASE)


class ReaderFacingText(unittest.TestCase):
    def assertPlain(self, text: str) -> None:
        self.assertIsNone(BANNED.search(text), text)

    def test_notes_a_dashboard_or_email_prints(self):
        self.assertPlain(WAREHOUSE_NOT_BUILT_NOTE)
        self.assertPlain(available_kpis([{"snapshot_id": "rpt_not_in_any_catalog"}], "dev")[1])
        self.assertPlain(window_sentence(None, 30, "2026-09-29"))

    def test_about_this_workstream(self):
        for about in WORKSTREAM_ABOUT.values():
            for text in [about["summary"], *about["not_included"], *(r["via"] for r in about["related"])]:
                self.assertPlain(text)

    def test_an_unknown_data_set(self):
        with self.assertRaises(CatalogError) as caught:
            get_snapshot("no_such_thing", "dev")
        self.assertIn("data set", str(caught.exception))
        self.assertNotRegex(str(caught.exception), r"(?i)snapshot")

    def test_a_data_set_outside_the_readers_grant(self):
        ctx = AuthContext(id="u", email="u@utility.gov", display_name="u", role="user", client_id="dev",
                          organization_id="dev", organization_name="Dev", permissions=set(), workstreams=["billing"])
        with self.assertRaises(HTTPException) as caught:
            assert_snapshot_access(ctx, "rpt_sa_aged_balance")
        self.assertPlain(caught.exception.detail)


if __name__ == "__main__":
    unittest.main()
