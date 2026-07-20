import pytest

from api.raw_sql_validator import RawSqlValidationError, apply_row_cap, validate_raw_sql


def test_accepts_select_on_snapshot_table():
    sql = "SELECT bseg_id, total_calc_amt FROM CISADM.BSEG_BILLED_USAGE_RPT_CURR WHERE ROWNUM <= 10"
    assert validate_raw_sql(sql, "BSEG_BILLED_USAGE_RPT_CURR") == sql


def test_rejects_delete():
    with pytest.raises(RawSqlValidationError):
        validate_raw_sql("DELETE FROM CISADM.FT_RPT_CURR", "FT_RPT_CURR")


def test_rejects_wrong_table():
    with pytest.raises(RawSqlValidationError):
        validate_raw_sql("SELECT * FROM CISADM.FT_RPT_CURR", "BSEG_BILLED_USAGE_RPT_CURR")


def test_apply_row_cap_wraps_query():
    capped = apply_row_cap("SELECT * FROM CISADM.FT_RPT_CURR", 25)
    assert "ROWNUM <= 25" in capped
