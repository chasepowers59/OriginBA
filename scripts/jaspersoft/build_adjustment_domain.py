#!/usr/bin/env python3
"""Adjustment - Domain: one row per adjustment with everything around it, for every adjustment
report the Standard Offering needs.

Successor of the Workstreams "Adjustment - Domain", rebuilt for the Standard Offering: root
CI_ADJ, EVERY join outer (the old one was inner to SA / account / customer / labels and dropped an
adjustment whose SA is gone -- 2 of 16 on Odessa), no client-built CMS view, and the parts it
lacked: adjustment-type configuration (A/P request type, distribution code, approval profile,
freeze option), the adjustment's own financial transactions folded to one row (frozen FT, cancel
FT, accounting/ARS dates, GL division, bill, net amounts), characteristics folded to one row,
approval request with its profile and status labels, the transfer partner adjustment, the A/P
request, service agreement + SA type (service type, special role), account + every class label,
main customer with person facts, characteristic and mailing premises, and a Flags set.

Grain, measured on Origin_DEV's database (Ellensburg 25.4) 2026-09-24: 501,193 adjustments; the
main-customer chain (MAIN_CUST_SW = Y, NAME_TYPE_FLG = PRIM) resolves 501,193 of 501,193 with no
fan-out; at most 2 FTs (AD + AX) and 3 characteristics per adjustment, both folded by derived
tables so the row count stays the adjustment count. Column lists come from ALL_TAB_COLUMNS on
that database (never from memory); secrets (ALERT_INFO, WEB_PASSWD*) are not declared.

    python3 scripts/jaspersoft/build_adjustment_domain.py --ds Origin_DEV_DS --out schema.xml
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import domain_schema  # noqa: E402

S, T, N, L = "java.lang.String", "java.sql.Timestamp", "java.math.BigDecimal", "java.lang.Long"
LBL = [("LANGUAGE_CD", S), ("DESCR", S)]
LOOKUP = [("FIELD_NAME", S), ("FIELD_VALUE", S), ("LANGUAGE_CD", S), ("DESCR", S)]
ADDRESS = [("ADDRESS1", S), ("ADDRESS2", S), ("ADDRESS3", S), ("ADDRESS4", S), ("CITY", S), ("COUNTY", S), ("STATE", S), ("POSTAL", S), ("COUNTRY", S)]

# lookup table id -> the CI_LOOKUP_VAL_L field family it decodes (decode per family, never across)
LOOKUPS = {"ADJ_STAT_L": "ADJ_STATUS_FLG", "SA_STAT_L": "SA_STATUS_FLG", "REQ_STAT_L": "PYMNT_SEL_STAT_FLG", "PAY_METHOD_L": "PYMNT_METHOD_FLG",
           "FRZ_OPT_L": "AD_FRZ_OPT_FLG", "AMT_TYPE_L": "ADJ_AMT_TYPE_FLG", "PER_BUS_L": "PER_OR_BUS_FLG",
           "STRT_RSN_L": "STRT_RSN_FLG", "STOP_RSN_L": "STOP_RSN_FLG"}

TABLES: domain_schema.Tables = {
    "CI_ADJ": ("CI_ADJ", [("ADJ_ID", S), ("SA_ID", S), ("ADJ_TYPE_CD", S), ("ADJ_STATUS_FLG", S), ("CRE_DT", T), ("CAN_RSN_CD", S), ("ADJ_AMT", N),
                          ("XFER_ADJ_ID", S), ("CURRENCY_CD", S), ("COMMENTS", S), ("BEHALF_SA_ID", S), ("BASE_AMT", N), ("GEN_REF_DT", T),
                          ("APPR_REQ_ID", S), ("ILM_DT", T), ("ILM_ARCH_SW", S), ("VERSION", N)]),
    "CI_ADJ_TYPE": ("CI_ADJ_TYPE", [("ADJ_TYPE_CD", S), ("AP_REQ_TYPE_CD", S), ("DST_ID", S), ("CURRENCY_CD", S), ("SYNCH_CUR_SW", S), ("DFLT_AMT", N),
                                    ("AP_1099_FLG", S), ("PRT_DFLT_SW", S), ("AD_FRZ_OPT_FLG", S), ("ADJ_AMT_TYPE_FLG", S), ("APPR_PROF_CD", S), ("CIS_DIVISION", S)]),
    "CI_ADJ_TYPE_L": ("CI_ADJ_TYPE_L", [("ADJ_TYPE_CD", S)] + LBL + [("DESCR_ON_BILL", S)]),
    "CI_DST_CODE_L": ("CI_DST_CODE_L", [("DST_ID", S)] + LBL),
    "TYPE_APPR_PROF_L": ("CI_APPR_PROF_L", [("APPR_PROF_CD", S)] + LBL),
    "CI_ADJ_CAN_RSN_L": ("CI_ADJ_CAN_RSN_L", [("CAN_RSN_CD", S)] + LBL),
    "CI_CURRENCY_CD_L": ("CI_CURRENCY_CD_L", [("CURRENCY_CD", S)] + LBL),
    "ADJ_STAT_L": ("CI_LOOKUP_VAL_L", LOOKUP), "FRZ_OPT_L": ("CI_LOOKUP_VAL_L", LOOKUP), "AMT_TYPE_L": ("CI_LOOKUP_VAL_L", LOOKUP),
    "CI_APPR_REQ": ("CI_APPR_REQ", [("APPR_REQ_ID", S), ("APPR_PROF_CD", S), ("BUS_OBJ_CD", S), ("BO_STATUS_CD", S)]),
    "CI_APPR_PROF_L": ("CI_APPR_PROF_L", [("APPR_PROF_CD", S)] + LBL),
    "APPR_STAT_L": ("F1_BUS_OBJ_STATUS_L", [("BUS_OBJ_CD", S), ("BO_STATUS_CD", S)] + LBL),
    "CI_ADJ_XFER": ("CI_ADJ", [("ADJ_ID", S), ("SA_ID", S), ("ADJ_TYPE_CD", S), ("ADJ_STATUS_FLG", S), ("ADJ_AMT", N), ("CRE_DT", T)]),
    "CI_ADJ_TYPE_L_XFER": ("CI_ADJ_TYPE_L", [("ADJ_TYPE_CD", S)] + LBL),
    "CI_SA_XFER": ("CI_SA", [("SA_ID", S), ("ACCT_ID", S), ("SA_TYPE_CD", S), ("CIS_DIVISION", S)]),
    "CI_ADJ_APREQ": ("CI_ADJ_APREQ", [("AP_REQ_ID", S), ("ADJ_ID", S), ("PYMNT_SEL_STAT_FLG", S), ("PAID_AMT", N), ("CURRENCY_PYMNT", S),
                                      ("SCHEDULED_PAY_DT", T), ("PYMNT_DT", T), ("PAY_DOC_ID", S), ("PAY_DOC_DT", T), ("PYMNT_ID", S),
                                      ("PYMNT_METHOD_FLG", S), ("BATCH_CD", S), ("BATCH_NBR", N), ("ENTITY_NAME", S)] + ADDRESS),
    "REQ_STAT_L": ("CI_LOOKUP_VAL_L", LOOKUP), "PAY_METHOD_L": ("CI_LOOKUP_VAL_L", LOOKUP),
    "CI_SA": ("CI_SA", [("SA_ID", S), ("ACCT_ID", S), ("CIS_DIVISION", S), ("SA_TYPE_CD", S), ("SA_STATUS_FLG", S), ("START_DT", T), ("END_DT", T),
                        ("START_OPT_CD", S), ("CHAR_PREM_ID", S), ("CURRENCY_CD", S), ("OLD_ACCT_ID", S), ("STRT_RSN_FLG", S), ("STOP_RSN_FLG", S),
                        ("STRT_REQED_BY", S), ("STOP_REQED_BY", S), ("SA_REL_ID", S), ("BUS_ACTIVITY_DESC", S), ("TOT_TO_BILL_AMT", N), ("SIC_CD", S)]),
    "SA_STAT_L": ("CI_LOOKUP_VAL_L", LOOKUP), "STRT_RSN_L": ("CI_LOOKUP_VAL_L", LOOKUP), "STOP_RSN_L": ("CI_LOOKUP_VAL_L", LOOKUP),
    "CI_SA_TYPE": ("CI_SA_TYPE", [("CIS_DIVISION", S), ("SA_TYPE_CD", S), ("SVC_TYPE_CD", S), ("SPECIAL_ROLE_FLG", S), ("REV_CL_CD", S), ("DEBT_CL_CD", S),
                                  ("DST_ID", S), ("GL_DIVISION", S), ("BILL_PERIOD_CD", S), ("DEP_CL_CD", S), ("ADJ_TYPE_NSF", S), ("LATE_PAY_CHARGE_SW", S)]),
    "CI_SA_TYPE_L": ("CI_SA_TYPE_L", [("CIS_DIVISION", S), ("SA_TYPE_CD", S)] + LBL + [("DFLT_DESCR_ON_BILL", S)]),
    "CI_SVC_TYPE_L": ("CI_SVC_TYPE_L", [("SVC_TYPE_CD", S)] + LBL),
    "CI_ACCT": ("CI_ACCT", [("ACCT_ID", S), ("BILL_CYC_CD", S), ("SETUP_DT", T), ("CURRENCY_CD", S), ("ACCT_MGMT_GRP_CD", S), ("CIS_DIVISION", S),
                            ("MAILING_PREM_ID", S), ("COLL_CL_CD", S), ("CUST_CL_CD", S), ("BUD_PLAN_CD", S), ("CR_REVIEW_DT", T),
                            ("POSTPONE_CR_RVW_DT", T), ("BILL_AFTER_DT", T), ("ACCESS_GRP_CD", S)]),
    "CI_CIS_DIVISION_L": ("CI_CIS_DIVISION_L", [("CIS_DIVISION", S)] + LBL),
    "CI_CUST_CL_L": ("CI_CUST_CL_L", [("CUST_CL_CD", S)] + LBL),
    "CI_COLL_CL_L": ("CI_COLL_CL_L", [("COLL_CL_CD", S)] + LBL),
    "CI_BILL_CYC_L": ("CI_BILL_CYC_L", [("BILL_CYC_CD", S)] + LBL),
    "CI_ACCT_MGMT_GR_L": ("CI_ACCT_MGMT_GR_L", [("ACCT_MGMT_GRP_CD", S)] + LBL),
    "CI_BUD_PLAN_L": ("CI_BUD_PLAN_L", [("BUD_PLAN_CD", S)] + LBL),
    "CI_ACCT_PER": ("CI_ACCT_PER", [("ACCT_ID", S), ("PER_ID", S), ("MAIN_CUST_SW", S), ("ACCT_REL_TYPE_CD", S), ("FIN_RESP_SW", S),
                                    ("BILL_RTE_TYPE_CD", S), ("WEB_ACCESS_FLG", S), ("RECEIVE_COPY_SW", S)]),
    "CI_PER_NAME": ("CI_PER_NAME", [("PER_ID", S), ("ENTITY_NAME", S), ("NAME_TYPE_FLG", S), ("ENTITY_NAME_UPR", S)]),
    "CI_PER": ("CI_PER", [("PER_ID", S), ("PER_OR_BUS_FLG", S), ("EMAILID", S), ("LANGUAGE_CD", S), ("LS_SL_FLG", S)]),
    "PER_BUS_L": ("CI_LOOKUP_VAL_L", LOOKUP),
    "CI_PREM": ("CI_PREM", [("PREM_ID", S), ("PREM_TYPE_CD", S), ("CIS_DIVISION", S)] + ADDRESS
                + [("IN_CITY_LIMIT", S), ("GEO_CODE", S), ("TREND_AREA_CD", S), ("LL_ID", S), ("PRNT_PREM_ID", S), ("MAIL_ADDR_SW", S)]),
    "CI_PREM_TYPE_L": ("CI_PREM_TYPE_L", [("PREM_TYPE_CD", S)] + LBL),
    "CI_PREM_MAIL": ("CI_PREM", [("PREM_ID", S)] + ADDRESS),
}

DERIVED: domain_schema.Derived = {
    # the adjustment's financial side folded to one row: AD = the frozen FT, AX = its cancellation
    "ADJ_FT": ("""select ft.sibling_id as adj_id,
       count(*) as ft_count,
       max(case when ft.ft_type_flg = 'AD' then ft.ft_id end) as frozen_ft_id,
       max(case when ft.ft_type_flg = 'AX' then ft.ft_id end) as cancel_ft_id,
       min(case when ft.ft_type_flg = 'AD' then ft.freeze_dttm end) as freeze_dttm,
       max(case when ft.ft_type_flg = 'AX' then ft.freeze_dttm end) as cancel_dttm,
       max(case when ft.ft_type_flg = 'AD' then ft.freeze_user_id end) as freeze_user_id,
       max(case when ft.ft_type_flg = 'AX' then ft.freeze_user_id end) as cancel_user_id,
       min(case when ft.ft_type_flg = 'AD' then ft.accounting_dt end) as accounting_dt,
       min(case when ft.ft_type_flg = 'AD' then ft.ars_dt end) as ars_dt,
       max(ft.gl_division) as gl_division,
       max(case when ft.ft_type_flg = 'AD' then ft.bill_id end) as bill_id,
       max(case when ft.ft_type_flg = 'AD' then ft.cur_amt end) as frozen_cur_amt,
       max(case when ft.ft_type_flg = 'AD' then ft.tot_amt end) as frozen_tot_amt,
       sum(ft.cur_amt) as net_cur_amt,
       sum(ft.tot_amt) as net_tot_amt,
       max(case when ft.ft_type_flg = 'AD' then ft.gl_distrib_status end) as gl_distrib_status,
       max(ft.xfer_to_gl_dt) as xfer_to_gl_dt,
       max(case when ft.ft_type_flg = 'AD' then ft.match_evt_id end) as match_evt_id,
       max(case when ft.ft_type_flg = 'AD' then ft.show_on_bill_sw end) as show_on_bill_sw,
       max(case when ft.ft_type_flg = 'AD' then ft.not_in_ars_sw end) as not_in_ars_sw,
       trunc(min(case when ft.ft_type_flg = 'AD' then ft.freeze_dttm end)) - a.cre_dt as days_to_freeze
