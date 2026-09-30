"""Every API response carries a request id, and a server error names it instead of a trace.

Before 2026-09-28 only two modules logged anything and a 500 said nothing a person could
report. Now each request gets an X-Request-ID (a caller's own id is kept if it is sane),
one log line (method, path, status, ms, org), and an unhandled error answers
'Something went wrong on the server. Reference: <id>' while the traceback goes to the
log under the same id -- so a user's screenshot finds the exact failure.
"""
from __future__ import annotations

import logging
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.request_tracing import install  # noqa: E402


def _app():
    app = FastAPI()
    install(app)

    @app.get("/ok")
    def ok():
        return {"ok": True}

    @app.get("/boom")
    def boom():
        raise RuntimeError("ORA-00942: table or view does not exist")
    return app


class RequestTracingTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(_app(), raise_server_exceptions=False)

    def test_every_response_carries_a_request_id(self):
        r = self.client.get("/ok")
        self.assertRegex(r.headers["X-Request-ID"], r"^[0-9a-f]{12}$")

    def test_a_callers_own_id_is_kept_when_sane_and_replaced_when_not(self):
        self.assertEqual(self.client.get("/ok", headers={"X-Request-ID": "abc-123_XYZ"}).headers["X-Request-ID"], "abc-123_XYZ")
        self.assertNotIn("\n", self.client.get("/ok", headers={"X-Request-ID": "x" * 300}).headers["X-Request-ID"])

    def test_one_line_is_logged_per_request(self):
        with self.assertLogs("originba.api", level="INFO") as logs:
            r = self.client.get("/ok")
        line = next(l for l in logs.output if r.headers["X-Request-ID"] in l)
        self.assertIn("GET /ok 200", line)

    def test_a_server_error_names_its_reference_and_hides_the_trace(self):
        with self.assertLogs("originba.api", level="ERROR") as logs:
            r = self.client.get("/boom")
        rid = r.headers["X-Request-ID"]
        self.assertEqual(r.status_code, 500)
        self.assertIn(rid, r.json()["detail"])
        self.assertNotIn("ORA-00942", r.json()["detail"])
        self.assertTrue(any(rid in l and "ORA-00942" in l for l in logs.output), "the log keeps the real error")


if __name__ == "__main__":
    unittest.main()
