"""
Data density and freshness check for Oracle C2M (CISADM) tables used by the BI pipeline.
Evolved into a Data Quality Profiling tool: table counts, date/version overrides, balance
reconciliation, ARS_DT null density, orphan SA check, per-table column shape sample, and
a Workstream Health Matrix (7-day freshness per workstream; Data Currency Risk when stale).

Usage (from repo root with venv active and .env set):
  python -m pipeline.validate_tables

For every table referenced in the BI and entity-resolution queries, prints:
  - Total row count
  - MAX(<date_column>) or MAX(VERSION) using explicit overrides or discovery (CRE_DTTM, etc.).
  - Columns (sample): column list from a 3-row sample (metadata only).
Then a Data quality section and a Workstream Health Matrix. If a workstream's source-of-truth
table has no record created/frozen in the last 7 days, it is flagged as Data Currency Risk;
output/workstream_health.json is written so generate_narrative.py can alert the AI. See docs/pipeline.md.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv()

# Tables to check. Schema.Table. Date column can be a string, None (try to discover), or a list to try in order.
_TABLE_CHECKS = [
    # Existing BI + entity resolution
    ("CISADM.CI_FT", "CRE_DTTM"),           # Arrears + Duplicate payment source of truth
    ("CISADM.CI_SA", None),                 # Service agreements – discover date col
    ("CISADM.CI_SA_TYPE", None),            # Debt class (small lookup)
    ("CISADM.CI_ACCT", None),               # Accounts – discover date col
    ("CISADM.CI_ACCT_ALERT", None),         # Bankruptcy flags – discover date col
    ("CISADM.CI_CC", "CC_DTTM"),            # Customer contacts / letters
    ("CISADM.CI_LETTER_TMPL", None),        # Letter template catalog
    ("CISADM.CI_PREM", None),               # Premise/address (Common workstream)
    ("CISADM.CI_PER_NAME", None),          # Customer name – VERSION (non-date) override
    ("CISADM.CI_ACCT_PER", None),           # Account–person link – LAST_UPDATE_DTTM override
    # Billing & Rates
    ("CISADM.CI_BSEG", "CRE_DTTM"),
    ("CISADM.CI_BILL", None),
    ("CISADM.CI_RS_L", None),
    # Cashiering
    ("CISADM.CI_PAY_EVENT", "CRE_DTTM"),
    ("CISADM.CI_PAY_TNDR", None),
    ("CISADM.CI_DEP_CTL", None),
    # Meter Operations (Domain Designs: D1_DVC, D1_DVC_CFG, D1_INSTALL_EVT)
    # In this environment D1 tables are exposed under CISADM.
    ("CISADM.D1_DVC", "CRE_DTTM"),
    ("CISADM.D1_DVC_CFG", "CRE_DTTM"),
    ("CISADM.D1_INSTALL_EVT", "CRE_DTTM"),
    ("CISADM.CI_SP", None),
    # New Services
    ("CISADM.CI_SP_CHAR", None),
    # Finance
    ("CISADM.CI_FT_GL", "CRE_DTTM"),
    ("CISADM.CI_FT_PROC", None),
    # Common
    ("CISADM.CI_LOOKUP_VAL", None),
    # F1 Metadata Layer (OCX & Field Tasks, Batch Health)
    ("CISADM.F1_TSK", "CRE_DTTM"),
    ("CISADM.F1_TSK_LOG", "LOG_DTTM"),
    ("CISADM.F1_BATCH_RUN", "START_DTTM"),
    ("CISADM.F1_EXT_LOOKUP", None),
]

# Explicit column overrides for tables that use non-standard or non-date "freshness" columns.
# VERSION = numeric max (name-update activity); others = date/timestamp for MAX().
_OVERRIDES = {
    "CISADM.CI_PER_NAME": "VERSION",         # Not a date; MAX(VERSION) indicates name updates
    "CISADM.CI_PREM": "CRE_DTTM",           # If present in build; else discovery
    "CISADM.CI_ACCT_PER": "LAST_UPDATE_DTTM",
    "CISADM.D1_INSTALL_EVT": "D1_INSTALL_DTTM",  # Install event date (ground truth for meter ops)
}

# Candidate date/timestamp columns to try (in order) when discovering.
_DATE_CANDIDATES = [
    "CRE_DTTM",
    "UPD_DTTM",
    "CHG_DTTM",
    "INSTALL_DTTM",   # D1_MTR meter install date
    "LAST_UPDATE_DTTM",
    "MODIFIED_DT",
    "CRE_DT",
    "UPD_DT",
]


# Arrears filters: active/relevant only (frozen, in arrears, not payment types, valid ARS_DT).
_CI_FT_ARS_FILTER = (
    "FREEZE_SW = 'Y' AND NOT_IN_ARS_SW = 'N' AND FT_TYPE_FLG NOT IN ('PS', 'PX') AND ARS_DT IS NOT NULL"
)


def _get_table_columns(engine, full_table_name: str) -> list[str]:
    """Return ordered list of column names for the table from ALL_TAB_COLUMNS (no SELECT *)."""
    import pandas as pd
    owner, table_name = full_table_name.split(".", 1)
    owner, table_name = owner.upper(), table_name.upper()
    try:
        df = pd.read_sql(
            """SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS
               WHERE OWNER = :owner AND TABLE_NAME = :tname
               ORDER BY COLUMN_ID""",
            engine,
            params={"owner": owner, "tname": table_name},
        )
        if df.empty:
            return []
        return [str(c).upper() for c in df.iloc[:, 0]]
    except Exception:
        return []


def _discover_date_column(engine, full_table_name: str) -> str | None:
    """Return first existing date/timestamp column for the table, or None."""
    import pandas as pd
    owner, table_name = full_table_name.split(".", 1)
    owner, table_name = owner.upper(), table_name.upper()
    try:
        df = pd.read_sql(
            """SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS
               WHERE OWNER = :owner AND TABLE_NAME = :tname
               AND (DATA_TYPE = 'DATE' OR DATA_TYPE LIKE 'TIMESTAMP%')
               ORDER BY COLUMN_ID""",
            engine,
            params={"owner": owner, "tname": table_name},
        )
        if df.empty:
            return None
        columns = [c.upper() for c in df.iloc[:, 0].astype(str)]
        for cand in _DATE_CANDIDATES:
            if cand in columns:
                return cand
        return columns[0] if columns else None
    except Exception:
        return None


def run_balance_reconciliation(engine) -> None:
    """
    Check that sum of arrears buckets equals TOTAL_DEBT (tolerance 0.01).
    Prints count of mismatched rows and up to 5 sample rows.
    """
    import pandas as pd
    from fetch_usage import _QUERY_ARREARS_STRATEGIC

    reconcile_sql = f"""
