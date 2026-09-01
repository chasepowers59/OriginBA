"""H2 (2026-09-01): credentials fell back across tenants.

Three fallbacks had the same shape as the warehouse leak (C2): when an org had no
credentials of its own, it silently inherited someone else's.

  1. `data_source_store.load_config(org)` fell through to the vault's `_legacy`
     single-org payload for ANY org — a pre-multi-org migration artifact that, once
     present, answered for every tenant.
  2. `organizations.org_env_connection_config(org)` fell back to the global
     DEMO_DB_USER / DB_USER / ORACLE_USER when the per-org prefix was unset.
  3. `demo_db.env_connection_config(org)` did the same at the driver level.

Contract: a missing per-org credential is an ERROR. Sharing is EXPLICIT — only the
orgs named in the shared-credential allow-list may use the global keys, and the
legacy vault entry belongs to one named org or to nobody.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import data_source_store, demo_db, organizations  # noqa: E402

LEGACY = {"user": "legacy_user", "password": "pw", "dsn": "legacy-host:1521/LEG"}


class VaultLegacyEntryTests(unittest.TestCase):
    def test_legacy_entry_is_not_served_to_an_arbitrary_org(self):
        with mock.patch.object(data_source_store, "_read_vault_orgs",
                               return_value={"_legacy": dict(LEGACY)}):
            for org in ("ellensburg", "citycorp", "newark"):
                with self.subTest(org=org):
                    self.assertIsNone(data_source_store.load_config(org))

    def test_legacy_entry_is_served_only_to_its_declared_owner(self):
        with mock.patch.object(data_source_store, "_read_vault_orgs",
                               return_value={"_legacy": dict(LEGACY)}), \
             mock.patch.dict(os.environ, {"PORTAL_LEGACY_VAULT_ORGANIZATION": "ellensburg"}):
            cfg = data_source_store.load_config("ellensburg")
            self.assertIsNotNone(cfg)
            self.assertIsNone(data_source_store.load_config("citycorp"))

    def test_a_real_per_org_entry_still_wins(self):
        with mock.patch.object(data_source_store, "_read_vault_orgs",
                               return_value={"citycorp": dict(LEGACY), "_legacy": dict(LEGACY)}):
            self.assertIsNotNone(data_source_store.load_config("citycorp"))


class EnvCredentialFallbackTests(unittest.TestCase):
    GLOBALS = {
        "DEMO_DB_USER": "demo_user", "DEMO_DB_PASSWORD": "pw",
        "DEMO_ORACLE_DSN": "demo-host:1521/DEMO",
        "DB_USER": "demo_user", "DB_PASSWORD": "pw",
    }

    def test_client_org_without_its_own_keys_gets_nothing(self):
        # Only the shared/global keys exist here — no CITYCORP_* — so the demo
        # credentials must not stand in for the client's own. `_load_env` is the
        # single seam that reads both the .env file and the process environment.
        with mock.patch.object(organizations, "_load_env", return_value=dict(self.GLOBALS)):
            self.assertIsNone(organizations.org_env_connection_config("citycorp"))

    def test_org_with_its_own_keys_still_resolves(self):
        env = dict(self.GLOBALS)
        env.update({"CITYCORP_DB_USER": "cc_user", "CITYCORP_DB_PASSWORD": "cc_pw",
                    "CITYCORP_ORACLE_DSN": "cc-host:1521/CC"})
        with mock.patch.object(organizations, "_load_env", return_value=env):
            cfg = organizations.org_env_connection_config("citycorp")
            self.assertIsNotNone(cfg)
            self.assertEqual(cfg[0], "cc_user")

    def test_demo_org_may_use_the_shared_keys(self):
        self.assertIn("demo", organizations.SHARED_CREDENTIAL_ORGS)

    def test_driver_level_fallback_is_also_org_scoped(self):
        with mock.patch.object(organizations, "_load_env", return_value=dict(self.GLOBALS)), \
             mock.patch.object(demo_db, "load_env", return_value=dict(self.GLOBALS)):
            with self.assertRaises(RuntimeError):
                demo_db.env_connection_config("citycorp")

    def test_driver_level_still_serves_the_shared_org(self):
        with mock.patch.object(organizations, "_load_env", return_value=dict(self.GLOBALS)), \
             mock.patch.object(demo_db, "load_env", return_value=dict(self.GLOBALS)):
            user, _pw, dsn, _lib, _thick = demo_db.env_connection_config("demo")
            self.assertEqual(user, "demo_user")
            self.assertEqual(dsn, "demo-host:1521/DEMO")


if __name__ == "__main__":
    unittest.main()
