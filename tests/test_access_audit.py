"""Query/report access audit: tests written before the code.

Contract under test (api/access_audit.py + wiring):
  - record_access_event() writes a portal_audit_log row (actor, action, target,
    detail) and NEVER raises — an audit failure must not fail the query it logs.
  - POST /snapshots/{id}/query records a `report_run` event naming the snapshot.
  - POST /database/sql/execute records `sql_execute` on success and `sql_refused`
    when the fence blocks the statement — refusals are the security-valuable part.
  - GET /auth/audit-log accepts an `action` filter so report traffic doesn't
    drown the admin events.
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

_AUTH_DB = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
_AUTH_DB.close()
os.environ["PORTAL_AUTH_DATABASE_URL"] = f"sqlite:///{_AUTH_DB.name}"
os.environ.pop("PORTAL_STATE_DATABASE_URL", None)
os.environ["PORTAL_AUTH_DISABLED"] = "true"
os.environ["PORTAL_DEV_ORGANIZATION"] = "dev"

from api import access_audit  # noqa: E402
from api.auth.bootstrap import init_auth_database  # noqa: E402
from api.auth.database import get_session_factory  # noqa: E402
from api.auth.models import AuditLog  # noqa: E402


def _events(action: str | None = None) -> list[AuditLog]:
    with get_session_factory()() as session:
        q = session.query(AuditLog)
        if action:
            q = q.filter(AuditLog.action == action)
        return [  # detach plain values before the session closes
            AuditLog(actor_email=e.actor_email, action=e.action,
                     target_type=e.target_type, target_id=e.target_id, detail=e.detail)
            for e in q.order_by(AuditLog.created_at.desc()).all()]


class RecordEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_auth_database()

    def test_writes_a_row(self):
        access_audit.record_access_event(
            actor_email="analyst@utility.gov", action="report_run",
            target_type="snapshot", target_id="rpt_bill_segment",
            detail="dims=division; rows=42")
        rows = _events("report_run")
        self.assertTrue(rows)
        self.assertEqual(rows[0].actor_email, "analyst@utility.gov")
        self.assertEqual(rows[0].target_id, "rpt_bill_segment")
        self.assertIn("rows=42", rows[0].detail)

    def test_never_raises_when_db_is_down(self):
        with mock.patch.object(access_audit, "get_session_factory",
                               side_effect=RuntimeError("db down")):
            access_audit.record_access_event(
                actor_email="x@y.gov", action="report_run",
                target_type="snapshot", target_id="s", detail="")
        # reaching here without an exception IS the assertion


class RouteWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.snapshot_explorer import router as snapshot_router
        from api.database_routes import router as database_router

        # another module may flip auth on at import time; pin it per-class
        # The SQL routes now refuse an org with no warehouse (audit C2), so the
        # dev org needs one configured before the audit wiring can be exercised.
        cls._env = mock.patch.dict(os.environ, {
            "PORTAL_AUTH_DISABLED": "true", "PORTAL_DEV_ORGANIZATION": "dev",
            "WAREHOUSE_DATABASE_URL": "postgresql://test@localhost/test"})
        cls._env.start()
        init_auth_database()
        app = FastAPI()
        app.include_router(snapshot_router)
        app.include_router(database_router)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()

    def test_snapshot_query_records_report_run(self):
        with mock.patch("api.warehouse_db.execute_query",
                        return_value=(["Bill Cycle"], [["CYCLE1"]])), \
             mock.patch("api.warehouse_db.warehouse_configured", return_value=True):
            r = self.client.post(
                "/snapshots/rpt_bill_segment/query",
                json={"dimensions": ["Bill Cycle"],
                      "measures": [{"field": "*", "agg": "count"}]})
        self.assertEqual(r.status_code, 200, r.text)
        rows = _events("report_run")
        self.assertTrue(rows)
        self.assertEqual(rows[0].target_id, "rpt_bill_segment")
        self.assertEqual(rows[0].actor_email, "dev@origin.local")

    def test_sql_refused_is_recorded(self):
        r = self.client.post(
            "/database/sql/execute",
            json={"sql": "SELECT micr_id FROM cisadm.ci_pay_tndr", "offset": 0,
                  "page_size": 50})
        self.assertEqual(r.status_code, 400)
        rows = _events("sql_refused")
        self.assertTrue(rows)
        self.assertIn("micr_id", rows[0].detail.lower())

    def test_sql_execute_is_recorded(self):
        with mock.patch("api.database_routes._run",
                        return_value=(["n"], [[1]])):
            r = self.client.post(
                "/database/sql/execute",
                json={"sql": "SELECT 1 AS n FROM reporting.rpt_bill_segment",
                      "offset": 0, "page_size": 50})
        self.assertEqual(r.status_code, 200, r.text)
        rows = _events("sql_execute")
        self.assertTrue(rows)
        self.assertIn("rpt_bill_segment", rows[0].detail)


class AuditListFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.auth.routes import router as auth_router

        cls._env = mock.patch.dict(os.environ, {
            "PORTAL_AUTH_DISABLED": "true", "PORTAL_DEV_ORGANIZATION": "dev"})
        cls._env.start()
        init_auth_database()
        access_audit.record_access_event(
            actor_email="a@b.gov", action="report_run",
            target_type="snapshot", target_id="rpt_x", detail="")
        access_audit.record_access_event(
            actor_email="a@b.gov", action="sql_execute",
            target_type="sql", target_id="", detail="SELECT 1")
        app = FastAPI()
        app.include_router(auth_router)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()

    def test_action_filter(self):
        r = self.client.get("/auth/audit-log?action=sql_execute")
        self.assertEqual(r.status_code, 200, r.text)
        actions = {e["action"] for e in r.json()}
        self.assertEqual(actions, {"sql_execute"})


if __name__ == "__main__":
    unittest.main()