SELECT ACCT_ID, DEBT_CL_CD,
       (NVL(DEBT_30_DAYS,0) + NVL(DEBT_60_DAYS,0) + NVL(DEBT_OVER_60,0)) AS SUM_BUCKETS,
       TOTAL_DEBT
FROM ( {_QUERY_ARREARS_STRATEGIC.strip()} )
WHERE ABS((NVL(DEBT_30_DAYS,0) + NVL(DEBT_60_DAYS,0) + NVL(DEBT_OVER_60,0)) - TOTAL_DEBT) > 0.01
"""
    try:
        df = pd.read_sql(reconcile_sql, engine)
        if not df.empty:
            df.columns = [c.lower() for c in df.columns]
        n = len(df)
        print(f"Balance reconciliation: {n} row(s) where sum(buckets) != TOTAL_DEBT (tolerance 0.01)")
        if n > 0:
            sample = df.head(5)
            for _, row in sample.iterrows():
                print(f"  Sample: ACCT_ID={row.get('acct_id')} DEBT_CL_CD={row.get('debt_cl_cd')} "
                      f"SUM_BUCKETS={row.get('sum_buckets')} TOTAL_DEBT={row.get('total_debt')}")
        else:
            print("  (none)")
    except Exception as e:
        print(f"Balance reconciliation: ERROR - {e}")


def _run_ars_dt_null_density(engine) -> None:
    """Report percentage of CI_FT (arrears population) rows with ARS_DT IS NULL."""
    import pandas as pd

    sql = f"""
SELECT COUNT(*) AS total,
       SUM(CASE WHEN ARS_DT IS NULL THEN 1 ELSE 0 END) AS nulls
FROM CISADM.CI_FT
WHERE {_CI_FT_ARS_FILTER}
"""
    try:
        df = pd.read_sql(sql, engine)
        total = int(df.iloc[0, 0]) if not df.empty else 0
        nulls = int(df.iloc[0, 1]) if not df.empty and df.shape[1] > 1 else 0
        pct = (100.0 * nulls / total) if total else 0.0
        print(f"CI_FT ARS_DT null density: {pct:.1f}% ({nulls} of {total} rows)")
    except Exception as e:
        print(f"CI_FT ARS_DT null density: ERROR - {e}")


def _run_orphan_sa_check(engine) -> int:
    """Report SAs (active status) with no CI_FT rows under arrears filters; show up to 5 sample. Returns count."""
    import pandas as pd

    sql = """
