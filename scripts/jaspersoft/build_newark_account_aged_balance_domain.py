#!/usr/bin/env python3
"""Build Newark Account Aged Balance domain import (REP8 LPC parity)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO / "domains/manual_imports/newark_account_aged_balance"
DOMAIN_NAME = "Newark_Account_Aged_Balance___Domain"
JOIN_TREE_ID = "JoinTree_1"
DS_ID = "Newark1_DS"
DS_URI = "/DataSource/Newark1_DS"
FOLDER = "/SmartCity/Report/Workstreams/Debt_Management"

NEWARK_PREM_CHARS_SQL = """SELECT
  prem_id,
  MAX(CASE WHEN char_type_cd = 'LOT' THEN TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), ''))) END) AS lot,
  MAX(CASE WHEN char_type_cd = 'LOTSUFF' THEN TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), ''))) END) AS lotsuff,
  MAX(CASE WHEN char_type_cd = 'BLOCK' THEN TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), ''))) END) AS block,
  MAX(CASE WHEN char_type_cd = 'BLOCKSUF' THEN TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), ''))) END) AS blocksuf,
  MAX(CASE WHEN char_type_cd = 'BLCK/LOT' THEN TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), ''))) END) AS block_lot,
  MAX(CASE WHEN char_type_cd = 'CMC-QLFR' THEN TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), ''))) END) AS qlfr,
  MAX(CASE WHEN char_type_cd = 'WARD' THEN TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), ''))) END) AS ward
FROM cisadm.ci_prem_char
WHERE char_type_cd IN ('LOT', 'LOTSUFF', 'BLOCK', 'BLOCKSUF', 'BLCK/LOT', 'CMC-QLFR', 'WARD')
GROUP BY prem_id"""

NEWARK_ACCT_SVC_PREM_SQL = """SELECT acct_id, MIN(prem_id) AS prem_id
FROM (
  SELECT DISTINCT sa.acct_id, sp.prem_id
  FROM cisadm.ci_sa sa
  JOIN cisadm.ci_sa_sp sasp ON sasp.sa_id = sa.sa_id AND sasp.stop_dttm IS NULL
  JOIN cisadm.ci_sp sp ON sp.sp_id = sasp.sp_id
  WHERE sp.prem_id IS NOT NULL
)
GROUP BY acct_id"""

NEWARK_ACCT_MAIN_PER_SQL = """SELECT acct_id, MIN(per_id) AS per_id
FROM cisadm.ci_acct_per
GROUP BY acct_id"""

NEWARK_LATEST_PAY_SQL = """SELECT p.acct_id, MAX(pe.pay_dt) AS latest_pay_dt
FROM cisadm.ci_pay p
JOIN cisadm.ci_pay_event pe ON p.pay_event_id = pe.pay_event_id
WHERE p.pay_status_flg = '50'
GROUP BY p.acct_id"""

NEWARK_PA_FLAG_SQL = """SELECT sa.acct_id,
  CASE WHEN COUNT(*) > 0 THEN 'Y' ELSE 'N' END AS pa_flag
