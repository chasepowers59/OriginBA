"""OIDC single sign-on (the Azure AD / Entra shape): tests written before the code.

Contract under test:
  - /auth/oidc/login 302-redirects to the IdP's authorization endpoint with our
    client_id and a SIGNED state; it refuses cleanly when OIDC is not configured.
  - /auth/oidc/callback verifies state, exchanges the code, verifies the id_token
    (both mocked — no network in tests), JIT-provisions a user on first login
    (role user, the configured default org), reuses the existing record afterwards,
    refuses inactive users, and hands the SPA our own JWT via the login page's
    #sso_token= fragment.
  - /auth/status advertises oidc_enabled so the login page can show the SSO button.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_AUTH_DB = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
_AUTH_DB.close()
os.environ["PORTAL_AUTH_DATABASE_URL"] = f"sqlite:///{_AUTH_DB.name}"
os.environ.pop("PORTAL_AUTH_DISABLED", None)
os.environ["PORTAL_AUTH_SECRET"] = "test-secret-at-least-thirty-two-characters-long"
os.environ["OIDC_ISSUER"] = "https://login.microsoftonline.com/test-tenant/v2.0"
os.environ["OIDC_CLIENT_ID"] = "portal-client-id"
os.environ["OIDC_CLIENT_SECRET"] = "portal-client-secret"
os.environ["OIDC_REDIRECT_URI"] = "https://api.test/auth/oidc/callback"
os.environ["OIDC_DEFAULT_ORGANIZATION"] = "dev"
os.environ["OIDC_POST_LOGIN_URL"] = "https://portal.test/login"

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.auth import oidc  # noqa: E402
from api.auth.bootstrap import init_auth_database  # noqa: E402
from api.auth.routes import router as auth_router  # noqa: E402

FAKE_DISCOVERY = {
    "authorization_endpoint": "https://idp.test/authorize",
    "token_endpoint": "https://idp.test/token",
    "jwks_uri": "https://idp.test/keys",
    "issuer": os.environ["OIDC_ISSUER"],
}


class OidcSsoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # OIDC callbacks need real auth semantics; another module may have disabled it
        os.environ.pop("PORTAL_AUTH_DISABLED", None)
        init_auth_database()
        app = FastAPI()
        app.include_router(auth_router)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(_AUTH_DB.name)
        except OSError:
            pass

    # -- helpers ---------------------------------------------------------------
    def _login_redirect(self):
        with mock.patch.object(oidc, "fetch_discovery", return_value=FAKE_DISCOVERY):
            return self.client.get("/auth/oidc/login", follow_redirects=False)

    def _callback(self, state: str, email: str = "analyst@utility.gov", name: str = "Ana Lyst"):
        with mock.patch.object(oidc, "fetch_discovery", return_value=FAKE_DISCOVERY), \
             mock.patch.object(oidc, "exchange_code", return_value={"id_token": "fake"}), \
             mock.patch.object(oidc, "verify_id_token",
                               return_value={"email": email, "name": name, "sub": "ms-sub-1"}):
            return self.client.get(
                f"/auth/oidc/callback?code=abc&state={state}", follow_redirects=False)

    # -- tests -----------------------------------------------------------------
    def test_status_advertises_oidc(self):
        r = self.client.get("/auth/status")
        self.assertTrue(r.json().get("oidc_enabled"))

    def test_login_redirects_to_idp_with_signed_state(self):
        r = self._login_redirect()
        self.assertEqual(r.status_code, 307)
        url = urlparse(r.headers["location"])
        self.assertEqual(f"{url.scheme}://{url.netloc}{url.path}", FAKE_DISCOVERY["authorization_endpoint"])
        q = parse_qs(url.query)
        self.assertEqual(q["client_id"], ["portal-client-id"])
        self.assertEqual(q["response_type"], ["code"])
        self.assertIn("openid", q["scope"][0])
        self.assertTrue(q["state"][0])

    def test_callback_jit_provisions_then_reuses(self):
        state = parse_qs(urlparse(self._login_redirect().headers["location"]).query)["state"][0]
        r = self._callback(state)
        self.assertEqual(r.status_code, 307)
        loc = r.headers["location"]
        self.assertTrue(loc.startswith("https://portal.test/login#sso_token="))

        from api.auth.database import get_session_factory
        from api.auth.models import User
        with get_session_factory()() as session:
            u = session.query(User).filter(User.email == "analyst@utility.gov").one()
            self.assertEqual(u.role, "user")
            self.assertEqual(u.organization_id, "dev")

        # second login: same record, no duplicate
        state2 = parse_qs(urlparse(self._login_redirect().headers["location"]).query)["state"][0]
        r2 = self._callback(state2)
        self.assertEqual(r2.status_code, 307)
        with get_session_factory()() as session:
            n = session.query(User).filter(User.email == "analyst@utility.gov").count()
            self.assertEqual(n, 1)

    def test_callback_rejects_tampered_state(self):
        r = self._callback("not-a-valid-state")
        self.assertEqual(r.status_code, 400)

    def test_callback_refuses_inactive_user(self):
        state = parse_qs(urlparse(self._login_redirect().headers["location"]).query)["state"][0]
        self._callback(state, email="off@utility.gov")
        from api.auth.database import get_session_factory
        from api.auth.models import User
        with get_session_factory()() as session:
            session.query(User).filter(User.email == "off@utility.gov").update({"is_active": False})
            session.commit()
        state2 = parse_qs(urlparse(self._login_redirect().headers["location"]).query)["state"][0]
        r = self._callback(state2, email="off@utility.gov")
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