SELECT sa.SA_ID, sa.ACCT_ID
FROM CISADM.CI_SA sa
LEFT JOIN (
    SELECT DISTINCT SA_ID FROM CISADM.CI_FT
    WHERE """ + _CI_FT_ARS_FILTER + """
) ft ON ft.SA_ID = sa.SA_ID
WHERE ft.SA_ID IS NULL
  AND NULLIF(TRIM(sa.SA_STATUS_FLG), '') = '20'
"""
    try:
        df = pd.read_sql(sql, engine)
        if not df.empty:
            df.columns = [c.lower() for c in df.columns]
        n = len(df)
        print(f"Orphan SAs (active, no CI_FT arrears rows): {n}")
        if n > 0:
            sample = df.head(5)
            for _, row in sample.iterrows():
                print(f"  Sample: SA_ID={row.get('sa_id')} ACCT_ID={row.get('acct_id')}")
        return n
    except Exception as e:
        print(f"Orphan SAs check: ERROR - {e}")
        return -1


def _table_has_column(engine, owner: str, table: str, column: str) -> bool:
    """Return True if OWNER.TABLE has COLUMN in ALL_TAB_COLUMNS."""
    import pandas as pd

    try:
        df = pd.read_sql(
            """SELECT 1 FROM ALL_TAB_COLUMNS
               WHERE OWNER = :owner AND TABLE_NAME = :tname AND COLUMN_NAME = :col""",
            engine,
            params={"owner": owner.upper(), "tname": table.upper(), "col": column.upper()},
        )
        return not df.empty
    except Exception:
        return False


def run_configuration_completeness_checks(engine) -> dict:
    """
    Best-practice configuration completeness checks for Functional Architects.
    Example: active SAs missing a rate schedule reference. Returns rules dict for validation_metadata.
    """
    import pandas as pd
    from pathlib import Path

    rules: dict[str, dict] = {}
    print("-" * 70)
    print("Configuration Completeness (Best Practices)")
    print("-" * 70)

    # Rule 1: Active SA missing rate (RATE_RS_CD or equivalent)
    owner = "CISADM"
    table = "CI_SA"
    rate_col = "RATE_RS_CD"
    if not _table_has_column(engine, owner, table, rate_col):
        print(f"Rule: Active SA missing rate - SKIPPED (column {owner}.{table}.{rate_col} not present in this schema).")
        rules["active_sa_missing_rate"] = {
            "applies": False,
            "count": 0,
            "samples": [],
            "note": f"{owner}.{table}.{rate_col} not present in this schema.",
        }
    else:
        try:
            sql_cnt = f"""
SELECT COUNT(*) AS cnt
FROM {owner}.{table}
WHERE NULLIF(TRIM(SA_STATUS_FLG), '') = '20'
  AND (TRIM({rate_col}) IS NULL)
"""
            df_cnt = pd.read_sql(sql_cnt, engine)
            total_missing = int(df_cnt.iloc[0, 0]) if not df_cnt.empty else 0
            print(f"Rule: Active SA missing rate ({owner}.{table}.{rate_col} IS NULL) -> {total_missing} row(s).")
            samples: list[dict] = []
            if total_missing > 0:
                sql_sample = f"""
SELECT SA_ID, ACCT_ID, SA_STATUS_FLG
FROM {owner}.{table}
WHERE NULLIF(TRIM(SA_STATUS_FLG), '') = '20'
  AND (TRIM({rate_col}) IS NULL)
  AND ROWNUM <= 10
"""
                df_sample = pd.read_sql(sql_sample, engine)
                if not df_sample.empty:
                    df_sample.columns = [c.lower() for c in df_sample.columns]
                    for _, row in df_sample.iterrows():
                        samples.append(
                            {
                                "sa_id": row.get("sa_id"),
                                "acct_id": row.get("acct_id"),
                                "sa_status_flg": row.get("sa_status_flg"),
                            }
                        )
                        print(
                            f"  Sample: SA_ID={row.get('sa_id')} ACCT_ID={row.get('acct_id')} "
                            f"SA_STATUS_FLG={row.get('sa_status_flg')}"
                        )
                print(
                    "  Explanation: Active service agreements without a rate schedule code may not bill correctly. "
                    "Review these in C2M and update RATE_RS_CD or the equivalent configuration."
                )
            rules["active_sa_missing_rate"] = {
                "applies": True,
                "count": total_missing,
                "samples": samples,
            }
        except Exception as e:
            print(f"Rule: Active SA missing rate - ERROR querying {owner}.{table}.{rate_col}: {e}")
            rules["active_sa_missing_rate"] = {
                "applies": True,
                "count": None,
                "samples": [],
                "error": str(e),
            }

    # Rule 2: Billing Gap - active SAs with no CI_FT rows in the last 60 days
    try:
        sql_cnt_gap = """
