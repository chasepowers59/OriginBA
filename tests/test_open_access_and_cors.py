"""Two ways a deployment can hand itself to the internet. Audit M7 and M9.

M7 — `PORTAL_AUTH_DISABLED=true` yields `_dev_context()`: a full ADMIN, with
users:manage, data_source:manage, settings:manage and tenant switching, on a literal
dev JWT secret. Nothing checked whether this was production. One env var set by mistake
on a real deployment is a total compromise, and the variable is genuinely used every
day in local work, so it is not the kind of thing anybody notices in a diff.

The fix is the same direction as /health (audit M3): open access requires AFFIRMATIVE
proof of development, not merely the absence of proof of production. `is_production()`
defaults to False for an unrecognised environment, so "refuse when is_production()"
would have defended nothing on Render, which sets none of the three markers.

That is why tests/conftest.py declares ENVIRONMENT=test for the suite: the tests are a
development environment and should say so, rather than the fence being loosened to let
them through.

M9 — `PORTAL_CORS_ORIGINS` is appended verbatim to `allow_origins`, and the middleware
runs `allow_credentials=True`. Starlette treats a "*" entry as allow-all, and when
credentials are enabled it ECHOES the caller's origin rather than sending "*" — so any
website could make credentialed calls against the API with a logged-in user's cookies.
A wildcard and credentials are mutually exclusive by the CORS spec's own reasoning; the
wildcard is dropped rather than silently honoured.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class OpenAccessRequiresDevelopmentTests(unittest.TestCase):
    def test_open_access_works_when_development_is_declared(self):
        from api.auth.config import auth_disabled
        for env in ("development", "dev", "local", "test"):
            with mock.patch.dict(os.environ, {"PORTAL_AUTH_DISABLED": "true",
                                              "ENVIRONMENT": env}):
                self.assertTrue(auth_disabled(), env)

    def test_open_access_is_REFUSED_in_declared_production(self):
        from api.auth.config import auth_disabled
        for env in ("production", "prod"):
            with mock.patch.dict(os.environ, {"PORTAL_AUTH_DISABLED": "true",
                                              "ENVIRONMENT": env}):
                self.assertFalse(auth_disabled(), env)

    def test_open_access_is_REFUSED_when_the_environment_is_unknown(self):
        """The case that matters: Render sets none of the three markers, so an
        unrecognised deployment is the REAL one, not a hypothetical."""
        from api.auth.config import auth_disabled
        with mock.patch.dict(os.environ, {"PORTAL_AUTH_DISABLED": "true"}):
            for var in ("ENVIRONMENT", "RAILWAY_ENVIRONMENT_NAME", "VERCEL_ENV"):
                os.environ.pop(var, None)
            self.assertFalse(auth_disabled(),
                             "open access must not be available to an undeclared deployment")

    def test_platform_production_markers_also_refuse_it(self):
        from api.auth.config import auth_disabled
        for var in ("RAILWAY_ENVIRONMENT_NAME", "VERCEL_ENV"):
            with mock.patch.dict(os.environ, {"PORTAL_AUTH_DISABLED": "true", var: "production"}):
                os.environ.pop("ENVIRONMENT", None)
                self.assertFalse(auth_disabled(), var)

    def test_auth_stays_on_when_the_flag_is_absent_whatever_the_environment(self):
        from api.auth.config import auth_disabled
        for env in ("development", "production", "anything"):
            with mock.patch.dict(os.environ, {"ENVIRONMENT": env}):
                os.environ.pop("PORTAL_AUTH_DISABLED", None)
                self.assertFalse(auth_disabled(), env)


class CorsOriginTests(unittest.TestCase):
    def test_the_built_in_origins_are_present(self):
        from api.app import _cors_origins
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PORTAL_CORS_ORIGINS", None)
            origins = _cors_origins()
        self.assertIn("http://localhost:3000", origins)

    def test_a_configured_origin_is_added(self):
        from api.app import _cors_origins
        with mock.patch.dict(os.environ,
                             {"PORTAL_CORS_ORIGINS": "https://portal.city.gov"}):
            self.assertIn("https://portal.city.gov", _cors_origins())

    def test_a_wildcard_is_never_honoured_alongside_credentials(self):
        """allow_credentials=True + "*" makes Starlette echo ANY origin."""
        from api.app import _cors_origins
        for attack in ("*", " * ", "https://ok.example,*"):
            with mock.patch.dict(os.environ, {"PORTAL_CORS_ORIGINS": attack}):
                self.assertNotIn("*", _cors_origins(), attack)

    def test_a_non_origin_string_is_refused(self):
        """An origin is scheme://host. Anything else cannot match a browser Origin
        header, so honouring it only widens the list with noise."""
        from api.app import _cors_origins
        with mock.patch.dict(os.environ,
                             {"PORTAL_CORS_ORIGINS": "evil.example,ftp://x,https://ok.example"}):
            origins = _cors_origins()
        self.assertIn("https://ok.example", origins)
        self.assertNotIn("evil.example", origins)
        self.assertNotIn("ftp://x", origins)

    def test_credentials_are_still_enabled(self):
        """The app relies on them; the point is that "*" cannot coexist with them."""
        src = (ROOT / "api" / "app.py").read_text()
        self.assertIn("allow_credentials=True", src)


if __name__ == "__main__":
    unittest.main()
