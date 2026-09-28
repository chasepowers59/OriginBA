"""Single sign-on groups decide a person's access, on every sign-in.

OIDC_GROUP_MAP (JSON) maps identity-provider groups to portal access:
    [{"group": "Billing-Analysts", "role": "editor", "organization_id": "dev",
      "access_groups": ["Finance"], "row_rules": [{"field": "Service Type", "values": ["Water"]}]}]
The group claim is OIDC_GROUPS_CLAIM ("groups" by default; Entra can send "roles").
With a map configured, access follows the person's groups at every sign-in, so removing
them from a group at the IdP takes effect at their next login. The highest matching role
wins; the map never grants admin, and an existing admin is never changed by it. Someone in
no mapped group is refused, and an existing account of theirs is deactivated (removal at
the IdP ends their sessions, schedules and embeds); groups pointing at two different
clients are refused rather than guessed. Row rules change only when a matching group
DECLARES them ("row_rules": [] declares no restriction): a map that says nothing about rows
never widens rules an administrator set. A malformed groups claim, a broken rule in the map
or an identity token saying the address is unverified is refused, never half-applied.
Without a map, first sign-in provisions a user in the default org, as before.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.auth import oidc  # noqa: E402

MAP = [
    {"group": "portal-users", "role": "user", "organization_id": "dev"},
    {"group": "billing-analysts", "role": "editor", "organization_id": "dev",
     "row_rules": [{"field": "Service Type", "values": ["Water"]}]},
    {"group": "all-data", "role": "user", "organization_id": "dev", "row_rules": []},
    {"group": "citycorp-users", "role": "user", "organization_id": "citycorp"},
    {"group": "it-admins", "role": "admin", "organization_id": None},
]


class MappingTests(unittest.TestCase):
    def test_the_highest_matching_role_wins(self):
        out = oidc.mapped_access({"groups": ["portal-users", "billing-analysts"]}, MAP, "groups")
        self.assertEqual(out["role"], "editor")
        self.assertEqual(out["organization_id"], "dev")
        self.assertEqual(out["row_rules"], [{"field": "Service Type", "values": ["Water"]}])

    def test_no_matching_group_is_no_access(self):
        with self.assertRaisesRegex(oidc.SsoAccessError, "not in a group"):
            oidc.mapped_access({"groups": ["someone-else"]}, MAP, "groups")

    def test_two_clients_are_refused_not_guessed(self):
        with self.assertRaisesRegex(oidc.SsoAccessError, "more than one"):
            oidc.mapped_access({"groups": ["portal-users", "citycorp-users"]}, MAP, "groups")

    def test_the_map_never_grants_admin(self):
        out = oidc.mapped_access({"groups": ["it-admins", "portal-users"]}, MAP, "groups")
        self.assertEqual(out["role"], "user")

    def test_a_single_string_claim_counts_as_one_group(self):
        self.assertEqual(oidc.mapped_access({"roles": "portal-users"}, MAP, "roles")["role"], "user")

    def test_a_malformed_groups_claim_is_refused(self):
        for raw in ({"portal-users": 1}, 5, ["portal-users", {"x": 1}]):
            with self.assertRaises(oidc.SsoAccessError):
                oidc.mapped_access({"groups": raw}, MAP, "groups")

    def test_a_broken_rule_in_the_map_refuses_rather_than_widening(self):
        broken = [{"group": "g", "role": "editor", "organization_id": "dev",
                   "row_rules": [{"field": "Service Type", "values": []}]}]
        with self.assertRaises(oidc.SsoAccessError):
            oidc.mapped_access({"groups": ["g"]}, broken, "groups")

    def test_rules_are_undeclared_unless_a_group_declares_them(self):
        self.assertIsNone(oidc.mapped_access({"groups": ["portal-users"]}, MAP, "groups")["row_rules"])
        self.assertEqual(oidc.mapped_access({"groups": ["all-data"]}, MAP, "groups")["row_rules"], [])


FAKE_DISCOVERY = {"authorization_endpoint": "https://idp.test/authorize", "token_endpoint": "https://idp.test/token",
                  "jwks_uri": "https://idp.test/keys", "issuer": "https://idp.test"}


class SignInTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {
            "PORTAL_AUTH_DISABLED": "false", "PORTAL_AUTH_DATABASE_URL": f"sqlite:///{self.tmp.name}/a.db",
            "PORTAL_AUTH_SECRET": "test-secret-at-least-thirty-two-characters-long",
            "PORTAL_BOOTSTRAP_ADMIN_PASSWORD": "test-bootstrap-admin-pw",
            "OIDC_ISSUER": "https://idp.test", "OIDC_CLIENT_ID": "cid", "OIDC_CLIENT_SECRET": "sec",
            "OIDC_REDIRECT_URI": "https://api.test/auth/oidc/callback", "OIDC_DEFAULT_ORGANIZATION": "dev",
            "OIDC_POST_LOGIN_URL": "https://portal.test/login", "OIDC_GROUP_MAP": json.dumps(MAP)})
        self.env.start()
        from api.auth.database import temporary_engine
        self.engine = temporary_engine()
        self.engine.__enter__()
        from api.auth.bootstrap import init_auth_database
        init_auth_database()
        from api.auth.routes import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.engine.__exit__(None, None, None)
        self.env.stop()
        self.tmp.cleanup()

    def _sign_in(self, groups, email="ana@utility.gov", **claims):
        with mock.patch.object(oidc, "fetch_discovery", return_value=FAKE_DISCOVERY), \
             mock.patch.object(oidc, "exchange_code", return_value={"id_token": "x"}), \
             mock.patch.object(oidc, "verify_id_token",
                               return_value={"email": email, "name": "Ana", "groups": groups, **claims}):
            return self.client.get(f"/auth/oidc/callback?code=c&state={oidc.make_state()}", follow_redirects=False)

    def _user(self, email="ana@utility.gov"):
        from api.auth.database import get_session_factory
        from api.auth.models import User
        from api.auth.service import user_to_public
        with get_session_factory()() as s:
            return user_to_public(s.query(User).filter(User.email == email).one())

    def test_first_sign_in_gets_the_groups_access(self):
        r = self._sign_in(["billing-analysts"])
        self.assertIn(r.status_code, (302, 307))
        self.assertIn("sso_token=", urlparse(r.headers["location"]).fragment)
        u = self._user()
        self.assertEqual((u["role"], u["organization_id"]), ("editor", "dev"))
        self.assertEqual(u["row_rules"], [{"field": "Service Type", "values": ["Water"]}])

    def test_access_follows_the_groups_at_every_sign_in(self):
        self._sign_in(["billing-analysts"])
        self._sign_in(["portal-users"])
        u = self._user()
        self.assertEqual(u["role"], "user")
        # portal-users says nothing about rows, so the restriction stays
        self.assertEqual(u["row_rules"], [{"field": "Service Type", "values": ["Water"]}])
        self._sign_in(["all-data"])
        self.assertEqual(self._user()["row_rules"], [])

    def test_removal_from_every_group_deactivates_the_account(self):
        self._sign_in(["billing-analysts"])
        self.assertEqual(self._sign_in(["marketing"]).status_code, 403)
        self.assertFalse(self._user()["is_active"])

    def test_an_unverified_address_is_refused(self):
        r = self._sign_in(["billing-analysts"], email_verified=False)
        self.assertEqual(r.status_code, 403)
        from api.auth.database import get_session_factory
        from api.auth.models import User
        with get_session_factory()() as s:
            self.assertEqual(s.query(User).filter(User.email == "ana@utility.gov").count(), 0)

    def test_someone_in_no_mapped_group_is_refused(self):
        r = self._sign_in(["marketing"])
        self.assertEqual(r.status_code, 403)
        self.assertIn("not in a group", r.json()["detail"])

    def test_an_existing_admin_is_never_changed(self):
        from api.auth.database import get_session_factory
        from api.auth.models import User
        from api.auth.security import hash_password
        with get_session_factory()() as s:
            s.add(User(email="root@utility.gov", display_name="root", password_hash=hash_password("x" * 12),
                       role="admin", organization_id=None, is_active=True))
            s.commit()
        self._sign_in(["portal-users"], email="root@utility.gov")
        self.assertEqual(self._user("root@utility.gov")["role"], "admin")


if __name__ == "__main__":
    unittest.main()