SELECT COUNT(*) AS cnt
FROM CISADM.CI_SA sa
WHERE NULLIF(TRIM(sa.SA_STATUS_FLG), '') = '20'
  AND NOT EXISTS (
    SELECT 1
    FROM CISADM.CI_FT ft
    WHERE ft.SA_ID = sa.SA_ID
      AND ft.CRE_DTTM >= TRUNC(SYSDATE) - 60
  )
"""
        df_cnt_gap = pd.read_sql(sql_cnt_gap, engine)
        total_gap = int(df_cnt_gap.iloc[0, 0]) if not df_cnt_gap.empty else 0
        print(f"Rule: Billing Gap (active SAs with no CI_FT rows in last 60 days) -> {total_gap} row(s).")
        samples_gap: list[dict] = []
        if total_gap > 0:
            sql_sample_gap = """
SELECT sa.SA_ID, sa.ACCT_ID, sa.SA_STATUS_FLG
FROM CISADM.CI_SA sa
WHERE NULLIF(TRIM(sa.SA_STATUS_FLG), '') = '20'
  AND NOT EXISTS (
    SELECT 1
    FROM CISADM.CI_FT ft
    WHERE ft.SA_ID = sa.SA_ID
      AND ft.CRE_DTTM >= TRUNC(SYSDATE) - 60
  )
  AND ROWNUM <= 10
"""
            df_sample_gap = pd.read_sql(sql_sample_gap, engine)
            if not df_sample_gap.empty:
                df_sample_gap.columns = [c.lower() for c in df_sample_gap.columns]
                for _, row in df_sample_gap.iterrows():
                    samples_gap.append(
                        {
                            "sa_id": row.get("sa_id"),
                            "acct_id": row.get("acct_id"),
                            "sa_status_flg": row.get("sa_status_flg"),
                        }
                    )
                    print(
                        f"  Sample: SA_ID={row.get('sa_id')} ACCT_ID={row.get('acct_id')} "
                        f"SA_STATUS_FLG={row.get('sa_status_flg')}"
                    )
            print(
                "  Explanation: Active service agreements with no financial transactions in the last 60 days "
                "may indicate a billing gap or operational issue for Customer Operations."
            )
        rules["billing_gap_60d"] = {
            "applies": True,
            "count": total_gap,
            "samples": samples_gap,
        }
    except Exception as e:
        print(f"Rule: Billing Gap (60d) - ERROR querying CISADM.CI_SA/CISADM.CI_FT: {e}")
        rules["billing_gap_60d"] = {
            "applies": True,
            "count": None,
            "samples": [],
            "error": str(e),
        }

    # Rule 2b: Billing Gap (cycle-aware) - critical only when no FT within cycle-based lookback
    # Monthly (M/01/1) -> 35 days; Quarterly (Q/03/3) -> 95 days; else 60 days.
    try:
        if _table_has_column(engine, "CISADM", "CI_ACCT", "BILL_CYC_CD"):
            sql_cycle_gap = """
SELECT COUNT(*) AS cnt
FROM CISADM.CI_SA sa
JOIN CISADM.CI_ACCT a ON a.ACCT_ID = sa.ACCT_ID
WHERE NULLIF(TRIM(sa.SA_STATUS_FLG), '') = '20'
  AND NOT EXISTS (
    SELECT 1 FROM CISADM.CI_FT ft
    WHERE ft.SA_ID = sa.SA_ID AND ft.CRE_DTTM >= TRUNC(SYSDATE) - (
      CASE WHEN UPPER(TRIM(NVL(a.BILL_CYC_CD,''))) IN ('M','01','1','MONTHLY') THEN 35
           WHEN UPPER(TRIM(NVL(a.BILL_CYC_CD,''))) IN ('Q','03','3','QUARTERLY') THEN 95
           ELSE 60 END
    )
  )
"""
            df_cycle = pd.read_sql(sql_cycle_gap, engine)
            cycle_gap = int(df_cycle.iloc[0, 0]) if not df_cycle.empty else 0
            print(f"Rule: Billing Gap (cycle-aware: no FT within cycle lookback) -> {cycle_gap} row(s).")
            rules["billing_gap_cycle_aware"] = {"applies": True, "count": cycle_gap, "samples": []}
        else:
            rules["billing_gap_cycle_aware"] = {"applies": False, "count": 0, "note": "CI_ACCT.BILL_CYC_CD not present."}
    except Exception as e:
        print(f"Rule: Billing Gap (cycle-aware) - ERROR: {e}")
        rules["billing_gap_cycle_aware"] = {"applies": True, "count": None, "error": str(e)}

    # Rule 2c: System Latency Risk - latest CI_FT older than last successful batch run
    try:
        if _table_has_column(engine, "CISADM", "F1_BATCH_RUN", "END_DTTM"):
            sql_max_ft = "SELECT MAX(CRE_DTTM) AS max_ft FROM CISADM.CI_FT"
            sql_max_batch = """