FROM cisadm.ci_sa sa
WHERE sa.sa_type_cd = 'PA' AND sa.sa_status_flg = '20'
GROUP BY sa.acct_id"""

NEWARK_REP8_BUCKETS_SQL = """SELECT
  rc.acct_id,
  rpt.rpt_dt,
  SUM(CASE WHEN rc.ars_dt <= rpt.rpt_dt THEN rc.cur_amt ELSE 0 END) AS current_bal,
  SUM(CASE WHEN rc.cur_amt > 0 AND rc.ars_dt BETWEEN rpt.rpt_dt - 30 AND rpt.rpt_dt THEN rc.cur_amt ELSE 0 END)
    + LEAST(SUM(CASE WHEN (rc.cur_amt > 0 AND rc.ars_dt < rpt.rpt_dt - 30) OR rc.cur_amt < 0 THEN rc.cur_amt ELSE 0 END), 0) AS new_charges,
  GREATEST(
    SUM(CASE WHEN rc.cur_amt > 0 AND rc.ars_dt BETWEEN rpt.rpt_dt - 60 AND rpt.rpt_dt - 31 AND rc.parent_id NOT IN ('LPC') THEN rc.cur_amt ELSE 0 END)
    + LEAST(SUM(CASE WHEN (rc.cur_amt > 0 AND rc.ars_dt < rpt.rpt_dt - 60) OR rc.cur_amt < 0 THEN rc.cur_amt ELSE 0 END), 0),
    0) AS arrears_30_principal,
  GREATEST(SUM(CASE WHEN rc.ars_dt BETWEEN rpt.rpt_dt - 60 AND rpt.rpt_dt - 31 AND rc.parent_id IN ('LPC') THEN rc.cur_amt ELSE 0 END), 0) AS arrears_30_interest,
  GREATEST(
    SUM(CASE WHEN rc.cur_amt > 0 AND rc.ars_dt BETWEEN rpt.rpt_dt - 90 AND rpt.rpt_dt - 61 AND rc.parent_id NOT IN ('LPC') THEN rc.cur_amt ELSE 0 END)
    + LEAST(SUM(CASE WHEN (rc.cur_amt > 0 AND rc.ars_dt < rpt.rpt_dt - 90) OR rc.cur_amt < 0 THEN rc.cur_amt ELSE 0 END), 0),
    0) AS arrears_60_principal,
  GREATEST(SUM(CASE WHEN rc.ars_dt BETWEEN rpt.rpt_dt - 90 AND rpt.rpt_dt - 61 AND rc.parent_id IN ('LPC') THEN rc.cur_amt ELSE 0 END), 0) AS arrears_60_interest,
  GREATEST(SUM(CASE WHEN
    (rc.cur_amt > 0 AND (rc.ars_dt < rpt.rpt_dt - 120 OR (rc.parent_id NOT IN ('LPC') AND rc.ars_dt BETWEEN rpt.rpt_dt - 120 AND rpt.rpt_dt - 91)))
    OR rc.cur_amt < 0
    THEN rc.cur_amt ELSE 0 END), 0) AS arrears_90_principal,
  GREATEST(SUM(CASE WHEN rc.ars_dt BETWEEN rpt.rpt_dt - 120 AND rpt.rpt_dt - 91 AND rc.parent_id IN ('LPC') THEN rc.cur_amt ELSE 0 END), 0) AS arrears_90_interest,
  GREATEST(SUM(CASE WHEN (rc.cur_amt > 0 AND rc.ars_dt < rpt.rpt_dt - 31) OR rc.cur_amt < 0 THEN rc.cur_amt ELSE 0 END), 0) AS arrears_total
