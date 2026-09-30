#!/usr/bin/env python3
"""Give the Field Activity domain the CCB field activity behind each MDM activity, additively.

Measured on Ellensburg 2026-09-24 (the earlier note that the two do not link tested FA_EXT_ID and
the BO external reference, which are indeed empty): `D1_ACTIVITY_IDENTIFIER` of type `D1RI`
carries the CCB field activity id and resolves to `CI_FA` on 101,668 of 101,668 rows, ONE per
activity (max 1), up to 8 activities per FA; 33,886 of the domain's 37,057 field activities carry
one. So activity -> identifier (D1RI) -> CI_FA adds the CCB side (type, C/P/X status, priority,
scheduled and created times, dispatch group, field order, cancel and reschedule reasons,
instructions) at activity grain without fan-out, and every join is outer. Verify the D1RI resolve
rate on each client before promoting (the apply tool's probe shows how many rows carry an FA).
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import domain_schema  # noqa: E402

S, T, N = "java.lang.String", "java.sql.Timestamp", "java.math.BigDecimal"
LBL = [("LANGUAGE_CD", S), ("DESCR", S)]
TABLES: domain_schema.Tables = {
    "CIS_FA_IDENTIFIER": ("D1_ACTIVITY_IDENTIFIER", [("D1_ACTIVITY_ID", S), ("ACTIVITY_ID_TYPE_FLG", S), ("ID_VALUE", S)]),
    "CIS_FA": ("CI_FA", [("FA_ID", S), ("FA_TYPE_CD", S), ("FA_STATUS_FLG", S), ("FA_PRIORITY_FLG", S), ("SCHED_DTTM", T), ("CRE_DTTM", T),
                         ("DISP_GRP_CD", S), ("FO_ID", S), ("FA_CAN_RSN_CD", S), ("FA_RESCHED_RSN_CD", S), ("FA_CREATED_BY_FLG", S), ("ELIG_DISPATCH_SW", S),
                         ("USER_ID", S), ("FA_INT_STATUS_FLG", S), ("SP_ID", S), ("INSTRUCTIONS", S), ("DESCRLONG", S)]),
    "CIS_FA_TYPE_L": ("CI_FA_TYPE_L", [("FA_TYPE_CD", S)] + LBL),
    "CIS_FA_STAT_L": ("CI_LOOKUP_VAL_L", [("FIELD_NAME", S), ("FIELD_VALUE", S), ("LANGUAGE_CD", S), ("DESCR", S)]),
    "CIS_DISP_GRP_L": ("CI_DISP_GRP_L", [("DISP_GRP_CD", S)] + LBL),
    "CIS_FA_CAN_RSN_L": ("CI_FA_CAN_RSN_L", [("FA_CAN_RSN_CD", S)] + LBL),
    "CIS_FO": ("CI_FO", [("FO_ID", S), ("PREM_ID", S), ("WORKED_BY", S), ("REP_CD", S), ("DISP_GRP_CD", S), ("SCHED_DTTM", T), ("SCHED_END_DTTM", T),
                         ("FO_STATUS_FLG", S), ("WORK_DTTM", T), ("FA_RESCHED_RSN_CD", S), ("FA_CAN_RSN_CD", S)]),
}
JOINS = [
    ("D1_ACTIVITY.D1_ACTIVITY_ID == CIS_FA_IDENTIFIER.D1_ACTIVITY_ID and CIS_FA_IDENTIFIER.ACTIVITY_ID_TYPE_FLG == 'D1RI'", "D1_ACTIVITY", "CIS_FA_IDENTIFIER"),
    ("CIS_FA_IDENTIFIER.ID_VALUE == CIS_FA.FA_ID", "CIS_FA_IDENTIFIER", "CIS_FA"),
    ("CIS_FA.FA_TYPE_CD == CIS_FA_TYPE_L.FA_TYPE_CD and CIS_FA_TYPE_L.LANGUAGE_CD == 'ENG'", "CIS_FA", "CIS_FA_TYPE_L"),
    ("CIS_FA.FA_STATUS_FLG == CIS_FA_STAT_L.FIELD_VALUE and CIS_FA_STAT_L.FIELD_NAME == 'FA_STATUS_FLG' and CIS_FA_STAT_L.LANGUAGE_CD == 'ENG'", "CIS_FA", "CIS_FA_STAT_L"),
    ("CIS_FA.DISP_GRP_CD == CIS_DISP_GRP_L.DISP_GRP_CD and CIS_DISP_GRP_L.LANGUAGE_CD == 'ENG'", "CIS_FA", "CIS_DISP_GRP_L"),
    ("CIS_FA.FA_CAN_RSN_CD == CIS_FA_CAN_RSN_L.FA_CAN_RSN_CD and CIS_FA_CAN_RSN_L.LANGUAGE_CD == 'ENG'", "CIS_FA", "CIS_FA_CAN_RSN_L"),
    ("CIS_FA.FO_ID == CIS_FO.FO_ID", "CIS_FA", "CIS_FO"),
]
CALCULATED: domain_schema.Calculated = [
    ("CIS_FA_LINKED", "CaseWhen(IsNull(CIS_FA.FA_ID), 'N', 'Y')", S),
    ("CIS_FA_DAYS_ACTIVITY_TO_SCHEDULE", "ElapsedDays(CIS_FA.SCHED_DTTM, D1_ACTIVITY.CRE_DTTM)", N),
]
SETS: domain_schema.Sets = [
    ("SET_CIS_FA", "1.) Field Activity - CIS", [
        ("CIS_FA_ID", "CIS Field Activity ID", "CIS_FA.FA_ID"),
        ("CIS_FA_TYPE_CD", "CIS Field Activity Type Code", "CIS_FA.FA_TYPE_CD"),
        ("CIS_FA_TYPE_DESCR", "CIS Field Activity Type", "CIS_FA_TYPE_L.DESCR"),
        ("CIS_FA_STATUS_FLG", "CIS Field Activity Status Code", "CIS_FA.FA_STATUS_FLG"),
        ("CIS_FA_STATUS_DESCR", "CIS Field Activity Status", "CIS_FA_STAT_L.DESCR"),
        ("CIS_FA_PRIORITY_FLG", "CIS Field Activity Priority", "CIS_FA.FA_PRIORITY_FLG"),
        ("CIS_FA_SCHED_DTTM", "CIS Scheduled Date/Time", "CIS_FA.SCHED_DTTM"),
        ("CIS_FA_CRE_DTTM", "CIS Created Date/Time", "CIS_FA.CRE_DTTM"),
        ("CIS_FA_DISP_GRP_CD", "Dispatch Group Code", "CIS_FA.DISP_GRP_CD"),
        ("CIS_FA_DISP_GRP_DESCR", "Dispatch Group", "CIS_DISP_GRP_L.DESCR"),
        ("CIS_FA_CAN_RSN_CD", "CIS Cancel Reason Code", "CIS_FA.FA_CAN_RSN_CD"),
        ("CIS_FA_CAN_RSN_DESCR", "CIS Cancel Reason", "CIS_FA_CAN_RSN_L.DESCR"),
        ("CIS_FA_RESCHED_RSN_CD", "CIS Reschedule Reason Code", "CIS_FA.FA_RESCHED_RSN_CD"),
        ("CIS_FA_CREATED_BY_FLG", "CIS Created By", "CIS_FA.FA_CREATED_BY_FLG"),
        ("CIS_FA_ELIG_DISPATCH_SW", "Eligible For Dispatch Switch", "CIS_FA.ELIG_DISPATCH_SW"),
        ("CIS_FA_USER_ID", "CIS Field Activity User", "CIS_FA.USER_ID"),
        ("CIS_FA_INT_STATUS_FLG", "CIS Intermediate Status", "CIS_FA.FA_INT_STATUS_FLG"),
        ("CIS_FA_SP_ID", "CIS Service Point ID", "CIS_FA.SP_ID"),
        ("CIS_FA_INSTRUCTIONS", "CIS Instructions", "CIS_FA.INSTRUCTIONS"),
        ("CIS_FA_DESCRLONG", "CIS Description", "CIS_FA.DESCRLONG"),
        ("CIS_FA_LINKED", "Activity Has A CIS Field Activity", "CIS_FA_LINKED"),
        ("CIS_FA_DAYS_ACTIVITY_TO_SCHEDULE", "Days From Activity Created To CIS Schedule", "CIS_FA_DAYS_ACTIVITY_TO_SCHEDULE"),
    ]),
    ("SET_CIS_FO", "1.) Field Order - CIS", [
        ("CIS_FO_ID", "Field Order ID", "CIS_FO.FO_ID"),
        ("CIS_FO_PREM_ID", "Field Order Premise ID", "CIS_FO.PREM_ID"),
        ("CIS_FO_WORKED_BY", "Field Order Worked By", "CIS_FO.WORKED_BY"),
        ("CIS_FO_REP_CD", "Field Order Representative", "CIS_FO.REP_CD"),
        ("CIS_FO_DISP_GRP_CD", "Field Order Dispatch Group Code", "CIS_FO.DISP_GRP_CD"),
        ("CIS_FO_SCHED_DTTM", "Field Order Scheduled Date/Time", "CIS_FO.SCHED_DTTM"),
        ("CIS_FO_SCHED_END_DTTM", "Field Order Scheduled End Date/Time", "CIS_FO.SCHED_END_DTTM"),
        ("CIS_FO_STATUS_FLG", "Field Order Status Code", "CIS_FO.FO_STATUS_FLG"),
        ("CIS_FO_WORK_DTTM", "Field Order Worked Date/Time", "CIS_FO.WORK_DTTM"),
    ]),
]


def patch_schema(schema: str) -> str:
    return domain_schema.add_to_schema(schema, TABLES, JOINS, CALCULATED, SETS, guard_id="CIS_FA_IDENTIFIER")