SELECT MAX(BR.END_DTTM) AS last_run
FROM CISADM.F1_BATCH_RUN BR
WHERE BR.START_DTTM >= TRUNC(SYSDATE) - 2
  AND BR.BATCH_CD IN ('BILLING','FINANCE','PAYMENT')
  AND UPPER(TRIM(NVL(BR.STATUS_CD,''))) = 'SUCCESS'
"""
            df_ft = pd.read_sql(sql_max_ft, engine)
            df_br = pd.read_sql(sql_max_batch, engine)
            max_ft = df_ft.iloc[0, 0] if not df_ft.empty and df_ft.iloc[0, 0] is not None else None
            last_batch = df_br.iloc[0, 0] if not df_br.empty and df_br.iloc[0, 0] is not None else None
            flagged = bool(max_ft is not None and last_batch is not None and max_ft < last_batch)
            if flagged:
                print("Rule: System Latency Risk - FLAGGED (latest CI_FT.CRE_DTTM older than last successful batch run).")
            else:
                print("Rule: System Latency Risk - OK (data not older than last batch run).")
            rules["system_latency_risk"] = {
                "applies": True,
                "flagged": flagged,
                "max_ft_cre_dttm": str(max_ft) if max_ft else None,
                "last_batch_end_dttm": str(last_batch) if last_batch else None,
            }
        else:
            rules["system_latency_risk"] = {"applies": False, "flagged": None, "note": "F1_BATCH_RUN.END_DTTM not present."}
    except Exception as e:
        print(f"Rule: System Latency Risk - ERROR: {e}")
        rules["system_latency_risk"] = {"applies": True, "flagged": None, "error": str(e)}

    # Rule 3: Cashiering - Missing deposits for active SAs
    try:
        sql_missing_dep = """
SELECT COUNT(DISTINCT sa.ACCT_ID) AS cnt
FROM CISADM.CI_SA sa
WHERE NULLIF(TRIM(sa.SA_STATUS_FLG), '') = '20'
  AND NOT EXISTS (
    SELECT 1
    FROM CISADM.CI_FT ft
    WHERE ft.SA_ID = sa.SA_ID
      AND ft.FT_TYPE_FLG = 'DP'
      AND ft.FREEZE_SW = 'Y'
  )
"""
        df_missing_dep = pd.read_sql(sql_missing_dep, engine)
        total_missing_dep = int(df_missing_dep.iloc[0, 0]) if not df_missing_dep.empty else 0
        print(f"Rule: Missing Deposits (active SAs without deposit FT) -> {total_missing_dep} account(s).")
        if total_missing_dep > 0:
            print("  Explanation: Active service agreements may require deposits per policy. Review collection policy.")
        rules["missing_deposits"] = {
            "applies": True,
            "count": total_missing_dep,
            "samples": [],
        }
    except Exception as e:
        print(f"Rule: Missing Deposits - ERROR: {e}")
        rules["missing_deposits"] = {"applies": True, "count": None, "samples": [], "error": str(e)}

    # Rule 4: Meter Ops - Service points without device install events (if D1 tables exist)
    # Note: Check CI_SP directly (not through CI_SA join) since CI_SA may not have SP_ID column
    try:
        if _table_has_column(engine, "CISADM", "D1_INSTALL_EVT", "INSTALL_EVT_ID"):
            sql_no_device = """
SELECT COUNT(DISTINCT sp.SP_ID) AS cnt
FROM CISADM.CI_SP sp
WHERE NOT EXISTS (
    SELECT 1
    FROM CISADM.D1_INSTALL_EVT ie
    WHERE ie.D1_SP_ID = sp.SP_ID
)
  AND sp.SP_STATUS_FLG IS NOT NULL
"""
            df_no_device = pd.read_sql(sql_no_device, engine)
            total_no_device = int(df_no_device.iloc[0, 0]) if not df_no_device.empty else 0
            print(f"Rule: Service Points without Device Install Events -> {total_no_device} SP(s).")
            if total_no_device > 0:
                print("  Explanation: Service points should have device install history for meter operations. This may be expected if D1 tables are not fully populated.")
            rules["sp_without_device_install"] = {
                "applies": True,
                "count": total_no_device,
                "samples": [],
            }
        else:
            print("Rule: Service Points without Device Install Events - SKIPPED (D1_INSTALL_EVT not present).")
            rules["sp_without_device_install"] = {"applies": False, "count": 0, "samples": []}
    except Exception as e:
        print(f"Rule: Service Points without Device Install Events - ERROR: {e}")
        rules["sp_without_device_install"] = {"applies": True, "count": None, "samples": [], "error": str(e)}

    # Rule 5: Customer Ops - Accounts without customer class
    try:
        sql_no_cust_class = """
