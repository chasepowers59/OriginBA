"""C2 (2026-09-01): every org fell back to ONE shared warehouse.

`warehouse_url()` ended at the global `WAREHOUSE_DATABASE_URL` and then a hardcoded
default, so `warehouse_configured()` was True for every input — including orgs that
have no Postgres warehouse at all and names that are not orgs. In the shipped
config (render.yaml sets only the global key) that meant an Oracle-backed client's
dashboard could read another tenant's database.

Contract:
  - an ORACLE-backed org never resolves a warehouse (demo_db serves it);
  - a client Postgres org resolves ONLY its own `WAREHOUSE_DATABASE_URL_<ORG>`;
  - the shared/global URL serves the internal `dev` org only;
  - an unknown org resolves nothing;
  - `warehouse_configured()` means it.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import warehouse_db  # noqa: E402

SHARED = "postgresql://shared@host/shared_warehouse"
ELLENSBURG = "postgresql://eb@host/ellensburg"


def _env(**over):
    """Only the warehouse keys — the repo .env must not leak into the assertions."""
    base = {k: v for k, v in os.environ.items() if not k.startswith("WAREHOUSE_DATABASE_URL")}
    base.update(over)
    return mock.patch.dict(os.environ, base, clear=True)


class WarehouseUrlIsolationTests(unittest.TestCase):
    def setUp(self):
        # the .env fallback would otherwise supply the global key
        self._noenv = mock.patch.object(warehouse_db, "ROOT", Path("/nonexistent"))
        self._noenv.start()

    def tearDown(self):
        self._noenv.stop()

    def test_oracle_org_never_resolves_a_warehouse(self):
        with _env(WAREHOUSE_DATABASE_URL=SHARED):
            for org in ("ellensburg", "citycorp", "newark", "demo"):
                with self.subTest(org=org):
                    self.assertIsNone(warehouse_db.warehouse_url(org))
                    self.assertFalse(warehouse_db.warehouse_configured(org))

    def test_unknown_org_resolves_nothing(self):
        with _env(WAREHOUSE_DATABASE_URL=SHARED):
            self.assertIsNone(warehouse_db.warehouse_url("nonexistent_org"))
            self.assertFalse(warehouse_db.warehouse_configured("nonexistent_org"))

    def test_dev_may_use_the_shared_url(self):
        with _env(WAREHOUSE_DATABASE_URL=SHARED):
            self.assertEqual(warehouse_db.warehouse_url("dev"), SHARED)
            self.assertTrue(warehouse_db.warehouse_configured("dev"))

    def test_per_org_url_wins_and_is_required_for_a_client(self):
        # A hypothetical Postgres-backed client: its own key, or nothing.
        with _env(WAREHOUSE_DATABASE_URL=SHARED,
                  WAREHOUSE_DATABASE_URL_ELLENSBURG=ELLENSBURG):
            with mock.patch.object(warehouse_db, "org_backend", return_value=("postgres", "dbt")):
                self.assertEqual(warehouse_db.warehouse_url("ellensburg"), ELLENSBURG)
        with _env(WAREHOUSE_DATABASE_URL=SHARED):
            with mock.patch.object(warehouse_db, "org_backend", return_value=("postgres", "dbt")):
                self.assertIsNone(warehouse_db.warehouse_url("ellensburg"))

    def test_nothing_configured_means_not_configured(self):
        with _env():
            self.assertIsNone(warehouse_db.warehouse_url("dev"))
            self.assertFalse(warehouse_db.warehouse_configured("dev"))

    def test_connecting_without_a_url_raises_rather_than_guessing(self):
        # psycopg2 with dsn=None falls back to libpq env/socket defaults, which is
        # another way to land on the wrong database. It must refuse instead.
        with _env(WAREHOUSE_DATABASE_URL=SHARED):
            with self.assertRaises(RuntimeError):
                warehouse_db._pool("citycorp")

    def test_no_hardcoded_default_url_remains(self):
        self.assertFalse(
            hasattr(warehouse_db, "DEFAULT_URL"),
            "a hardcoded warehouse URL is a cross-client leak waiting to happen",
        )


if __name__ == "__main__":
    unittest.main()
