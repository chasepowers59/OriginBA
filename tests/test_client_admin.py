"""The client admin: administers one client's users, groups and audit trail, and nothing else.

Until 2026-09-30 an admin could only be the platform (root) admin, because users, access
groups and the audit log were filtered by one deployment-wide client_id: an admin bound to
a client would have administered every client (tests/test_admin_org_isolation.py). Groups
and the audit log now carry the organization, and the client_admin role is scoped to its
own on every read and write. The platform admin is unchanged and sees everything.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
from api.auth.dependencies import _resolve_active_organization  # noqa: E402
from api.auth.permissions import permissions_for_role  # noqa: E402
from api.auth.routes import router as auth_router  # noqa: E402
from api.auth.service import create_user  # noqa: E402

PW = "Client-Admin-1!"
ACCOUNTS = {
    "root": ("root@ca.test", "admin", None),
    "ell_admin": ("ell-admin@ca.test", "client_admin", "ellensburg"),
    "ell_user": ("ell-user@ca.test", "user", "ellensburg"),
    "dev_admin": ("dev-admin@ca.test", "client_admin", "dev"),
    "dev_user": ("dev-user@ca.test", "user", "dev"),
}


class ClientAdminTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_auth_database()
        with get_session_factory()() as session:
            for key, (email, role, org) in ACCOUNTS.items():
                create_user(session, "admin", {"email": email, "display_name": key, "password": PW,
                                               "role": role, "organization_id": org})
            session.commit()
        app = FastAPI()
        app.include_router(auth_router)
        cls.client = TestClient(app)
        cls.tokens = {}
        for key, (email, _, _) in ACCOUNTS.items():
            out = cls.client.post("/auth/login", json={"email": email, "password": PW}).json()
            token = out["access_token"]
            if out["user"].get("must_change_password"):
                cls.client.post("/auth/change-password", headers={"Authorization": f"Bearer {token}"},
                                json={"current_password": PW, "new_password": PW + "x"})
                token = cls.client.post("/auth/login", json={"email": email, "password": PW + "x"}).json()["access_token"]
            cls.tokens[key] = token
        cls.ids = {u["email"]: u["id"] for u in cls.as_("root", "GET", "/auth/users").json()}

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(_AUTH_DB.name)
        except OSError:
            pass

    @classmethod
    def as_(cls, who: str, method: str, path: str, **kw):
        return cls.client.request(method, path, headers={"Authorization": f"Bearer {cls.tokens[who]}"}, **kw)

    def test_the_role_exists_below_admin_with_no_platform_powers(self):
        perms = permissions_for_role("client_admin")
        self.assertTrue({"users:manage", "groups:manage", "saved_views:write"} <= perms)
        self.assertFalse({"data_source:manage", "settings:manage", "snapshots:raw_sql"} & perms)
        self.assertIsNone(_resolve_active_organization("client_admin", "dev"))

    def test_a_client_admin_lists_only_their_clients_users(self):
        orgs = {u["organization_id"] for u in self.as_("ell_admin", "GET", "/auth/users").json()}
        self.assertEqual(orgs, {"ellensburg"})
        everyone = {u["email"] for u in self.as_("root", "GET", "/auth/users").json()}
        self.assertTrue({"ell-user@ca.test", "dev-user@ca.test"} <= everyone)

    def test_a_client_admin_creates_users_only_in_their_client(self):
        made = self.as_("ell_admin", "POST", "/auth/users", json={
            "email": "new-ell@ca.test", "display_name": "New Ell", "password": PW, "role": "editor"})
        self.assertEqual(made.status_code, 200, made.text)
        self.assertEqual(made.json()["organization_id"], "ellensburg")
        other = self.as_("ell_admin", "POST", "/auth/users", json={
            "email": "sneaky@ca.test", "display_name": "Sneaky", "password": PW, "role": "user",
            "organization_id": "dev"})
        self.assertIn(other.status_code, (400, 403))
        root = self.as_("ell_admin", "POST", "/auth/users", json={
            "email": "root2@ca.test", "display_name": "Root Two", "password": PW, "role": "admin"})
        self.assertIn(root.status_code, (400, 403))

    def test_a_client_admin_cannot_touch_another_clients_user(self):
        dev_user = self.ids["dev-user@ca.test"]
        self.assertEqual(self.as_("ell_admin", "PUT", f"/auth/users/{dev_user}",
                                  json={"display_name": "Taken"}).status_code, 404)
        ell_user = self.ids["ell-user@ca.test"]
        moved = self.as_("ell_admin", "PUT", f"/auth/users/{ell_user}", json={"organization_id": "dev"})
        self.assertIn(moved.status_code, (400, 403))
        promoted = self.as_("ell_admin", "PUT", f"/auth/users/{ell_user}", json={"role": "admin"})
        self.assertIn(promoted.status_code, (400, 403))

    def test_groups_belong_to_one_client(self):
        made = self.as_("ell_admin", "POST", "/auth/groups", json={"name": "Ellensburg billing",
                                                                   "workstreams": ["billing"]})
        self.assertEqual(made.status_code, 200, made.text)
        gid = made.json()["id"]
        self.assertEqual(made.json()["organization_id"], "ellensburg")
        self.assertNotIn(gid, {g["id"] for g in self.as_("dev_admin", "GET", "/auth/groups").json()})
        self.assertEqual(self.as_("dev_admin", "PUT", f"/auth/groups/{gid}", json={"name": "Taken over"}).status_code, 404)
        self.assertEqual(self.as_("dev_admin", "DELETE", f"/auth/groups/{gid}").status_code, 404)
        self.assertIn(gid, {g["id"] for g in self.as_("root", "GET", "/auth/groups").json()})

    def test_a_client_admin_cannot_hand_out_another_clients_group(self):
        dev_group = self.as_("dev_admin", "POST", "/auth/groups", json={"name": "Dev only"}).json()["id"]
        ell_user = self.ids["ell-user@ca.test"]
        out = self.as_("ell_admin", "PUT", f"/auth/users/{ell_user}", json={"group_ids": [dev_group]})
        self.assertNotIn(dev_group, {g["id"] for g in out.json().get("groups", [])} if out.status_code == 200 else set())

    def test_the_audit_trail_is_per_client(self):
        self.as_("dev_admin", "POST", "/auth/groups", json={"name": "Dev audit probe"})
        self.as_("ell_admin", "POST", "/auth/groups", json={"name": "Ell audit probe"})
        ell = self.as_("ell_admin", "GET", "/auth/audit-log").json()
        self.assertTrue(any(e["detail"] == "Ell audit probe" for e in ell))
        self.assertFalse(any(e["detail"] == "Dev audit probe" for e in ell))
        self.assertTrue({"ellensburg"} >= {e.get("organization_id") for e in ell})
        root = self.as_("root", "GET", "/auth/audit-log").json()
        self.assertTrue({"Ell audit probe", "Dev audit probe"} <= {e["detail"] for e in root})

    def test_a_client_admin_sees_only_their_own_client_in_the_roster(self):
        self.assertEqual([o["id"] for o in self.as_("ell_admin", "GET", "/auth/organizations").json()],
                         ["ellensburg"])
        self.assertGreater(len(self.as_("root", "GET", "/auth/organizations").json()), 1)

    def test_a_normal_user_still_administers_nothing(self):
        for method, path in (("GET", "/auth/users"), ("GET", "/auth/groups"), ("GET", "/auth/audit-log")):
            self.assertEqual(self.as_("ell_user", method, path).status_code, 403)


if __name__ == "__main__":
    unittest.main()
