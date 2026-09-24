#!/usr/bin/env python3
"""Bill Cycle Schedule - Domain: the billing calendar, one row per cycle window.

The Standard Offering had no Ad Hoc surface for `CI_BILL_CYC_SCH` (the legacy Inventory library
range-joined it under bills; 2026-09-24 gap read). This domain puts the calendar first: every
scheduled window with its accounting and estimated dates and freeze-complete switch, the bills the
window actually produced (folded from CI_BILL: bills, completed, pending, first and last
completion, accounts billed), the accounts on the cycle today, and age flags computed in SQL.

Verify live before trusting the fold: a bill's WIN_START_DT is stamped from its schedule row, so
the equality join should cover every bill; measure the bills whose (cycle, window start) has no
schedule row. Bill status P / C is the base-product lifecycle.

    python3 scripts/jaspersoft/build_bill_cycle_schedule_domain.py --ds Origin_DEV_DS --out schema.xml
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import domain_schema  # noqa: E402

S, T, N, L = "java.lang.String", "java.sql.Timestamp", "java.math.BigDecimal", "java.lang.Long"

TABLES: domain_schema.Tables = {
    "CI_BILL_CYC_SCH": ("CI_BILL_CYC_SCH", [("BILL_CYC_CD", S), ("WIN_START_DT", T), ("WIN_END_DT", T), ("ACCOUNTING_DT", T), ("EST_DT", T), ("FREEZE_COMPLETE_SW", S), ("VERSION", N)]),
    "CI_BILL_CYC_L": ("CI_BILL_CYC_L", [("BILL_CYC_CD", S), ("LANGUAGE_CD", S), ("DESCR", S)]),
}
DERIVED: domain_schema.Derived = {
    "WINDOW_BILLS": ("""select b.bill_cyc_cd, b.win_start_dt,
       count(*) as bill_count,
       sum(case when b.bill_stat_flg = 'C' then 1 else 0 end) as completed_count,
       sum(case when b.bill_stat_flg = 'P' then 1 else 0 end) as pending_count,
       count(distinct b.acct_id) as accounts_billed,
       min(b.complete_dttm) as first_complete_dttm,
       max(b.complete_dttm) as last_complete_dttm,
       min(b.bill_dt) as first_bill_dt,
       max(b.due_dt) as last_due_dt
from cisadm.ci_bill b
group by b.bill_cyc_cd, b.win_start_dt""",
                     [("BILL_CYC_CD", S), ("WIN_START_DT", T), ("BILL_COUNT", L), ("COMPLETED_COUNT", L), ("PENDING_COUNT", L), ("ACCOUNTS_BILLED", L),
                      ("FIRST_COMPLETE_DTTM", T), ("LAST_COMPLETE_DTTM", T), ("FIRST_BILL_DT", T), ("LAST_DUE_DT", T)]),
    "CYCLE_ACCOUNTS": ("""select a.bill_cyc_cd, count(*) as account_count
from cisadm.ci_acct a
group by a.bill_cyc_cd""", [("BILL_CYC_CD", S), ("ACCOUNT_COUNT", L)]),
    # age in SQL, where the database computes it (a DomEL Today() runs in memory under the row cap)
    "WINDOW_AGE": ("""select s.bill_cyc_cd, s.win_start_dt,
       trunc(sysdate) - s.win_end_dt as days_since_window_end,
       case when s.win_end_dt < trunc(sysdate) then 'Y' else 'N' end as window_is_past,
       case when s.win_end_dt < trunc(sysdate) and s.freeze_complete_sw <> 'Y' then 'Y' else 'N' end as past_and_not_frozen,
       case when s.win_start_dt <= trunc(sysdate) and s.win_end_dt >= trunc(sysdate) then 'Y' else 'N' end as window_is_current
