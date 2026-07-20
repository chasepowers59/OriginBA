import pytest

from api.sql_workspace_validator import (
    SqlWorkspaceValidationError,
    validate_workspace_sql,
    wrap_count_sql,
    wrap_paginated_sql,
)


def test_accepts_select():
    sql = "SELECT * FROM CISADM.FT_RPT_CURR WHERE ROWNUM <= 10"
    assert validate_workspace_sql(sql) == sql


def test_accepts_with_cte():
    sql = "WITH x AS (SELECT 1 n FROM dual) SELECT n FROM x"
    assert validate_workspace_sql(sql) == sql


def test_rejects_delete():
    with pytest.raises(SqlWorkspaceValidationError):
        validate_workspace_sql("DELETE FROM CISADM.FT_RPT_CURR")


def test_rejects_multiple_statements():
    with pytest.raises(SqlWorkspaceValidationError):
        validate_workspace_sql("SELECT 1 FROM dual; SELECT 2 FROM dual")


def test_wrap_paginated():
    wrapped = wrap_paginated_sql("SELECT 1 FROM dual", offset=50, limit=50, probe_extra=1)
    assert "OFFSET 50 ROWS" in wrapped
    assert "FETCH NEXT 51 ROWS ONLY" in wrapped


def test_wrap_count():
    wrapped = wrap_count_sql("SELECT * FROM CISADM.FT_RPT_CURR")
    assert "COUNT(*)" in wrapped
