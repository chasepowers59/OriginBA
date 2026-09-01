"""The whole-row guard must block a projection star without blocking COUNT(*).

The C4 guard refuses `SELECT *` against the four secret-bearing tables, because
blocking column NAMES does nothing against a whole-row projection. Its pattern allowed
an opening paren immediately before the star, so `COUNT(*)` matched as though it were a
bare star: the shipped "Accounts by customer class" starter query -- a pure aggregate
over CI_ACCT that returns a code, a label and a count, and no row data at all -- was
refused in the SQL workspace with "SELECT * is not allowed".

A star is a whole-row projection only where a projection can appear: followed by a comma
or by FROM. As a function argument it is followed by `)` and reveals nothing.
"""
from __future__ import annotations

import pytest

from api.sql_workspace_validator import (
    SqlWorkspaceValidationError,
    enforce_secrets,
    strip_sql_noise,
)


def _check(sql: str) -> None:
    """The fence sees comment-stripped SQL, which is what enforce_secrets expects."""
    enforce_secrets(strip_sql_noise(sql))

STARTER = """SELECT a.cust_cl_cd,
       l.descr AS customer_class,
       COUNT(*) AS accounts
FROM cisadm.ci_acct a
LEFT JOIN cisadm.ci_cust_cl_l l
  ON l.cust_cl_cd = a.cust_cl_cd AND l.language_cd = 'ENG'
GROUP BY a.cust_cl_cd, l.descr
ORDER BY accounts DESC"""


@pytest.mark.parametrize(
    "sql",
    [
        STARTER,
        "SELECT COUNT(*) FROM CISADM.CI_ACCT",
        "SELECT COUNT( * ) AS n FROM CISADM.CI_PER",
        "SELECT COUNT(*) OVER () AS n, acct_id FROM CISADM.CI_ACCT",
        # A star on a table that carries no secrets was always fine.
        "SELECT * FROM CISADM.FT_RPT_CURR",
    ],
)
def test_allows_aggregates_and_safe_stars(sql):
    _check(sql)  # must not raise


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM CISADM.CI_ACCT",
        "SELECT * FROM CISADM.CI_PAY_TNDR",
        "SELECT a.* FROM CISADM.CI_PER a",
        "SELECT *, 1 FROM CISADM.CI_ACCT_APAY",
        "SELECT COUNT(*), a.* FROM CISADM.CI_ACCT a",
    ],
)
def test_still_blocks_a_whole_row_projection(sql):
    with pytest.raises(SqlWorkspaceValidationError):
        _check(sql)
