#!/usr/bin/env python3
"""Give the Budget domain what budget billing reports need: who is ON budget, their late fees,
and every budget amount change.

The domain (Standard Offering > Billing and Rates > Budget Billing) is at SA x recurring-charge
row grain. College Station asked (2026-09-29) for active accounts on budget, those with late fees
in the past year, and system-updated budgets by month. Measured on College Station TEST before
writing this (2026-09-30):

- ON BUDGET is C2M's own configuration, never the plan code: an SA on a budget-ELIGIBLE SA type
  (CI_SA_TYPE.ELIG_BUDGET_SW = 'Y'), Active or Pending Stop, whose CURRENT recurring charge (the
  latest CI_SA_RCHG_HIST row not in the future) is above zero. 965 accounts, 5,552 SAs. The
  budget plan code alone matches 104,826 accounts; amount > 0 without the eligibility flag adds
  496 flat recurring charges that are not budgets.
- LATE FEES come from CI_ADJ by status (50 frozen counts, 60 cancelled is counted apart), never by
  summing ADJ_AMT over CI_FT (a cancelled fee has two FTs and counted twice). Which adjustment
  type is the late fee is the client's configuration -- College Station's CM-LATEPYMT algorithm
  names LPC -- so it is the VIEW's filter, not this domain's. 594 budget accounts, 4,330 fees,
  $28,884.35 in the last 12 months. Grouping CI_FT for this timed out at College Station.
- WHO changed a budget is not recorded: CI_SA_RCHG_HIST has no source column and CI_BUD_RVW keeps
  only each account's LATEST review (1,617 rows, 1,617 accounts; 23 same-day matches to a change).
  So the change tree lists every change, with the latest review beside it, and says no more.

Added, nothing existing touched (domain_schema.additions_only):
- JoinTree_1: CI_SA_TYPE.ELIG_BUDGET_SW and an "Is On Budget" flag on the SA row.
- JoinTree_2 "2.) Budget Accounts": one row per account on budget (BA_BUDGET, always included),
  account context, main customer name, latest budget review, adjustments by type (12 months).
- JoinTree_3 "3.) Budget Changes": one row per budget amount change (BC_CHANGE, always included).

Applied live by `jrs_domain_patch_apply.py --patch patch_budget_domain`.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import domain_schema  # noqa: E402

S, T, N, L = "java.lang.String", "java.sql.Timestamp", "java.math.BigDecimal", "java.lang.Long"

# ---- the population rules, as Oracle SQL the domain parser accepts (SELECT first, no CTE, no bind)
BUDGET_ACCOUNTS_SQL = """
SELECT B.ACCT_ID,
  COUNT(*) AS BUDGET_SA_COUNT,
  SUM(CASE WHEN B.SA_STATUS_FLG = '30' THEN 1 ELSE 0 END) AS PENDING_STOP_SA_COUNT,
  SUM(B.RCR_CHG_AMT) AS BUDGET_AMT,
  MAX(B.EFFDT) AS LATEST_BUDGET_EFFDT,
  MIN(B.START_DT) AS EARLIEST_BUDGET_SA_START_DT
