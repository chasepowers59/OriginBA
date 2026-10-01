"""The data model page names the table where THIS organization's warehouse holds it.

The catalog is shared, and named every table `reporting.rpt_x` (the Postgres shape). For an
in-database organization (Ellensburg, CityCorp) the table is ORIGINBA_REPORTING.RPT_X inside the
client's own C2M Oracle, which is what an analyst would type in the SQL page (2026-10-01)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import snapshot_explorer as se  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402

CTX = AuthContext(id="u", email="u@utility.gov", display_name="u", role="editor", client_id="dev",
                  organization_id="citycorp", organization_name="CityCorp", permissions={"snapshots:read"}, workstreams=["*"])


class TableNameTests(unittest.TestCase):
    def _meta(self, backend):
        snapshot = se.get_snapshot("rpt_payment", "citycorp")
        with mock.patch.object(se, "require_org_for_data", return_value="citycorp"), \
             mock.patch.object(se, "_require_snapshot_access", return_value=snapshot), \
             mock.patch.object(se, "_default_date_filter", return_value=None), \
             mock.patch.object(se, "data_as_of", return_value=None), \
             mock.patch.object(se, "snapshot_backend", return_value=backend):
            return se.snapshot_metadata("rpt_payment", ctx=CTX)["data_model"]["snapshot_table"]

    def test_an_in_database_org_sees_its_oracle_table(self):
        self.assertEqual(self._meta(("oracle", "oracle_dbt", "ORIGINBA_REPORTING")), "ORIGINBA_REPORTING.RPT_PAYMENT")

    def test_a_warehouse_org_sees_its_postgres_table(self):
        self.assertEqual(self._meta(("postgres", "postgres", "reporting")), "reporting.rpt_payment")

    def test_the_shared_catalog_is_not_changed(self):
        self._meta(("oracle", "oracle_dbt", "ORIGINBA_REPORTING"))
        self.assertEqual(se.get_snapshot("rpt_payment", "citycorp")["data_model"]["snapshot_table"], "reporting.rpt_payment")


if __name__ == "__main__":
    unittest.main()
