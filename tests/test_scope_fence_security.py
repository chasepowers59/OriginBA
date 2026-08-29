"""Regression tests for the workspace SQL scope fence.

These lock in the 2026-08-28 security fix: an authenticated database:sql user must
not be able to escape the reporting layer to reach CISADM (PII, MICR bank routing)
via quoted schema qualifiers or comment obfuscation. Both the Postgres and the
in-database Oracle (oracle_dbt) fences are covered.
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

    def test_blocks_quoted_schema_qualifier(self):
        # the confirmed bypass: quotes between the schema name and the dot
        self.assertTrue(self._blocked('SELECT * FROM "CISADM"."CI_ACCT"'))
        self.assertTrue(self._blocked('SELECT * FROM "CISADM" . CI_ACCT'))

    def test_blocks_comment_obfuscated_qualifier(self):
        self.assertTrue(self._blocked("SELECT * FROM CISADM/**/.CI_ACCT"))
        self.assertTrue(self._blocked("SELECT * FROM CISADM.CI_PAY_TNDR -- micr\n"))

    def test_blocks_bare_and_unknown_schemas(self):
        self.assertTrue(self._blocked("SELECT * FROM cisadm.ci_pay_tndr"))
        # positive allow-list: an UNKNOWN schema in FROM position is rejected too
        self.assertTrue(self._blocked("SELECT * FROM SOMEONES_SECRETS.pii"))

    def test_blocks_oracle_escape_hatches(self):
        self.assertTrue(self._blocked("SELECT * FROM ALL_TABLES"))
        self.assertTrue(self._blocked("SELECT * FROM rpt_x JOIN dba_users u ON 1=1"))
        self.assertTrue(self._blocked("SELECT dbms_metadata.get_ddl('TABLE','X') FROM dual"))
        self.assertTrue(self._blocked("SELECT * FROM rpt_x@remote_link"))

    def test_allows_legitimate_reporting_queries(self):
        self.assertFalse(self._blocked('SELECT "Account ID" FROM rpt_financial_txn FETCH FIRST 10 ROWS ONLY'))
        self.assertFalse(self._blocked('SELECT t."FT ID", t."Current Amount" FROM rpt_financial_txn t'))
        self.assertFalse(self._blocked("SELECT * FROM ORIGINBA_REPORTING.rpt_bill_segment"))
        self.assertFalse(self._blocked('SELECT a."Bill ID" FROM rpt_financial_txn a JOIN rpt_bill b ON a."Bill ID" = b."Bill ID"'))
        # a string literal that merely CONTAINS a schema-like token is not code
        self.assertFalse(self._blocked("SELECT * FROM rpt_x WHERE note = 'see cisadm.notes'"))


class PostgresScopeFenceTests(unittest.TestCase):
    def _blocked(self, sql: str) -> bool:
        try:
            validate_reporting_scope(sql)
            return False
        except SqlWorkspaceValidationError:
            return True

    def test_blocks_quoted_and_comment_bypass(self):
        self.assertTrue(self._blocked('SELECT * FROM "cisadm"."ci_acct"'))
        self.assertTrue(self._blocked("SELECT * FROM staging/**/.stg_x"))
        self.assertTrue(self._blocked("SELECT * FROM cisadm.ci_acct"))

    def test_allows_reporting(self):
        self.assertFalse(self._blocked("SELECT * FROM reporting.rpt_financial_txn"))
        self.assertFalse(self._blocked('SELECT "Account ID" FROM rpt_bill t WHERE t."Bill ID" > 0'))


if __name__ == "__main__":
    unittest.main()