FROM (
  SELECT SA.ACCT_ID, SA.SA_ID, SA.SA_STATUS_FLG, SA.START_DT, H.EFFDT, H.RCR_CHG_AMT,
    MAX(H.EFFDT) OVER (PARTITION BY H.SA_ID) AS LATEST_EFFDT
  FROM CISADM.CI_SA SA, CISADM.CI_SA_TYPE T, CISADM.CI_SA_RCHG_HIST H
  WHERE T.CIS_DIVISION = SA.CIS_DIVISION AND T.SA_TYPE_CD = SA.SA_TYPE_CD AND H.SA_ID = SA.SA_ID
    AND T.ELIG_BUDGET_SW = 'Y' AND SA.SA_STATUS_FLG IN ('20', '30') AND H.EFFDT <= TRUNC(SYSDATE)
) B
WHERE B.EFFDT = B.LATEST_EFFDT AND B.RCR_CHG_AMT > 0
GROUP BY B.ACCT_ID
"""

ADJUSTMENTS_12M_SQL = """
SELECT SA.ACCT_ID, ADJ.ADJ_TYPE_CD,
  SUM(CASE WHEN ADJ.ADJ_STATUS_FLG = '50' THEN 1 ELSE 0 END) AS ADJ_COUNT,
  SUM(CASE WHEN ADJ.ADJ_STATUS_FLG = '50' THEN ADJ.ADJ_AMT ELSE 0 END) AS ADJ_AMT,
  SUM(CASE WHEN ADJ.ADJ_STATUS_FLG = '60' THEN 1 ELSE 0 END) AS CANCELLED_COUNT,
  MAX(CASE WHEN ADJ.ADJ_STATUS_FLG = '50' THEN ADJ.CRE_DT END) AS LAST_ADJ_DT
FROM CISADM.CI_ADJ ADJ, CISADM.CI_SA SA
WHERE ADJ.SA_ID = SA.SA_ID AND ADJ.ADJ_STATUS_FLG IN ('50', '60')
  AND ADJ.CRE_DT >= ADD_MONTHS(TRUNC(SYSDATE), -12)
GROUP BY SA.ACCT_ID, ADJ.ADJ_TYPE_CD
"""

BUDGET_CHANGES_SQL = """
SELECT C.SA_ID, C.ACCT_ID, C.CIS_DIVISION, C.SA_TYPE_CD, C.SA_STATUS_FLG, C.EFFDT,
  TRUNC(C.EFFDT, 'MM') AS CHANGE_MONTH,
  C.PRIOR_AMT, C.RCR_CHG_AMT AS NEW_AMT, C.RCR_CHG_AMT - NVL(C.PRIOR_AMT, 0) AS CHANGE_AMT,
  CASE WHEN C.PRIOR_AMT IS NULL THEN 'Budget Started'
       WHEN C.RCR_CHG_AMT = 0 THEN 'Budget Ended'
       WHEN C.PRIOR_AMT = 0 THEN 'Budget Restarted'
       WHEN C.RCR_CHG_AMT > C.PRIOR_AMT THEN 'Increased'
       ELSE 'Decreased' END AS CHANGE_KIND
