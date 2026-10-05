"""What the audit trail and the request log keep (production-readiness ledger item 7, 2026-10-05).

1. Audit rows kept up to 300 characters of the SQL that ran, literals included, so a
   customer's name or account number typed into a WHERE clause sat in the trail. The shape
   of the statement is what an investigation needs; values are replaced with ?.
2. The request log's org= was the X-Organization-Id header as sent, which a non-admin may
   forge and the API then ignores, so the log named a client that was never served. It now
   names the organization the request was actually served for.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import Depends, FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api import request_tracing  # noqa: E402
from api.access_audit import sql_for_audit  # noqa: E402
from api.auth import dependencies  # noqa: E402
from api.auth.dependencies import AuthContext, get_auth_context  # noqa: E402


class SqlForAudit(unittest.TestCase):
    def test_values_are_replaced_and_the_shape_kept(self):
        sql = """SELECT acct_id, "Main Customer Name" FROM rpt_customer_account
                 WHERE "Main Customer Name" = 'SMITH, JOHN' AND acct_id IN (1234567890, 42) AND x = 'it''s'"""
        out = sql_for_audit(sql)
        self.assertNotIn("SMITH", out)
        self.assertNotIn("1234567890", out)
        self.assertNotIn("it", out.split("x =")[-1])
        self.assertIn('"Main Customer Name" = ?', out)
        self.assertIn("IN (?, 42)", out)        # small numbers (LIMIT 500, a flag 1) are not personal
        self.assertNotIn("\n", out)

    def test_it_is_capped(self):
        self.assertLessEqual(len(sql_for_audit("SELECT " + "a, " * 500 + "b FROM t")), 300)

    def test_every_audit_site_uses_it(self):
        import re
        for name in ("assistant.py", "database_routes.py", "snapshot_explorer.py"):
            text = (ROOT / "api" / name).read_text()
            self.assertFalse(re.search(r"sql: \{[a-z_.]*sql[a-z_]*\[:300\]\}|sql: \{validated\[:300\]\}", text),
                             f"api/{name} audits raw SQL")


class RequestLogNamesTheServedOrganization(unittest.TestCase):
    def test_a_forged_header_is_not_what_the_log_names(self):
        served = AuthContext(id="u-123456789", email="ann@citycorp.test", display_name="Ann", role="user",
                             client_id="dev", organization_id="citycorp", organization_name="CityCorp",
                             permissions={"portal:read"}, workstreams=["*"])
        app = FastAPI()
        request_tracing.install(app)

        @app.get("/probe")
        def probe(ctx: AuthContext = Depends(get_auth_context)):
            return {"org": ctx.effective_organization_id()}

        with mock.patch.object(dependencies, "_resolve_auth_context", return_value=served), \
             self.assertLogs("originba.api", level="INFO") as logs:
            TestClient(app).get("/probe", headers={"X-Organization-Id": "ellensburg"})
        line = next(l for l in logs.output if "/probe" in l)
        self.assertIn("org=citycorp", line)
        self.assertNotIn("ellensburg", line)


if __name__ == "__main__":
    unittest.main()
