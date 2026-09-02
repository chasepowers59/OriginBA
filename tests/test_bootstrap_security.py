"""Hardcoded values in the auth bootstrap that are a security risk.

Measured on a fresh auth database, 2026-09-02, with auth ENABLED:

    email='admin@origin.local' role='admin' organization_id='demo' must_change=True
    default password from source authenticates: True

Two problems, one of which is an account-takeover path:

1. api/auth/config.py shipped `bootstrap_admin_password()` with the literal default
   "ChangeMe-Admin-1!", beside a default email "admin@origin.local". Any deployment
   that did not set PORTAL_BOOTSTRAP_ADMIN_PASSWORD had an admin login that is public
   in this repository. must_change_password=True limits what the intruder can READ
   before changing it, but it does not stop them: they authenticate, POST
   /auth/change-password, and now own the account while the real operator is locked
   out. The codebase already has the right pattern for this — PORTAL_AUTH_SECRET
   RAISES rather than defaulting — so bootstrap now does the same.

2. The bootstrap admin was created with organization_id='demo', which is exactly the
   account tests/test_admin_org_isolation.py forbids: an admin bound to a client. The
   service layer refuses it, but bootstrap builds the User model directly and so
   bypassed that check — the one account every deployment starts with was the one
   shape that is not allowed.

Separately, jwt_algorithm() read PORTAL_AUTH_ALGORITHM with no allowlist, so the
signing algorithm could be set to "none" — decode() would then accept unsigned tokens.
The security skill claims the algorithm is pinned; now it is.
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


def _fresh_db_env(**extra: str) -> dict[str, str]:
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    env = {
        "PORTAL_AUTH_DATABASE_URL": f"sqlite:///{tmp.name}",
        "PORTAL_AUTH_DISABLED": "false",
        "PORTAL_AUTH_SECRET": "x" * 40,
    }
    env.update(extra)
    return env


class BootstrapAdminCredentialTests(unittest.TestCase):
    def _bootstrap(self, env: dict[str, str]):
        """Bootstrap against a throwaway database, then hand the previous engine back.

        The engine is a process-wide singleton: leaving it pointed at this test's temp
        file strands every module that runs afterwards, and merely CLEARING it empties
        the in-memory databases other modules are mid-way through using. Both happened
        the first time this ran with the full suite.
        """
        from api.auth import database as db
        from api.auth.bootstrap import init_auth_database
        from api.auth.models import User

        with mock.patch.dict(os.environ, env, clear=False), db.temporary_engine():
            init_auth_database()
            with db.get_session_factory()() as session:
                return list(session.query(User).all())

    def test_refuses_to_create_an_admin_with_no_password_configured(self):
        from api.auth.config import BootstrapError

        # Patched to empty, not popped: other modules set this in the real environment,
        # and popping it from OUR dict leaves theirs in place.
        env = _fresh_db_env(PORTAL_BOOTSTRAP_ADMIN_PASSWORD="")
        with self.assertRaises(BootstrapError) as caught:
            self._bootstrap(env)
        message = str(caught.exception)
        self.assertIn("PORTAL_BOOTSTRAP_ADMIN_PASSWORD", message)

    def test_no_source_literal_authenticates_the_bootstrap_admin(self):
        """The specific regression: the repo's own default must not be a valid login."""
        from api.auth.security import verify_password

        users = self._bootstrap(_fresh_db_env(PORTAL_BOOTSTRAP_ADMIN_PASSWORD="A-Real-Secret-1!"))
        admin = users[0]
        self.assertFalse(verify_password("ChangeMe-Admin-1!", admin.password_hash))
        self.assertTrue(verify_password("A-Real-Secret-1!", admin.password_hash))

    def test_the_bootstrap_admin_is_a_platform_admin(self):
        """An admin bound to a client is forbidden — see test_admin_org_isolation."""
        users = self._bootstrap(_fresh_db_env(PORTAL_BOOTSTRAP_ADMIN_PASSWORD="A-Real-Secret-1!"))
        admin = users[0]
        self.assertEqual(admin.role, "admin")
        self.assertIsNone(admin.organization_id)

    def test_still_forces_a_password_change_on_first_login(self):
        users = self._bootstrap(_fresh_db_env(PORTAL_BOOTSTRAP_ADMIN_PASSWORD="A-Real-Secret-1!"))
        self.assertTrue(users[0].must_change_password)

    def test_auth_disabled_needs_no_bootstrap_password(self):
        """Local open access must keep working with no configuration at all."""
        env = _fresh_db_env(PORTAL_AUTH_DISABLED="true", PORTAL_BOOTSTRAP_ADMIN_PASSWORD="")
        self.assertEqual(self._bootstrap(env), [])


class JwtAlgorithmTests(unittest.TestCase):
    def test_none_is_refused(self):
        from api.auth.config import jwt_algorithm

        for bad in ("none", "None", "NONE", ""):
            with mock.patch.dict(os.environ, {"PORTAL_AUTH_ALGORITHM": bad}):
                self.assertEqual(jwt_algorithm(), "HS256", bad)

    def test_an_unknown_algorithm_falls_back_rather_than_being_trusted(self):
        from api.auth.config import jwt_algorithm

        with mock.patch.dict(os.environ, {"PORTAL_AUTH_ALGORITHM": "HS256-but-not-really"}):
            self.assertEqual(jwt_algorithm(), "HS256")

    def test_a_stronger_algorithm_is_still_allowed(self):
        from api.auth.config import jwt_algorithm

        with mock.patch.dict(os.environ, {"PORTAL_AUTH_ALGORITHM": "HS512"}):
            self.assertEqual(jwt_algorithm(), "HS512")

    def test_default_is_hs256(self):
        from api.auth.config import jwt_algorithm

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PORTAL_AUTH_ALGORITHM", None)
            self.assertEqual(jwt_algorithm(), "HS256")


if __name__ == "__main__":
    unittest.main()