FROM (
  SELECT H.SA_ID, SA.ACCT_ID, SA.CIS_DIVISION, SA.SA_TYPE_CD, SA.SA_STATUS_FLG, H.EFFDT, H.RCR_CHG_AMT,
    LAG(H.RCR_CHG_AMT) OVER (PARTITION BY H.SA_ID ORDER BY H.EFFDT) AS PRIOR_AMT
  FROM CISADM.CI_SA_RCHG_HIST H, CISADM.CI_SA SA, CISADM.CI_SA_TYPE T
  WHERE H.SA_ID = SA.SA_ID AND T.CIS_DIVISION = SA.CIS_DIVISION AND T.SA_TYPE_CD = SA.SA_TYPE_CD
    AND T.ELIG_BUDGET_SW = 'Y'
) C
WHERE (C.PRIOR_AMT IS NULL AND C.RCR_CHG_AMT <> 0) OR C.PRIOR_AMT <> C.RCR_CHG_AMT
"""

DERIVED = {
    "BA_BUDGET": (BUDGET_ACCOUNTS_SQL, [("ACCT_ID", S), ("BUDGET_SA_COUNT", N), ("PENDING_STOP_SA_COUNT", N), ("BUDGET_AMT", N),
                                        ("LATEST_BUDGET_EFFDT", T), ("EARLIEST_BUDGET_SA_START_DT", T)]),
    "BA_ADJ_12M": (ADJUSTMENTS_12M_SQL, [("ACCT_ID", S), ("ADJ_TYPE_CD", S), ("ADJ_COUNT", N), ("ADJ_AMT", N),
                                         ("CANCELLED_COUNT", N), ("LAST_ADJ_DT", T)]),
    "BC_CHANGE": (BUDGET_CHANGES_SQL, [("SA_ID", S), ("ACCT_ID", S), ("CIS_DIVISION", S), ("SA_TYPE_CD", S), ("SA_STATUS_FLG", S),
                                       ("EFFDT", T), ("CHANGE_MONTH", T), ("PRIOR_AMT", N), ("NEW_AMT", N), ("CHANGE_AMT", N),
                                       ("CHANGE_KIND", S)]),
}

LABEL = [("LANGUAGE_CD", S), ("DESCR", S)]


def _account_tables(pfx: str) -> dict:
    """The account context each new tree carries, as that tree's own copies of the tables."""
    return {
        f"{pfx}_ACCT": ("CI_ACCT", [("ACCT_ID", S), ("CIS_DIVISION", S), ("BUD_PLAN_CD", S), ("BILL_CYC_CD", S),
                                    ("CUST_CL_CD", S), ("SETUP_DT", T), ("MAILING_PREM_ID", S)]),
        f"{pfx}_ACCT_PER": ("CI_ACCT_PER", [("ACCT_ID", S), ("PER_ID", S), ("MAIN_CUST_SW", S)]),
        f"{pfx}_PER_NAME": ("CI_PER_NAME", [("PER_ID", S), ("SEQ_NUM", N), ("ENTITY_NAME", S), ("NAME_TYPE_FLG", S)]),
        f"{pfx}_BUD_PLAN_L": ("CI_BUD_PLAN_L", [("BUD_PLAN_CD", S)] + LABEL),
        f"{pfx}_BUD_RVW": ("CI_BUD_RVW", [("ACCT_ID", S), ("REVIEW_DT", T), ("BUD_WORKED_SW", S), ("SUGG_BUD_AMT", N), ("TOT_BUD_AMT", N)]),
    }


def _account_joins(pfx: str, population: str) -> list:
    """The main customer chain (MAIN_CUST_SW -> PRIM name) and the review, all outer from the account."""
    a = f"{pfx}_ACCT"
    return [
        (f"{a}.ACCT_ID == {population}.ACCT_ID", a, population, "inner"),
        (f"{a}.ACCT_ID == {pfx}_ACCT_PER.ACCT_ID and {pfx}_ACCT_PER.MAIN_CUST_SW == 'Y'", a, f"{pfx}_ACCT_PER", "leftOuter"),
        (f"{pfx}_ACCT_PER.PER_ID == {pfx}_PER_NAME.PER_ID and {pfx}_PER_NAME.NAME_TYPE_FLG == 'PRIM'", f"{pfx}_ACCT_PER", f"{pfx}_PER_NAME", "leftOuter"),
        (f"{a}.BUD_PLAN_CD == {pfx}_BUD_PLAN_L.BUD_PLAN_CD and {pfx}_BUD_PLAN_L.LANGUAGE_CD == 'ENG'", a, f"{pfx}_BUD_PLAN_L", "leftOuter"),
        (f"{a}.ACCT_ID == {pfx}_BUD_RVW.ACCT_ID", a, f"{pfx}_BUD_RVW", "leftOuter"),
    ]


def _review_items(pfx: str) -> list:
    return [
        (f"{pfx}_REVIEW_DT", "Latest Budget Review Date", f"{pfx}_BUD_RVW.REVIEW_DT"),
        (f"{pfx}_BUD_WORKED_SW", "Latest Review Worked", f"{pfx}_BUD_RVW.BUD_WORKED_SW"),
        (f"{pfx}_SUGG_BUD_AMT", "Suggested Budget Amount (Latest Review)", f"{pfx}_BUD_RVW.SUGG_BUD_AMT"),
        (f"{pfx}_TOT_BUD_AMT", "Budget Amount At Latest Review", f"{pfx}_BUD_RVW.TOT_BUD_AMT"),
    ]


