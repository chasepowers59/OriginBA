"""Settings told a working Postgres org its database was not configured.

`public_status` only ever consulted the ORACLE paths -- the portal vault, then the
DEMO_*/DB_* environment credentials. A dbt/Postgres organization keeps its warehouse in
WAREHOUSE_DATABASE_URL, which nothing here looked at, so the settings page reported
"Not configured / Source: none" for a database that was demonstrably serving the app.

Measured on the `dev` org, three signals at the same moment:

    GET /portal/data-source   configured=False, source="none"
    GET /snapshots            db_configured=True
    POST .../query            returned 3 rows

The snapshots index already carries the fix, with a comment naming this exact
symptom -- "Demo-only here showed warehouse tenants 'Connect database' with a live
warehouse behind them" -- so this is the same bug in a second place that never got the
same change.

The fix has to stay HONEST about which database is configured. Reporting a warehouse
org as `source: "environment"` would claim an Oracle connection it does not have and
would put a masked Oracle DSN on screen for a Postgres tenant. It reports
`source: "warehouse"` with no Oracle credential fields, so the page can say what is
actually true: this tenant reads the dbt warehouse, and there is no Oracle connection
to manage here.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import data_source_store as store  # noqa: E402


class WarehouseOrgStatusTests(unittest.TestCase):
    def _status(self, *, env_configured: bool, warehouse: bool):
        with mock.patch.object(store, "load_config", return_value=None), \
             mock.patch.object(store, "warehouse_configured", return_value=warehouse):
            return store.public_status(organization_id="dev", env_configured=env_configured)

    def test_a_warehouse_org_is_reported_configured(self):
        s = self._status(env_configured=False, warehouse=True)
        self.assertTrue(s["configured"])

    def test_it_names_the_warehouse_rather_than_claiming_an_oracle_connection(self):
        s = self._status(env_configured=False, warehouse=True)
        self.assertEqual(s["source"], "warehouse")

    def test_it_invents_no_oracle_credentials_to_display(self):
        """A masked Oracle DSN on a Postgres tenant's settings page would be fiction."""
        s = self._status(env_configured=False, warehouse=True)
        self.assertIsNone(s["user_masked"])
        self.assertIsNone(s["dsn_masked"])
        self.assertFalse(s["thick_mode"])
        self.assertFalse(s["has_oracle_client_lib_dir"])

    def test_an_org_with_neither_is_still_unconfigured(self):
        s = self._status(env_configured=False, warehouse=False)
        self.assertFalse(s["configured"])
        self.assertEqual(s["source"], "none")

    def test_an_oracle_env_org_is_unchanged(self):
        """The Oracle path keeps precedence and its masked fields."""
        masked = {"user_masked": "CP***", "dsn_masked": "10.1***",
                  "thick_mode": True, "has_oracle_client_lib_dir": True}
        with mock.patch.object(store, "load_config", return_value=None), \
             mock.patch.object(store, "warehouse_configured", return_value=True), \
             mock.patch("api.demo_db.env_connection_config_masked", return_value=masked):
            s = store.public_status(organization_id="citycorp", env_configured=True)
        self.assertEqual(s["source"], "environment")
        self.assertEqual(s["user_masked"], "CP***")


if __name__ == "__main__":
    unittest.main()