FROM (
  SELECT
    sa.acct_id,
    ft.cur_amt,
    TRUNC(ft.ars_dt) AS ars_dt,
    NVL(ft.parent_id, ' ') AS parent_id
  FROM cisadm.ci_ft ft
  JOIN cisadm.ci_sa sa ON sa.sa_id = ft.sa_id
  WHERE ft.freeze_sw = 'Y'
    AND ft.not_in_ars_sw = 'N'
    AND ft.ars_dt IS NOT NULL
    AND ft.ft_type_flg NOT IN ('PS', 'PX')
) rc
CROSS JOIN (
  SELECT TRUNC(SYSDATE) AS rpt_dt FROM dual
) rpt
GROUP BY rc.acct_id, rpt.rpt_dt"""


def xml_escape_text(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def derived_sql(sql: str) -> str:
    return f"SELECT * FROM (\n{sql.strip()}\n) X"


def field_lines(fields: list[tuple[str, str]], *, expr: dict[str, str] | None = None) -> str:
    expr = expr or {}
    lines: list[str] = []
    for fid, ftype in fields:
        if fid in expr:
            lines.append(
                f'        <field id="{fid}" dataSetExpression="{expr[fid]}" type="{ftype}"></field>'
            )
        else:
            lines.append(f'        <field id="{fid}" type="{ftype}"></field>')
    return "\n".join(lines)


def jdbc_query_block(qid: str, fields: list[tuple[str, str]], sql: str) -> str:
    return (
        f'    <jdbcQuery id="{qid}" datasourceId="{DS_ID}">\n'
        f"      <fieldList>\n"
        f"{field_lines(fields)}\n"
        f"      </fieldList>\n"
        f"      <query>{xml_escape_text(derived_sql(sql))}</query>\n"
        f"    </jdbcQuery>"
    )


def jdbc_table_block(
    tid: str,
    table_name: str,
    fields: list[tuple[str, str]],
) -> str:
    return (
        f'    <jdbcTable id="{tid}" datasourceId="{DS_ID}" datasourceTableName="{table_name}" schemaAlias="CISADM">\n'
        f"      <fieldList>\n"
        f"{field_lines(fields)}\n"
        f"      </fieldList>\n"
        f"    </jdbcTable>"
    )


def join_line(expr: str, left: str, right: str, join_type: str = "leftOuter") -> str:
    return (
        f'        <join expr="{expr}" left="{left}" right="{right}" '
        f'type="{join_type}" weight="1"></join>'
    )


def table_ref_line(alias: str, table_id: str) -> str:
    return (
        f'        <tableRef alwaysIncludeTable="false" tableAlias="{alias}" '
        f'tableId="{table_id}"></tableRef>'
    )


def build_schema_text() -> str:
    scalar_fields = [
        ("NEWARK_REP8_BUCKETS.ACCT_ID", "java.lang.String"),
        ("NEWARK_REP8_BUCKETS.RPT_DT", "java.sql.Timestamp"),
        ("NEWARK_REP8_BUCKETS.CURRENT_BAL", "java.math.BigDecimal"),
        ("NEWARK_REP8_BUCKETS.NEW_CHARGES", "java.math.BigDecimal"),
        ("NEWARK_REP8_BUCKETS.ARREARS_30_PRINCIPAL", "java.math.BigDecimal"),
        ("NEWARK_REP8_BUCKETS.ARREARS_30_INTEREST", "java.math.BigDecimal"),
        ("NEWARK_REP8_BUCKETS.ARREARS_60_PRINCIPAL", "java.math.BigDecimal"),
        ("NEWARK_REP8_BUCKETS.ARREARS_60_INTEREST", "java.math.BigDecimal"),
        ("NEWARK_REP8_BUCKETS.ARREARS_90_PRINCIPAL", "java.math.BigDecimal"),
        ("NEWARK_REP8_BUCKETS.ARREARS_90_INTEREST", "java.math.BigDecimal"),
        ("NEWARK_REP8_BUCKETS.ARREARS_TOTAL", "java.math.BigDecimal"),
        ("NEWARK_PREM_CHARS.LOT", "java.lang.String"),
        ("NEWARK_PREM_CHARS.LOTSUFF", "java.lang.String"),
        ("NEWARK_PREM_CHARS.BLOCK", "java.lang.String"),
        ("NEWARK_PREM_CHARS.BLOCKSUF", "java.lang.String"),
        ("NEWARK_PREM_CHARS.BLOCK_LOT", "java.lang.String"),
        ("NEWARK_PREM_CHARS.QLFR", "java.lang.String"),
        ("NEWARK_PREM_CHARS.WARD", "java.lang.String"),
        ("CI_ACCT_REP8.COLL_CL_CD", "java.lang.String"),
        ("CI_ACCT_REP8.BILL_CYC_CD", "java.lang.String"),
        ("CI_ACCT_REP8.MAILING_PREM_ID", "java.lang.String"),
        ("CI_PREM_SVC.ADDRESS1", "java.lang.String"),
        ("CI_PREM_SVC.ADDRESS2", "java.lang.String"),
        ("CI_PREM_SVC.POSTAL", "java.lang.String"),
        ("CI_PREM_MAIL.ADDRESS1", "java.lang.String"),
        ("CI_PREM_MAIL.CITY", "java.lang.String"),
        ("CI_PREM_MAIL.STATE", "java.lang.String"),
        ("CI_PREM_MAIL.POSTAL", "java.lang.String"),
        ("CI_PER_NAME_REP8.ENTITY_NAME", "java.lang.String"),
        ("CI_PER_PHONE.PHONE", "java.lang.String"),
        ("NEWARK_LATEST_PAY.LATEST_PAY_DT", "java.sql.Timestamp"),
        ("NEWARK_PA_FLAG.PA_FLAG", "java.lang.String"),
    ]
    calc_exprs = {
        "REP8_ARREARS_30": "NEWARK_REP8_BUCKETS.ARREARS_30_PRINCIPAL + NEWARK_REP8_BUCKETS.ARREARS_30_INTEREST",
        "REP8_ARREARS_60": "NEWARK_REP8_BUCKETS.ARREARS_60_PRINCIPAL + NEWARK_REP8_BUCKETS.ARREARS_60_INTEREST",
        "REP8_ARREARS_90": "NEWARK_REP8_BUCKETS.ARREARS_90_PRINCIPAL + NEWARK_REP8_BUCKETS.ARREARS_90_INTEREST",
    }
    calc_fields = [
        ("REP8_ARREARS_30", "java.math.BigDecimal"),
        ("REP8_ARREARS_60", "java.math.BigDecimal"),
        ("REP8_ARREARS_90", "java.math.BigDecimal"),
    ]

    exposed = [
        ("REP8_REPORT_DATE", "Report Date (As-Of)", f"{JOIN_TREE_ID}.NEWARK_REP8_BUCKETS.RPT_DT"),
        ("REP8_ACCOUNT", "Account", f"{JOIN_TREE_ID}.NEWARK_REP8_BUCKETS.ACCT_ID"),
        ("REP8_BLOCK_LOT", "Block Lot", f"{JOIN_TREE_ID}.NEWARK_PREM_CHARS.BLOCK_LOT"),
        ("REP8_BLOCK", "Block", f"{JOIN_TREE_ID}.NEWARK_PREM_CHARS.BLOCK"),
        ("REP8_BLOCKSUF", "Block Suffix", f"{JOIN_TREE_ID}.NEWARK_PREM_CHARS.BLOCKSUF"),
        ("REP8_LOT", "Lot", f"{JOIN_TREE_ID}.NEWARK_PREM_CHARS.LOT"),
        ("REP8_LOTSUFF", "Lot Suffix", f"{JOIN_TREE_ID}.NEWARK_PREM_CHARS.LOTSUFF"),
        ("REP8_QLFR", "Qualifier", f"{JOIN_TREE_ID}.NEWARK_PREM_CHARS.QLFR"),
        ("REP8_WARD", "Ward", f"{JOIN_TREE_ID}.NEWARK_PREM_CHARS.WARD"),
        ("REP8_STATUS", "Status (Collection Class)", f"{JOIN_TREE_ID}.CI_ACCT_REP8.COLL_CL_CD"),
        ("REP8_CYCLE", "Bill Cycle", f"{JOIN_TREE_ID}.CI_ACCT_REP8.BILL_CYC_CD"),
        ("REP8_PROPERTY_DESCR", "Property Description", f"{JOIN_TREE_ID}.CI_PREM_SVC.ADDRESS2"),
        ("REP8_SERVICE_LOCATION", "Service Location Name", f"{JOIN_TREE_ID}.CI_PREM_SVC.ADDRESS1"),
        ("REP8_STREET_NAME", "Street Name", f"{JOIN_TREE_ID}.CI_PREM_SVC.ADDRESS1"),
        ("REP8_SERVICE_ADDRESS", "Service Address", f"{JOIN_TREE_ID}.CI_PREM_SVC.ADDRESS1"),
        ("REP8_SERVICE_ZIP", "Service Zip", f"{JOIN_TREE_ID}.CI_PREM_SVC.POSTAL"),
        ("REP8_BILLING_NAME", "Billing Name", f"{JOIN_TREE_ID}.CI_PER_NAME_REP8.ENTITY_NAME"),
        ("REP8_BILLING_ADDRESS", "Billing Address", f"{JOIN_TREE_ID}.CI_PREM_MAIL.ADDRESS1"),
        ("REP8_CITY_STATE", "Billing City", f"{JOIN_TREE_ID}.CI_PREM_MAIL.CITY"),
        ("REP8_ZIP_CODE", "Billing Zip", f"{JOIN_TREE_ID}.CI_PREM_MAIL.POSTAL"),
        ("REP8_BILLING_PHONE", "Billing Phone", f"{JOIN_TREE_ID}.CI_PER_PHONE.PHONE"),
        ("REP8_CURRENT_BAL", "Current Balance", f"{JOIN_TREE_ID}.NEWARK_REP8_BUCKETS.CURRENT_BAL"),
        ("REP8_NEW_CHARGES", "New Charges", f"{JOIN_TREE_ID}.NEWARK_REP8_BUCKETS.NEW_CHARGES"),
        ("REP8_ARREARS_30_PRINCIPAL", "Arrears 30 Principal", f"{JOIN_TREE_ID}.NEWARK_REP8_BUCKETS.ARREARS_30_PRINCIPAL"),
        ("REP8_ARREARS_30_INTEREST", "Arrears 30 Interest (LPC)", f"{JOIN_TREE_ID}.NEWARK_REP8_BUCKETS.ARREARS_30_INTEREST"),
        ("REP8_ARREARS_30", "Arrears 30 Total", f"{JOIN_TREE_ID}.REP8_ARREARS_30"),
        ("REP8_ARREARS_60_PRINCIPAL", "Arrears 60 Principal", f"{JOIN_TREE_ID}.NEWARK_REP8_BUCKETS.ARREARS_60_PRINCIPAL"),
        ("REP8_ARREARS_60_INTEREST", "Arrears 60 Interest (LPC)", f"{JOIN_TREE_ID}.NEWARK_REP8_BUCKETS.ARREARS_60_INTEREST"),
        ("REP8_ARREARS_60", "Arrears 60 Total", f"{JOIN_TREE_ID}.REP8_ARREARS_60"),
        ("REP8_ARREARS_90_PRINCIPAL", "Arrears 90 Principal", f"{JOIN_TREE_ID}.NEWARK_REP8_BUCKETS.ARREARS_90_PRINCIPAL"),
        ("REP8_ARREARS_90_INTEREST", "Arrears 90 Interest (LPC)", f"{JOIN_TREE_ID}.NEWARK_REP8_BUCKETS.ARREARS_90_INTEREST"),
        ("REP8_ARREARS_90", "Arrears 90 Total", f"{JOIN_TREE_ID}.REP8_ARREARS_90"),
        ("REP8_ARREARS_TOTAL", "Arrears Total", f"{JOIN_TREE_ID}.NEWARK_REP8_BUCKETS.ARREARS_TOTAL"),
        ("REP8_LATEST_PAY_DT", "Latest Payment Date", f"{JOIN_TREE_ID}.NEWARK_LATEST_PAY.LATEST_PAY_DT"),
        ("REP8_PA_FLAG", "Payment Arrangement Flag", f"{JOIN_TREE_ID}.NEWARK_PA_FLAG.PA_FLAG"),
    ]
    item_lines = "\n".join(
        f'        <item id="{iid}" label="{label}" resourceId="{rid}"></item>' for iid, label, rid in exposed
    )

    resources = [
        jdbc_query_block(
            "NEWARK_REP8_BUCKETS",
            [
                ("ACCT_ID", "java.lang.String"),
                ("RPT_DT", "java.sql.Timestamp"),
                ("CURRENT_BAL", "java.math.BigDecimal"),
                ("NEW_CHARGES", "java.math.BigDecimal"),
                ("ARREARS_30_PRINCIPAL", "java.math.BigDecimal"),
                ("ARREARS_30_INTEREST", "java.math.BigDecimal"),
                ("ARREARS_60_PRINCIPAL", "java.math.BigDecimal"),
                ("ARREARS_60_INTEREST", "java.math.BigDecimal"),
                ("ARREARS_90_PRINCIPAL", "java.math.BigDecimal"),
                ("ARREARS_90_INTEREST", "java.math.BigDecimal"),
                ("ARREARS_TOTAL", "java.math.BigDecimal"),
            ],
            NEWARK_REP8_BUCKETS_SQL,
        ),
        jdbc_query_block(
            "NEWARK_PREM_CHARS",
            [
                ("PREM_ID", "java.lang.String"),
                ("LOT", "java.lang.String"),
                ("LOTSUFF", "java.lang.String"),
                ("BLOCK", "java.lang.String"),
                ("BLOCKSUF", "java.lang.String"),
                ("BLOCK_LOT", "java.lang.String"),
                ("QLFR", "java.lang.String"),
                ("WARD", "java.lang.String"),
            ],
            NEWARK_PREM_CHARS_SQL,
        ),
        jdbc_query_block(
            "NEWARK_ACCT_SVC_PREM",
            [("ACCT_ID", "java.lang.String"), ("PREM_ID", "java.lang.String")],
            NEWARK_ACCT_SVC_PREM_SQL,
        ),
        jdbc_query_block(
            "NEWARK_ACCT_MAIN_PER",
            [("ACCT_ID", "java.lang.String"), ("PER_ID", "java.lang.String")],
            NEWARK_ACCT_MAIN_PER_SQL,
        ),
        jdbc_query_block(
            "NEWARK_LATEST_PAY",
            [("ACCT_ID", "java.lang.String"), ("LATEST_PAY_DT", "java.sql.Timestamp")],
            NEWARK_LATEST_PAY_SQL,
        ),
        jdbc_query_block(
            "NEWARK_PA_FLAG",
            [("ACCT_ID", "java.lang.String"), ("PA_FLAG", "java.lang.String")],
            NEWARK_PA_FLAG_SQL,
        ),
        jdbc_table_block(
            "CI_ACCT_REP8",
            "CI_ACCT",
            [
                ("ACCT_ID", "java.lang.String"),
                ("COLL_CL_CD", "java.lang.String"),
                ("BILL_CYC_CD", "java.lang.String"),
                ("MAILING_PREM_ID", "java.lang.String"),
            ],
        ),
        jdbc_table_block(
            "CI_PREM_SVC",
            "CI_PREM",
            [("PREM_ID", "java.lang.String"), ("ADDRESS1", "java.lang.String"), ("ADDRESS2", "java.lang.String"), ("POSTAL", "java.lang.String")],
        ),
        jdbc_table_block(
            "CI_PREM_MAIL",
            "CI_PREM",
            [
                ("PREM_ID", "java.lang.String"),
                ("ADDRESS1", "java.lang.String"),
                ("CITY", "java.lang.String"),
                ("STATE", "java.lang.String"),
                ("POSTAL", "java.lang.String"),
            ],
        ),
        jdbc_table_block(
            "CI_PER_NAME_REP8",
            "CI_PER_NAME",
            [("PER_ID", "java.lang.String"), ("ENTITY_NAME", "java.lang.String")],
        ),
        jdbc_table_block(
            "CI_PER_PHONE",
            "CI_PER_PHONE",
            [("PER_ID", "java.lang.String"), ("PHONE", "java.lang.String")],
        ),
        (
            f'    <jdbcTable id="{JOIN_TREE_ID}" datasourceId="{DS_ID}" datasourceTableName="CI_ACCT" schemaAlias="CISADM">\n'
            f"      <fieldList>\n"
            f"{field_lines(scalar_fields)}\n"
            f"{field_lines(calc_fields, expr=calc_exprs)}\n"
            f"      </fieldList>\n"
            f'      <joinInfo alias="CI_ACCT_REP8" referenceId="CI_ACCT_REP8"></joinInfo>\n'
            f"      <joinList>\n"
            f'{join_line("CI_ACCT_REP8.ACCT_ID == NEWARK_REP8_BUCKETS.ACCT_ID", "CI_ACCT_REP8", "NEWARK_REP8_BUCKETS", "inner")}\n'
            f'{join_line("CI_ACCT_REP8.ACCT_ID == NEWARK_ACCT_MAIN_PER.ACCT_ID", "CI_ACCT_REP8", "NEWARK_ACCT_MAIN_PER")}\n'
            f'{join_line("NEWARK_ACCT_MAIN_PER.PER_ID == CI_PER_NAME_REP8.PER_ID", "NEWARK_ACCT_MAIN_PER", "CI_PER_NAME_REP8")}\n'
            f'{join_line("CI_ACCT_REP8.ACCT_ID == NEWARK_ACCT_SVC_PREM.ACCT_ID", "CI_ACCT_REP8", "NEWARK_ACCT_SVC_PREM")}\n'
            f'{join_line("NEWARK_ACCT_SVC_PREM.PREM_ID == CI_PREM_SVC.PREM_ID", "NEWARK_ACCT_SVC_PREM", "CI_PREM_SVC")}\n'
            f'{join_line("NEWARK_ACCT_SVC_PREM.PREM_ID == NEWARK_PREM_CHARS.PREM_ID", "NEWARK_ACCT_SVC_PREM", "NEWARK_PREM_CHARS")}\n'
            f'{join_line("CI_ACCT_REP8.MAILING_PREM_ID == CI_PREM_MAIL.PREM_ID", "CI_ACCT_REP8", "CI_PREM_MAIL")}\n'
            f'{join_line("NEWARK_ACCT_MAIN_PER.PER_ID == CI_PER_PHONE.PER_ID", "NEWARK_ACCT_MAIN_PER", "CI_PER_PHONE")}\n'
            f'{join_line("CI_ACCT_REP8.ACCT_ID == NEWARK_LATEST_PAY.ACCT_ID", "CI_ACCT_REP8", "NEWARK_LATEST_PAY")}\n'
            f'{join_line("CI_ACCT_REP8.ACCT_ID == NEWARK_PA_FLAG.ACCT_ID", "CI_ACCT_REP8", "NEWARK_PA_FLAG")}\n'
            f"      </joinList>\n"
            f"      <joinOptions></joinOptions>\n"
            f"      <tableRefList>\n"
            f"{table_ref_line('CI_ACCT_REP8', 'CI_ACCT_REP8')}\n"
            f"{table_ref_line('NEWARK_REP8_BUCKETS', 'NEWARK_REP8_BUCKETS')}\n"
            f"{table_ref_line('NEWARK_ACCT_MAIN_PER', 'NEWARK_ACCT_MAIN_PER')}\n"
            f"{table_ref_line('CI_PER_NAME_REP8', 'CI_PER_NAME_REP8')}\n"
            f"{table_ref_line('NEWARK_ACCT_SVC_PREM', 'NEWARK_ACCT_SVC_PREM')}\n"
            f"{table_ref_line('CI_PREM_SVC', 'CI_PREM_SVC')}\n"
            f"{table_ref_line('NEWARK_PREM_CHARS', 'NEWARK_PREM_CHARS')}\n"
            f"{table_ref_line('CI_PREM_MAIL', 'CI_PREM_MAIL')}\n"
            f"{table_ref_line('CI_PER_PHONE', 'CI_PER_PHONE')}\n"
            f"{table_ref_line('NEWARK_LATEST_PAY', 'NEWARK_LATEST_PAY')}\n"
            f"{table_ref_line('NEWARK_PA_FLAG', 'NEWARK_PA_FLAG')}\n"
            f"      </tableRefList>\n"
            f"    </jdbcTable>"
        ),
    ]

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<schema xmlns="http://www.jaspersoft.com/2007/SL/XMLSchema" version="1.3">
  <dataIslands>
    <itemGroup id="{JOIN_TREE_ID}" label="Newark Aged Balance (REP8)" resourceId="{JOIN_TREE_ID}"></itemGroup>
  </dataIslands>
  <dataSources>
    <jdbcDataSource id="{DS_ID}">
      <schemaMap>
        <entry key="defaultSchema">
          <string></string>
        </entry>
        <entry key="CISADM">
          <string>CISADM</string>
        </entry>
      </schemaMap>
    </jdbcDataSource>
  </dataSources>
  <itemGroups>
    <itemGroup id="Newark_REP8_Fields" label="Newark Aged Balance (REP8)" resourceId="{JOIN_TREE_ID}">
      <items>
{item_lines}
      </items>
    </itemGroup>
  </itemGroups>
  <resources>
{chr(10).join(resources)}
  </resources>
</schema>
"""