SELECT COUNT(*) AS cnt
FROM CISADM.CI_ACCT a
WHERE NULLIF(TRIM(a.CUST_CL_CD), '') IS NULL
"""
        df_no_cust_class = pd.read_sql(sql_no_cust_class, engine)
        total_no_cust_class = int(df_no_cust_class.iloc[0, 0]) if not df_no_cust_class.empty else 0
        print(f"Rule: Accounts without Customer Class -> {total_no_cust_class} account(s).")
        if total_no_cust_class > 0:
            print("  Explanation: Customer class is required for billing and collections. Review account setup.")
        rules["accounts_without_cust_class"] = {
            "applies": True,
            "count": total_no_cust_class,
            "samples": [],
        }
    except Exception as e:
        print(f"Rule: Accounts without Customer Class - ERROR: {e}")
        rules["accounts_without_cust_class"] = {"applies": True, "count": None, "samples": [], "error": str(e)}

    # Rule 6: Finance - GL distributions without status
    try:
        sql_no_gl_status = """
SELECT COUNT(DISTINCT ft.FT_ID) AS cnt
FROM CISADM.CI_FT ft
JOIN CISADM.CI_FT_GL fg ON fg.FT_ID = ft.FT_ID
WHERE ft.CRE_DTTM >= TRUNC(SYSDATE) - 30
  AND NULLIF(TRIM(ft.GL_DISTRIB_STATUS), '') IS NULL
"""
        df_no_gl_status = pd.read_sql(sql_no_gl_status, engine)
        total_no_gl_status = int(df_no_gl_status.iloc[0, 0]) if not df_no_gl_status.empty else 0
        print(f"Rule: GL Distributions without Status (last 30 days) -> {total_no_gl_status} FT(s).")
        if total_no_gl_status > 0:
            print("  Explanation: Financial transactions with GL distributions should have a distribution status.")
        rules["gl_distributions_without_status"] = {
            "applies": True,
            "count": total_no_gl_status,
            "samples": [],
        }
    except Exception as e:
        print(f"Rule: GL Distributions without Status - ERROR: {e}")
        rules["gl_distributions_without_status"] = {"applies": True, "count": None, "samples": [], "error": str(e)}

    # Rule 7: F1 Metadata Layer - Batch Health (Critical Path Risk)
    # Check if Billing/Finance/Payment batches ran successfully in last 24 hours
    try:
        from fetch_usage import fetch_batch_health
        batch_health = fetch_batch_health()
        if batch_health and batch_health.get("critical_path_risk") is not None:
            failures = batch_health.get("total_batch_failures_24h", 0)
            runs = batch_health.get("total_batch_runs_24h", 0)
            if failures > 0:
                print(f"Rule: Batch Health (Critical Path Risk) - {failures} batch failure(s) in last 24 hours out of {runs} run(s).")
                print("  Explanation: Billing, Finance, or Payment batches failed. This is a Critical Path Risk - revenue operations may be impacted.")
                rules["batch_health_critical_path"] = {
                    "applies": True,
                    "count": failures,
                    "total_runs": runs,
                    "critical_path_risk": True,
                    "batches": batch_health.get("batches", []),
                }
            else:
                print(f"Rule: Batch Health - All batches successful ({runs} run(s) in last 24 hours).")
                rules["batch_health_critical_path"] = {
                    "applies": True,
                    "count": 0,
                    "total_runs": runs,
                    "critical_path_risk": False,
                }
        else:
            print("Rule: Batch Health - SKIPPED (F1_BATCH_RUN not present or no batch runs found).")
            rules["batch_health_critical_path"] = {
                "applies": False,
                "count": 0,
                "critical_path_risk": None,
                "note": "F1_BATCH_RUN table not present or no batch runs in last 24 hours.",
            }
    except Exception as e:
        print(f"Rule: Batch Health - ERROR: {e}")
        rules["batch_health_critical_path"] = {"applies": True, "count": None, "critical_path_risk": None, "error": str(e)}

    # Rule 8: Customer Contact Letter Readiness
    # 8a) Printable contacts missing template code
    try:
        sql_cc_missing_tmpl = """
SELECT COUNT(*) AS cnt
FROM CISADM.CI_CC cc
WHERE cc.PRINT_LETTER_SW = 'Y'
  AND NULLIF(TRIM(cc.LTR_TMPL_CD), '') IS NULL
