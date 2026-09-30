"""The remaining untested backend helpers: auth config, roles, catalog, DSNs.

Everything here was named in no test while having three or more callers. Most of it
turned out correct and is now pinned. Three were not:

1. `access_token_minutes()` was a bare `int(os.getenv(...))`. A typo raises ValueError
   inside `create_access_token`, so EVERY LOGIN 500s over a malformed env var — and a
   value of 0 or a negative mints tokens that are already expired, which looks exactly
   like "the password is wrong" to every user at once. Clamped now, with a floor.

2. `role_at_least(role, minimum)` read `ROLE_RANK.get(minimum, 0)`, so an unknown or
   misspelled MINIMUM ranked 0 and **everyone passed**. Unknown ACTOR roles already
   failed closed; the two directions disagreed and the open one is the dangerous one.
   Latent today — both call sites pass "admin" — and one typo away from not being.

3. `/health` disclosed the client roster unauthenticated (audit M3). See
   test_health_disclosure below for why the DEFAULT was the bug.

Pinned-as-correct, worth stating because each is a place the obvious guess is wrong:
`can_assign_role` only lets an admin make an admin; `demo_configured(None)` is False
rather than falling back to a global; `is_warehouse` means "is a dbt canvas", NOT "is
Postgres" (an in-database Oracle org is a warehouse too, which is exactly the
shortcut `org_backend`'s docstring warns about); and `resolve_snapshot_key` tries all
three casings, which is what keeps a lowercase canvas id resolvable.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class AccessTokenMinutesTests(unittest.TestCase):
    def test_the_default_is_eight_hours(self):
        from api.auth.config import access_token_minutes
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PORTAL_AUTH_ACCESS_MINUTES", None)
            self.assertEqual(access_token_minutes(), 480)

    def test_a_configured_value_is_honoured(self):
        from api.auth.config import access_token_minutes
        with mock.patch.dict(os.environ, {"PORTAL_AUTH_ACCESS_MINUTES": "60"}):
            self.assertEqual(access_token_minutes(), 60)

    def test_a_malformed_value_does_not_break_every_login(self):
        """int() raised inside create_access_token, so the whole login path 500s."""
        from api.auth.config import access_token_minutes
        for junk in ("8h", "", "  ", "abc", "60.5"):
            with mock.patch.dict(os.environ, {"PORTAL_AUTH_ACCESS_MINUTES": junk}):
                self.assertEqual(access_token_minutes(), 480, junk)

    def test_a_zero_or_negative_lifetime_is_refused(self):
        """A token expiring at or before issue reads as "wrong password" to everyone."""
        from api.auth.config import access_token_minutes
        for bad in ("0", "-1", "-480"):
            with mock.patch.dict(os.environ, {"PORTAL_AUTH_ACCESS_MINUTES": bad}):
                self.assertGreaterEqual(access_token_minutes(), 1, bad)


class JwtSecretTests(unittest.TestCase):
    def test_auth_enabled_demands_a_real_secret(self):
        from api.auth.config import jwt_secret
        for weak in ("", "short", "x" * 31):
            with mock.patch.dict(os.environ, {"PORTAL_AUTH_SECRET": weak,
                                              "PORTAL_AUTH_DISABLED": "false"}):
                with self.assertRaises(RuntimeError, msg=repr(weak)):
                    jwt_secret()

    def test_thirty_two_characters_is_enough(self):
        from api.auth.config import jwt_secret
        with mock.patch.dict(os.environ, {"PORTAL_AUTH_SECRET": "y" * 32,
                                          "PORTAL_AUTH_DISABLED": "false"}):
            self.assertEqual(jwt_secret(), "y" * 32)

    def test_open_access_does_not_demand_one(self):
        from api.auth.config import jwt_secret
        with mock.patch.dict(os.environ, {"PORTAL_AUTH_DISABLED": "true"}):
            os.environ.pop("PORTAL_AUTH_SECRET", None)
            self.assertTrue(jwt_secret())

    def test_the_algorithm_cannot_be_configured_to_none(self):
        """`none` would make decode() accept UNSIGNED tokens."""
        from api.auth.config import jwt_algorithm
        for attack in ("none", "None", "RS256", "", "garbage"):
            with mock.patch.dict(os.environ, {"PORTAL_AUTH_ALGORITHM": attack}):
                self.assertIn(jwt_algorithm(), {"HS256", "HS384", "HS512"}, attack)


class RoleTests(unittest.TestCase):
    def test_the_ladder_orders_as_documented(self):
        from api.auth.permissions import role_at_least
        self.assertTrue(role_at_least("admin", "user"))
        self.assertTrue(role_at_least("editor", "user"))
        self.assertTrue(role_at_least("user", "user"))
        self.assertFalse(role_at_least("user", "editor"))
        self.assertFalse(role_at_least("editor", "admin"))

    def test_an_unknown_ACTOR_role_is_refused(self):
        from api.auth.permissions import role_at_least
        for junk in ("", "superadmin", "root", "Admin "):
            self.assertFalse(role_at_least(junk, "user"), junk)

    def test_an_unknown_MINIMUM_refuses_everyone(self):
        """It ranked 0, so a misspelled requirement admitted every caller."""
        from api.auth.permissions import role_at_least
        for typo in ("adminn", "administrator", "", "owner"):
            self.assertFalse(role_at_least("user", typo), typo)
            self.assertFalse(role_at_least("admin", typo), typo)

    def test_only_an_admin_can_make_an_admin(self):
        from api.auth.permissions import can_assign_role
        self.assertTrue(can_assign_role("admin", "admin"))
        self.assertTrue(can_assign_role("admin", "editor"))
        self.assertFalse(can_assign_role("editor", "user"))
        self.assertFalse(can_assign_role("user", "user"))

    def test_permissions_accumulate_up_the_ladder(self):
        from api.auth.permissions import permissions_for_role
        self.assertLess(permissions_for_role("user"), permissions_for_role("admin"))
        self.assertIn("settings:manage", permissions_for_role("admin"))
        self.assertNotIn("settings:manage", permissions_for_role("editor"))
        self.assertEqual(permissions_for_role("nonsense"), set())


class HealthDisclosureTests(unittest.TestCase):
    """Audit M3: the client roster was public because the DEFAULT was 'not production'.

    `is_production()` reads ENVIRONMENT, then Railway's and Vercel's own variables, and
    otherwise returns False. ENVIRONMENT appears in no deployment file and is not in
    deploy/api.env.example; the API runs on Render, which sets neither of the other
    two. So the verbose branch was live in production, and `/health` takes no auth.

    The fix is the direction of the default, not another platform name: detail now
    requires AFFIRMATIVE proof of development, so an unrecognised environment is
    treated as production and says nothing.
    """

    def test_an_unknown_environment_is_treated_as_production(self):
        from api.security import is_development
        with mock.patch.dict(os.environ, {}, clear=False):
            for var in ("ENVIRONMENT", "RAILWAY_ENVIRONMENT_NAME", "VERCEL_ENV"):
                os.environ.pop(var, None)
            self.assertFalse(is_development(),
                             "an unrecognised deployment must not be assumed to be dev")

    def test_development_must_say_so(self):
        from api.security import is_development
        for value in ("development", "dev", "local", "test", "DEV"):
            with mock.patch.dict(os.environ, {"ENVIRONMENT": value}):
                self.assertTrue(is_development(), value)

    def test_production_is_never_development(self):
        from api.security import is_development, is_production
        for value in ("production", "prod", "PRODUCTION"):
            with mock.patch.dict(os.environ, {"ENVIRONMENT": value}):
                self.assertTrue(is_production(), value)
                self.assertFalse(is_development(), value)

    def test_platform_production_markers_still_win(self):
        from api.security import is_development, is_production
        for var in ("RAILWAY_ENVIRONMENT_NAME", "VERCEL_ENV"):
            with mock.patch.dict(os.environ, {var: "production"}):
                os.environ.pop("ENVIRONMENT", None)
                self.assertTrue(is_production(), var)
                self.assertFalse(is_development(), var)

    def test_health_says_nothing_when_the_environment_is_unknown(self):
        from fastapi.testclient import TestClient
        with mock.patch.dict(os.environ, {"PORTAL_AUTH_DISABLED": "true",
                                          "PORTAL_DEV_ORGANIZATION": "dev"}):
            for var in ("ENVIRONMENT", "RAILWAY_ENVIRONMENT_NAME", "VERCEL_ENV"):
                os.environ.pop(var, None)
            from api.app import app
            body = TestClient(app).get("/health").json()
        self.assertEqual(body, {"status": "ok"})
        for leaked in ("organizations", "configured_organizations", "dev_organization"):
            self.assertNotIn(leaked, body)

    def test_health_is_still_useful_when_development_is_declared(self):
        from fastapi.testclient import TestClient
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "development",
                                          "PORTAL_AUTH_DISABLED": "true",
                                          "PORTAL_DEV_ORGANIZATION": "dev"}):
            from api.app import app
            body = TestClient(app).get("/health").json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("configured_organizations", body)


class CatalogHelperTests(unittest.TestCase):
    def test_resolve_snapshot_key_tries_every_casing(self):
        from api.snapshot_catalog import resolve_snapshot_key
        snaps = {"rpt_bill": {}, "RPT_GL": {}}
        self.assertEqual(resolve_snapshot_key(snaps, "rpt_bill"), "rpt_bill")
        self.assertEqual(resolve_snapshot_key(snaps, "RPT_BILL"), "rpt_bill")
        self.assertEqual(resolve_snapshot_key(snaps, "rpt_gl"), "RPT_GL")

    def test_an_unknown_key_comes_back_unchanged_so_the_caller_can_error(self):
        from api.snapshot_catalog import resolve_snapshot_key
        self.assertEqual(resolve_snapshot_key({"a": {}}, "nope"), "nope")

    def test_list_snapshots_returns_the_catalog_in_workstream_order(self):
        from api.snapshot_catalog import list_snapshots, load_catalog
        with mock.patch.dict(os.environ, {"PORTAL_DEV_ORGANIZATION": "dev"}):
            snaps = list_snapshots(organization_id=None)
            order = load_catalog(organization_id=None).get("workstream_order", [])
        self.assertTrue(snaps)
        seen = [s["workstream"] for s in snaps if s.get("workstream") in order]
        ranks = [order.index(w) for w in seen]
        self.assertEqual(ranks, sorted(ranks), "snapshots must come back grouped by workstream")


class DemoConfiguredTests(unittest.TestCase):
    def test_no_organization_is_never_configured(self):
        """Fails closed rather than falling back to a global connection (audit H2)."""
        from api.demo_db import demo_configured
        self.assertFalse(demo_configured(None))
        self.assertFalse(demo_configured(""))


class OracleDsnTests(unittest.TestCase):
    def test_strips_the_jdbc_prefixes_a_dba_pastes(self):
        from api.oracle_client import normalize_oracle_dsn
        host = "db.example.com:1521/PDB1"
        for given in (host, f"jdbc:oracle:thin:@//{host}", f"jdbc:oracle:thin:@{host}",
                      f"//{host}", f"  {host}  "):
            self.assertEqual(normalize_oracle_dsn(given), host, given)

    def test_empty_input_is_empty_output(self):
        from api.oracle_client import normalize_oracle_dsn
        self.assertEqual(normalize_oracle_dsn(""), "")
        self.assertEqual(normalize_oracle_dsn(None), "")


class SettingsTokenTests(unittest.TestCase):
    """H1 is fixed: the token is a SECOND FACTOR, never the gate.

    `verify_settings_token` returning True when unset is only safe because
    `_require_data_source_manage` demands the permission unconditionally. Pinned so the
    return value is never promoted back to an authorization decision.
    """

    def test_unset_means_no_second_factor_is_required(self):
        from api.data_source_store import settings_token_required, verify_settings_token
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PORTAL_SETTINGS_TOKEN", None)
            self.assertFalse(settings_token_required())
            self.assertTrue(verify_settings_token(None))

    def test_when_set_it_must_match(self):
        from api.data_source_store import settings_token_required, verify_settings_token
        with mock.patch.dict(os.environ, {"PORTAL_SETTINGS_TOKEN": "s3cret"}):
            self.assertTrue(settings_token_required())
            self.assertTrue(verify_settings_token("s3cret"))
            self.assertTrue(verify_settings_token("  s3cret  "))
            for bad in (None, "", "wrong", "s3cre"):
                self.assertFalse(verify_settings_token(bad), repr(bad))


if __name__ == "__main__":
    unittest.main()
