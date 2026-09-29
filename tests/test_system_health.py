"""An administrator can see what the API has been doing without server logs.

GET /portal/health (admins) reports, for this API process since it started: requests and
server errors per route (by route pattern), the slowest recent requests, the last server
errors with their reference (the id a user sees in 'Reference: ...'), the result cache's
hits and misses, and each organization's warehouse build stamp. Route patterns, never raw
paths: an embed link's token is a credential and must not be stored or logged.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api import request_tracing as rt  # noqa: E402
from api import summary_cache as sc  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402

TOKEN = "eyJhbGciOiJIUzI1NiJ9.secret-part.sig"


def _app():
    app = FastAPI()
    rt.install(app)

    @app.get("/embed/{token}/data")
    def embed(token: str):
        return {"ok": True}

    @app.get("/boom")
    def boom():
        raise RuntimeError("ORA-00942: table or view does not exist")

    @app.get("/slow")
    def slow():
        return {"ok": True}
    return app


def _ctx(role):
    return AuthContext(id="u", email="u@utility.gov", display_name="u", role=role, client_id="dev",
                       organization_id="dev", organization_name="Dev", permissions={"portal:read"}, workstreams=["*"])


class HealthTests(unittest.TestCase):
    def setUp(self):
        rt.reset()
        sc.clear()
        self.client = TestClient(_app(), raise_server_exceptions=False)

    def test_a_server_error_is_kept_with_its_reference(self):
        r = self.client.get("/boom")
        rid = r.headers["X-Request-ID"]
        errors = rt.snapshot()["errors"]
        self.assertEqual(errors[0]["reference"], rid)
        self.assertEqual(errors[0]["route"], "GET /boom")
        self.assertIn("ORA-00942", errors[0]["error"])

    def test_routes_are_counted_by_pattern_and_tokens_never_kept(self):
        with self.assertLogs("originba.api", level="INFO") as logs:
            self.client.get(f"/embed/{TOKEN}/data")
            self.client.get("/embed/another-token/data")
        routes = {r["route"]: r for r in rt.snapshot()["routes"]}
        self.assertEqual(routes["GET /embed/{token}/data"]["requests"], 2)
        self.assertNotIn("secret-part", repr(rt.snapshot()))
        self.assertNotIn("secret-part", "\n".join(logs.output))

    def test_slow_requests_are_listed(self):
        with mock.patch.object(rt, "SLOW_MS", 0):
            self.client.get("/slow")
        self.assertEqual(rt.snapshot()["slow"][0]["route"], "GET /slow")

    def test_the_cache_counts_hits_and_misses(self):
        sc.cached(("k",), lambda: {"n": 1})
        sc.cached(("k",), lambda: {"n": 2})
        self.assertEqual((sc.stats()["hits"], sc.stats()["misses"]), (1, 1))

    def test_only_an_admin_sees_it(self):
        from api import health_routes as hr
        with self.assertRaises(HTTPException) as err:
            hr.system_health(ctx=_ctx("editor"))
        self.assertEqual(err.exception.status_code, 403)
        out = hr.system_health(ctx=_ctx("admin"))
        for key in ("started_at", "routes", "slow", "errors", "cache", "data_versions", "warmed"):
            self.assertIn(key, out)


    def test_each_known_organizations_last_build_and_whether_it_is_stale(self):
        # an administrator could not see Ellensburg's tables were 19 days old (2026-09-29)
        from api import health_routes as hr
        fresh = {"ellensburg": {"built_at": "2026-09-29T12:39:07-04:00", "age_hours": 1.2, "stale": False},
                 "int_dev": {"built_at": "2026-09-27T05:45:00-04:00", "age_hours": 55.0, "stale": True}}
        with mock.patch.object(hr.data_version, "known",
                               return_value={o: {"version": "v", "read_seconds_ago": 1} for o in fresh}), \
             mock.patch.object(hr, "freshness", side_effect=lambda org: fresh[org]):
            out = hr.system_health(ctx=_ctx("admin"))
        self.assertEqual(out["freshness"], fresh)


if __name__ == "__main__":
    unittest.main()
