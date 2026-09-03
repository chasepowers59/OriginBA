"""The Oracle workspace fence must block escape hatches WITHOUT costing query power.

The fence is safe: measured against dictionary views, v$ views, PL/SQL packages,
UTL_HTTP, dblinks, other schemas and the internal build schemas, nothing leaks. But
`_ORACLE_DICTIONARY` matched `all_|dba_|user_|cdb_|v$|gv$` ANYWHERE in the statement,
and two of those prefixes are ordinary CISADM COLUMN names. Measured on Ellensburg:
USER_ID alone is on 378 TABLES, with USER_EDITED_FLG, USER_WHERE_CLAUSE,
USER_EXIT_PGM_NAME, ALL_OPERATORS_SW and four more behind it — 385 tables in total
carried a column this fence rejected:

    SELECT USER_ID FROM CISADM.CI_TD_ENTRY      -> "Data dictionary views are not
    SELECT ALL_DAY_SW FROM CISADM.CI_BILL          queryable from the workspace"

An analyst writing a perfectly ordinary query was told the workspace is fenced against
something they had not done — in the tab that exists so they can use the schema they
already know. That is a capability bug, not a safety one.

WHY POSITION IS THE RIGHT TEST. Oracle can only READ a dictionary view through a table
reference: FROM, JOIN, or a comma in the FROM list — including inside subqueries and
scalar subqueries, which carry their own FROM. There is no path to one from a SELECT
list or a WHERE predicate. So the check belongs on table references.

WHAT STAYS GLOBAL, deliberately:
  * `v$` / `gv$` — `$` does not appear in CISADM column names.
  * `dba_` / `cdb_` — MEASURED on Ellensburg CISADM: zero columns begin with either.
    If one ever turns up at another client, move it into the positional set alongside
    all_/user_ rather than deleting the pattern.
  * PL/SQL packages (`dbms_`, `utl_`, `owa_`, xml/network) — callable straight from a
    SELECT list, so position tells you nothing and the global match is the point.
  * dblinks (`@`) — attach to any table reference, qualified or not.

Only `all_` and `user_`, the two that collide with real column names, become
position-sensitive.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.sql_workspace_validator import (  # noqa: E402
    SqlWorkspaceValidationError,
    validate_oracle_cisadm_scope,
    validate_oracle_reporting_scope,
)

FENCES = (validate_oracle_cisadm_scope, validate_oracle_reporting_scope)


def blocked(fence, sql: str) -> str | None:
    try:
        fence(sql)
        return None
    except SqlWorkspaceValidationError as exc:
        return str(exc)


class CapabilityTests(unittest.TestCase):
    """Ordinary analyst SQL must run. Each of these is a real C2M query shape."""

    LEGITIMATE = {
        "optimizer hint": "SELECT /*+ PARALLEL(b,4) */ b.BILL_ID FROM CISADM.CI_BILL b",
        "index hint": "SELECT /*+ INDEX(b XT001) */ BILL_ID FROM CISADM.CI_BILL b",
        "CTE": "WITH x AS (SELECT ACCT_ID FROM CISADM.CI_BILL) SELECT * FROM x",
        "analytic function": (
            "SELECT ACCT_ID, ROW_NUMBER() OVER (PARTITION BY ACCT_ID ORDER BY BILL_DT) rn "
            "FROM CISADM.CI_BILL"),
        "fetch first": (
            "SELECT BILL_ID FROM CISADM.CI_BILL ORDER BY BILL_DT FETCH FIRST 10 ROWS ONLY"),
        "group by having": (
            "SELECT ACCT_ID, COUNT(*) c FROM CISADM.CI_BILL GROUP BY ACCT_ID HAVING COUNT(*) > 5"),
        "self join": (
            "SELECT a.BILL_ID FROM CISADM.CI_BILL a JOIN CISADM.CI_BILL b "
            "ON a.ACCT_ID = b.ACCT_ID"),
        "case expression": (
            "SELECT CASE WHEN BILL_DT > SYSDATE-30 THEN 'new' ELSE 'old' END FROM CISADM.CI_BILL"),
        # The two the fence used to reject:
        "USER_ID in the select list": "SELECT USER_ID FROM CISADM.CI_TD_ENTRY",
        "USER_ID in a predicate": "SELECT BILL_ID FROM CISADM.CI_BILL WHERE USER_ID = 'X'",
        "ALL_ prefixed column": "SELECT ALL_DAY_SW FROM CISADM.CI_BILL",
        "both, aliased and ordered": (
            "SELECT t.USER_ID, t.ALL_DAY_SW FROM CISADM.CI_BILL t ORDER BY t.USER_ID"),
        "user_ column in an aggregate": (
            "SELECT USER_ID, COUNT(*) FROM CISADM.CI_TD_ENTRY GROUP BY USER_ID"),
    }

    def test_ordinary_analyst_sql_is_not_fenced_out(self):
        for fence in FENCES:
            for name, sql in self.LEGITIMATE.items():
                self.assertIsNone(blocked(fence, sql), f"{fence.__name__}: {name}")


class EscapeHatchTests(unittest.TestCase):
    """Nothing below may become reachable in the course of fixing the above."""

    DANGEROUS = {
        "dictionary view, unqualified": "SELECT * FROM ALL_TABLES",
        "dictionary view, joined": "SELECT * FROM CISADM.CI_BILL b JOIN ALL_USERS u ON 1=1",
        "dictionary view, comma join": "SELECT * FROM CISADM.CI_BILL, ALL_TABLES",
        "dictionary view, subquery": (
            "SELECT BILL_ID FROM CISADM.CI_BILL WHERE 1 IN (SELECT 1 FROM ALL_TABLES)"),
        "dictionary view, scalar subquery": (
            "SELECT (SELECT COUNT(*) FROM ALL_TABLES) FROM CISADM.CI_BILL"),
        "dictionary view in a CTE": (
            "WITH x AS (SELECT * FROM ALL_TABLES) SELECT * FROM x"),
        "user_ dictionary view": "SELECT * FROM USER_TABLES",
        "user_ view joined": "SELECT * FROM CISADM.CI_BILL b JOIN USER_TAB_COLS c ON 1=1",
        "user_ view comma joined": "SELECT * FROM CISADM.CI_BILL, USER_TABLES",
        "dba_ view": "SELECT * FROM DBA_USERS",
        "v$ view": "SELECT * FROM V$SESSION",
        "gv$ view": "SELECT * FROM GV$SESSION",
        "cdb_ view": "SELECT * FROM CDB_USERS",
        "dbms package": "SELECT DBMS_RANDOM.VALUE FROM DUAL",
        "utl_http": "SELECT UTL_HTTP.REQUEST('http://evil') FROM DUAL",
        "xmltype": "SELECT XMLTYPE('<a/>') FROM DUAL",
        "dblink": "SELECT * FROM CISADM.CI_BILL@remote",
        "other schema": "SELECT * FROM SYS.USER$",
        "internal build schema": "SELECT * FROM ORIGINBA_STAGING.STG_BILL",
    }

    def test_every_escape_hatch_stays_shut(self):
        for fence in FENCES:
            for name, sql in self.DANGEROUS.items():
                self.assertIsNotNone(blocked(fence, sql), f"{fence.__name__}: {name} LEAKED")

    def test_a_name_that_only_appears_in_a_comment_is_not_a_read(self):
        """strip_sql_noise removes comments before the check, so a mention cannot
        smuggle a view in — and equally cannot fake one that is not really read."""
        for fence in FENCES:
            self.assertIsNone(
                blocked(fence, "SELECT BILL_ID FROM CISADM.CI_BILL /* not ALL_TABLES */"),
                f"{fence.__name__}: a mention in a comment is not a read")

    def test_secrets_remain_fenced(self):
        for fence in FENCES:
            self.assertIsNotNone(blocked(fence, "SELECT MICR_ID FROM CISADM.CI_PAY_TNDR"))


if __name__ == "__main__":
    unittest.main()
