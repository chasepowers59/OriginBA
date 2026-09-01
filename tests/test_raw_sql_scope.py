"""H3 (2026-09-01): snapshot-scoped raw SQL was scoped by SUBSTRING PRESENCE.

`validate_raw_sql` only required the allowed table's name to APPEAR somewhere in the
text — a comment mentioning it was enough — and applied no secrets guard and no
Oracle escape-hatch fence. Executed by the audit with allowed_table=FT_RPT_CURR, all
of these were accepted:

    SELECT MICR_ID FROM CISADM.CI_PAY_TNDR WHERE 1=(SELECT 1 FROM CISADM.FT_RPT_CURR ...)
    SELECT ... UNION ALL SELECT '' FROM CISADM.FT_RPT_CURR
    SELECT username FROM DBA_USERS WHERE 1=(... FT_RPT_CURR ...)
    SELECT * FROM CISADM.FT_RPT_CURR@evil

Contract: every table the statement reads must be the allowed one; the Oracle escape
hatches and the secrets guard apply here exactly as they do in the SQL workspace.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.raw_sql_validator import RawSqlValidationError, validate_raw_sql  # noqa: E402

TABLE = "FT_RPT_CURR"


class RawSqlScopeTests(unittest.TestCase):
    def _blocked(self, sql: str) -> bool:
        try:
            validate_raw_sql(sql, TABLE)
            return False
        except RawSqlValidationError:
            return True

    def test_blocks_reading_another_table_via_a_subquery(self):
        self.assertTrue(self._blocked(
            "SELECT MICR_ID FROM CISADM.CI_PAY_TNDR WHERE 1=("
            "SELECT 1 FROM CISADM.FT_RPT_CURR WHERE ROWNUM=1)"))

    def test_blocks_union_to_another_table(self):
        self.assertTrue(self._blocked(
            "SELECT ACCT_ID FROM CISADM.CI_ACCT UNION ALL "
            "SELECT ACCT_ID FROM CISADM.FT_RPT_CURR"))

    def test_blocks_the_dictionary_even_when_the_table_is_mentioned(self):
        self.assertTrue(self._blocked(
            "SELECT username FROM DBA_USERS WHERE 1=("
            "SELECT 1 FROM CISADM.FT_RPT_CURR WHERE ROWNUM=1)"))

    def test_blocks_a_database_link(self):
        self.assertTrue(self._blocked("SELECT * FROM CISADM.FT_RPT_CURR@evil"))

    def test_a_comment_naming_the_table_is_not_enough(self):
        self.assertTrue(self._blocked(
            "SELECT * FROM CISADM.CI_ACCT -- CISADM.FT_RPT_CURR"))
        self.assertTrue(self._blocked(
            "SELECT * FROM CISADM.CI_ACCT /* CISADM.FT_RPT_CURR */"))

    def test_blocks_protected_columns(self):
        self.assertTrue(self._blocked("SELECT MICR_ID FROM CISADM.FT_RPT_CURR"))
        self.assertTrue(self._blocked("SELECT ALERT_INFO FROM CISADM.FT_RPT_CURR"))

    def test_allows_a_genuine_query_on_the_allowed_table(self):
        for sql in (
            "SELECT ACCT_ID, CUR_AMT FROM CISADM.FT_RPT_CURR WHERE ROWNUM < 50",
            "SELECT COUNT(*) FROM CISADM.FT_RPT_CURR",
            "select acct_id from cisadm.ft_rpt_curr where cur_amt > 0",
            "SELECT f.ACCT_ID FROM CISADM.FT_RPT_CURR f WHERE f.CUR_AMT > 0",
        ):
            with self.subTest(sql=sql):
                self.assertFalse(self._blocked(sql), sql)

    def test_still_rejects_the_basics(self):
        self.assertTrue(self._blocked("DELETE FROM CISADM.FT_RPT_CURR"))
        self.assertTrue(self._blocked(
            "SELECT * FROM CISADM.FT_RPT_CURR; SELECT * FROM CISADM.CI_ACCT"))
        self.assertTrue(self._blocked("SELECT 1 FROM DUAL"))


if __name__ == "__main__":
    unittest.main()