# ---- JoinTree_2: one row per account on budget
BA_TABLES = {
    **_account_tables("BA"),
    "BA_BILL_CYC_L": ("CI_BILL_CYC_L", [("BILL_CYC_CD", S)] + LABEL),
    "BA_CUST_CL_L": ("CI_CUST_CL_L", [("CUST_CL_CD", S)] + LABEL),
    "BA_ADJ_TYPE_L": ("CI_ADJ_TYPE_L", [("ADJ_TYPE_CD", S)] + LABEL),
}
BA_DERIVED = {k: DERIVED[k] for k in ("BA_BUDGET", "BA_ADJ_12M")}
BA_JOINS = _account_joins("BA", "BA_BUDGET") + [
    ("BA_ACCT.BILL_CYC_CD == BA_BILL_CYC_L.BILL_CYC_CD and BA_BILL_CYC_L.LANGUAGE_CD == 'ENG'", "BA_ACCT", "BA_BILL_CYC_L", "leftOuter"),
    ("BA_ACCT.CUST_CL_CD == BA_CUST_CL_L.CUST_CL_CD and BA_CUST_CL_L.LANGUAGE_CD == 'ENG'", "BA_ACCT", "BA_CUST_CL_L", "leftOuter"),
    # one row per adjustment type: fields from this set list an account once per type it was charged
    ("BA_ACCT.ACCT_ID == BA_ADJ_12M.ACCT_ID", "BA_ACCT", "BA_ADJ_12M", "leftOuter"),
    ("BA_ADJ_12M.ADJ_TYPE_CD == BA_ADJ_TYPE_L.ADJ_TYPE_CD and BA_ADJ_TYPE_L.LANGUAGE_CD == 'ENG'", "BA_ADJ_12M", "BA_ADJ_TYPE_L", "leftOuter"),
]
BA_CALCULATED = [
    ("BA_ACCOUNT_COUNT", "CountDistinct(BA_ACCT.ACCT_ID, 'Current')", L),
    ("BA_REVIEW_DIFF", "BA_BUD_RVW.SUGG_BUD_AMT - BA_BUD_RVW.TOT_BUD_AMT", N),
]
BA_SETS = [
    ("SET_BA_ACCOUNT", "2.) Budget Account", [
        ("BA_ACCT_ID", "Account ID", "BA_ACCT.ACCT_ID"),
        ("BA_CUSTOMER_NAME", "Main Customer Name", "BA_PER_NAME.ENTITY_NAME"),
        ("BA_BUD_PLAN_CD", "Budget Plan Code", "BA_ACCT.BUD_PLAN_CD"),
        ("BA_BUD_PLAN", "Budget Plan", "BA_BUD_PLAN_L.DESCR"),
        ("BA_BILL_CYC_CD", "Bill Cycle Code", "BA_ACCT.BILL_CYC_CD"),
        ("BA_BILL_CYC", "Bill Cycle", "BA_BILL_CYC_L.DESCR"),
        ("BA_CUST_CL_CD", "Customer Class Code", "BA_ACCT.CUST_CL_CD"),
        ("BA_CUST_CL", "Customer Class", "BA_CUST_CL_L.DESCR"),
        ("BA_CIS_DIVISION", "CIS Division", "BA_ACCT.CIS_DIVISION"),
        ("BA_SETUP_DT", "Account Setup Date", "BA_ACCT.SETUP_DT"),
        ("BA_BUDGET_AMT", "Monthly Budget Amount", "BA_BUDGET.BUDGET_AMT"),
        ("BA_BUDGET_SA_COUNT", "Budget Service Agreements", "BA_BUDGET.BUDGET_SA_COUNT"),
        ("BA_PENDING_STOP_SA_COUNT", "Budget Service Agreements Pending Stop", "BA_BUDGET.PENDING_STOP_SA_COUNT"),
        ("BA_LATEST_BUDGET_EFFDT", "Latest Budget Amount Effective Date", "BA_BUDGET.LATEST_BUDGET_EFFDT"),
        ("BA_EARLIEST_SA_START_DT", "Earliest Budget Service Agreement Start", "BA_BUDGET.EARLIEST_BUDGET_SA_START_DT"),
        ("BA_ACCOUNT_COUNT", "Distinct Accounts", "BA_ACCOUNT_COUNT"),
    ]),
    ("SET_BA_REVIEW", "2.) Latest Budget Review", _review_items("BA") + [
        ("BA_REVIEW_DIFF", "Suggested Minus Budget At Review", "BA_REVIEW_DIFF"),
    ]),
    ("SET_BA_ADJ", "2.) Adjustments (Last 12 Months)", [
        ("BA_ADJ_TYPE_CD", "Adjustment Type Code", "BA_ADJ_12M.ADJ_TYPE_CD"),
        ("BA_ADJ_TYPE", "Adjustment Type", "BA_ADJ_TYPE_L.DESCR"),
        ("BA_ADJ_COUNT", "Adjustments Assessed", "BA_ADJ_12M.ADJ_COUNT"),
        ("BA_ADJ_AMT", "Adjustment Amount (Frozen)", "BA_ADJ_12M.ADJ_AMT"),
        ("BA_ADJ_CANCELLED_COUNT", "Adjustments Cancelled", "BA_ADJ_12M.CANCELLED_COUNT"),
        ("BA_LAST_ADJ_DT", "Last Adjustment Date", "BA_ADJ_12M.LAST_ADJ_DT"),
    ]),
]
BA_MEASURES = {"BA_BUDGET_AMT": "Sum", "BA_BUDGET_SA_COUNT": "Sum", "BA_PENDING_STOP_SA_COUNT": "Sum",
               "BA_ADJ_COUNT": "Sum", "BA_ADJ_AMT": "Sum", "BA_ADJ_CANCELLED_COUNT": "Sum"}

