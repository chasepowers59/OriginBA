"""Integration tests for multi-tenant login binding and the public tenant lookup.

Locks in the 2026-08-30 multi-tenant work: a /<slug> tenant URL (or a typed org at the
root login) is authorized server-side. A non-admin may only enter the organization their
account belongs to; an admin may enter any registered tenant. The public /auth/tenants
lookup resolves one slug without exposing the full client roster.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Auth ENABLED for these tests (the login route refuses when auth is disabled). Use a
# shared temp-file sqlite DB (not :memory:) so the TestClient's threadpool connection
# sees the tables/users seeded on the main thread.
_AUTH_DB = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
_AUTH_DB.close()
os.environ["PORTAL_AUTH_DATABASE_URL"] = f"sqlite:///{_AUTH_DB.name}"
os.environ.pop("PORTAL_AUTH_DISABLED", None)
os.environ["PORTAL_AUTH_SECRET"] = "test-secret-at-least-thirty-two-characters-long"
os.environ.setdefault("PORTAL_BOOTSTRAP_ADMIN_PASSWORD", "test-bootstrap-admin-pw")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.auth.bootstrap import init_auth_database  # noqa: E402
from api.auth.database import get_session_factory  # noqa: E402
from api.auth.routes import router as auth_router  # noqa: E402
from api.auth.service import create_user  # noqa: E402


class TenantLoginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_auth_database()
        factory = get_session_factory()
        with factory() as session:
            create_user(session, "admin", {
                "email": "ellensburg-user@tenant.test", "display_name": "E User",
                "password": "Ellensburg-1!", "role": "user", "organization_id": "ellensburg",
            })
            create_user(session, "admin", {
                "email": "dev-user@tenant.test", "display_name": "D User",
                "password": "Dev-User-1!", "role": "user", "organization_id": "dev",
            })
            create_user(session, "admin", {
                "email": "root-admin@tenant.test", "display_name": "Root Admin",
                "password": "Root-Admin-1!", "role": "admin", "organization_id": None,
            })
            session.commit()
        app = FastAPI()
        app.include_router(auth_router)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(_AUTH_DB.name)
        except OSError:
            pass

    def _login(self, email: str, password: str, organization: str | None = None):
        body: dict[str, str] = {"email": email, "password": password}
        if organization is not None:
            body["organization"] = organization
        return self.client.post("/auth/login", json=body)

    def test_non_admin_enters_own_tenant(self) -> None:
        r = self._login("ellensburg-user@tenant.test", "Ellensburg-1!", "ellensburg")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["active_organization_id"], "ellensburg")

    def test_non_admin_blocked_from_other_tenant(self) -> None:
        r = self._login("ellensburg-user@tenant.test", "Ellensburg-1!", "dev")
        self.assertEqual(r.status_code, 403)

    def test_login_without_org_uses_home(self) -> None:
        r = self._login("ellensburg-user@tenant.test", "Ellensburg-1!")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["active_organization_id"], "ellensburg")

    def test_admin_may_enter_any_tenant(self) -> None:
        r = self._login("root-admin@tenant.test", "Root-Admin-1!", "ellensburg")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["active_organization_id"], "ellensburg")

    def test_unknown_org_rejected(self) -> None:
        r = self._login("dev-user@tenant.test", "Dev-User-1!", "does-not-exist")
        self.assertEqual(r.status_code, 400)

    def test_org_accepts_display_name(self) -> None:
        r = self._login("dev-user@tenant.test", "Dev-User-1!", "INT_DEV (internal dev CISADM)")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["active_organization_id"], "dev")

    def test_public_tenant_lookup(self) -> None:
        ok = self.client.get("/auth/tenants/ellensburg")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["id"], "ellensburg")
        self.assertEqual(self.client.get("/auth/tenants/nope").status_code, 404)


if __name__ == "__main__":
    unittest.main()
