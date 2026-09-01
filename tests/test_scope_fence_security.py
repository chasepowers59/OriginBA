"""Regression tests for the workspace SQL scope fence.

2026-08-31 contract: the SQL workspace is for utility analysts who know CISADM, so
CISADM *is* queryable (alongside the reporting layer). What stays fenced:
  - every other schema (staging/core/internal/dictionary) and quoted qualifiers,
  - Oracle escape hatches (dictionary views, PL/SQL packages, database links),
  - SECRETS: MICR_ID (bank routing), WEB_PASSWD*, ALERT_INFO are never selectable,
    and SELECT * on the tender table (which carries MICR_ID) requires an explicit
    column list instead.
Both the Postgres and the in-database Oracle (oracle_dbt) fences are covered.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.sql_workspace_validator import (  # noqa: E402
    SqlWorkspaceValidationError,
    validate_oracle_reporting_scope,
    validate_reporting_scope,
)


class OracleScopeFenceTests(unittest.TestCase):
    def _blocked(self, sql: str) -> bool:
        try:
            validate_oracle_reporting_scope(sql)
            return False
        except SqlWorkspaceValidationError:
            return True

    def test_allows_cisadm_queries(self):
        # Utility analysts know CISADM; it is the workspace's primary surface.
        self.assertFalse(self._blocked("SELECT acct_id FROM CISADM.CI_ACCT"))
        self.assertFalse(self._blocked(
            "SELECT b.bill_id, s.bseg_id FROM CISADM.CI_BILL b JOIN CISADM.CI_BSEG s ON s.bill_id = b.bill_id"))
        self.assertFalse(self._blocked("SELECT * FROM cisadm.ci_ft WHERE freeze_sw = 'Y'"))

    def test_blocks_quoted_schema_qualifier(self):
        self.assertTrue(self._blocked('SELECT * FROM "CISADM"."CI_ACCT"'))
        self.assertTrue(self._blocked('SELECT * FROM "ORIGINBA_STAGING" . stg_x'))

    def test_blocks_internal_and_unknown_schemas(self):
        self.assertTrue(self._blocked("SELECT * FROM ORIGINBA_STAGING.stg_acct"))
        self.assertTrue(self._blocked("SELECT * FROM originba_core.dim_account"))
        self.assertTrue(self._blocked("SELECT * FROM SOMEONES_SECRETS.pii"))
        self.assertTrue(self._blocked("SELECT * FROM sys.user_history$"))

    def test_blocks_oracle_escape_hatches(self):
        self.assertTrue(self._blocked("SELECT * FROM ALL_TABLES"))
        self.assertTrue(self._blocked("SELECT * FROM rpt_x JOIN dba_users u ON 1=1"))
        self.assertTrue(self._blocked("SELECT dbms_metadata.get_ddl('TABLE','X') FROM dual"))
        self.assertTrue(self._blocked("SELECT * FROM rpt_x@remote_link"))

    def test_blocks_secret_columns(self):
        self.assertTrue(self._blocked("SELECT micr_id FROM CISADM.CI_PAY_TNDR"))
        self.assertTrue(self._blocked("SELECT t.MICR_ID FROM CISADM.CI_PAY_TNDR t"))
        self.assertTrue(self._blocked("SELECT web_passwd FROM CISADM.CI_WEB_USR"))
        self.assertTrue(self._blocked("SELECT alert_info FROM CISADM.CI_ACCT"))

    def test_blocks_select_star_on_tender(self):
        # CI_PAY_TNDR carries MICR_ID; a star select would leak it.
        self.assertTrue(self._blocked("SELECT * FROM CISADM.CI_PAY_TNDR"))
        self.assertTrue(self._blocked("SELECT t.* FROM cisadm.ci_pay_tndr t"))
        # An explicit non-secret column list is fine.
        self.assertFalse(self._blocked(
            "SELECT pay_event_id, tender_amt FROM CISADM.CI_PAY_TNDR"))

    def test_allows_reporting_queries_still(self):
        self.assertFalse(self._blocked('SELECT "Account ID" FROM rpt_financial_txn FETCH FIRST 10 ROWS ONLY'))
        self.assertFalse(self._blocked("SELECT * FROM ORIGINBA_REPORTING.rpt_bill_segment"))
        # a string literal that merely CONTAINS a schema-like token is not code
        self.assertFalse(self._blocked("SELECT * FROM rpt_x WHERE note = 'see sys.notes'"))


class PostgresScopeFenceTests(unittest.TestCase):
    def _blocked(self, sql: str) -> bool:
        try:
            validate_reporting_scope(sql)
            return False
        except SqlWorkspaceValidationError:
            return True

    def test_allows_cisadm_queries(self):
        self.assertFalse(self._blocked("SELECT acct_id FROM cisadm.ci_acct"))
        self.assertFalse(self._blocked(
            "SELECT f.ft_type_flg, sum(f.cur_amt) FROM cisadm.ci_ft f GROUP BY 1"))

    def test_blocks_quoted_and_internal_schemas(self):
        self.assertTrue(self._blocked('SELECT * FROM "cisadm"."ci_acct"'))
        self.assertTrue(self._blocked("SELECT * FROM staging.stg_x"))
        self.assertTrue(self._blocked("SELECT * FROM core.dim_account"))
        self.assertTrue(self._blocked("SELECT * FROM pg_catalog.pg_shadow"))
        self.assertTrue(self._blocked("SELECT * FROM information_schema.tables"))

    def test_blocks_secret_columns(self):
        self.assertTrue(self._blocked("SELECT micr_id FROM cisadm.ci_pay_tndr"))
        self.assertTrue(self._blocked("SELECT web_passwd FROM cisadm.ci_web_usr"))
        self.assertTrue(self._blocked("SELECT alert_info FROM cisadm.ci_acct"))

    def test_blocks_select_star_on_tender(self):
        self.assertTrue(self._blocked("SELECT * FROM cisadm.ci_pay_tndr"))
        self.assertFalse(self._blocked("SELECT pay_event_id, tender_amt FROM cisadm.ci_pay_tndr"))

    def test_allows_reporting(self):
        self.assertFalse(self._blocked("SELECT * FROM reporting.rpt_financial_txn"))
        self.assertFalse(self._blocked('SELECT "Account ID" FROM rpt_bill t WHERE t."Bill ID" > 0'))


class SecretsProjectionTests(unittest.TestCase):
    """C4 (2026-09-01): the secrets guard blocked column NAMES, not whole rows.

    Blocking `micr_id` does nothing if the row itself can be projected as a value,
    and the `SELECT *` rule named only the tender table while `ci_per` carries
    web_passwd and `ci_acct` carries alert_info.
    """

    def _blocked(self, sql: str) -> bool:
        try:
            validate_reporting_scope(sql)
            return False
        except SqlWorkspaceValidationError:
            return True

    def test_blocks_whole_row_projection_of_a_secret_table(self):
        for sql in (
            "SELECT row_to_json(t) FROM cisadm.ci_pay_tndr t",
            "SELECT to_jsonb(t) FROM cisadm.ci_pay_tndr t",
            "SELECT t::text FROM cisadm.ci_pay_tndr t",
            "SELECT CAST(t AS text) FROM cisadm.ci_pay_tndr t",
            "SELECT row_to_json(p) FROM cisadm.ci_per p",
            "SELECT to_jsonb(a) FROM cisadm.ci_acct a",
        ):
            with self.subTest(sql=sql):
                self.assertTrue(self._blocked(sql), sql)

    def test_blocks_select_star_on_every_secret_bearing_table(self):
        for table in ("ci_pay_tndr", "ci_per", "ci_acct", "ci_acct_apay"):
            with self.subTest(table=table):
                self.assertTrue(self._blocked(f"SELECT * FROM cisadm.{table}"))
                self.assertTrue(self._blocked(f"SELECT t.* FROM cisadm.{table} t"))

    def test_still_allows_explicit_columns_on_those_tables(self):
        self.assertFalse(self._blocked(
            "SELECT pay_event_id, tender_amt FROM cisadm.ci_pay_tndr"))
        self.assertFalse(self._blocked("SELECT per_id, per_or_bus_flg FROM cisadm.ci_per"))
        self.assertFalse(self._blocked("SELECT acct_id, cis_division FROM cisadm.ci_acct"))

    def test_row_projection_of_a_harmless_table_is_fine(self):
        # The rule is about tables that carry secrets, not about the functions.
        self.assertFalse(self._blocked("SELECT row_to_json(b) FROM cisadm.ci_bseg b"))
        self.assertFalse(self._blocked("SELECT * FROM cisadm.ci_bseg"))


class LegacyOracleEngineFenceTests(unittest.TestCase):
    """C1 (2026-09-01): the legacy `oracle` engine had NO fence.

    `database_routes._validate` fenced only 'postgres' and 'oracle_dbt', so six of
    eight orgs — every org whose catalog is not 'dbt', with `database:sql` held by
    the lowest role — reached MICR_ID, the data dictionary, other schemas, dblinks
    and UTL_HTTP. These tests pin the ROUTING, not just the validator, because the
    routing is where the hole was.
    """

    def _validate(self, engine: str, sql: str):
        from api.database_routes import _validate

        return _validate(engine, sql)

    def _blocked(self, engine: str, sql: str) -> bool:
        try:
            self._validate(engine, sql)
            return False
        except SqlWorkspaceValidationError:
            return True

    def test_every_engine_applies_a_fence(self):
        # A fenced statement must be refused on EVERY engine the router knows.
        for engine in ("postgres", "oracle", "oracle_dbt"):
            with self.subTest(engine=engine):
                self.assertTrue(
                    self._blocked(engine, "SELECT micr_id FROM cisadm.ci_pay_tndr"))

    def test_legacy_oracle_blocks_the_audited_bypasses(self):
        for sql in (
            "SELECT micr_id FROM cisadm.ci_pay_tndr",
            "SELECT username FROM dba_users",
            "SELECT sid FROM v$session",
            "SELECT * FROM sys.user$",
            "SELECT * FROM cisadm.ci_acct@remote",
            "SELECT utl_http.request('http://x') FROM dual",
            "SELECT * FROM scott.emp",
            'SELECT * FROM "CISADM"."CI_ACCT"',
        ):
            with self.subTest(sql=sql):
                self.assertTrue(self._blocked("oracle", sql), sql)

    def test_legacy_oracle_still_serves_its_own_snapshots(self):
        # The legacy orgs read *_RPT_CURR in CISADM — that must keep working.
        for sql in (
            "SELECT ACCT_ID, CUR_AMT FROM CISADM.FT_RPT_CURR WHERE ROWNUM < 50",
            "SELECT COUNT(*) FROM FT_RPT_CURR",
            "SELECT a.ACCT_ID FROM CISADM.ACCT_CUSTOMER_RPT_CURR a "
            "JOIN CISADM.FT_RPT_CURR f ON f.ACCT_ID = a.ACCT_ID",
        ):
            with self.subTest(sql=sql):
                self.assertEqual(self._validate("oracle", sql), sql.strip())

    def test_legacy_oracle_refuses_a_reporting_schema_it_does_not_have(self):
        # A legacy CISADM org has no ORIGINBA_REPORTING; naming it is a mistake,
        # and allowing it would widen the fence for no reason.
        self.assertTrue(
            self._blocked("oracle", "SELECT * FROM ORIGINBA_REPORTING.RPT_BILL_SEGMENT"))


if __name__ == "__main__":
    unittest.main()