"""
        df_cc_missing_tmpl = pd.read_sql(sql_cc_missing_tmpl, engine)
        missing_tmpl = int(df_cc_missing_tmpl.iloc[0, 0]) if not df_cc_missing_tmpl.empty else 0
        print(f"Rule: Contact Letters missing template code -> {missing_tmpl} row(s).")
        rules["contact_letter_missing_template"] = {
            "applies": True,
            "count": missing_tmpl,
            "samples": [],
        }
    except Exception as e:
        print(f"Rule: Contact Letters missing template code - ERROR: {e}")
        rules["contact_letter_missing_template"] = {"applies": True, "count": None, "samples": [], "error": str(e)}

    # 8b) Printable contacts missing recipient essentials (name or address1)
    try:
        sql_cc_missing_recipient = """
SELECT COUNT(*) AS cnt
FROM CISADM.CI_CC cc
LEFT JOIN CISADM.CI_PER_NAME pn
  ON pn.PER_ID = cc.PER_ID
 AND pn.PRIM_NAME_SW = 'Y'
LEFT JOIN CISADM.CI_PREM pr
  ON pr.PREM_ID = cc.PREM_ID
WHERE cc.PRINT_LETTER_SW = 'Y'
  AND (
      NULLIF(TRIM(pn.ENTITY_NAME), '') IS NULL
      OR NULLIF(TRIM(pr.ADDRESS1), '') IS NULL
  )