from cisadm.ci_bill_cyc_sch s""",
                   [("BILL_CYC_CD", S), ("WIN_START_DT", T), ("DAYS_SINCE_WINDOW_END", N), ("WINDOW_IS_PAST", S), ("PAST_AND_NOT_FROZEN", S), ("WINDOW_IS_CURRENT", S)]),
}
JOINS: domain_schema.Joins = [(e, l, r, "leftOuter") for e, l, r in [
    ("CI_BILL_CYC_SCH.BILL_CYC_CD == CI_BILL_CYC_L.BILL_CYC_CD and CI_BILL_CYC_L.LANGUAGE_CD == 'ENG'", "CI_BILL_CYC_SCH", "CI_BILL_CYC_L"),
    ("CI_BILL_CYC_SCH.BILL_CYC_CD == WINDOW_BILLS.BILL_CYC_CD and CI_BILL_CYC_SCH.WIN_START_DT == WINDOW_BILLS.WIN_START_DT", "CI_BILL_CYC_SCH", "WINDOW_BILLS"),
    ("CI_BILL_CYC_SCH.BILL_CYC_CD == CYCLE_ACCOUNTS.BILL_CYC_CD", "CI_BILL_CYC_SCH", "CYCLE_ACCOUNTS"),
    ("CI_BILL_CYC_SCH.BILL_CYC_CD == WINDOW_AGE.BILL_CYC_CD and CI_BILL_CYC_SCH.WIN_START_DT == WINDOW_AGE.WIN_START_DT", "CI_BILL_CYC_SCH", "WINDOW_AGE"),
]]
BASE_PRODUCT_LITERALS = {"Y", "N"}
CALCULATED: domain_schema.Calculated = [
    ("IS_FREEZE_COMPLETE", "CaseWhen(CI_BILL_CYC_SCH.FREEZE_COMPLETE_SW == 'Y', 'Y', 'N')", S),
    ("HAS_BILLS", "CaseWhen(IsNull(WINDOW_BILLS.BILL_CYC_CD), 'N', 'Y')", S),
    ("WINDOW_DAYS", "ElapsedDays(CI_BILL_CYC_SCH.WIN_END_DT, CI_BILL_CYC_SCH.WIN_START_DT)", N),
    ("DAYS_WINDOW_END_TO_LAST_COMPLETE", "ElapsedDays(WINDOW_BILLS.LAST_COMPLETE_DTTM, CI_BILL_CYC_SCH.WIN_END_DT)", N),
    ("DAYS_ESTIMATE_TO_ACCOUNTING", "ElapsedDays(CI_BILL_CYC_SCH.ACCOUNTING_DT, CI_BILL_CYC_SCH.EST_DT)", N),
    ("WINDOW_DIST", "CountDistinct(Concatenate(CI_BILL_CYC_SCH.BILL_CYC_CD, '_', CI_BILL_CYC_SCH.WIN_START_DT), 'Current')", L),
]
SETS: domain_schema.Sets = [
    ("SET_SCHEDULE", "1.) Bill Cycle Schedule", [
        ("BILL_CYC_CD", "Bill Cycle Code", "CI_BILL_CYC_SCH.BILL_CYC_CD"),
        ("BILL_CYC_DESCR", "Bill Cycle", "CI_BILL_CYC_L.DESCR"),
        ("WIN_START_DT", "Window Start Date", "CI_BILL_CYC_SCH.WIN_START_DT"),
        ("WIN_END_DT", "Window End Date", "CI_BILL_CYC_SCH.WIN_END_DT"),
        ("ACCOUNTING_DT", "Accounting Date", "CI_BILL_CYC_SCH.ACCOUNTING_DT"),
        ("EST_DT", "Estimated Date", "CI_BILL_CYC_SCH.EST_DT"),
        ("FREEZE_COMPLETE_SW", "Freeze Complete Switch", "CI_BILL_CYC_SCH.FREEZE_COMPLETE_SW"),
    ]),
    ("SET_WINDOW_BILLS", "1.1) Bills In The Window", [
        ("BILL_COUNT", "Bill Count", "WINDOW_BILLS.BILL_COUNT"),
        ("COMPLETED_COUNT", "Completed Bill Count", "WINDOW_BILLS.COMPLETED_COUNT"),
        ("PENDING_COUNT", "Pending Bill Count", "WINDOW_BILLS.PENDING_COUNT"),
        ("ACCOUNTS_BILLED", "Accounts Billed", "WINDOW_BILLS.ACCOUNTS_BILLED"),
        ("FIRST_COMPLETE_DTTM", "First Bill Completed Date/Time", "WINDOW_BILLS.FIRST_COMPLETE_DTTM"),
        ("LAST_COMPLETE_DTTM", "Last Bill Completed Date/Time", "WINDOW_BILLS.LAST_COMPLETE_DTTM"),
        ("FIRST_BILL_DT", "First Bill Date", "WINDOW_BILLS.FIRST_BILL_DT"),
        ("LAST_DUE_DT", "Last Due Date", "WINDOW_BILLS.LAST_DUE_DT"),
    ]),
    ("SET_CYCLE", "1.2) Cycle Today", [
        ("ACCOUNT_COUNT", "Accounts On Cycle", "CYCLE_ACCOUNTS.ACCOUNT_COUNT"),
    ]),
    ("SET_FLAGS", "2.) Flags And Formulas", [
        ("IS_FREEZE_COMPLETE", "Freeze Is Complete", "IS_FREEZE_COMPLETE"),
        ("HAS_BILLS", "Window Has Bills", "HAS_BILLS"),
        ("WINDOW_IS_PAST", "Window Is Past", "WINDOW_AGE.WINDOW_IS_PAST"),
        ("WINDOW_IS_CURRENT", "Window Is Current", "WINDOW_AGE.WINDOW_IS_CURRENT"),
        ("PAST_AND_NOT_FROZEN", "Past And Freeze Not Complete", "WINDOW_AGE.PAST_AND_NOT_FROZEN"),
        ("DAYS_SINCE_WINDOW_END", "Days Since Window End", "WINDOW_AGE.DAYS_SINCE_WINDOW_END"),
        ("WINDOW_DAYS", "Window Length (Days)", "WINDOW_DAYS"),
        ("DAYS_WINDOW_END_TO_LAST_COMPLETE", "Days From Window End To Last Completion", "DAYS_WINDOW_END_TO_LAST_COMPLETE"),
        ("DAYS_ESTIMATE_TO_ACCOUNTING", "Days From Estimated To Accounting Date", "DAYS_ESTIMATE_TO_ACCOUNTING"),
        ("WINDOW_DIST", "Distinct Windows", "WINDOW_DIST"),
    ]),
]
MEASURES: domain_schema.Measures = [
    ("BILL_COUNT_TOTAL", "Bill Count Total", "WINDOW_BILLS.BILL_COUNT", "Sum"),
    ("COMPLETED_COUNT_TOTAL", "Completed Bill Count Total", "WINDOW_BILLS.COMPLETED_COUNT", "Sum"),
    ("PENDING_COUNT_TOTAL", "Pending Bill Count Total", "WINDOW_BILLS.PENDING_COUNT", "Sum"),
    ("ACCOUNTS_BILLED_TOTAL", "Accounts Billed Total", "WINDOW_BILLS.ACCOUNTS_BILLED", "Sum"),
    ("CYCLE_COUNT", "Cycle Count", "CI_BILL_CYC_SCH.BILL_CYC_CD", "CountDistinct"),
]


def schema(ds: str) -> str:
    return domain_schema.schema(ds, "CI_BILL_CYC_SCH", TABLES, JOINS, CALCULATED, SETS, MEASURES, DERIVED)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ds", required=True); ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(schema(a.ds), encoding="utf-8")
    r = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve().parent / "validate_domain_schema.py"), str(a.out)], capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise SystemExit(f"schema validation failed:\n{r.stdout}{r.stderr}")
    print(f"wrote {a.out} for {a.ds}: {len(TABLES)} tables, {len(DERIVED)} derived, {sum(len(s[2]) for s in SETS) + len(MEASURES)} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