# ---- JoinTree_3: one row per budget amount change
BC_TABLES = {
    **_account_tables("BC"),
    "BC_SA_TYPE_L": ("CI_SA_TYPE_L", [("CIS_DIVISION", S), ("SA_TYPE_CD", S)] + LABEL),
    "BC_SA_STATUS_L": ("CI_LOOKUP_VAL_L", [("FIELD_NAME", S), ("FIELD_VALUE", S)] + LABEL),
}
BC_DERIVED = {"BC_CHANGE": DERIVED["BC_CHANGE"]}
BC_JOINS = _account_joins("BC", "BC_CHANGE") + [
    ("BC_CHANGE.CIS_DIVISION == BC_SA_TYPE_L.CIS_DIVISION and BC_CHANGE.SA_TYPE_CD == BC_SA_TYPE_L.SA_TYPE_CD"
     " and BC_SA_TYPE_L.LANGUAGE_CD == 'ENG'", "BC_CHANGE", "BC_SA_TYPE_L", "leftOuter"),
    ("BC_CHANGE.SA_STATUS_FLG == BC_SA_STATUS_L.FIELD_VALUE and BC_SA_STATUS_L.FIELD_NAME == 'SA_STATUS_FLG'"
     " and BC_SA_STATUS_L.LANGUAGE_CD == 'ENG'", "BC_CHANGE", "BC_SA_STATUS_L", "leftOuter"),
]
BC_CALCULATED = [
    ("BC_ACCOUNT_COUNT", "CountDistinct(BC_CHANGE.ACCT_ID, 'Current')", L),
    ("BC_SA_COUNT", "CountDistinct(BC_CHANGE.SA_ID, 'Current')", L),
]
BC_SETS = [
    ("SET_BC_CHANGE", "3.) Budget Change", [
        ("BC_ACCT_ID", "Account ID", "BC_CHANGE.ACCT_ID"),
        ("BC_CUSTOMER_NAME", "Main Customer Name", "BC_PER_NAME.ENTITY_NAME"),
        ("BC_SA_ID", "Service Agreement ID", "BC_CHANGE.SA_ID"),
        ("BC_SA_TYPE_CD", "SA Type Code", "BC_CHANGE.SA_TYPE_CD"),
        ("BC_SA_TYPE", "SA Type", "BC_SA_TYPE_L.DESCR"),
        ("BC_SA_STATUS_CD", "SA Status Code", "BC_CHANGE.SA_STATUS_FLG"),
        ("BC_SA_STATUS", "SA Status", "BC_SA_STATUS_L.DESCR"),
        ("BC_EFFDT", "Change Effective Date", "BC_CHANGE.EFFDT"),
        ("BC_CHANGE_MONTH", "Change Month", "BC_CHANGE.CHANGE_MONTH"),
        ("BC_CHANGE_KIND", "Change Kind", "BC_CHANGE.CHANGE_KIND"),
        ("BC_PRIOR_AMT", "Prior Budget Amount", "BC_CHANGE.PRIOR_AMT"),
        ("BC_NEW_AMT", "New Budget Amount", "BC_CHANGE.NEW_AMT"),
        ("BC_CHANGE_AMT", "Change Amount", "BC_CHANGE.CHANGE_AMT"),
        ("BC_BUD_PLAN_CD", "Budget Plan Code", "BC_ACCT.BUD_PLAN_CD"),
        ("BC_BUD_PLAN", "Budget Plan", "BC_BUD_PLAN_L.DESCR"),
        ("BC_ACCOUNT_COUNT", "Distinct Accounts", "BC_ACCOUNT_COUNT"),
        ("BC_SA_COUNT", "Distinct Service Agreements", "BC_SA_COUNT"),
    ]),
    ("SET_BC_REVIEW", "3.) Latest Budget Review", _review_items("BC")),
]
BC_MEASURES = {"BC_CHANGE_AMT": "Sum"}