"""
        df_cc_missing_recipient = pd.read_sql(sql_cc_missing_recipient, engine)
        missing_recipient = int(df_cc_missing_recipient.iloc[0, 0]) if not df_cc_missing_recipient.empty else 0
        print(f"Rule: Contact Letters missing recipient essentials -> {missing_recipient} row(s).")
        if missing_recipient > 0:
            print("  Explanation: Printable letters require both recipient name and mailing address.")
        rules["contact_letter_missing_recipient"] = {
            "applies": True,
            "count": missing_recipient,
            "samples": [],
        }
    except Exception as e:
        print(f"Rule: Contact Letters missing recipient essentials - ERROR: {e}")
        rules["contact_letter_missing_recipient"] = {"applies": True, "count": None, "samples": [], "error": str(e)}

    # Write JSON summary for AI / dashboards
    cfg_path = Path(__file__).resolve().parent.parent / "output" / "config_completeness.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({"rules": rules}, f, indent=2)
        print(f"Wrote {cfg_path}")
    except Exception as e:
        print(f"Error writing configuration completeness JSON: {e}")
    return rules


def run_workstream_health_matrix(engine) -> dict:
    """
    For each workstream, check if the primary Source of Truth table has had a record
    created/frozen in the last 7 days. Returns dict: workstream -> {has_recent: bool, count_7d: int, primary_table, date_col}.
    Writes output/workstream_health.json so generate_narrative can flag Data Currency Risk.
    """
    import pandas as pd

    try:
        from . import queries as _q
    except Exception:
        import queries as _q

    health = {}
    rows_out = []
    for ws_name, full_table, date_col in getattr(_q, "WORKSTREAM_HEALTH", []) or []:
        count_7d = 0
        has_recent = False
        err = None
        try:
            if date_col:
                sql = f"SELECT COUNT(*) AS cnt FROM {full_table} WHERE {date_col} >= TRUNC(SYSDATE) - 7"
            else:
                # No date column: use table existence and total count only (cannot assess 7d)
                sql = f"SELECT COUNT(*) AS cnt FROM {full_table}"
            df = pd.read_sql(sql, engine)
            count_7d = int(df.iloc[0, 0]) if not df.empty else 0
            has_recent = count_7d > 0 if date_col else None  # None = not applicable
        except Exception as e:
            err = str(e)
            if "ORA-00942" in str(e).upper() or "TABLE OR VIEW DOES NOT EXIST" in str(e).upper():
                has_recent = None
                count_7d = None
            else:
                has_recent = False
                count_7d = 0

        health[ws_name] = {
            "has_recent": has_recent,
            "count_7d": count_7d,
            "primary_table": full_table,
            "date_col": date_col,
            "error": err,
        }
        risk = "Data Currency Risk" if (date_col and has_recent is False and err is None) else ("N/A" if has_recent is None else "OK")
        # When no date column, show "—" for Count (7d) instead of total table count
        display_cnt = "—" if date_col is None else (count_7d if count_7d is not None else "N/A")
        rows_out.append((ws_name, full_table, date_col or "N/A", display_cnt, risk))

    # Print matrix
    print("-" * 70)
    print("Workstream Health Matrix (Source of Truth table; 7-day freshness)")
    print("-" * 70)
    print(f"{'Workstream':<16} {'Primary Table':<28} {'Date Col':<18} {'Count (7d)':<12} {'Risk'}")
    print("-" * 70)
    for ws_name, tbl, col, cnt, risk in rows_out:
        print(f"{ws_name:<16} {tbl:<28} {str(col):<18} {str(cnt):<12} {risk}")
    print("-" * 70)
    stale = [ws for ws, v in health.items() if v.get("date_col") and v.get("has_recent") is False and not v.get("error")]
    if stale:
        print("Data Currency Risk (no records in last 7 days):", ", ".join(stale))
        print("generate_narrative will alert the client when these workstreams are referenced.")
    # Write JSON for generate_narrative
    out_path = Path(__file__).resolve().parent.parent / "output" / "workstream_health.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"workstreams": health, "stale_workstreams": stale}, f, indent=2)
    print(f"Wrote {out_path}")
    return health


def main() -> None:
    if not all([os.getenv("ORACLE_USER"), os.getenv("ORACLE_PASSWORD"), os.getenv("ORACLE_DSN")]):
        print("Set ORACLE_USER, ORACLE_PASSWORD, and ORACLE_DSN in .env to run validation.", file=sys.stderr)
        sys.exit(1)

    import pandas as pd
    from fetch_usage import _create_oracle_engine

    print("Connecting to Oracle...", flush=True)
    engine = _create_oracle_engine()
    try:
        print("-" * 70)
        for table, date_col in _TABLE_CHECKS:
            try:
                count_sql = f"SELECT COUNT(*) AS cnt FROM {table}"
                df_count = pd.read_sql(count_sql, engine)
                count = int(df_count.iloc[0, 0])
            except Exception as e:
                err = str(e).upper()
                if "ORA-00942" in err or "TABLE OR VIEW DOES NOT EXIST" in err:
                    print(f"{table}: not present (schema/table not in this database)")
                else:
                    print(f"{table}: ERROR reading count - {e}")
                continue
            # Resolve column: explicit override first, then _TABLE_CHECKS, then discover
            effective_col = _OVERRIDES.get(table) or date_col
            if effective_col is None:
                effective_col = _discover_date_column(engine, table)
            is_version = effective_col == "VERSION"
            max_dt = "N/A"
            if effective_col:
                try:
                    max_sql = f"SELECT MAX({effective_col}) AS max_val FROM {table}"
                    df_max = pd.read_sql(max_sql, engine)
                    val = df_max.iloc[0, 0] if not df_max.empty and df_max.iloc[0, 0] is not None else None
                    if val is not None:
                        max_dt = val if is_version else val
                    else:
                        max_dt = "NULL"
                except Exception:
                    if not is_version:
                        discovered = _discover_date_column(engine, table)
                        if discovered:
                            try:
                                max_sql2 = f"SELECT MAX({discovered}) AS max_val FROM {table}"
                                df_max2 = pd.read_sql(max_sql2, engine)
                                val = df_max2.iloc[0, 0] if not df_max2.empty and df_max2.iloc[0, 0] is not None else None
                                max_dt = val if val is not None else "NULL"
                                effective_col = discovered
                            except Exception:
                                pass
            display_col = effective_col or "N/A"
            status = "OK" if count > 0 else "EMPTY or STALE?"
            print(f"{table}: rows = {count:,}  MAX({display_col}) = {max_dt}  [{status}]")
            # Column list from metadata only (no SELECT *)
            try:
                cols = _get_table_columns(engine, table)
                if not cols:
                    print(f"  Columns: (none or no access)")
                else:
                    print(f"  Columns: {', '.join(cols)}")
            except Exception as e:
                print(f"  Columns: ERROR - {e}")
        print("-" * 70)
        print("If any table shows 0 rows or a very old MAX date, verify it is the correct production source.")
        # Data quality section
        print("-" * 70)
        print("Data quality")
        print("-" * 70)
        run_balance_reconciliation(engine)
        _run_ars_dt_null_density(engine)
        orphan_sa_count = _run_orphan_sa_check(engine)
        run_workstream_health_matrix(engine)
        rules = run_configuration_completeness_checks(engine)
        # Write validation metadata for pipeline and Jaspersoft Audit band
        from datetime import datetime, timezone
        meta = {
            "last_run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "orphan_sa_count": orphan_sa_count if orphan_sa_count >= 0 else None,
            "system_latency_risk": ((rules.get("system_latency_risk") or {}).get("flagged") is True),
        }
        meta_path = Path(__file__).resolve().parent.parent / "output" / "validation_metadata.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            print(f"Wrote {meta_path}")
        except Exception as e:
            print(f"Error writing validation_metadata.json: {e}")
        print("-" * 70)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
