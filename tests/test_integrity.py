"""Integrity evidence (api/integrity.py): the dbt repo's parity runs, served per canvas.
No database: the two QA result files are written to a temp directory and read through
ORIGINBA_QA_REPORTS. What is asserted is the reading, not the QA itself: which org maps to
which client, what "proven" means, that a source that moved on after the build is named
as such rather than as a defect, and that a deployment without the files says so."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ENVIRONMENT", "test")

from api import integrity  # noqa: E402

SOURCE = {
    "client": "ellensburg", "run_at": "2026-09-15T10:07:32", "elapsed_secs": 661.1,
    "summary": {"total": 5, "failed": 2, "tables": 3},
    "checks": [
        {"table": "rpt_financial_txn", "check": "count = CI_FT", "kind": "parity",
         "warehouse": 5394280.0, "source": 5394329.0, "status": "fail", "secs": 1},
        {"table": "rpt_financial_txn", "check": "sum Current Amount = CI_FT.cur_amt", "kind": "parity",
         "warehouse": 100.0, "source": 319.34, "status": "fail", "secs": 1},
        {"table": "rpt_financial_txn", "check": "row count > 0", "kind": "nonempty",
         "warehouse": 5394280.0, "source": None, "status": "pass", "secs": 0},
        {"table": "rpt_bill", "check": "count = CI_BILL", "kind": "parity",
         "warehouse": 10.0, "source": 10.0, "status": "pass", "secs": 0},
        {"table": "rpt_gl", "check": "count = CI_FT_GL", "kind": "parity",
         "warehouse": 90.0, "source": 100.0, "status": "fail", "secs": 0},
    ],
}
SNAPSHOT = {
    "client": "ellensburg", "run_at": "2026-09-15T10:40:00", "canvas_as_of": "2026-09-09T12:32:41",
    "checks": [
        {"check": "aged balance per SA = CMS_SA_SNAPSHOT", "snapshot": "CISADM.CMS_SA_SNAPSHOT",
         "canvas": "ORIGINBA_REPORTING.RPT_SA_AGED_BALANCE", "total": 138104, "newer": 9,
         "missing_stable": 0, "compared": 138086, "ok": True, "secs": 146.0,
         "values": {"current_balance": {"mismatch": 0, "soft": False, "abs_diff": 0.0},
                    "bucket_0_30": {"mismatch": 173, "soft": True, "abs_diff": 230710.59}},
         "samples": {}},
        {"check": "financial transactions per FT = FT_RPT_CURR", "snapshot": "CISADM.FT_RPT_CURR",
         "canvas": "ORIGINBA_REPORTING.RPT_FINANCIAL_TXN", "total": 2382650, "newer": 40,
         "missing_stable": 0, "compared": 2382600, "ok": True, "secs": 90.0,
         "values": {"current_amount": {"mismatch": 0, "soft": False, "abs_diff": 0.0}}, "samples": {}},
    ],
}


class WithReports(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = Path(self.dir.name)
        (d / "parity_ellensburg_latest.json").write_text(json.dumps(SOURCE))
        (d / "snapshot_parity_ellensburg_latest.json").write_text(json.dumps(SNAPSHOT))
        self.env = mock.patch.dict(os.environ, {"ORIGINBA_QA_REPORTS": self.dir.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.dir.cleanup()

    def test_an_org_resolves_to_its_dbt_client_through_the_registry_export(self):
        self.assertEqual(integrity.client_for_org("ellensburg"), "ellensburg")
        self.assertIsNone(integrity.client_for_org("no-such-org"))

    def test_a_canvas_that_ties_everywhere_is_proven(self):
        s = integrity.canvas_summary("ellensburg", "rpt_sa_aged_balance")
        self.assertEqual(s["verdict"], "proven")
        self.assertEqual(s["snapshot"]["against"], "CMS_SA_SNAPSHOT")
        self.assertEqual(s["snapshot"]["compared"], 138086)
        self.assertEqual([v["name"] for v in s["snapshot"]["soft_differences"]], ["bucket_0_30"])
        self.assertEqual(s["canvas_as_of"], "2026-09-09T12:32:41")

    def test_a_source_that_moved_on_after_the_build_is_named_not_blamed(self):
        s = integrity.canvas_summary("ellensburg", "rpt_financial_txn")
        self.assertEqual(s["verdict"], "differences")
        diffs = {d["check"]: d for d in s["source"]["differences"]}
        self.assertIn("source has changed since the canvas build", diffs["count = CI_FT"]["likely_cause"])
        # a 219% gap is not staleness, and must not be excused as such
        self.assertNotIn("likely_cause", diffs["sum Current Amount = CI_FT.cur_amt"])
        self.assertEqual(s["source"]["green"], 1)
        self.assertEqual(s["source"]["checks"], 3)

    def test_a_canvas_with_no_snapshot_twin_is_judged_on_source_alone(self):
        self.assertEqual(integrity.canvas_summary("ellensburg", "rpt_bill")["verdict"], "proven")
        self.assertIsNone(integrity.canvas_summary("ellensburg", "rpt_bill")["snapshot"])

    def test_an_unlisted_canvas_is_not_covered(self):
        self.assertEqual(integrity.canvas_summary("ellensburg", "rpt_todo")["verdict"], "not covered")

    def test_the_overview_lists_every_canvas_with_its_verdict(self):
        o = integrity.overview("ellensburg")
        self.assertTrue(o["available"])
        self.assertEqual(o["canvas_as_of"], "2026-09-09T12:32:41")
        self.assertEqual({c["canvas"]: c["verdict"] for c in o["canvases"]},
                         {"rpt_financial_txn": "differences", "rpt_bill": "proven", "rpt_gl": "differences",
                          "rpt_sa_aged_balance": "proven"})

    def test_a_query_names_the_canvases_it_read(self):
        sql = ('select b."Bill ID" from ORIGINBA_REPORTING.RPT_BILL b '
               'join reporting."rpt_gl" g on g."Bill ID" = b."Bill ID" where "x" > 1')
        self.assertEqual(integrity.canvases_read(sql), ["rpt_bill", "rpt_gl"])

    def test_the_compact_form_fits_a_query_card(self):
        c = integrity.for_query("ellensburg", "select 1 from ORIGINBA_REPORTING.RPT_SA_AGED_BALANCE")
        self.assertEqual(c[0]["canvas"], "rpt_sa_aged_balance")
        self.assertEqual(c[0]["verdict"], "proven")
        self.assertIn("CMS_SA_SNAPSHOT", c[0]["summary"])
        self.assertIn("138,086", c[0]["summary"])


class WithoutReports(unittest.TestCase):
    def test_no_files_means_unavailable_never_a_guess(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"ORIGINBA_QA_REPORTS": d}):
            self.assertFalse(integrity.overview("ellensburg")["available"])
            self.assertEqual(integrity.canvas_summary("ellensburg", "rpt_bill")["verdict"], "unavailable")
            self.assertEqual(integrity.for_query("ellensburg", "select 1 from rpt_bill"), [])

    def test_an_org_without_a_client_is_unavailable(self):
        self.assertFalse(integrity.overview("no-such-org")["available"])


class Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.auth import init_auth_database
        from api.integrity_routes import router
        cls._dir = tempfile.TemporaryDirectory()  # no QA files: the dev org must read as unavailable
        cls._env = mock.patch.dict(os.environ, {
            "PORTAL_AUTH_DISABLED": "true", "PORTAL_DEV_ORGANIZATION": "dev",
            "WAREHOUSE_DATABASE_URL": "postgresql://test@localhost/test",
            "ORIGINBA_QA_REPORTS": cls._dir.name})
        cls._env.start()
        init_auth_database()
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()
        cls._dir.cleanup()

    def test_the_overview_and_one_canvas_answer_for_this_org(self):
        with mock.patch("api.integrity_routes.overview", return_value={"available": False, "canvases": []}) as o:
            self.assertEqual(self.client.get("/portal/integrity").json()["available"], False)
        self.assertEqual(o.call_args.args[0], "dev")
        r = self.client.get("/portal/integrity/rpt_bill")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["verdict"], "unavailable")

    def test_a_canvas_id_is_validated(self):
        self.assertEqual(self.client.get("/portal/integrity/DROP%20TABLE").status_code, 422)


if __name__ == "__main__":
    unittest.main()
