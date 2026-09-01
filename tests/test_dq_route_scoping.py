"""C3 (2026-09-01): the data-quality routes were unpermissioned and mis-scoped.

`/dq/findings`, `/dq/ack` and `/dq/unack` took only `get_auth_context` — no
permission check at all — and read `ctx.organization_id` (the caller's HOME org)
instead of the effective one, so an admin's tenant switch was ignored while a user
with no org resolved `None` and fell through to the shared warehouse plus a shared
ack file.

Contract:
  - all three routes require `portal:read`;
  - all three scope to the EFFECTIVE organization (require_org_for_data);
  - an org with no Postgres warehouse gets `configured: False`, never another
    tenant's findings;
  - acks are stored per organization.
"""
from __future__ import annotations

import inspect
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import dq_routes  # noqa: E402


class DqRouteContractTests(unittest.TestCase):
    ROUTES = ("dq_findings", "dq_ack", "dq_unack")

    def test_every_route_requires_a_permission(self):
        for name in self.ROUTES:
            with self.subTest(route=name):
                src = inspect.getsource(getattr(dq_routes, name))
                self.assertIn(
                    "require_permission", src,
                    f"{name} has no permission check — any authenticated caller reaches it",
                )

    def test_no_route_reads_the_home_org_directly(self):
        for name in self.ROUTES:
            with self.subTest(route=name):
                src = inspect.getsource(getattr(dq_routes, name))
                self.assertNotIn(
                    "ctx.organization_id", src,
                    f"{name} must use require_org_for_data(ctx), not the home org",
                )
                self.assertIn("require_org_for_data", src)


class DqWarehouseScopingTests(unittest.TestCase):
    def setUp(self):
        os.environ["PORTAL_AUTH_DISABLED"] = "true"
        os.environ["PORTAL_DEV_ORGANIZATION"] = "dev"
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(dq_routes.router)
        self.client = TestClient(app)

    def test_org_without_a_warehouse_gets_configured_false(self):
        # An Oracle-backed org has no Postgres warehouse; it must be told so
        # rather than served whatever the shared URL points at.
        with mock.patch.object(dq_routes, "warehouse_configured", return_value=False), \
             mock.patch.object(dq_routes, "warehouse_connection") as conn:
            r = self.client.get("/dq/findings")
            self.assertEqual(r.status_code, 200, r.text)
            self.assertFalse(r.json()["configured"])
            conn.assert_not_called()

    def test_acks_are_stored_per_organization(self):
        a = dq_routes._ack_path("ellensburg")
        b = dq_routes._ack_path("citycorp")
        self.assertNotEqual(a, b)
        # and no org must ever share the fallback file with another
        self.assertNotIn("default", str(a).lower())


if __name__ == "__main__":
    unittest.main()