def validate_schema(path: Path) -> None:
    validator = REPO / "scripts/jaspersoft/validate_domain_schema.py"
    result = subprocess.run(
        [sys.executable, str(validator), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"schema validation failed:\n{result.stdout}\n{result.stderr}")


def main() -> None:
    schema_out = OUT_ROOT / f"{DOMAIN_NAME}_files" / "schema.data"
    schema_out.parent.mkdir(parents=True, exist_ok=True)
    schema_out.write_text(build_schema_text(), encoding="utf-8")
    validate_schema(schema_out)

    domain_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<semanticLayerDataSource exportedWithPermissions="true">
    <folder>{FOLDER}</folder>
    <name>{DOMAIN_NAME}</name>
    <version>2</version>
    <label>Newark Account Aged Balance - Domain</label>
    <description>Newark REP8 replacement domain. Join tree reproduces OTC REP8 bucket logic (LPC principal/interest split) from live CISADM CI_FT plus municipal premise joins. Bucket as-of date defaults to TRUNC(SYSDATE). Use Standard Offering SA Snapshot domain separately for snapshot-based Ad Hoc.</description>
    <creationDate>2026-09-02T19:15:00.000Z</creationDate>
    <updateDate>2026-09-02T19:45:00.000Z</updateDate>
    <schema>
        <localResource
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            exportedWithPermissions="false" dataFile="schema.data" xsi:type="fileResource">
            <folder>{FOLDER}/{DOMAIN_NAME}_files</folder>
            <name>schema</name>
            <version>2</version>
            <label>schema</label>
            <description>schema</description>
            <creationDate>2026-09-02T19:15:00.000Z</creationDate>
            <updateDate>2026-09-02T19:45:00.000Z</updateDate>
            <fileType>xml</fileType>
        </localResource>
    </schema>
    <dataSource>
        <alias>{DS_ID}</alias>
        <dataSourceReference>
            <uri>{DS_URI}</uri>
        </dataSourceReference>
    </dataSource>
</semanticLayerDataSource>
"""
    domain_path = OUT_ROOT / f"{DOMAIN_NAME}.xml"
    domain_path.write_text(domain_xml, encoding="utf-8")

    folder_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<folder exportedWithPermissions="true">
    <folder>{FOLDER}</folder>
    <name>Debt_Management</name>
    <version>0</version>
    <label>Debt Management</label>
    <description></description>
    <creationDate>2026-09-02T19:15:00.000Z</creationDate>
    <updateDate>2026-09-02T19:45:00.000Z</updateDate>
    <permission>
        <permissionMask>1</permissionMask>
    </permission>
</folder>
"""
    folder_path = OUT_ROOT / "_resources" / "SmartCity" / "Report" / "Workstreams" / "Debt_Management" / ".folder.xml"
    folder_path.parent.mkdir(parents=True, exist_ok=True)
    folder_path.write_text(folder_xml, encoding="utf-8")

    zip_path = OUT_ROOT / "Newark_Account_Aged_Balance_Domain_import.zip"
    if zip_path.exists():
        zip_path.unlink()
    base = OUT_ROOT / "_import_staging"
    if base.exists():
        shutil.rmtree(base)
    res = base / "resources" / "SmartCity" / "Report" / "Workstreams" / "Debt_Management"
    res.mkdir(parents=True, exist_ok=True)
    shutil.copy2(domain_path, res / f"{DOMAIN_NAME}.xml")
    files_dir = res / f"{DOMAIN_NAME}_files"
    files_dir.mkdir(exist_ok=True)
    shutil.copy2(schema_out, files_dir / "schema.data")
    shutil.copy2(folder_path, res / ".folder.xml")
    (base / "index.xml").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<export>
  <module id="repositoryResources">
    <resource>{FOLDER}/{DOMAIN_NAME}</resource>
  </module>
  <property name="pathProcessorId" value="zip"/>
</export>
""",
        encoding="utf-8",
    )
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(base.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(base).as_posix())

    downloads = Path("/Users/chase/Downloads")
    shutil.copy2(zip_path, downloads / "Newark_Account_Aged_Balance_Domain_import.zip")
    shutil.copy2(domain_path, downloads / f"{DOMAIN_NAME}.xml")
    downloads_schema = downloads / f"{DOMAIN_NAME}_files"
    downloads_schema.mkdir(exist_ok=True)
    shutil.copy2(schema_out, downloads_schema / "schema.data")
    print(f"Wrote schema: {schema_out}")
    print(f"Wrote import zip: {zip_path}")
    print(f"Copied to: {downloads}")


if __name__ == "__main__":
    main()
