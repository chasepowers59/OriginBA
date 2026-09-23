#!/usr/bin/env python3
"""Adjustment A/P Request - Domain: one row per A/P request, its adjustment, the account behind it.

The Standard Offering had no Ad Hoc surface for CISADM.CI_ADJ_APREQ (the A/P request the ERP pays
or cancels for a refund adjustment). The control question -- "which requests did the ERP cancel
while the adjustment is still open?" -- needs the request's status and the adjustment's status
side by side, which this domain gives Ad Hoc directly, plus an Action Needed flag.

Grain and joins, measured on Odessa 2026-09-23: 16 requests, 16 distinct adjustments, 0 requests
without an adjustment (request -> adjustment is inner and never fans out); 2 of 16 adjustments
point at a service agreement that no longer exists, so SA, account and customer are OUTER.
Statuses decoded from CI_LOOKUP_VAL_L by FIELD_NAME (PYMNT_SEL_STAT_FLG: N/R/H/P/X/C/D/V;
ADJ_STATUS_FLG: 05/10/20/30/50/60) -- base-product lifecycles, so the two codes the flag keys on
are safe literals. Table field lists are the ones the existing SC_Adjustment_Domain carries
(known-good on 25.4); every table takes the datasource id you pass.

    python3 scripts/jaspersoft/build_adj_ap_request_domain.py --ds Origin_DEV_DS --out schema.xml
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
from xml.sax.saxutils import escape

S, T, N = "java.lang.String", "java.sql.Timestamp", "java.math.BigDecimal"

TABLES: dict[str, tuple[str, list[tuple[str, str]]]] = {   # id -> (CISADM table, fields)
    "CI_ADJ_APREQ": ("CI_ADJ_APREQ", [("AP_REQ_ID", S), ("ADJ_ID", S), ("PYMNT_SEL_STAT_FLG", S), ("PAID_AMT", N), ("CURRENCY_PYMNT", S),
                                      ("SCHEDULED_PAY_DT", T), ("PYMNT_DT", T), ("PAY_DOC_ID", S), ("PAY_DOC_DT", T), ("PYMNT_ID", S),
                                      ("PYMNT_METHOD_FLG", S), ("BATCH_CD", S), ("BATCH_NBR", N), ("ENTITY_NAME", S),
                                      ("ADDRESS1", S), ("ADDRESS2", S), ("ADDRESS3", S), ("ADDRESS4", S), ("CITY", S), ("COUNTY", S),
                                      ("STATE", S), ("POSTAL", S), ("COUNTRY", S), ("VERSION", N)]),
    "CI_ADJ": ("CI_ADJ", [("ADJ_ID", S), ("SA_ID", S), ("ADJ_TYPE_CD", S), ("ADJ_STATUS_FLG", S), ("CRE_DT", T), ("CAN_RSN_CD", S),
                          ("ADJ_AMT", N), ("BASE_AMT", N), ("CURRENCY_CD", S), ("COMMENTS", S), ("XFER_ADJ_ID", S), ("GEN_REF_DT", T),
                          ("APPR_REQ_ID", S), ("VERSION", N)]),
    "CI_ADJ_TYPE": ("CI_ADJ_TYPE", [("ADJ_TYPE_CD", S), ("AP_REQ_TYPE_CD", S), ("DST_ID", S), ("CURRENCY_CD", S), ("AP_1099_FLG", S),
                                    ("AD_FRZ_OPT_FLG", S), ("ADJ_AMT_TYPE_FLG", S), ("APPR_PROF_CD", S), ("CIS_DIVISION", S)]),
    "CI_ADJ_TYPE_L": ("CI_ADJ_TYPE_L", [("ADJ_TYPE_CD", S), ("LANGUAGE_CD", S), ("DESCR", S), ("DESCR_ON_BILL", S)]),
    "CI_ADJ_CAN_RSN_L": ("CI_ADJ_CAN_RSN_L", [("CAN_RSN_CD", S), ("LANGUAGE_CD", S), ("DESCR", S)]),
    "CI_SA": ("CI_SA", [("SA_ID", S), ("ACCT_ID", S), ("SA_TYPE_CD", S), ("SA_STATUS_FLG", S), ("CIS_DIVISION", S), ("START_DT", T),
                        ("END_DT", T), ("CHAR_PREM_ID", S)]),
    "CI_ACCT": ("CI_ACCT", [("ACCT_ID", S), ("CIS_DIVISION", S), ("CUST_CL_CD", S), ("BILL_CYC_CD", S), ("SETUP_DT", T),
                            ("MAILING_PREM_ID", S), ("ACCT_MGMT_GRP_CD", S)]),
    "CI_ACCT_PER": ("CI_ACCT_PER", [("ACCT_ID", S), ("PER_ID", S), ("MAIN_CUST_SW", S)]),
    "CI_PER_NAME": ("CI_PER_NAME", [("PER_ID", S), ("ENTITY_NAME", S), ("NAME_TYPE_FLG", S)]),
    "REQ_STAT_L": ("CI_LOOKUP_VAL_L", [("FIELD_NAME", S), ("FIELD_VALUE", S), ("LANGUAGE_CD", S), ("DESCR", S)]),
    "ADJ_STAT_L": ("CI_LOOKUP_VAL_L", [("FIELD_NAME", S), ("FIELD_VALUE", S), ("LANGUAGE_CD", S), ("DESCR", S)]),
}

JOINS = [  # (expr, left, right, type)
    ("CI_ADJ_APREQ.ADJ_ID == CI_ADJ.ADJ_ID", "CI_ADJ_APREQ", "CI_ADJ", "inner"),
    ("CI_ADJ.ADJ_TYPE_CD == CI_ADJ_TYPE.ADJ_TYPE_CD", "CI_ADJ", "CI_ADJ_TYPE", "leftOuter"),
    ("CI_ADJ.ADJ_TYPE_CD == CI_ADJ_TYPE_L.ADJ_TYPE_CD and CI_ADJ_TYPE_L.LANGUAGE_CD == 'ENG'", "CI_ADJ", "CI_ADJ_TYPE_L", "leftOuter"),
    ("CI_ADJ.CAN_RSN_CD == CI_ADJ_CAN_RSN_L.CAN_RSN_CD and CI_ADJ_CAN_RSN_L.LANGUAGE_CD == 'ENG'", "CI_ADJ", "CI_ADJ_CAN_RSN_L", "leftOuter"),
    ("CI_ADJ.SA_ID == CI_SA.SA_ID", "CI_ADJ", "CI_SA", "leftOuter"),
    ("CI_SA.ACCT_ID == CI_ACCT.ACCT_ID", "CI_SA", "CI_ACCT", "leftOuter"),
    ("CI_ACCT.ACCT_ID == CI_ACCT_PER.ACCT_ID and CI_ACCT_PER.MAIN_CUST_SW == 'Y'", "CI_ACCT", "CI_ACCT_PER", "leftOuter"),
    ("CI_ACCT_PER.PER_ID == CI_PER_NAME.PER_ID and CI_PER_NAME.NAME_TYPE_FLG == 'PRIM'", "CI_ACCT_PER", "CI_PER_NAME", "leftOuter"),
    ("CI_ADJ_APREQ.PYMNT_SEL_STAT_FLG == REQ_STAT_L.FIELD_VALUE and REQ_STAT_L.FIELD_NAME == 'PYMNT_SEL_STAT_FLG' and REQ_STAT_L.LANGUAGE_CD == 'ENG'", "CI_ADJ_APREQ", "REQ_STAT_L", "leftOuter"),
    ("CI_ADJ.ADJ_STATUS_FLG == ADJ_STAT_L.FIELD_VALUE and ADJ_STAT_L.FIELD_NAME == 'ADJ_STATUS_FLG' and ADJ_STAT_L.LANGUAGE_CD == 'ENG'", "CI_ADJ", "ADJ_STAT_L", "leftOuter"),
]

CALCULATED = [  # (field id, DomEL, java type)
    ("ACTION_NEEDED", "CaseWhen(CI_ADJ_APREQ.PYMNT_SEL_STAT_FLG == 'X' and (CI_ADJ.ADJ_STATUS_FLG == '30' or CI_ADJ.ADJ_STATUS_FLG == '50'), 'Y', 'N')", S),
    ("PAID_BUT_ADJ_CANCELED", "CaseWhen(CI_ADJ_APREQ.PYMNT_SEL_STAT_FLG == 'P' and CI_ADJ.ADJ_STATUS_FLG == '60', 'Y', 'N')", S),
    ("AP_REQ_DIST", "CountDistinct(CI_ADJ_APREQ.AP_REQ_ID, 'Current')", "java.lang.Long"),
]

# set id, label, [(item id, label, resource)] where resource is TABLE.FIELD or a calculated field id
SETS = [
    ("SET_REQUEST", "1.) A/P Request", [
        ("AP_REQ_ID", "A/P Request ID", "CI_ADJ_APREQ.AP_REQ_ID"),
        ("REQ_ADJ_ID", "Adjustment ID", "CI_ADJ_APREQ.ADJ_ID"),
        ("PYMNT_SEL_STAT_FLG", "A/P Request Status Code", "CI_ADJ_APREQ.PYMNT_SEL_STAT_FLG"),
        ("REQ_STATUS_DESCR", "A/P Request Status", "REQ_STAT_L.DESCR"),
        ("PAID_AMT", "Paid Amount", "CI_ADJ_APREQ.PAID_AMT"),
        ("CURRENCY_PYMNT", "Payment Currency", "CI_ADJ_APREQ.CURRENCY_PYMNT"),
        ("SCHEDULED_PAY_DT", "Scheduled Payment Date", "CI_ADJ_APREQ.SCHEDULED_PAY_DT"),
        ("PYMNT_DT", "Payment Date", "CI_ADJ_APREQ.PYMNT_DT"),
        ("PAY_DOC_ID", "Payment Document ID", "CI_ADJ_APREQ.PAY_DOC_ID"),
        ("PAY_DOC_DT", "Payment Document Date", "CI_ADJ_APREQ.PAY_DOC_DT"),
        ("PYMNT_ID", "Payment ID", "CI_ADJ_APREQ.PYMNT_ID"),
        ("PYMNT_METHOD_FLG", "Payment Method Code", "CI_ADJ_APREQ.PYMNT_METHOD_FLG"),
        ("BATCH_CD", "Batch Control", "CI_ADJ_APREQ.BATCH_CD"),
        ("BATCH_NBR", "Batch Number", "CI_ADJ_APREQ.BATCH_NBR"),
        ("PAYEE_NAME", "Payee Name", "CI_ADJ_APREQ.ENTITY_NAME"),
        ("PAYEE_ADDRESS1", "Payee Address 1", "CI_ADJ_APREQ.ADDRESS1"),
        ("PAYEE_ADDRESS2", "Payee Address 2", "CI_ADJ_APREQ.ADDRESS2"),
        ("PAYEE_CITY", "Payee City", "CI_ADJ_APREQ.CITY"),
        ("PAYEE_STATE", "Payee State", "CI_ADJ_APREQ.STATE"),
        ("PAYEE_POSTAL", "Payee Postal", "CI_ADJ_APREQ.POSTAL"),
    ]),
    ("SET_ADJUSTMENT", "1.1) Adjustment", [
        ("ADJ_ID", "Adjustment ID", "CI_ADJ.ADJ_ID"),
        ("ADJ_SA_ID", "Service Agreement ID", "CI_ADJ.SA_ID"),
        ("ADJ_TYPE_CD", "Adjustment Type Code", "CI_ADJ.ADJ_TYPE_CD"),
        ("ADJ_TYPE_DESCR", "Adjustment Type", "CI_ADJ_TYPE_L.DESCR"),
        ("ADJ_STATUS_FLG", "Adjustment Status Code", "CI_ADJ.ADJ_STATUS_FLG"),
        ("ADJ_STATUS_DESCR", "Adjustment Status", "ADJ_STAT_L.DESCR"),
        ("ADJ_CRE_DT", "Adjustment Created Date", "CI_ADJ.CRE_DT"),
        ("ADJ_AMT", "Adjustment Amount", "CI_ADJ.ADJ_AMT"),
        ("BASE_AMT", "Base Amount", "CI_ADJ.BASE_AMT"),
        ("ADJ_CURRENCY_CD", "Adjustment Currency", "CI_ADJ.CURRENCY_CD"),
        ("CAN_RSN_CD", "Cancel Reason Code", "CI_ADJ.CAN_RSN_CD"),
        ("CAN_RSN_DESCR", "Cancel Reason", "CI_ADJ_CAN_RSN_L.DESCR"),
        ("ADJ_COMMENTS", "Adjustment Comments", "CI_ADJ.COMMENTS"),
        ("XFER_ADJ_ID", "Transfer Adjustment ID", "CI_ADJ.XFER_ADJ_ID"),
        ("GEN_REF_DT", "General Reference Date", "CI_ADJ.GEN_REF_DT"),
        ("APPR_REQ_ID", "Approval Request ID", "CI_ADJ.APPR_REQ_ID"),
    ]),
    ("SET_ADJ_TYPE", "1.2) Adjustment Type Configuration", [
        ("AP_REQ_TYPE_CD", "A/P Request Type", "CI_ADJ_TYPE.AP_REQ_TYPE_CD"),
        ("TYPE_DST_ID", "Distribution Code", "CI_ADJ_TYPE.DST_ID"),
        ("AP_1099_FLG", "1099 Flag", "CI_ADJ_TYPE.AP_1099_FLG"),
        ("AD_FRZ_OPT_FLG", "Freeze Option", "CI_ADJ_TYPE.AD_FRZ_OPT_FLG"),
        ("ADJ_AMT_TYPE_FLG", "Amount Type", "CI_ADJ_TYPE.ADJ_AMT_TYPE_FLG"),
        ("APPR_PROF_CD", "Approval Profile", "CI_ADJ_TYPE.APPR_PROF_CD"),
        ("TYPE_CIS_DIVISION", "Type CIS Division", "CI_ADJ_TYPE.CIS_DIVISION"),
    ]),
    ("SET_ACCOUNT", "1.3) Service Agreement, Account And Customer", [
        ("SA_ID", "Service Agreement ID", "CI_SA.SA_ID"),
        ("SA_TYPE_CD", "SA Type Code", "CI_SA.SA_TYPE_CD"),
        ("SA_STATUS_FLG", "SA Status Code", "CI_SA.SA_STATUS_FLG"),
        ("SA_START_DT", "SA Start Date", "CI_SA.START_DT"),
        ("SA_END_DT", "SA End Date", "CI_SA.END_DT"),
        ("CHAR_PREM_ID", "Characteristic Premise ID", "CI_SA.CHAR_PREM_ID"),
        ("ACCT_ID", "Account ID", "CI_ACCT.ACCT_ID"),
        ("CIS_DIVISION", "CIS Division", "CI_ACCT.CIS_DIVISION"),
        ("CUST_CL_CD", "Customer Class Code", "CI_ACCT.CUST_CL_CD"),
        ("BILL_CYC_CD", "Bill Cycle Code", "CI_ACCT.BILL_CYC_CD"),
        ("ACCT_SETUP_DT", "Account Set Up Date", "CI_ACCT.SETUP_DT"),
        ("MAILING_PREM_ID", "Mailing Premise ID", "CI_ACCT.MAILING_PREM_ID"),
        ("MAIN_CUSTOMER_NAME", "Main Customer Name", "CI_PER_NAME.ENTITY_NAME"),
    ]),
    ("SET_FORMULAS", "1.) Formulas", [
        ("ACTION_NEEDED", "Action Needed (Request Canceled, Adjustment Open)", "ACTION_NEEDED"),
        ("PAID_BUT_ADJ_CANCELED", "Paid But Adjustment Canceled", "PAID_BUT_ADJ_CANCELED"),
        ("AP_REQ_DIST", "Distinct A/P Requests", "AP_REQ_DIST"),
    ]),
]
MEASURES = [  # (item id, label, resource, defaultAgg)
    ("AP_REQ_COUNT", "A/P Request Count", "CI_ADJ_APREQ.AP_REQ_ID", "CountDistinct"),
    ("ADJ_AMT_TOTAL", "Adjustment Amount Total", "CI_ADJ.ADJ_AMT", "Sum"),
    ("PAID_AMT_TOTAL", "Paid Amount Total", "CI_ADJ_APREQ.PAID_AMT", "Sum"),
]


def schema(ds: str) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<schema xmlns="http://www.jaspersoft.com/2007/SL/XMLSchema" version="1.3">',
           '  <dataIslands>', '    <itemGroup id="JoinTree_1" label="JoinTree_1" resourceId="JoinTree_1"></itemGroup>', '  </dataIslands>',
           '  <dataSources>', f'    <jdbcDataSource id="{ds}">', '      <schemaMap>',
           '        <entry key="defaultSchema">', '          <string></string>', '        </entry>',
           '        <entry key="CISADM">', '          <string>CISADM</string>', '        </entry>',
           '      </schemaMap>', '    </jdbcDataSource>', '  </dataSources>', '  <itemGroups>']
    for sid, label, items in SETS:
        out += [f'    <itemGroup id="{sid}" label="{escape(label)}" resourceId="JoinTree_1">', '      <items>']
        out += [f'        <item id="{i}" label="{escape(l)}" resourceId="JoinTree_1.{r}"></item>' for i, l, r in items]
        out += ['      </items>', '    </itemGroup>']
    out += ['    <itemGroup id="SET_METRICS" label="Measures" resourceId="JoinTree_1">', '      <items>']
    out += [f'        <item defaultAgg="{agg}" dimensionOrMeasure="Measure" id="{i}" label="{escape(l)}" resourceId="JoinTree_1.{r}"></item>' for i, l, r, agg in MEASURES]
    out += ['      </items>', '    </itemGroup>', '  </itemGroups>', '  <resources>']
    for tid, (table, fields) in TABLES.items():
        out += [f'    <jdbcTable id="{tid}" datasourceId="{ds}" datasourceTableName="{table}" schemaAlias="CISADM">', '      <fieldList>']
        out += [f'        <field id="{f}" type="{t}"></field>' for f, t in fields]
        out += ['      </fieldList>', '    </jdbcTable>']
    out += [f'    <jdbcTable id="JoinTree_1" datasourceId="{ds}" datasourceTableName="CI_ADJ_APREQ" schemaAlias="CISADM">', '      <fieldList>']
    for tid, (_, fields) in TABLES.items():
        out += [f'        <field id="{tid}.{f}" type="{t}"></field>' for f, t in fields]
    out += [f'        <field id="{fid}" dataSetExpression="{escape(expr)}" type="{t}"></field>' for fid, expr, t in CALCULATED]
    # no <filterString>: an EMPTY one is parsed and the query engine answers
    # "exception parsing filter string ''" (measured on Origin_DEV, 2026-09-23)
    out += ['      </fieldList>', '      <joinInfo alias="JoinTree_1" referenceId="CI_ADJ_APREQ"></joinInfo>', '      <joinList>']
    out += [f'        <join expr="{escape(e)}" left="{l}" right="{r}" type="{ty}" weight="1"></join>' for e, l, r, ty in JOINS]
    out += ['      </joinList>', '      <joinOptions></joinOptions>', '      <tableRefList>']
    out += [f'        <tableRef alwaysIncludeTable="false" tableAlias="{tid}" tableId="{tid}"></tableRef>' for tid in TABLES]
    out += ['      </tableRefList>', '    </jdbcTable>', '  </resources>', '</schema>', '']
    return "\n".join(out)


def validate(path: pathlib.Path) -> None:
    v = pathlib.Path(__file__).resolve().parent / "validate_domain_schema.py"
    r = subprocess.run([sys.executable, str(v), str(path)], capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise SystemExit(f"schema validation failed:\n{r.stdout}{r.stderr}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ds", required=True, help="the org's datasource id, e.g. Origin_DEV_DS")
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(schema(a.ds), encoding="utf-8")
    validate(a.out)
    print(f"wrote {a.out} for {a.ds}: {len(TABLES)} tables, {len(JOINS)} joins, {sum(len(s[2]) for s in SETS) + len(MEASURES)} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