from cisadm.ci_ft ft
join cisadm.ci_adj a on a.adj_id = ft.sibling_id
where ft.ft_type_flg in ('AD', 'AX')
group by ft.sibling_id, a.cre_dt""",
               [("ADJ_ID", S), ("FT_COUNT", L), ("FROZEN_FT_ID", S), ("CANCEL_FT_ID", S), ("FREEZE_DTTM", T), ("CANCEL_DTTM", T), ("FREEZE_USER_ID", S),
                ("CANCEL_USER_ID", S), ("ACCOUNTING_DT", T), ("ARS_DT", T), ("GL_DIVISION", S), ("BILL_ID", S), ("FROZEN_CUR_AMT", N), ("FROZEN_TOT_AMT", N),
                ("NET_CUR_AMT", N), ("NET_TOT_AMT", N), ("GL_DISTRIB_STATUS", S), ("XFER_TO_GL_DT", T), ("MATCH_EVT_ID", S), ("SHOW_ON_BILL_SW", S), ("NOT_IN_ARS_SW", S), ("DAYS_TO_FREEZE", N)]),
    # characteristics folded to one row, every type resolved to its label and its value (ad hoc, foreign key or predefined)
    "ADJ_CHAR": ("""select c.adj_id,
       count(*) as char_count,
       listagg(trim(coalesce(l.descr, c.char_type_cd)) || ' = ' || coalesce(nullif(trim(c.adhoc_char_val), ''), nullif(trim(c.char_val_fk1), ''), nullif(trim(c.char_val), '')), '; ')
           within group (order by c.char_type_cd, c.seq_num) as characteristics
