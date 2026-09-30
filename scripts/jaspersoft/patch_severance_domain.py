#!/usr/bin/env python3
"""Give the Severance Process domain the field activity each event created, and the template's rules.

The offering's domain is at severance EVENT grain (CI_SEV_PROC -> CI_SEV_EVT) with the template's
LABEL only. The legacy Inventory library read two more base-product tables (2026-09-24 gap read):
`CI_SEV_EVT_FA` (which CCB field activity a cut-off / reconnect event created: process id + event
seq -> FA id, one-to-one by key) and `CI_SEV_PROC_TMP` (the template's auto-cancel switch and
cancel-criteria / post-cancel algorithms). Through the FA id the CCB field activity itself
(`CI_FA`: type, status, priority, scheduled and created times, dispatch group, cancel reason)
answers "was the disconnect dispatched, when, and did it complete" per event. Every new join is
outer, so the row count is unchanged.

patch_schema() takes the org's exported schema.data and returns it with three tables, one label
table, one status lookup, the joins, the join-tree fields, two calculated flags and two sets
added; nothing existing is touched. Applied live by `jrs_domain_patch_apply.py`.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import domain_schema  # noqa: E402

S, T, N = "java.lang.String", "java.sql.Timestamp", "java.math.BigDecimal"
TABLES = {
    "CI_SEV_PROC_TMP": ("CI_SEV_PROC_TMP", [("SEV_PROC_TMPL_CD", S), ("AUTO_CANCEL_SW", S), ("CAN_CRIT_ALG_CD", S), ("POST_CAN_ALG_CD", S), ("VERSION", N)]),
    "CI_SEV_EVT_FA": ("CI_SEV_EVT_FA", [("SEV_PROC_ID", S), ("EVT_SEQ", N), ("FA_ID", S), ("VERSION", N)]),
    "CI_FA": ("CI_FA", [("FA_ID", S), ("FA_TYPE_CD", S), ("FA_STATUS_FLG", S), ("FA_PRIORITY_FLG", S), ("SCHED_DTTM", T), ("CRE_DTTM", T),
                        ("DISP_GRP_CD", S), ("FO_ID", S), ("FA_CAN_RSN_CD", S), ("FA_CREATED_BY_FLG", S), ("ELIG_DISPATCH_SW", S), ("USER_ID", S),
                        ("FA_EXT_ID", S), ("FA_INT_STATUS_FLG", S), ("SP_ID", S), ("INSTRUCTIONS", S)]),
    "CI_FA_TYPE_L": ("CI_FA_TYPE_L", [("FA_TYPE_CD", S), ("LANGUAGE_CD", S), ("DESCR", S)]),
    "SEV_FA_STAT_L": ("CI_LOOKUP_VAL_L", [("FIELD_NAME", S), ("FIELD_VALUE", S), ("LANGUAGE_CD", S), ("DESCR", S)]),
}
JOINS = [
    ("CI_SEV_PROC.SEV_PROC_TMPL_CD == CI_SEV_PROC_TMP.SEV_PROC_TMPL_CD", "CI_SEV_PROC", "CI_SEV_PROC_TMP"),
    ("CI_SEV_EVT.SEV_PROC_ID == CI_SEV_EVT_FA.SEV_PROC_ID and CI_SEV_EVT.EVT_SEQ == CI_SEV_EVT_FA.EVT_SEQ", "CI_SEV_EVT", "CI_SEV_EVT_FA"),
    ("CI_SEV_EVT_FA.FA_ID == CI_FA.FA_ID", "CI_SEV_EVT_FA", "CI_FA"),
    ("CI_FA.FA_TYPE_CD == CI_FA_TYPE_L.FA_TYPE_CD and CI_FA_TYPE_L.LANGUAGE_CD == 'ENG'", "CI_FA", "CI_FA_TYPE_L"),
    ("CI_FA.FA_STATUS_FLG == SEV_FA_STAT_L.FIELD_VALUE and SEV_FA_STAT_L.FIELD_NAME == 'FA_STATUS_FLG' and SEV_FA_STAT_L.LANGUAGE_CD == 'ENG'", "CI_FA", "SEV_FA_STAT_L"),
]
CALCULATED = [
    ("SEV_EVT_HAS_FA", "CaseWhen(IsNull(CI_SEV_EVT_FA.FA_ID), 'N', 'Y')", S),
    ("SEV_FA_DAYS_TRIGGER_TO_SCHEDULE", "ElapsedDays(CI_FA.SCHED_DTTM, CI_SEV_EVT.TRIGGER_DT)", N),
]
SETS = [
    ("SET_SEV_FA", "1.) Severance Field Activity", [
        ("SEV_FA_ID", "Field Activity ID", "CI_SEV_EVT_FA.FA_ID"),
        ("SEV_FA_TYPE_CD", "Field Activity Type Code", "CI_FA.FA_TYPE_CD"),
        ("SEV_FA_TYPE_DESCR", "Field Activity Type", "CI_FA_TYPE_L.DESCR"),
        ("SEV_FA_STATUS_FLG", "Field Activity Status Code", "CI_FA.FA_STATUS_FLG"),
        ("SEV_FA_STATUS_DESCR", "Field Activity Status", "SEV_FA_STAT_L.DESCR"),
        ("SEV_FA_PRIORITY_FLG", "Field Activity Priority", "CI_FA.FA_PRIORITY_FLG"),
        ("SEV_FA_SCHED_DTTM", "Field Activity Scheduled Date/Time", "CI_FA.SCHED_DTTM"),
        ("SEV_FA_CRE_DTTM", "Field Activity Created Date/Time", "CI_FA.CRE_DTTM"),
        ("SEV_FA_DISP_GRP_CD", "Dispatch Group", "CI_FA.DISP_GRP_CD"),
        ("SEV_FA_FO_ID", "Field Order ID", "CI_FA.FO_ID"),
        ("SEV_FA_CAN_RSN_CD", "Field Activity Cancel Reason Code", "CI_FA.FA_CAN_RSN_CD"),
        ("SEV_FA_CREATED_BY_FLG", "Field Activity Created By", "CI_FA.FA_CREATED_BY_FLG"),
        ("SEV_FA_ELIG_DISPATCH_SW", "Eligible For Dispatch Switch", "CI_FA.ELIG_DISPATCH_SW"),
        ("SEV_FA_USER_ID", "Field Activity User", "CI_FA.USER_ID"),
        ("SEV_FA_EXT_ID", "Field Activity External ID", "CI_FA.FA_EXT_ID"),
        ("SEV_FA_INT_STATUS_FLG", "Field Activity Intermediate Status", "CI_FA.FA_INT_STATUS_FLG"),
        ("SEV_FA_SP_ID", "Field Activity Service Point ID", "CI_FA.SP_ID"),
        ("SEV_FA_INSTRUCTIONS", "Field Activity Instructions", "CI_FA.INSTRUCTIONS"),
        ("SEV_EVT_HAS_FA", "Event Created A Field Activity", "SEV_EVT_HAS_FA"),
        ("SEV_FA_DAYS_TRIGGER_TO_SCHEDULE", "Days From Event Trigger To FA Schedule", "SEV_FA_DAYS_TRIGGER_TO_SCHEDULE"),
    ]),
    ("SET_SEV_TEMPLATE", "1.) Severance Template Rules", [
        ("SEV_TMPL_AUTO_CANCEL_SW", "Template Auto Cancel Switch", "CI_SEV_PROC_TMP.AUTO_CANCEL_SW"),
        ("SEV_TMPL_CAN_CRIT_ALG_CD", "Template Cancel Criteria Algorithm", "CI_SEV_PROC_TMP.CAN_CRIT_ALG_CD"),
        ("SEV_TMPL_POST_CAN_ALG_CD", "Template Post Cancel Algorithm", "CI_SEV_PROC_TMP.POST_CAN_ALG_CD"),
    ]),
]


def patch_schema(schema: str) -> str:
    return domain_schema.add_to_schema(schema, TABLES, JOINS, CALCULATED, SETS, guard_id="CI_SEV_EVT_FA")