# ---- JoinTree_1: the same budget rule, as a flag on the existing SA rows
SA_TYPE_FIELDS = [("ELIG_BUDGET_SW", S)]
IS_ON_BUDGET = ("CaseWhen(CM_SA_RCHG_LATEST.LATEST_EFFDT == CI_SA_RCHG_HIST.EFFDT and CI_SA_RCHG_HIST.RCR_CHG_AMT > 0"
                " and CI_SA_TYPE.ELIG_BUDGET_SW == 'Y' and (CI_SA.SA_STATUS_FLG == '20' or CI_SA.SA_STATUS_FLG == '30'), 'Y', 'N')")
JT1_SETS = [
    ("SET_BUDGET_STATUS", "1.) Budget Status", [
        ("ELIG_BUDGET_SW", "Budget Eligible SA Type", "CI_SA_TYPE.ELIG_BUDGET_SW"),
        ("IS_ON_BUDGET", "Is On Budget", "IS_ON_BUDGET"),
    ]),
]

# The apply tool probes the first ten items of SETS in one query: the account tree comes first.
SETS = BA_SETS + BC_SETS + JT1_SETS


def patch_schema(schema: str) -> str:
    if 'id="IS_ON_BUDGET"' in schema:
        raise ValueError("the schema already carries IS_ON_BUDGET: not patching twice")
    schema = domain_schema.add_columns(schema, "CI_SA_TYPE", SA_TYPE_FIELDS)
    schema = domain_schema.add_to_schema(schema, {}, [], [("IS_ON_BUDGET", IS_ON_BUDGET, S)], JT1_SETS, guard_id="IS_ON_BUDGET_GUARD")
    schema = domain_schema.add_join_tree(schema, "JoinTree_2", "2.) Budget Accounts", "BA_ACCT", BA_TABLES, BA_DERIVED, BA_JOINS,
                                         BA_CALCULATED, BA_SETS, BA_MEASURES, always_include=("BA_BUDGET",))
    return domain_schema.add_join_tree(schema, "JoinTree_3", "3.) Budget Changes", "BC_ACCT", BC_TABLES, BC_DERIVED, BC_JOINS,
                                       BC_CALCULATED, BC_SETS, BC_MEASURES, always_include=("BC_CHANGE",))


if __name__ == "__main__":
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    dst.write_text(patch_schema(src.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"wrote {dst}")
