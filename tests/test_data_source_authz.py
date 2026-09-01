"""H1 (2026-09-01): the settings token was an ALTERNATIVE to the permission.

`verify_settings_token()` returns True when `PORTAL_SETTINGS_TOKEN` is unset — the
default, and it appears in no deploy file — and `_require_data_source_manage`
accepted that *instead of* `data_source:manage`. So any authenticated `user` could
repoint their org's database, and `POST /portal/data-source/test` with an arbitrary
DSN answered whether an internal host was reachable: a blind port scanner running
from the API host.

Contract:
  - `data_source:manage` is required unconditionally;
  - the token, when configured, is an ADDITIONAL factor on top of it;
  - a failed connection test never returns the raw driver error (it leaks whether a
    host/port is live).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import data_source_routes as routes  # noqa: E402
from api.data_source_store import verify_settings_token  # noqa: E402


class _Ctx:
    """Minimal AuthContext stand-in: only the bits the dependency reads."""

    def __init__(self, *, perms: set[str], role: str = "user", org: str = "dev"):
        self._perms = perms
        self.role = role
        self.organization_id = org
        self.email = "someone@utility.gov"
        self.id = "u1"

    def has_permission(self, name: str) -> bool:
        return name in self._perms

    def require_organization(self) -> str:
        return self.organization_id


class SettingsTokenIsNotAnAlternativeTests(unittest.TestCase):
    def _require(self, ctx, token=None):
        from fastapi import HTTPException

        try:
            return routes._require_data_source_manage(ctx=ctx, x_portal_settings_token=token)
        except HTTPException as exc:
            return exc.status_code

    def test_user_without_the_permission_is_refused_when_no_token_is_configured(self):
        # The audited hole: no PORTAL_SETTINGS_TOKEN set, so the token "verified"
        # and a plain user sailed through.
        with mock.patch.dict("os.environ", {}, clear=False) as _:
            with mock.patch.object(routes, "verify_settings_token", return_value=True):
                self.assertEqual(self._require(_Ctx(perms=set())), 403)

    def test_user_without_the_permission_is_refused_even_with_a_valid_token(self):
        with mock.patch.object(routes, "verify_settings_token", return_value=True):
            self.assertEqual(self._require(_Ctx(perms=set()), token="the-right-token"), 403)

    def test_manager_is_allowed(self):
        ctx = _Ctx(perms={"data_source:manage"})
        with mock.patch.object(routes, "verify_settings_token", return_value=True):
            self.assertIs(self._require(ctx), ctx)

    def test_manager_still_needs_the_token_when_one_is_configured(self):
        # Configured token = a second factor, not a replacement.
        with mock.patch.object(routes, "verify_settings_token", return_value=False):
            self.assertEqual(self._require(_Ctx(perms={"data_source:manage"})), 401)


class ConnectionTestDoesNotProbeTests(unittest.TestCase):
    def test_failed_test_does_not_return_the_raw_driver_error(self):
        ctx = _Ctx(perms={"data_source:manage"}, role="admin")
        body = routes.DataSourceBody(user="u", password="p", dsn="10.13.4.91:1521/PROD")
        with mock.patch.object(routes, "test_oracle_connection",
                               side_effect=Exception("ORA-12541: TNS:no listener")):
            out = routes.test_data_source(body=body, ctx=ctx, organization_id=None)
        self.assertFalse(out["ok"])
        self.assertNotIn("no listener", out["error"])
        self.assertNotIn("12541", out["error"])


class VerifySettingsTokenSemanticsTests(unittest.TestCase):
    def test_unset_token_still_verifies_true_but_is_no_longer_load_bearing(self):
        # Kept as-is deliberately: the helper answers "does the token check pass",
        # and the ROUTE decides that a permission is also required. The test pins
        # that the helper alone can never authorise anything.
        with mock.patch.dict("os.environ", {"PORTAL_SETTINGS_TOKEN": ""}):
            self.assertTrue(verify_settings_token(None))


if __name__ == "__main__":
    unittest.main()