from cisadm.ci_adj_char c
left join cisadm.ci_char_type_l l on l.char_type_cd = c.char_type_cd and l.language_cd = 'ENG'
group by c.adj_id""",
                 [("ADJ_ID", S), ("CHAR_COUNT", L), ("CHARACTERISTICS", S)]),
    # age in SQL: a DomEL ElapsedDays(Today(0), ...) is evaluated in memory by the Ad Hoc engine, which
    # stops at the server's 300,000-row cap (measured 2026-09-24: 478,372 of 501,193 grouped), while a
    # column the database computes is pushed down and counts everything
    "ADJ_AGE": ("""select a.adj_id,
       trunc(sysdate) - a.cre_dt as days_old,
       case when a.adj_status_flg not in ('50', '60') and a.cre_dt < trunc(sysdate) - 30 then 'Y' else 'N' end as open_over_30_days
from cisadm.ci_adj a""",
                [("ADJ_ID", S), ("DAYS_OLD", N), ("OPEN_OVER_30_DAYS", S)]),
}

def _lookup(left: str, col: str, lk: str) -> str:
    return f"{left}.{col} == {lk}.FIELD_VALUE and {lk}.FIELD_NAME == '{LOOKUPS[lk]}' and {lk}.LANGUAGE_CD == 'ENG'"

JOINS: domain_schema.Joins = [(e, l, r, "leftOuter") for e, l, r in [
    ("CI_ADJ.ADJ_TYPE_CD == CI_ADJ_TYPE.ADJ_TYPE_CD", "CI_ADJ", "CI_ADJ_TYPE"),
    ("CI_ADJ.ADJ_TYPE_CD == CI_ADJ_TYPE_L.ADJ_TYPE_CD and CI_ADJ_TYPE_L.LANGUAGE_CD == 'ENG'", "CI_ADJ", "CI_ADJ_TYPE_L"),
    ("CI_ADJ_TYPE.DST_ID == CI_DST_CODE_L.DST_ID and CI_DST_CODE_L.LANGUAGE_CD == 'ENG'", "CI_ADJ_TYPE", "CI_DST_CODE_L"),
    ("CI_ADJ_TYPE.APPR_PROF_CD == TYPE_APPR_PROF_L.APPR_PROF_CD and TYPE_APPR_PROF_L.LANGUAGE_CD == 'ENG'", "CI_ADJ_TYPE", "TYPE_APPR_PROF_L"),
    (_lookup("CI_ADJ_TYPE", "AD_FRZ_OPT_FLG", "FRZ_OPT_L"), "CI_ADJ_TYPE", "FRZ_OPT_L"),
    (_lookup("CI_ADJ_TYPE", "ADJ_AMT_TYPE_FLG", "AMT_TYPE_L"), "CI_ADJ_TYPE", "AMT_TYPE_L"),
    ("CI_ADJ.CAN_RSN_CD == CI_ADJ_CAN_RSN_L.CAN_RSN_CD and CI_ADJ_CAN_RSN_L.LANGUAGE_CD == 'ENG'", "CI_ADJ", "CI_ADJ_CAN_RSN_L"),
    ("CI_ADJ.CURRENCY_CD == CI_CURRENCY_CD_L.CURRENCY_CD and CI_CURRENCY_CD_L.LANGUAGE_CD == 'ENG'", "CI_ADJ", "CI_CURRENCY_CD_L"),
    (_lookup("CI_ADJ", "ADJ_STATUS_FLG", "ADJ_STAT_L"), "CI_ADJ", "ADJ_STAT_L"),
    ("CI_ADJ.ADJ_ID == ADJ_FT.ADJ_ID", "CI_ADJ", "ADJ_FT"),
    ("CI_ADJ.ADJ_ID == ADJ_CHAR.ADJ_ID", "CI_ADJ", "ADJ_CHAR"),
    ("CI_ADJ.ADJ_ID == ADJ_AGE.ADJ_ID", "CI_ADJ", "ADJ_AGE"),
    ("CI_ADJ.APPR_REQ_ID == CI_APPR_REQ.APPR_REQ_ID", "CI_ADJ", "CI_APPR_REQ"),
    ("CI_APPR_REQ.APPR_PROF_CD == CI_APPR_PROF_L.APPR_PROF_CD and CI_APPR_PROF_L.LANGUAGE_CD == 'ENG'", "CI_APPR_REQ", "CI_APPR_PROF_L"),
    ("CI_APPR_REQ.BUS_OBJ_CD == APPR_STAT_L.BUS_OBJ_CD and CI_APPR_REQ.BO_STATUS_CD == APPR_STAT_L.BO_STATUS_CD and APPR_STAT_L.LANGUAGE_CD == 'ENG'", "CI_APPR_REQ", "APPR_STAT_L"),
    ("CI_ADJ.XFER_ADJ_ID == CI_ADJ_XFER.ADJ_ID", "CI_ADJ", "CI_ADJ_XFER"),
    ("CI_ADJ_XFER.ADJ_TYPE_CD == CI_ADJ_TYPE_L_XFER.ADJ_TYPE_CD and CI_ADJ_TYPE_L_XFER.LANGUAGE_CD == 'ENG'", "CI_ADJ_XFER", "CI_ADJ_TYPE_L_XFER"),
    ("CI_ADJ_XFER.SA_ID == CI_SA_XFER.SA_ID", "CI_ADJ_XFER", "CI_SA_XFER"),
    ("CI_ADJ.ADJ_ID == CI_ADJ_APREQ.ADJ_ID", "CI_ADJ", "CI_ADJ_APREQ"),
    (_lookup("CI_ADJ_APREQ", "PYMNT_SEL_STAT_FLG", "REQ_STAT_L"), "CI_ADJ_APREQ", "REQ_STAT_L"),
    (_lookup("CI_ADJ_APREQ", "PYMNT_METHOD_FLG", "PAY_METHOD_L"), "CI_ADJ_APREQ", "PAY_METHOD_L"),
    ("CI_ADJ.SA_ID == CI_SA.SA_ID", "CI_ADJ", "CI_SA"),
    (_lookup("CI_SA", "SA_STATUS_FLG", "SA_STAT_L"), "CI_SA", "SA_STAT_L"),
    (_lookup("CI_SA", "STRT_RSN_FLG", "STRT_RSN_L"), "CI_SA", "STRT_RSN_L"),
    (_lookup("CI_SA", "STOP_RSN_FLG", "STOP_RSN_L"), "CI_SA", "STOP_RSN_L"),
    ("CI_SA.CIS_DIVISION == CI_SA_TYPE.CIS_DIVISION and CI_SA.SA_TYPE_CD == CI_SA_TYPE.SA_TYPE_CD", "CI_SA", "CI_SA_TYPE"),
    ("CI_SA.CIS_DIVISION == CI_SA_TYPE_L.CIS_DIVISION and CI_SA.SA_TYPE_CD == CI_SA_TYPE_L.SA_TYPE_CD and CI_SA_TYPE_L.LANGUAGE_CD == 'ENG'", "CI_SA", "CI_SA_TYPE_L"),
    ("CI_SA_TYPE.SVC_TYPE_CD == CI_SVC_TYPE_L.SVC_TYPE_CD and CI_SVC_TYPE_L.LANGUAGE_CD == 'ENG'", "CI_SA_TYPE", "CI_SVC_TYPE_L"),
    ("CI_SA.ACCT_ID == CI_ACCT.ACCT_ID", "CI_SA", "CI_ACCT"),
    ("CI_ACCT.CIS_DIVISION == CI_CIS_DIVISION_L.CIS_DIVISION and CI_CIS_DIVISION_L.LANGUAGE_CD == 'ENG'", "CI_ACCT", "CI_CIS_DIVISION_L"),
    ("CI_ACCT.CUST_CL_CD == CI_CUST_CL_L.CUST_CL_CD and CI_CUST_CL_L.LANGUAGE_CD == 'ENG'", "CI_ACCT", "CI_CUST_CL_L"),
    ("CI_ACCT.COLL_CL_CD == CI_COLL_CL_L.COLL_CL_CD and CI_COLL_CL_L.LANGUAGE_CD == 'ENG'", "CI_ACCT", "CI_COLL_CL_L"),
    ("CI_ACCT.BILL_CYC_CD == CI_BILL_CYC_L.BILL_CYC_CD and CI_BILL_CYC_L.LANGUAGE_CD == 'ENG'", "CI_ACCT", "CI_BILL_CYC_L"),
    ("CI_ACCT.ACCT_MGMT_GRP_CD == CI_ACCT_MGMT_GR_L.ACCT_MGMT_GRP_CD and CI_ACCT_MGMT_GR_L.LANGUAGE_CD == 'ENG'", "CI_ACCT", "CI_ACCT_MGMT_GR_L"),
    ("CI_ACCT.BUD_PLAN_CD == CI_BUD_PLAN_L.BUD_PLAN_CD and CI_BUD_PLAN_L.LANGUAGE_CD == 'ENG'", "CI_ACCT", "CI_BUD_PLAN_L"),
    ("CI_ACCT.ACCT_ID == CI_ACCT_PER.ACCT_ID and CI_ACCT_PER.MAIN_CUST_SW == 'Y'", "CI_ACCT", "CI_ACCT_PER"),
    ("CI_ACCT_PER.PER_ID == CI_PER_NAME.PER_ID and CI_PER_NAME.NAME_TYPE_FLG == 'PRIM'", "CI_ACCT_PER", "CI_PER_NAME"),
    ("CI_ACCT_PER.PER_ID == CI_PER.PER_ID", "CI_ACCT_PER", "CI_PER"),
    (_lookup("CI_PER", "PER_OR_BUS_FLG", "PER_BUS_L"), "CI_PER", "PER_BUS_L"),
    ("CI_SA.CHAR_PREM_ID == CI_PREM.PREM_ID", "CI_SA", "CI_PREM"),
    ("CI_PREM.PREM_TYPE_CD == CI_PREM_TYPE_L.PREM_TYPE_CD and CI_PREM_TYPE_L.LANGUAGE_CD == 'ENG'", "CI_PREM", "CI_PREM_TYPE_L"),
    ("CI_ACCT.MAILING_PREM_ID == CI_PREM_MAIL.PREM_ID", "CI_ACCT", "CI_PREM_MAIL"),
]]

# Lifecycle codes and switches are base product; PA/CD/WO/LO/NB is the fixed SPECIAL_ROLE_FLG domain
# (identical at all six clients, c2m-functional-architect); ' ' is how a CHAR key reads when unset.
BASE_PRODUCT_LITERALS = {"50", "60", "20", "X", "P", "30", "Y", "N", " ", "PA", "CD", "WO", "LO", "NB", "P"}
_OPEN = "CI_ADJ.ADJ_STATUS_FLG != '50' and CI_ADJ.ADJ_STATUS_FLG != '60'"
def _unset(col: str) -> str:   # a CHAR key that is null or all spaces
    return f"IsNull({col}) or {col} == ' '"

CALCULATED: domain_schema.Calculated = [
    ("IS_FROZEN", "CaseWhen(CI_ADJ.ADJ_STATUS_FLG == '50', 'Y', 'N')", S),
    ("IS_CANCELED", "CaseWhen(CI_ADJ.ADJ_STATUS_FLG == '60', 'Y', 'N')", S),
    ("IS_OPEN", f"CaseWhen({_OPEN}, 'Y', 'N')", S),
    ("AMOUNT_DIRECTION", "CaseWhen(CI_ADJ.ADJ_AMT < 0, 'Credit', 'Debit')", S),
    ("IS_TRANSFER", f"CaseWhen({_unset('CI_ADJ.XFER_ADJ_ID')}, 'N', 'Y')", S),
    ("IS_ON_BEHALF", f"CaseWhen({_unset('CI_ADJ.BEHALF_SA_ID')}, 'N', 'Y')", S),
    ("HAS_APPROVAL_REQUEST", f"CaseWhen({_unset('CI_ADJ.APPR_REQ_ID')}, 'N', 'Y')", S),
    ("IS_AP_ADJ_TYPE", f"CaseWhen({_unset('CI_ADJ_TYPE.AP_REQ_TYPE_CD')}, 'N', 'Y')", S),
    ("HAS_AP_REQUEST", "CaseWhen(IsNull(CI_ADJ_APREQ.AP_REQ_ID), 'N', 'Y')", S),
    ("AP_ACTION_NEEDED", "CaseWhen(CI_ADJ_APREQ.PYMNT_SEL_STAT_FLG == 'X' and (CI_ADJ.ADJ_STATUS_FLG == '30' or CI_ADJ.ADJ_STATUS_FLG == '50'), 'Y', 'N')", S),
    ("PAID_BUT_ADJ_CANCELED", "CaseWhen(CI_ADJ_APREQ.PYMNT_SEL_STAT_FLG == 'P' and CI_ADJ.ADJ_STATUS_FLG == '60', 'Y', 'N')", S),
    ("HAS_FT", "CaseWhen(IsNull(ADJ_FT.ADJ_ID), 'N', 'Y')", S),
    ("HAS_CHARACTERISTICS", "CaseWhen(IsNull(ADJ_CHAR.ADJ_ID), 'N', 'Y')", S),
    ("SA_IS_ACTIVE", "CaseWhen(CI_SA.SA_STATUS_FLG == '20', 'Y', 'N')", S),
    ("SA_IS_REVENUE_BEARING", "CaseWhen(CI_SA_TYPE.SPECIAL_ROLE_FLG == 'PA' or CI_SA_TYPE.SPECIAL_ROLE_FLG == 'CD' or CI_SA_TYPE.SPECIAL_ROLE_FLG == 'WO' or CI_SA_TYPE.SPECIAL_ROLE_FLG == 'LO' or CI_SA_TYPE.SPECIAL_ROLE_FLG == 'NB', 'N', 'Y')", S),
    ("CUSTOMER_IS_PERSON", "CaseWhen(CI_PER.PER_OR_BUS_FLG == 'P', 'Y', 'N')", S),
    ("ADJ_DIST", "CountDistinct(CI_ADJ.ADJ_ID, 'Current')", L),
    ("SA_DIST", "CountDistinct(CI_ADJ.SA_ID, 'Current')", L),
    ("ACCT_DIST", "CountDistinct(CI_SA.ACCT_ID, 'Current')", L),
    ("AP_REQ_DIST", "CountDistinct(CI_ADJ_APREQ.AP_REQ_ID, 'Current')", L),
]

SETS: domain_schema.Sets = [
    ("SET_ADJUSTMENT", "1.) Adjustment", [
        ("ADJ_ID", "Adjustment ID", "CI_ADJ.ADJ_ID"),
        ("ADJ_SA_ID", "Service Agreement ID", "CI_ADJ.SA_ID"),
        ("ADJ_TYPE_CD", "Adjustment Type Code", "CI_ADJ.ADJ_TYPE_CD"),
        ("ADJ_TYPE_DESCR", "Adjustment Type", "CI_ADJ_TYPE_L.DESCR"),
        ("ADJ_TYPE_DESCR_ON_BILL", "Adjustment Type Description On Bill", "CI_ADJ_TYPE_L.DESCR_ON_BILL"),
        ("ADJ_STATUS_FLG", "Adjustment Status Code", "CI_ADJ.ADJ_STATUS_FLG"),
        ("ADJ_STATUS_DESCR", "Adjustment Status", "ADJ_STAT_L.DESCR"),
        ("ADJ_CRE_DT", "Adjustment Created Date", "CI_ADJ.CRE_DT"),
        ("ADJ_AMT", "Adjustment Amount", "CI_ADJ.ADJ_AMT"),
        ("BASE_AMT", "Base Amount", "CI_ADJ.BASE_AMT"),
        ("ADJ_CURRENCY_CD", "Currency Code", "CI_ADJ.CURRENCY_CD"),
        ("ADJ_CURRENCY_DESCR", "Currency", "CI_CURRENCY_CD_L.DESCR"),
        ("CAN_RSN_CD", "Cancel Reason Code", "CI_ADJ.CAN_RSN_CD"),
        ("CAN_RSN_DESCR", "Cancel Reason", "CI_ADJ_CAN_RSN_L.DESCR"),
        ("ADJ_COMMENTS", "Adjustment Comments", "CI_ADJ.COMMENTS"),
        ("GEN_REF_DT", "General Reference Date", "CI_ADJ.GEN_REF_DT"),
        ("XFER_ADJ_ID", "Transfer Adjustment ID", "CI_ADJ.XFER_ADJ_ID"),
        ("BEHALF_SA_ID", "On Behalf Of Service Agreement ID", "CI_ADJ.BEHALF_SA_ID"),
        ("APPR_REQ_ID", "Approval Request ID", "CI_ADJ.APPR_REQ_ID"),
        ("ADJ_ILM_DT", "ILM Date", "CI_ADJ.ILM_DT"),
        ("ADJ_ILM_ARCH_SW", "ILM Archive Switch", "CI_ADJ.ILM_ARCH_SW"),
    ]),
    ("SET_ADJ_TYPE", "1.1) Adjustment Type Configuration", [
        ("AP_REQ_TYPE_CD", "A/P Request Type", "CI_ADJ_TYPE.AP_REQ_TYPE_CD"),
        ("TYPE_DST_ID", "Distribution Code", "CI_ADJ_TYPE.DST_ID"),
        ("TYPE_DST_DESCR", "Distribution Code Description", "CI_DST_CODE_L.DESCR"),
        ("TYPE_CURRENCY_CD", "Type Currency Code", "CI_ADJ_TYPE.CURRENCY_CD"),
        ("SYNCH_CUR_SW", "Sync Current Amount Switch", "CI_ADJ_TYPE.SYNCH_CUR_SW"),
        ("DFLT_AMT", "Default Amount", "CI_ADJ_TYPE.DFLT_AMT"),
        ("AP_1099_FLG", "1099 Flag", "CI_ADJ_TYPE.AP_1099_FLG"),
        ("PRT_DFLT_SW", "Print By Default Switch", "CI_ADJ_TYPE.PRT_DFLT_SW"),
        ("AD_FRZ_OPT_FLG", "Freeze Option Code", "CI_ADJ_TYPE.AD_FRZ_OPT_FLG"),
        ("AD_FRZ_OPT_DESCR", "Freeze Option", "FRZ_OPT_L.DESCR"),
        ("ADJ_AMT_TYPE_FLG", "Amount Type Code", "CI_ADJ_TYPE.ADJ_AMT_TYPE_FLG"),
        ("ADJ_AMT_TYPE_DESCR", "Amount Type", "AMT_TYPE_L.DESCR"),
        ("TYPE_APPR_PROF_CD", "Approval Profile Code", "CI_ADJ_TYPE.APPR_PROF_CD"),
        ("TYPE_APPR_PROF_DESCR", "Approval Profile", "TYPE_APPR_PROF_L.DESCR"),
        ("TYPE_CIS_DIVISION", "Type CIS Division", "CI_ADJ_TYPE.CIS_DIVISION"),
    ]),
    ("SET_ADJ_FT", "1.2) Adjustment Financial Transaction", [
        ("FT_COUNT", "FT Count", "ADJ_FT.FT_COUNT"),
        ("FROZEN_FT_ID", "Frozen FT ID", "ADJ_FT.FROZEN_FT_ID"),
        ("CANCEL_FT_ID", "Cancellation FT ID", "ADJ_FT.CANCEL_FT_ID"),
        ("FREEZE_DTTM", "Freeze Date/Time", "ADJ_FT.FREEZE_DTTM"),
        ("FREEZE_USER_ID", "Frozen By User", "ADJ_FT.FREEZE_USER_ID"),
        ("CANCEL_DTTM", "Cancellation Date/Time", "ADJ_FT.CANCEL_DTTM"),
        ("CANCEL_USER_ID", "Canceled By User", "ADJ_FT.CANCEL_USER_ID"),
        ("ACCOUNTING_DT", "Accounting Date", "ADJ_FT.ACCOUNTING_DT"),
        ("ARS_DT", "Arrears Date", "ADJ_FT.ARS_DT"),
        ("FT_GL_DIVISION", "GL Division", "ADJ_FT.GL_DIVISION"),
        ("FT_BILL_ID", "Bill ID", "ADJ_FT.BILL_ID"),
        ("FROZEN_CUR_AMT", "Frozen Current Amount", "ADJ_FT.FROZEN_CUR_AMT"),
        ("FROZEN_TOT_AMT", "Frozen Payoff Amount", "ADJ_FT.FROZEN_TOT_AMT"),
        ("NET_CUR_AMT", "Net Current Amount (After Cancellation)", "ADJ_FT.NET_CUR_AMT"),
        ("NET_TOT_AMT", "Net Payoff Amount (After Cancellation)", "ADJ_FT.NET_TOT_AMT"),
        ("GL_DISTRIB_STATUS", "GL Distribution Status", "ADJ_FT.GL_DISTRIB_STATUS"),
        ("XFER_TO_GL_DT", "Transferred To GL Date", "ADJ_FT.XFER_TO_GL_DT"),
        ("MATCH_EVT_ID", "Match Event ID", "ADJ_FT.MATCH_EVT_ID"),
        ("SHOW_ON_BILL_SW", "Show On Bill Switch", "ADJ_FT.SHOW_ON_BILL_SW"),
        ("NOT_IN_ARS_SW", "Not In Arrears Switch", "ADJ_FT.NOT_IN_ARS_SW"),
    ]),
    ("SET_ADJ_CHAR", "1.3) Adjustment Characteristics", [
        ("CHAR_COUNT", "Characteristic Count", "ADJ_CHAR.CHAR_COUNT"),
        ("CHARACTERISTICS", "Characteristics (Type = Value; ...)", "ADJ_CHAR.CHARACTERISTICS"),
    ]),
    ("SET_APPROVAL", "1.4) Approval Request", [
        ("APPR_REQ_ID_REQ", "Approval Request ID (Request)", "CI_APPR_REQ.APPR_REQ_ID"),
        ("APPR_PROF_CD", "Approval Profile Code", "CI_APPR_REQ.APPR_PROF_CD"),
        ("APPR_PROF_DESCR", "Approval Profile", "CI_APPR_PROF_L.DESCR"),
        ("APPR_BUS_OBJ_CD", "Approval Business Object", "CI_APPR_REQ.BUS_OBJ_CD"),
        ("APPR_BO_STATUS_CD", "Approval Status Code", "CI_APPR_REQ.BO_STATUS_CD"),
        ("APPR_BO_STATUS_DESCR", "Approval Status", "APPR_STAT_L.DESCR"),
    ]),
    ("SET_TRANSFER", "1.5) Transfer Partner Adjustment", [
        ("XFER_PARTNER_ADJ_ID", "Partner Adjustment ID", "CI_ADJ_XFER.ADJ_ID"),
        ("XFER_PARTNER_SA_ID", "Partner Service Agreement ID", "CI_ADJ_XFER.SA_ID"),
        ("XFER_PARTNER_ACCT_ID", "Partner Account ID", "CI_SA_XFER.ACCT_ID"),
        ("XFER_PARTNER_SA_TYPE_CD", "Partner SA Type Code", "CI_SA_XFER.SA_TYPE_CD"),
        ("XFER_PARTNER_ADJ_TYPE_CD", "Partner Adjustment Type Code", "CI_ADJ_XFER.ADJ_TYPE_CD"),
        ("XFER_PARTNER_ADJ_TYPE_DESCR", "Partner Adjustment Type", "CI_ADJ_TYPE_L_XFER.DESCR"),
        ("XFER_PARTNER_STATUS_FLG", "Partner Adjustment Status Code", "CI_ADJ_XFER.ADJ_STATUS_FLG"),
        ("XFER_PARTNER_AMT", "Partner Adjustment Amount", "CI_ADJ_XFER.ADJ_AMT"),
        ("XFER_PARTNER_CRE_DT", "Partner Created Date", "CI_ADJ_XFER.CRE_DT"),
    ]),
    ("SET_REQUEST", "2.) A/P Request", [
        ("AP_REQ_ID", "A/P Request ID", "CI_ADJ_APREQ.AP_REQ_ID"),
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
        ("PYMNT_METHOD_DESCR", "Payment Method", "PAY_METHOD_L.DESCR"),
        ("REQ_BATCH_CD", "Batch Control", "CI_ADJ_APREQ.BATCH_CD"),
        ("REQ_BATCH_NBR", "Batch Number", "CI_ADJ_APREQ.BATCH_NBR"),
        ("PAYEE_NAME", "Payee Name", "CI_ADJ_APREQ.ENTITY_NAME"),
        ("PAYEE_ADDRESS1", "Payee Address 1", "CI_ADJ_APREQ.ADDRESS1"),
        ("PAYEE_ADDRESS2", "Payee Address 2", "CI_ADJ_APREQ.ADDRESS2"),
        ("PAYEE_ADDRESS3", "Payee Address 3", "CI_ADJ_APREQ.ADDRESS3"),
        ("PAYEE_ADDRESS4", "Payee Address 4", "CI_ADJ_APREQ.ADDRESS4"),
        ("PAYEE_CITY", "Payee City", "CI_ADJ_APREQ.CITY"),
        ("PAYEE_COUNTY", "Payee County", "CI_ADJ_APREQ.COUNTY"),
        ("PAYEE_STATE", "Payee State", "CI_ADJ_APREQ.STATE"),
        ("PAYEE_POSTAL", "Payee Postal", "CI_ADJ_APREQ.POSTAL"),
        ("PAYEE_COUNTRY", "Payee Country", "CI_ADJ_APREQ.COUNTRY"),
    ]),
    ("SET_SA", "3.) Service Agreement", [
        ("SA_ID", "Service Agreement ID", "CI_SA.SA_ID"),
        ("SA_CIS_DIVISION", "SA CIS Division", "CI_SA.CIS_DIVISION"),
        ("SA_TYPE_CD", "SA Type Code", "CI_SA.SA_TYPE_CD"),
        ("SA_TYPE_DESCR", "SA Type", "CI_SA_TYPE_L.DESCR"),
        ("SA_TYPE_DESCR_ON_BILL", "SA Type Description On Bill", "CI_SA_TYPE_L.DFLT_DESCR_ON_BILL"),
        ("SA_STATUS_FLG", "SA Status Code", "CI_SA.SA_STATUS_FLG"),
        ("SA_STATUS_DESCR", "SA Status", "SA_STAT_L.DESCR"),
        ("SA_START_DT", "SA Start Date", "CI_SA.START_DT"),
        ("SA_END_DT", "SA End Date", "CI_SA.END_DT"),
        ("START_OPT_CD", "Start Option", "CI_SA.START_OPT_CD"),
        ("STRT_RSN_FLG", "Start Reason Code", "CI_SA.STRT_RSN_FLG"),
        ("STRT_RSN_DESCR", "Start Reason", "STRT_RSN_L.DESCR"),
        ("STOP_RSN_FLG", "Stop Reason Code", "CI_SA.STOP_RSN_FLG"),
        ("STOP_RSN_DESCR", "Stop Reason", "STOP_RSN_L.DESCR"),
        ("STRT_REQED_BY", "Start Requested By", "CI_SA.STRT_REQED_BY"),
        ("STOP_REQED_BY", "Stop Requested By", "CI_SA.STOP_REQED_BY"),
        ("CHAR_PREM_ID", "Characteristic Premise ID", "CI_SA.CHAR_PREM_ID"),
        ("SA_CURRENCY_CD", "SA Currency Code", "CI_SA.CURRENCY_CD"),
        ("OLD_ACCT_ID", "Old Account ID", "CI_SA.OLD_ACCT_ID"),
        ("SA_REL_ID", "SA Relationship ID", "CI_SA.SA_REL_ID"),
        ("BUS_ACTIVITY_DESC", "Business Activity", "CI_SA.BUS_ACTIVITY_DESC"),
        ("TOT_TO_BILL_AMT", "Total Amount To Bill", "CI_SA.TOT_TO_BILL_AMT"),
        ("SIC_CD", "SIC Code", "CI_SA.SIC_CD"),
    ]),
    ("SET_SA_TYPE", "3.1) SA Type Configuration", [
        ("SVC_TYPE_CD", "Service Type Code", "CI_SA_TYPE.SVC_TYPE_CD"),
        ("SVC_TYPE_DESCR", "Service Type", "CI_SVC_TYPE_L.DESCR"),
        ("SPECIAL_ROLE_FLG", "Special Role", "CI_SA_TYPE.SPECIAL_ROLE_FLG"),
        ("REV_CL_CD", "Revenue Class", "CI_SA_TYPE.REV_CL_CD"),
        ("DEBT_CL_CD", "Debt Class", "CI_SA_TYPE.DEBT_CL_CD"),
        ("SA_TYPE_DST_ID", "SA Type Distribution Code", "CI_SA_TYPE.DST_ID"),
        ("SA_TYPE_GL_DIVISION", "SA Type GL Division", "CI_SA_TYPE.GL_DIVISION"),
        ("BILL_PERIOD_CD", "Bill Period", "CI_SA_TYPE.BILL_PERIOD_CD"),
        ("DEP_CL_CD", "Deposit Class", "CI_SA_TYPE.DEP_CL_CD"),
        ("ADJ_TYPE_NSF", "NSF Adjustment Type", "CI_SA_TYPE.ADJ_TYPE_NSF"),
        ("LATE_PAY_CHARGE_SW", "Late Payment Charge Switch", "CI_SA_TYPE.LATE_PAY_CHARGE_SW"),
    ]),
    ("SET_ACCOUNT", "4.) Account", [
        ("ACCT_ID", "Account ID", "CI_ACCT.ACCT_ID"),
        ("CIS_DIVISION", "CIS Division", "CI_ACCT.CIS_DIVISION"),
        ("CIS_DIVISION_DESCR", "CIS Division Description", "CI_CIS_DIVISION_L.DESCR"),
        ("CUST_CL_CD", "Customer Class Code", "CI_ACCT.CUST_CL_CD"),
        ("CUST_CL_DESCR", "Customer Class", "CI_CUST_CL_L.DESCR"),
        ("COLL_CL_CD", "Collection Class Code", "CI_ACCT.COLL_CL_CD"),
        ("COLL_CL_DESCR", "Collection Class", "CI_COLL_CL_L.DESCR"),
        ("BILL_CYC_CD", "Bill Cycle Code", "CI_ACCT.BILL_CYC_CD"),
        ("BILL_CYC_DESCR", "Bill Cycle", "CI_BILL_CYC_L.DESCR"),
        ("ACCT_MGMT_GRP_CD", "Account Management Group Code", "CI_ACCT.ACCT_MGMT_GRP_CD"),
        ("ACCT_MGMT_GRP_DESCR", "Account Management Group", "CI_ACCT_MGMT_GR_L.DESCR"),
        ("BUD_PLAN_CD", "Budget Plan Code", "CI_ACCT.BUD_PLAN_CD"),
        ("BUD_PLAN_DESCR", "Budget Plan", "CI_BUD_PLAN_L.DESCR"),
        ("ACCT_SETUP_DT", "Account Set Up Date", "CI_ACCT.SETUP_DT"),
        ("ACCT_CURRENCY_CD", "Account Currency Code", "CI_ACCT.CURRENCY_CD"),
        ("CR_REVIEW_DT", "Last Credit Review Date", "CI_ACCT.CR_REVIEW_DT"),
        ("POSTPONE_CR_RVW_DT", "Postpone Credit Review Until", "CI_ACCT.POSTPONE_CR_RVW_DT"),
        ("BILL_AFTER_DT", "Bill After Date", "CI_ACCT.BILL_AFTER_DT"),
        ("MAILING_PREM_ID", "Mailing Premise ID", "CI_ACCT.MAILING_PREM_ID"),
        ("ACCESS_GRP_CD", "Access Group", "CI_ACCT.ACCESS_GRP_CD"),
    ]),
    ("SET_CUSTOMER", "5.) Main Customer", [
        ("PER_ID", "Person ID", "CI_ACCT_PER.PER_ID"),
        ("MAIN_CUSTOMER_NAME", "Main Customer Name", "CI_PER_NAME.ENTITY_NAME"),
        ("MAIN_CUSTOMER_NAME_UPPER", "Main Customer Name (Upper)", "CI_PER_NAME.ENTITY_NAME_UPR"),
        ("PER_OR_BUS_FLG", "Person Or Business Code", "CI_PER.PER_OR_BUS_FLG"),
        ("PER_OR_BUS_DESCR", "Person Or Business", "PER_BUS_L.DESCR"),
        ("EMAILID", "Email", "CI_PER.EMAILID"),
        ("PER_LANGUAGE_CD", "Language", "CI_PER.LANGUAGE_CD"),
        ("LS_SL_FLG", "Life Support / Sensitive Load", "CI_PER.LS_SL_FLG"),
        ("ACCT_REL_TYPE_CD", "Account Relationship Type", "CI_ACCT_PER.ACCT_REL_TYPE_CD"),
        ("FIN_RESP_SW", "Financially Responsible Switch", "CI_ACCT_PER.FIN_RESP_SW"),
        ("BILL_RTE_TYPE_CD", "Bill Route Type", "CI_ACCT_PER.BILL_RTE_TYPE_CD"),
        ("WEB_ACCESS_FLG", "Web Access", "CI_ACCT_PER.WEB_ACCESS_FLG"),
        ("RECEIVE_COPY_SW", "Receives Bill Copy Switch", "CI_ACCT_PER.RECEIVE_COPY_SW"),
    ]),
    ("SET_PREMISE", "6.) Premise", [
        ("PREM_ID", "Premise ID", "CI_PREM.PREM_ID"),
        ("PREM_TYPE_CD", "Premise Type Code", "CI_PREM.PREM_TYPE_CD"),
        ("PREM_TYPE_DESCR", "Premise Type", "CI_PREM_TYPE_L.DESCR"),
        ("PREM_CIS_DIVISION", "Premise CIS Division", "CI_PREM.CIS_DIVISION"),
        ("PREM_ADDRESS1", "Premise Address 1", "CI_PREM.ADDRESS1"),
        ("PREM_ADDRESS2", "Premise Address 2", "CI_PREM.ADDRESS2"),
        ("PREM_ADDRESS3", "Premise Address 3", "CI_PREM.ADDRESS3"),
        ("PREM_ADDRESS4", "Premise Address 4", "CI_PREM.ADDRESS4"),
        ("PREM_CITY", "Premise City", "CI_PREM.CITY"),
        ("PREM_COUNTY", "Premise County", "CI_PREM.COUNTY"),
        ("PREM_STATE", "Premise State", "CI_PREM.STATE"),
        ("PREM_POSTAL", "Premise Postal", "CI_PREM.POSTAL"),
        ("PREM_COUNTRY", "Premise Country", "CI_PREM.COUNTRY"),
        ("PREM_IN_CITY_LIMIT", "Premise In City Limit", "CI_PREM.IN_CITY_LIMIT"),
        ("PREM_GEO_CODE", "Premise Geographic Code", "CI_PREM.GEO_CODE"),
        ("TREND_AREA_CD", "Trend Area", "CI_PREM.TREND_AREA_CD"),
        ("LL_ID", "Landlord ID", "CI_PREM.LL_ID"),
        ("PRNT_PREM_ID", "Parent Premise ID", "CI_PREM.PRNT_PREM_ID"),
        ("PREM_MAIL_ADDR_SW", "Premise Is Mailing Address Switch", "CI_PREM.MAIL_ADDR_SW"),
        ("MAIL_ADDRESS1", "Mailing Address 1", "CI_PREM_MAIL.ADDRESS1"),
        ("MAIL_ADDRESS2", "Mailing Address 2", "CI_PREM_MAIL.ADDRESS2"),
        ("MAIL_CITY", "Mailing City", "CI_PREM_MAIL.CITY"),
        ("MAIL_STATE", "Mailing State", "CI_PREM_MAIL.STATE"),
        ("MAIL_POSTAL", "Mailing Postal", "CI_PREM_MAIL.POSTAL"),
    ]),
    ("SET_FLAGS", "7.) Flags And Formulas", [
        ("IS_FROZEN", "Is Frozen", "IS_FROZEN"),
        ("IS_CANCELED", "Is Canceled", "IS_CANCELED"),
        ("IS_OPEN", "Is Open (Not Frozen, Not Canceled)", "IS_OPEN"),
        ("OPEN_OVER_30_DAYS", "Open Over 30 Days", "ADJ_AGE.OPEN_OVER_30_DAYS"),
        ("AMOUNT_DIRECTION", "Amount Direction (Credit / Debit)", "AMOUNT_DIRECTION"),
        ("IS_TRANSFER", "Is Transfer", "IS_TRANSFER"),
        ("IS_ON_BEHALF", "Is On Behalf Of Another SA", "IS_ON_BEHALF"),
        ("HAS_APPROVAL_REQUEST", "Has Approval Request", "HAS_APPROVAL_REQUEST"),
        ("IS_AP_ADJ_TYPE", "Is A/P (Refund) Adjustment Type", "IS_AP_ADJ_TYPE"),
        ("HAS_AP_REQUEST", "Has A/P Request", "HAS_AP_REQUEST"),
        ("AP_ACTION_NEEDED", "A/P Action Needed (Request Canceled, Adjustment Open)", "AP_ACTION_NEEDED"),
        ("PAID_BUT_ADJ_CANCELED", "Paid But Adjustment Canceled", "PAID_BUT_ADJ_CANCELED"),
        ("HAS_FT", "Has Financial Transaction", "HAS_FT"),
        ("HAS_CHARACTERISTICS", "Has Characteristics", "HAS_CHARACTERISTICS"),
        ("SA_IS_ACTIVE", "SA Is Active", "SA_IS_ACTIVE"),
        ("SA_IS_REVENUE_BEARING", "SA Is Revenue Bearing", "SA_IS_REVENUE_BEARING"),
        ("CUSTOMER_IS_PERSON", "Customer Is A Person", "CUSTOMER_IS_PERSON"),
        ("DAYS_OLD", "Days Since Created", "ADJ_AGE.DAYS_OLD"),
        ("DAYS_TO_FREEZE", "Days From Created To Frozen", "ADJ_FT.DAYS_TO_FREEZE"),
        ("ADJ_DIST", "Distinct Adjustments", "ADJ_DIST"),
        ("SA_DIST", "Distinct Service Agreements", "SA_DIST"),
        ("ACCT_DIST", "Distinct Accounts", "ACCT_DIST"),
        ("AP_REQ_DIST", "Distinct A/P Requests", "AP_REQ_DIST"),
    ]),
]

MEASURES: domain_schema.Measures = [
    ("ADJ_COUNT", "Adjustment Count", "CI_ADJ.ADJ_ID", "CountDistinct"),
    ("ADJ_AMT_TOTAL", "Adjustment Amount Total", "CI_ADJ.ADJ_AMT", "Sum"),
    ("BASE_AMT_TOTAL", "Base Amount Total", "CI_ADJ.BASE_AMT", "Sum"),
    ("FROZEN_CUR_AMT_TOTAL", "Frozen Current Amount Total", "ADJ_FT.FROZEN_CUR_AMT", "Sum"),
    ("NET_CUR_AMT_TOTAL", "Net Current Amount Total (After Cancellation)", "ADJ_FT.NET_CUR_AMT", "Sum"),
    ("NET_TOT_AMT_TOTAL", "Net Payoff Amount Total (After Cancellation)", "ADJ_FT.NET_TOT_AMT", "Sum"),
    ("PAID_AMT_TOTAL", "A/P Paid Amount Total", "CI_ADJ_APREQ.PAID_AMT", "Sum"),
    ("AP_REQ_COUNT", "A/P Request Count", "CI_ADJ_APREQ.AP_REQ_ID", "CountDistinct"),
    ("SA_COUNT", "Service Agreement Count", "CI_ADJ.SA_ID", "CountDistinct"),
    ("ACCT_COUNT", "Account Count", "CI_SA.ACCT_ID", "CountDistinct"),
]


def schema(ds: str) -> str:
    return domain_schema.schema(ds, "CI_ADJ", TABLES, JOINS, CALCULATED, SETS, MEASURES, DERIVED)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ds", required=True, help="the org's datasource id, e.g. Origin_DEV_DS")
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(schema(a.ds), encoding="utf-8")
    v = pathlib.Path(__file__).resolve().parent / "validate_domain_schema.py"
    r = subprocess.run([sys.executable, str(v), str(a.out)], capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise SystemExit(f"schema validation failed:\n{r.stdout}{r.stderr}")
    print(f"wrote {a.out} for {a.ds}: {len(TABLES)} tables, {len(DERIVED)} derived, {len(JOINS)} joins, "
          f"{sum(len(s[2]) for s in SETS) + len(MEASURES)} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
