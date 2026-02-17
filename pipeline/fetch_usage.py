"""
Fetch monthly usage (and optionally weather) for the AI narrative pipeline.
- If ORACLE_USER, ORACLE_PASSWORD, and ORACLE_DSN are set in .env, fetches from Oracle C2M (governed query).
- Otherwise reads from CSV exported from C2M.

READ-ONLY: All queries in this module are SELECT-only. The pipeline must never run
INSERT, UPDATE, DELETE, or DDL against C2M. See docs/semantic-layer.md.

When connecting to live Oracle C2M, apply Origin governance in all queries:
  - Financial facts: FREEZE_SW = 'Y'
  - Active accounts: SA_STATUS_FLG = '20'
See docs/semantic-layer.md and sql/governance_snippets.sql.
"""

import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd

# Optional Oracle: only import when credentials are used
def _oracle_available() -> bool:
    return bool(
        os.getenv("ORACLE_USER")
        and os.getenv("ORACLE_PASSWORD")
        and os.getenv("ORACLE_DSN")
    )


_oracledb_thick_initialized = False
_oracledb_thick_failed = False  # True after we tried and failed (e.g. client not on PATH)

# Message when server requires encryption but thick mode could not be enabled
_MSG_THICK_REQUIRED = (
    "Oracle server requires Native Network Encryption (thick mode). "
    "Quick fix: 1) Download Oracle Instant Client (Basic) from "
    "https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html "
    "2) Unzip to e.g. C:\\oracle\\instantclient_19_21 "
    "3) In .env add: ORACLE_CLIENT_LIB_DIR=C:\\oracle\\instantclient_19_21 "
    "Then re-run. See docs/database-connections.md for details."
)


def _ensure_oracledb_thick() -> None:
    """
    Initialize python-oracledb in thick mode so the server's Native Network
    Encryption/Data Integrity is supported. Uses ORACLE_CLIENT_LIB_DIR if set;
    otherwise tries the system PATH. Call once before any oracledb.connect().
    """
    global _oracledb_thick_initialized, _oracledb_thick_failed
    if _oracledb_thick_initialized or _oracledb_thick_failed:
        return
    import oracledb
    lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")
    if lib_dir:
        try:
            oracledb.init_oracle_client(lib_dir=lib_dir)
            _oracledb_thick_initialized = True
        except Exception as e:
            raise RuntimeError(
                f"Cannot initialize Oracle thick mode from ORACLE_CLIENT_LIB_DIR={lib_dir!r}. "
                f"Error: {e}. Fix the path or install Oracle Instant Client there. "
                "See docs/database-connections.md."
            ) from e
        return
    # Try thick mode from system PATH (no lib_dir)
    try:
        oracledb.init_oracle_client()
        _oracledb_thick_initialized = True
    except Exception as e:
        msg = str(e).upper()
        # DPI-1047 = cannot locate Oracle Client; leave thin mode, connect may still work or we'll raise below
        if "DPI-1047" in msg or "CANNOT LOCATE" in msg or "CANNOT FIND" in msg:
            _oracledb_thick_failed = True
            return
        raise RuntimeError(
            f"Oracle thick mode init failed: {e}. "
            "Set ORACLE_CLIENT_LIB_DIR in .env to your Oracle Instant Client directory. "
            "See docs/database-connections.md."
        ) from e


def _create_oracle_engine():
    """
    Build a SQLAlchemy engine for Oracle using .env credentials.
    Ensures thick mode is initialized first. Caller must engine.dispose() when done.
    """
    from sqlalchemy import create_engine

    user = os.getenv("ORACLE_USER")
    password = os.getenv("ORACLE_PASSWORD")
    dsn = os.getenv("ORACLE_DSN")
    if not all((user, password, dsn)):
        raise ValueError(
            "Oracle credentials missing. Set ORACLE_USER, ORACLE_PASSWORD, and ORACLE_DSN in .env."
        )
    _ensure_oracledb_thick()
    # DSN format: host:port/service_name
    host_port, _, service_name = dsn.partition("/")
    if not service_name:
        raise ValueError("ORACLE_DSN must be host:port/service_name.")
    host, _, port = host_port.rpartition(":")
    if not host or not port:
        raise ValueError("ORACLE_DSN must be host:port/service_name.")
    url = (
        "oracle+oracledb://"
        f"{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/?service_name={quote_plus(service_name)}"
    )
    return create_engine(url)


def fetch_usage_from_csv(csv_path: str | Path | None = None) -> pd.DataFrame:
    """
    Load usage data from a CSV file (e.g. exported from C2M).
    If csv_path is None, uses USAGE_CSV_PATH from env or default 'data/usage.csv'.
    """
    path = csv_path or os.getenv("USAGE_CSV_PATH", "data/usage.csv")
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Usage CSV not found at {path}. "
            "Export from C2M or set USAGE_CSV_PATH to your file."
        )
    return pd.read_csv(path)


def get_monthly_summary(df: pd.DataFrame) -> dict:
    """
    Reduce usage DataFrame to a single row summary for the current and prior month.
    Expects columns like: period_end, amount, usage_kwh (adjust per your CSV).
    """
    if df.empty:
        return {
            "current_amount": 0,
            "prior_amount": 0,
            "amount_delta": 0,
            "percent_change": 0.0,
            "current_usage_kwh": 0,
            "prior_usage_kwh": 0,
            "heatwave_days": 0,
        }

    # Normalize period if present
    if "period_end" in df.columns and pd.api.types.is_datetime64_any_dtype(df["period_end"]):
        df = df.sort_values("period_end", ascending=False)
    elif "bill_dt" in df.columns:
        df = df.sort_values("bill_dt", ascending=False)

    row = df.iloc[0]
    prior = df.iloc[1] if len(df) > 1 else row

    amount_col = "amount" if "amount" in df.columns else "bill_amt"
    usage_col = "usage_kwh" if "usage_kwh" in df.columns else "total_usage"

    current_amount = float(row.get(amount_col, 0))
    prior_amount = float(prior.get(amount_col, 0))
    amount_delta = current_amount - prior_amount
    percent_change = (amount_delta / prior_amount * 100.0) if prior_amount else 0.0

    return {
        "current_amount": current_amount,
        "prior_amount": prior_amount,
        "amount_delta": amount_delta,
        "percent_change": percent_change,
        "current_usage_kwh": float(row.get(usage_col, 0)),
        "prior_usage_kwh": float(prior.get(usage_col, 0)),
        "heatwave_days": int(row.get("heatwave_days", 0)),
    }


# Governed SQL: import from pipeline.queries (single source of truth).
try:
    from . import queries as _q
except ImportError:
    import queries as _q

_USAGE_QUERY = _q.USAGE_QUERY
_QUERY_ARREARS_STRATEGIC = _q.QUERY_ARREARS_STRATEGIC
_QUERY_ARREARS_BY_ACCT = _q.QUERY_ARREARS_BY_ACCT
_QUERY_PREMISE_TO_ACCT = _q.QUERY_PREMISE_TO_ACCT
_QUERY_CUSTOMER_NAME_TO_ACCT = _q.QUERY_CUSTOMER_NAME_TO_ACCT
_QUERY_DUPLICATE_PAYMENT = _q.QUERY_DUPLICATE_PAYMENT
_QUERY_BANKRUPTCY_MONITOR = _q.QUERY_BANKRUPTCY_MONITOR
# Risk Data (Audit Mode)
_QUERY_REVENUE_LEAKAGE = getattr(_q, "QUERY_REVENUE_LEAKAGE_CANCELED_SA", None)
_QUERY_LIQUIDITY_PENDING = getattr(_q, "QUERY_LIQUIDITY_RISK_PENDING_PAYMENTS", None)
_QUERY_LIQUIDITY_UNFROZEN_FT = getattr(_q, "QUERY_LIQUIDITY_RISK_UNFROZEN_FT", None)
_QUERY_STALE_PENDING_SA = getattr(_q, "QUERY_STALE_PENDING_SA", None)
_VALIDATION_QUERIES = _q.VALIDATION_QUERIES


def validate_data_health(engine=None):
    """
    Check that core C2M tables contain recent, live data before running the BI pipeline.
    Returns True if all checks pass; False if any table appears empty or stale (so caller
    can return a "No Data Found" payload instead of sending empty metrics to the AI).
    """
    if engine is None:
        engine = _create_oracle_engine()
        dispose = True
    else:
        dispose = False
    try:
        all_ok = True
        for label, sql in _VALIDATION_QUERIES.items():
            try:
                df = pd.read_sql(sql, engine)
                count = int(df.iloc[0, 0]) if not df.empty else 0
                if count == 0:
                    print(f"CRITICAL WARNING: Table for {label!r} appears empty or stale.", flush=True)
                    all_ok = False
            except Exception as e:
                print(f"CRITICAL WARNING: Data health check failed for {label!r}: {e}", flush=True)
                all_ok = False
        return all_ok
    finally:
        if dispose:
            engine.dispose()


def fetch_usage_from_oracle() -> pd.DataFrame:
    """
    Load usage from Oracle C2M using credentials in .env (ORACLE_USER, ORACLE_PASSWORD, ORACLE_DSN).
    Uses a governed query (FREEZE_SW, date window). Returns DataFrame with bill_dt, amount.
    """
    engine = _create_oracle_engine()
    try:
        df = pd.read_sql(_USAGE_QUERY, engine)
        if not df.empty:
            df.columns = [c.lower() for c in df.columns]
        return df
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def _aggregate_bi_results(
    df_arrears: pd.DataFrame,
    df_duplicate: pd.DataFrame,
    df_bankruptcy: pd.DataFrame,
) -> dict:
    """Aggregate DataFrames from the three BI queries into one metrics dict for the AI."""
    total_debt = float(df_arrears["total_debt"].sum()) if not df_arrears.empty and "total_debt" in df_arrears.columns else 0.0
    debt_30_days = float(df_arrears["debt_30_days"].sum()) if not df_arrears.empty and "debt_30_days" in df_arrears.columns else 0.0
    debt_60_days = float(df_arrears["debt_60_days"].sum()) if not df_arrears.empty and "debt_60_days" in df_arrears.columns else 0.0
    debt_over_60 = float(df_arrears["debt_over_60"].sum()) if not df_arrears.empty and "debt_over_60" in df_arrears.columns else 0.0
    large_bill_count = int(df_arrears["large_bill_count"].sum()) if not df_arrears.empty and "large_bill_count" in df_arrears.columns else 0

    duplicate_payment_account_count = len(df_duplicate)
    duplicate_payment_example_amt = 0.0
    if not df_duplicate.empty and "acct_payments_today" in df_duplicate.columns:
        duplicate_payment_example_amt = float(df_duplicate["acct_payments_today"].iloc[0])

    bankruptcy_alert_count = len(df_bankruptcy)
    bankruptcy_pym_amt = float(df_bankruptcy["pym_amt"].sum()) if not df_bankruptcy.empty and "pym_amt" in df_bankruptcy.columns else 0.0

    return {
        "total_debt": total_debt,
        "debt_30_days": debt_30_days,
        "debt_60_days": debt_60_days,
        "debt_over_60": debt_over_60,
        "large_bill_count": large_bill_count,
        "duplicate_payment_account_count": duplicate_payment_account_count,
        "duplicate_payment_example_amt": duplicate_payment_example_amt,
        "bankruptcy_alert_count": bankruptcy_alert_count,
        "bankruptcy_pym_amt": bankruptcy_pym_amt,
    }


def _raise_if_encryption_required(e: Exception) -> None:
    """If the exception is about thick mode/encryption, raise a clear RuntimeError."""
    err_msg = str(e).lower()
    orig = getattr(e, "orig", None)
    if orig is not None:
        err_msg += " " + str(orig).lower()
    if "thick mode" in err_msg or "encryption" in err_msg or "dpy-3001" in err_msg:
        raise RuntimeError(_MSG_THICK_REQUIRED) from e


def _run_bi_queries() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Run the three BI queries (read-only SELECT). Returns (df_arrears, df_duplicate, df_bankruptcy).
    Used by fetch_bi_summary and by test_queries for validation.
    """
    print("  Connecting to Oracle...", flush=True)
    engine = _create_oracle_engine()
    try:
        print("  Arrears query...", flush=True)
        df_arrears = pd.read_sql(_QUERY_ARREARS_STRATEGIC, engine)
        print("  Duplicate payment query...", flush=True)
        df_duplicate = pd.read_sql(_QUERY_DUPLICATE_PAYMENT, engine)
        print("  Bankruptcy query...", flush=True)
        df_bankruptcy = pd.read_sql(_QUERY_BANKRUPTCY_MONITOR, engine)
        for df in (df_arrears, df_duplicate, df_bankruptcy):
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
        return df_arrears, df_duplicate, df_bankruptcy
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def _run_risk_queries() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame] | None:
    """
    Run Risk Data queries (Revenue Leakage, Liquidity Pending, Liquidity Unfrozen FT, Stale Pending SA).
    Returns (df_leakage, df_pending, df_unfrozen_ft, df_stale_sa) or None if risk queries are disabled/unavailable.
    """
    if os.getenv("RISK_DATA_ENABLED", "").strip().lower() not in ("1", "true", "yes"):
        return None
    if not all((_QUERY_REVENUE_LEAKAGE, _QUERY_LIQUIDITY_PENDING, _QUERY_LIQUIDITY_UNFROZEN_FT, _QUERY_STALE_PENDING_SA)):
        return None
    print("  Risk Data: connecting to Oracle...", flush=True)
    engine = _create_oracle_engine()
    try:
        print("  Revenue Leakage (canceled SA)...", flush=True)
        df_leakage = pd.read_sql(_QUERY_REVENUE_LEAKAGE, engine)
        print("  Liquidity Risk (pending payments)...", flush=True)
        df_pending = pd.read_sql(_QUERY_LIQUIDITY_PENDING, engine)
        print("  Liquidity Risk (unfrozen FT)...", flush=True)
        df_unfrozen_ft = pd.read_sql(_QUERY_LIQUIDITY_UNFROZEN_FT, engine)
        print("  Stale Pending SA...", flush=True)
        df_stale_sa = pd.read_sql(_QUERY_STALE_PENDING_SA, engine)
        for df in (df_leakage, df_pending, df_unfrozen_ft, df_stale_sa):
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
        return df_leakage, df_pending, df_unfrozen_ft, df_stale_sa
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def _aggregate_risk_results(
    df_leakage: pd.DataFrame,
    df_pending: pd.DataFrame,
    df_unfrozen_ft: pd.DataFrame,
    df_stale_sa: pd.DataFrame,
) -> dict:
    """Aggregate Risk Data DataFrames into metrics for narrative and business_snapshot."""
    # Revenue Leakage: canceled SA with unresolved debt
    revenue_leakage_acct_count = 0
    revenue_leakage_total_amt = 0.0
    if not df_leakage.empty and "total_unresolved_amt" in df_leakage.columns:
        revenue_leakage_acct_count = len(df_leakage)
        revenue_leakage_total_amt = float(df_leakage["total_unresolved_amt"].sum())

    # Liquidity: pending payments — amount and count older than 48 hours
    liquidity_pending_amt = 0.0
    liquidity_pending_count_48h = 0
    if not df_pending.empty:
        amt_col = "pay_amt" if "pay_amt" in df_pending.columns else df_pending.columns[2] if len(df_pending.columns) > 2 else None
        days_col = "days_since_cre" if "days_since_cre" in df_pending.columns else None
        if amt_col:
            liquidity_pending_amt = float(df_pending[amt_col].sum())
        if days_col:
            liquidity_pending_count_48h = int((df_pending[days_col] >= 2).sum())

    # Liquidity: unfrozen FT — amount and count older than 48 hours
    liquidity_unfrozen_amt = 0.0
    liquidity_unfrozen_count_48h = 0
    if not df_unfrozen_ft.empty:
        amt_col = "cur_amt" if "cur_amt" in df_unfrozen_ft.columns else None
        days_col = "days_since_cre" if "days_since_cre" in df_unfrozen_ft.columns else None
        if amt_col:
            liquidity_unfrozen_amt = float(df_unfrozen_ft[amt_col].sum())
        if days_col:
            liquidity_unfrozen_count_48h = int((df_unfrozen_ft[days_col] >= 2).sum())

    # Stale Pending SA
    stale_pending_sa_count = len(df_stale_sa) if not df_stale_sa.empty else 0

    return {
        "revenue_leakage_acct_count": revenue_leakage_acct_count,
        "revenue_leakage_total_amt": revenue_leakage_total_amt,
        "liquidity_pending_amt": liquidity_pending_amt,
        "liquidity_pending_count_48h": liquidity_pending_count_48h,
        "liquidity_unfrozen_amt": liquidity_unfrozen_amt,
        "liquidity_unfrozen_count_48h": liquidity_unfrozen_count_48h,
        "stale_pending_sa_count": stale_pending_sa_count,
    }


def resolve_acct_id_from_premise(address_or_premise: str) -> list[int]:
    """
    Resolve an address or premise to one or more ACCT_IDs using governed SQL.
    Returns empty list if no mapping exists (e.g. placeholder not yet implemented).
    """
    from sqlalchemy import text
    if not (address_or_premise or address_or_premise.strip()):
        return []
    engine = _create_oracle_engine()
    try:
        df = pd.read_sql(
            text(_QUERY_PREMISE_TO_ACCT),
            engine,
            params={"address": address_or_premise.strip()},
        )
        if df.empty or "acct_id" not in [c.lower() for c in df.columns]:
            return []
        col = [c for c in df.columns if c.lower() == "acct_id"][0]
        ids = [int(x) for x in df[col].dropna() if str(x).isdigit()]
        return ids
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def resolve_acct_id_from_customer_name(name: str) -> list[int]:
    """
    Resolve a customer name to one or more ACCT_IDs using governed SQL.
    Returns empty list if no mapping exists (e.g. placeholder not yet implemented).
    """
    from sqlalchemy import text
    if not (name or name.strip()):
        return []
    engine = _create_oracle_engine()
    try:
        df = pd.read_sql(
            text(_QUERY_CUSTOMER_NAME_TO_ACCT),
            engine,
            params={"customer_name": name.strip()},
        )
        if df.empty or "acct_id" not in [c.lower() for c in df.columns]:
            return []
        col = [c for c in df.columns if c.lower() == "acct_id"][0]
        ids = [int(x) for x in df[col].dropna() if str(x).isdigit()]
        return ids
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_bi_slice_for_account(acct_id: int) -> dict | None:
    """
    Fetch BI metrics for a single account (arrears; duplicate/bankruptcy filtered in Python).
    Returns a dict with same keys as portfolio metrics (total_debt, debt_30_days, etc.) or None if no row.
    """
    from sqlalchemy import text
    engine = _create_oracle_engine()
    try:
        df_ar = pd.read_sql(text(_QUERY_ARREARS_BY_ACCT), engine, params={"acct_id": acct_id})
        if df_ar.empty:
            return None
        df_ar.columns = [c.lower() for c in df_ar.columns]
        # One account may have multiple rows (debt class); sum to one row
        total_debt = float(df_ar["total_debt"].sum())
        debt_30_days = float(df_ar["debt_30_days"].sum())
        debt_60_days = float(df_ar["debt_60_days"].sum())
        debt_over_60 = float(df_ar["debt_over_60"].sum())
        large_bill_count = int(df_ar["large_bill_count"].sum())
        # Optional: run full duplicate/bankruptcy and filter to this account
        df_dup = pd.read_sql(_QUERY_DUPLICATE_PAYMENT, engine)
        if not df_dup.empty:
            df_dup.columns = [c.lower() for c in df_dup.columns]
        dup_count = 0
        dup_example = 0.0
        if not df_dup.empty and "acct_nbr" in df_dup.columns:
            match = df_dup[df_dup["acct_nbr"].astype(int) == acct_id]
            if not match.empty:
                dup_count = 1
                dup_example = float(match.iloc[0].get("acct_payments_today", 0) or 0)
        df_bank = pd.read_sql(_QUERY_BANKRUPTCY_MONITOR, engine)
        if not df_bank.empty:
            df_bank.columns = [c.lower() for c in df_bank.columns]
        bank_count = 0
        bank_amt = 0.0
        if not df_bank.empty and "acct_id" in df_bank.columns:
            match = df_bank[df_bank["acct_id"].astype(int) == acct_id]
            if not match.empty:
                bank_count = 1
                bank_amt = float(match["pym_amt"].sum())
        return {
            "total_debt": total_debt,
            "debt_30_days": debt_30_days,
            "debt_60_days": debt_60_days,
            "debt_over_60": debt_over_60,
            "large_bill_count": large_bill_count,
            "duplicate_payment_account_count": dup_count,
            "duplicate_payment_example_amt": dup_example if dup_count else 0.0,
            "bankruptcy_alert_count": bank_count,
            "bankruptcy_pym_amt": bank_amt,
        }
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


# -----------------------------------------------------------------------------
# Workstream-specific fetch functions (data slices for NLQ and narrative)
# Each returns a dict for metrics["workstream_slices"][workstream] or None.
# -----------------------------------------------------------------------------

def fetch_billing_slice(acct_id: int) -> dict | None:
    """Billing & Rates workstream: recent bills for an account (CI_BILL: BILL_DT, BILL_ID)."""
    from sqlalchemy import text
    engine = _create_oracle_engine()
    try:
        df = pd.read_sql(text(_q.QUERY_BILLING_BY_ACCT), engine, params={"acct_id": acct_id})
        if df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        latest_dt = df["bill_dt"].max() if "bill_dt" in df.columns else None

        # Optional rate configuration dictionary (environment-wide, not yet per-account)
        rate_config = None
        try:
            df_rates = pd.read_sql(_q.QUERY_RATE_CONFIG, engine)
            if not df_rates.empty:
                df_rates.columns = [c.lower() for c in df_rates.columns]
                rate_config = df_rates.to_dict(orient="records")
        except Exception:
            rate_config = None

        return {
            "workstream": "billing",
            "billing_total_amount": 0.0,
            "billing_last_bill_dt": str(latest_dt) if latest_dt is not None else None,
            "billing_bill_count": len(df),
            "billing_row_count": len(df),
            "billing_rate_config": rate_config,
        }
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_cashiering_slice(acct_id: int) -> dict | None:
    """Cashiering workstream: payment events and tender status (TNDR_STATUS = '25' = Valid)."""
    from sqlalchemy import text
    engine = _create_oracle_engine()
    try:
        df = pd.read_sql(text(_q.QUERY_CASHIERING_BY_ACCT), engine, params={"acct_id": acct_id})
        if df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        status_col = "tndr_status_flg" if "tndr_status_flg" in df.columns else "tndr_status"
        valid_count = int((df[status_col] == "25").sum()) if status_col in df.columns else 0
        amt_col = "pay_amt" if "pay_amt" in df.columns else "tender_amt"
        total_pay = float(df[amt_col].sum()) if amt_col in df.columns else 0.0
        return {
            "workstream": "cashiering",
            "cashiering_tndr_status_valid_count": valid_count,
            "cashiering_total_pay_amt": total_pay,
            "cashiering_payment_count": len(df),
        }
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_meter_ops_slice(acct_id: int | None = None, sp_id: int | None = None) -> dict | None:
    """Meter Operations workstream: device and install date. Uses D1_* when present; else CI_SP fallback."""
    from sqlalchemy import text
    engine = _create_oracle_engine()
    try:
        if sp_id is not None:
            df = pd.read_sql(text(_q.QUERY_METER_OPS_BY_SP), engine, params={"sp_id": sp_id})
        elif acct_id is not None:
            df = pd.read_sql(text(_q.QUERY_METER_OPS_BY_ACCT), engine, params={"acct_id": acct_id})
        else:
            return None
        if df.empty and acct_id is not None:
            # D1 tables may be missing: try CI_SP fallback (INSTALL_DT at service point)
            try:
                df = pd.read_sql(
                    text(getattr(_q, "QUERY_METER_OPS_FALLBACK_BY_ACCT", "")),
                    engine,
                    params={"acct_id": acct_id},
                )
            except Exception:
                return None
            if df.empty:
                return None
            df.columns = [c.lower() for c in df.columns]
            install_dttm = df["install_dt"].iloc[0] if "install_dt" in df.columns else None
            device_id = df["sp_id"].iloc[0] if "sp_id" in df.columns else None
            device_type = df["sp_status_flg"].iloc[0] if "sp_status_flg" in df.columns else None
            return {
                "workstream": "meter_ops",
                "meter_install_dttm": str(install_dttm) if install_dttm is not None else None,
                "meter_nbr": device_id,
                "d1_device_id": device_id,
                "device_type_cd": device_type,
                "meter_row_count": len(df),
            }
        if df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        install_col = "d1_install_dttm" if "d1_install_dttm" in df.columns else "install_dttm"
        install_dttm = df[install_col].iloc[0] if install_col in df.columns else None
        device_id = df["d1_device_id"].iloc[0] if "d1_device_id" in df.columns else None
        device_type = df["device_type_cd"].iloc[0] if "device_type_cd" in df.columns else None
        return {
            "workstream": "meter_ops",
            "meter_install_dttm": str(install_dttm) if install_dttm is not None else None,
            "meter_nbr": device_id,
            "d1_device_id": device_id,
            "device_type_cd": device_type,
            "meter_row_count": len(df),
        }
    except Exception as e:
        err = str(e).upper()
        if "ORA-00942" in err or "TABLE OR VIEW DOES NOT EXIST" in err:
            # D1 missing: try CI_SP fallback for account-only
            if acct_id is not None:
                try:
                    fallback = getattr(_q, "QUERY_METER_OPS_FALLBACK_BY_ACCT", None)
                    if fallback:
                        df = pd.read_sql(text(fallback), engine, params={"acct_id": acct_id})
                        if df.empty:
                            return None
                        df.columns = [c.lower() for c in df.columns]
                        install_dttm = df["install_dt"].iloc[0] if "install_dt" in df.columns else None
                        device_id = df["sp_id"].iloc[0] if "sp_id" in df.columns else None
                        device_type = df["sp_status_flg"].iloc[0] if "sp_status_flg" in df.columns else None
                        return {
                            "workstream": "meter_ops",
                            "meter_install_dttm": str(install_dttm) if install_dttm is not None else None,
                            "meter_nbr": device_id,
                            "d1_device_id": device_id,
                            "device_type_cd": device_type,
                            "meter_row_count": len(df),
                        }
                except Exception:
                    pass
            return None
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_customer_ops_slice(acct_id: int) -> dict | None:
    """Customer Operations workstream: account, person name, and alerts."""
    from sqlalchemy import text
    engine = _create_oracle_engine()
    try:
        df = pd.read_sql(text(_q.QUERY_CUSTOMER_OPS_BY_ACCT), engine, params={"acct_id": acct_id})
        if df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        row = df.iloc[0]
        alert_types = df["alert_type_cd"].dropna().unique().tolist() if "alert_type_cd" in df.columns else []
        return {
            "workstream": "customer_ops",
            "customer_acct_nbr": row.get("acct_id"),
            "customer_entity_name": row.get("entity_name"),
            "customer_cust_cl_cd": row.get("cust_cl_cd"),
            "customer_coll_cl_cd": row.get("coll_cl_cd"),
            "customer_alert_types": alert_types,
        }
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_new_services_slice(acct_id: int | None = None) -> dict | None:
    """New Services workstream: SA status 10 (Pending) / 20, initiation dates (pipeline view)."""
    from sqlalchemy import text
    engine = _create_oracle_engine()
    try:
        if acct_id is not None:
            df = pd.read_sql(text(_q.QUERY_NEW_SERVICES_BY_ACCT), engine, params={"acct_id": acct_id})
        else:
            df = pd.read_sql(_q.QUERY_NEW_SERVICES_PIPELINE, engine)
        if df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        pending = int((df["sa_status_flg"] == "10").sum()) if "sa_status_flg" in df.columns else 0
        latest = df["sa_initiation_dttm"].max() if "sa_initiation_dttm" in df.columns else None
        return {
            "workstream": "new_services",
            "new_services_sa_status_pending_count": pending,
            "new_services_latest_initiation_dttm": str(latest) if latest is not None else None,
            "new_services_row_count": len(df),
        }
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_finance_gl_slice(acct_id: int | None = None) -> dict | None:
    """Finance workstream: GL distributions and batch (GL_DISTRIB_STATUS)."""
    from sqlalchemy import text
    engine = _create_oracle_engine()
    try:
        if acct_id is not None:
            df = pd.read_sql(text(_q.QUERY_FINANCE_GL_BY_ACCT), engine, params={"acct_id": acct_id})
        else:
            df = pd.read_sql(_q.QUERY_FINANCE_GL_BATCH, engine)
        if df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        statuses = df["gl_distrib_status"].dropna().unique().tolist() if "gl_distrib_status" in df.columns else []
        total_amt = float(df["amount"].sum()) if "amount" in df.columns else 0.0
        return {
            "workstream": "finance",
            "finance_gl_distrib_status_list": statuses,
            "finance_total_amt": total_amt,
            "finance_row_count": len(df),
        }
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_debt_mgmt_slice(acct_id: int) -> dict | None:
    """Debt Management workstream: collection class, credit review date."""
    from sqlalchemy import text
    engine = _create_oracle_engine()
    try:
        df = pd.read_sql(text(getattr(_q, "QUERY_DEBT_MGMT_BY_ACCT", "SELECT 1 FROM DUAL WHERE 1=0")), engine, params={"acct_id": acct_id})
        if df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        row = df.iloc[0]
        return {
            "workstream": "debt_mgmt",
            "debt_mgmt_coll_cl_cd": row.get("coll_cl_cd"),
            "debt_mgmt_cr_review_dt": str(row.get("cr_review_dt")) if row.get("cr_review_dt") is not None else None,
            "debt_mgmt_postpone_cr_rvw_dt": str(row.get("postpone_cr_rvw_dt")) if row.get("postpone_cr_rvw_dt") is not None else None,
        }
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_field_ops_slice(acct_id: int) -> dict | None:
    """Field Operations workstream: service point install date and status (CI_SP)."""
    from sqlalchemy import text
    engine = _create_oracle_engine()
    try:
        df = pd.read_sql(text(getattr(_q, "QUERY_FIELD_OPS_BY_ACCT", "SELECT 1 FROM DUAL WHERE 1=0")), engine, params={"acct_id": acct_id})
        if df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        row = df.iloc[0]
        return {
            "workstream": "field_ops",
            "field_ops_sp_id": row.get("sp_id"),
            "field_ops_install_dt": str(row.get("install_dt")) if row.get("install_dt") is not None else None,
            "field_ops_sp_status_flg": row.get("sp_status_flg"),
            "field_ops_sp_count": len(df),
        }
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


# -----------------------------------------------------------------------------
# Strategic/Portfolio-level fetch functions (for BI dashboard and insights)
# Each returns portfolio-level metrics for a workstream
# -----------------------------------------------------------------------------

def fetch_billing_strategic() -> dict:
    """Billing & Rates: Portfolio-level metrics (rate distribution, late fees, billing cycles)."""
    engine = _create_oracle_engine()
    try:
        strategic = {}
        # Strategic summary
        try:
            df = pd.read_sql(getattr(_q, "QUERY_BILLING_STRATEGIC", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
                row = df.iloc[0]
                strategic.update({
                    "total_accounts_billed": int(row.get("total_accounts_billed", 0)),
                    "total_bills": int(row.get("total_bills", 0)),
                    "bills_with_late_fee": int(row.get("bills_with_late_fee", 0)),
                    "bill_cycle_count": int(row.get("bill_cycle_count", 0)),
                    "rate_schedule_count": int(row.get("rate_schedule_count", 0)),
                })
        except Exception:
            pass
        # Rate distribution
        try:
            df_rate = pd.read_sql(getattr(_q, "QUERY_BILLING_RATE_DISTRIBUTION", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df_rate.empty:
                df_rate.columns = [c.lower() for c in df_rate.columns]
                strategic["rate_distribution"] = df_rate.to_dict(orient="records")
        except Exception:
            pass
        return strategic if strategic else None
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_cashiering_strategic() -> dict:
    """Cashiering: Portfolio-level metrics (payment methods, tender status, deposits)."""
    engine = _create_oracle_engine()
    try:
        strategic = {}
        try:
            df = pd.read_sql(getattr(_q, "QUERY_CASHIERING_STRATEGIC", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
                row = df.iloc[0]
                strategic.update({
                    "accounts_with_payments": int(row.get("accounts_with_payments", 0)),
                    "total_payment_events": int(row.get("total_payment_events", 0)),
                    "total_payment_amount": float(row.get("total_payment_amount", 0)),
                    "valid_tenders": int(row.get("valid_tenders", 0)),
                    "deposits_controlled": int(row.get("deposits_controlled", 0)),
                    "tender_type_count": int(row.get("tender_type_count", 0)),
                })
        except Exception:
            pass
        try:
            df_tender = pd.read_sql(getattr(_q, "QUERY_CASHIERING_TENDER_DISTRIBUTION", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df_tender.empty:
                df_tender.columns = [c.lower() for c in df_tender.columns]
                strategic["tender_distribution"] = df_tender.to_dict(orient="records")
        except Exception:
            pass
        return strategic if strategic else None
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_meter_ops_strategic() -> dict:
    """Meter Operations: Portfolio-level metrics (device types, installation trends)."""
    engine = _create_oracle_engine()
    try:
        strategic = {}
        try:
            df = pd.read_sql(getattr(_q, "QUERY_METER_OPS_STRATEGIC", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
                row = df.iloc[0]
                strategic.update({
                    "service_points_with_devices": int(row.get("service_points_with_devices", 0)),
                    "total_install_events": int(row.get("total_install_events", 0)),
                    "device_type_count": int(row.get("device_type_count", 0)),
                    "earliest_install": str(row.get("earliest_install")) if row.get("earliest_install") is not None else None,
                    "latest_install": str(row.get("latest_install")) if row.get("latest_install") is not None else None,
                })
        except Exception:
            pass
        try:
            df_dev = pd.read_sql(getattr(_q, "QUERY_METER_OPS_DEVICE_TYPE_DISTRIBUTION", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df_dev.empty:
                df_dev.columns = [c.lower() for c in df_dev.columns]
                strategic["device_type_distribution"] = df_dev.to_dict(orient="records")
        except Exception:
            pass
        return strategic if strategic else None
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_customer_ops_strategic() -> dict:
    """Customer Operations: Portfolio-level metrics (customer classes, alerts)."""
    engine = _create_oracle_engine()
    try:
        strategic = {}
        try:
            df = pd.read_sql(getattr(_q, "QUERY_CUSTOMER_OPS_STRATEGIC", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
                row = df.iloc[0]
                strategic.update({
                    "total_accounts": int(row.get("total_accounts", 0)),
                    "customer_class_count": int(row.get("customer_class_count", 0)),
                    "collection_class_count": int(row.get("collection_class_count", 0)),
                    "bill_cycle_count": int(row.get("bill_cycle_count", 0)),
                    "accounts_with_alerts": int(row.get("accounts_with_alerts", 0)),
                    "total_active_alerts": int(row.get("total_active_alerts", 0)),
                })
        except Exception:
            pass
        try:
            df_class = pd.read_sql(getattr(_q, "QUERY_CUSTOMER_OPS_CLASS_DISTRIBUTION", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df_class.empty:
                df_class.columns = [c.lower() for c in df_class.columns]
                strategic["customer_class_distribution"] = df_class.to_dict(orient="records")
        except Exception:
            pass
        return strategic if strategic else None
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_new_services_strategic() -> dict:
    """New Services: Portfolio-level metrics (pipeline status, initiation trends)."""
    engine = _create_oracle_engine()
    try:
        strategic = {}
        try:
            df = pd.read_sql(getattr(_q, "QUERY_NEW_SERVICES_STRATEGIC", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
                row = df.iloc[0]
                strategic.update({
                    "accounts_in_pipeline": int(row.get("accounts_in_pipeline", 0)),
                    "total_sa_in_pipeline": int(row.get("total_sa_in_pipeline", 0)),
                    "pending_count": int(row.get("pending_count", 0)),
                    "active_new_count": int(row.get("active_new_count", 0)),
                    "earliest_initiation": str(row.get("earliest_initiation")) if row.get("earliest_initiation") is not None else None,
                    "latest_initiation": str(row.get("latest_initiation")) if row.get("latest_initiation") is not None else None,
                })
        except Exception:
            pass
        try:
            df_status = pd.read_sql(getattr(_q, "QUERY_NEW_SERVICES_STATUS_DISTRIBUTION", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df_status.empty:
                df_status.columns = [c.lower() for c in df_status.columns]
                strategic["status_distribution"] = df_status.to_dict(orient="records")
        except Exception:
            pass
        return strategic if strategic else None
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_finance_strategic() -> dict:
    """Finance: Portfolio-level metrics (GL distribution, batch processing)."""
    engine = _create_oracle_engine()
    try:
        strategic = {}
        try:
            df = pd.read_sql(getattr(_q, "QUERY_FINANCE_STRATEGIC", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
                row = df.iloc[0]
                strategic.update({
                    "total_gl_distributions": int(row.get("total_gl_distributions", 0)),
                    "gl_account_count": int(row.get("gl_account_count", 0)),
                    "total_gl_amount": float(row.get("total_gl_amount", 0)),
                    "batch_count": int(row.get("batch_count", 0)),
                    "distributed_count": int(row.get("distributed_count", 0)),
                })
        except Exception:
            pass
        try:
            df_status = pd.read_sql(getattr(_q, "QUERY_FINANCE_GL_DISTRIBUTION_STATUS", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df_status.empty:
                df_status.columns = [c.lower() for c in df_status.columns]
                strategic["gl_distribution_status"] = df_status.to_dict(orient="records")
        except Exception:
            pass
        return strategic if strategic else None
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_debt_mgmt_strategic() -> dict:
    """Debt Management: Portfolio-level metrics (collection classes, credit reviews)."""
    engine = _create_oracle_engine()
    try:
        strategic = {}
        try:
            df = pd.read_sql(getattr(_q, "QUERY_DEBT_MGMT_STRATEGIC", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
                row = df.iloc[0]
                strategic.update({
                    "total_accounts": int(row.get("total_accounts", 0)),
                    "collection_class_count": int(row.get("collection_class_count", 0)),
                    "accounts_with_cr_review": int(row.get("accounts_with_cr_review", 0)),
                    "cr_reviews_due": int(row.get("cr_reviews_due", 0)),
                    "postponed_reviews": int(row.get("postponed_reviews", 0)),
                })
        except Exception:
            pass
        try:
            df_coll = pd.read_sql(getattr(_q, "QUERY_DEBT_MGMT_COLLECTION_CLASS_DISTRIBUTION", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df_coll.empty:
                df_coll.columns = [c.lower() for c in df_coll.columns]
                strategic["collection_class_distribution"] = df_coll.to_dict(orient="records")
        except Exception:
            pass
        return strategic if strategic else None
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_field_ops_strategic() -> dict:
    """Field Operations: Portfolio-level metrics (service point status, installation trends)."""
    engine = _create_oracle_engine()
    try:
        strategic = {}
        try:
            df = pd.read_sql(getattr(_q, "QUERY_FIELD_OPS_STRATEGIC", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
                row = df.iloc[0]
                strategic.update({
                    "total_service_points": int(row.get("total_service_points", 0)),
                    "installed_sp_count": int(row.get("installed_sp_count", 0)),
                    "status_type_count": int(row.get("status_type_count", 0)),
                    "earliest_install": str(row.get("earliest_install")) if row.get("earliest_install") is not None else None,
                    "latest_install": str(row.get("latest_install")) if row.get("latest_install") is not None else None,
                })
        except Exception:
            pass
        try:
            df_status = pd.read_sql(getattr(_q, "QUERY_FIELD_OPS_STATUS_DISTRIBUTION", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df_status.empty:
                df_status.columns = [c.lower() for c in df_status.columns]
                strategic["status_distribution"] = df_status.to_dict(orient="records")
        except Exception:
            pass
        return strategic if strategic else None
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


# -----------------------------------------------------------------------------
# OCX & Field Tasks (F1 Metadata Layer)
# Hybrid Strategy: Join CI/D1 functional data with F1_TSK task metadata
# -----------------------------------------------------------------------------

def fetch_field_tasks_slice(acct_id: int) -> dict | None:
    """OCX & Field Tasks: Task tracking for an account (F1_TSK + F1_TSK_LOG)."""
    from sqlalchemy import text
    engine = _create_oracle_engine()
    try:
        df = pd.read_sql(text(getattr(_q, "QUERY_FIELD_TASKS_BY_ACCT", "SELECT 1 FROM DUAL WHERE 1=0")), engine, params={"acct_id": acct_id})
        if df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        open_tasks = int((df["bo_status_cd"].notna() & ~df["bo_status_cd"].isin(["COMPLETE", "CLOSED"])).sum()) if "bo_status_cd" in df.columns else 0
        return {
            "workstream": "field_tasks",
            "field_tasks_count_30d": len(df),
            "field_tasks_open": open_tasks,
            "field_tasks_with_logs": int(df["log_dttm"].notna().sum()) if "log_dttm" in df.columns else 0,
        }
    except Exception as e:
        err = str(e).upper()
        if "ORA-00942" in err or "TABLE OR VIEW DOES NOT EXIST" in err:
            # F1_TSK may not be present in all environments
            return None
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_field_tasks_strategic() -> dict:
    """OCX & Field Tasks: Portfolio-level metrics (task queue health, status distribution)."""
    engine = _create_oracle_engine()
    try:
        strategic = {}
        try:
            df = pd.read_sql(getattr(_q, "QUERY_FIELD_TASKS_STRATEGIC", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
                row = df.iloc[0]
                strategic.update({
                    "total_tasks_30d": int(row.get("total_tasks_30d", 0)),
                    "open_tasks": int(row.get("open_tasks", 0)),
                    "bus_obj_type_count": int(row.get("bus_obj_type_count", 0)),
                    "tasks_with_logs": int(row.get("tasks_with_logs", 0)),
                    "earliest_task": str(row.get("earliest_task")) if row.get("earliest_task") is not None else None,
                    "latest_task": str(row.get("latest_task")) if row.get("latest_task") is not None else None,
                })
        except Exception as e:
            err = str(e).upper()
            if "ORA-00942" not in err and "TABLE OR VIEW DOES NOT EXIST" not in err:
                pass  # Other errors: log but continue
        try:
            df_status = pd.read_sql(getattr(_q, "QUERY_FIELD_TASKS_STATUS_DISTRIBUTION", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df_status.empty:
                df_status.columns = [c.lower() for c in df_status.columns]
                strategic["task_status_distribution"] = df_status.to_dict(orient="records")
        except Exception:
            pass
        return strategic if strategic else None
    except Exception as e:
        err = str(e).upper()
        if "ORA-00942" in err or "TABLE OR VIEW DOES NOT EXIST" in err:
            return None  # F1_TSK not present
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_batch_health() -> dict:
    """
    F1 Metadata Layer: Batch Health Validation (Critical Path Risk).
    Check if Billing/Finance/Payment batches ran successfully in last 24 hours.
    Returns dict with batch health metrics for validate_tables.py and narrative alerts.
    """
    engine = _create_oracle_engine()
    try:
        health = {}
        try:
            df = pd.read_sql(getattr(_q, "QUERY_F1_BATCH_RUN_CRITICAL_PATH", "SELECT 1 FROM DUAL WHERE 1=0"), engine)
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
                health["batches"] = df.to_dict(orient="records")
                # Calculate overall health
                total_runs = int(df["run_count_24h"].sum()) if "run_count_24h" in df.columns else 0
                total_failures = int(df["failure_count"].sum()) if "failure_count" in df.columns else 0
                health["total_batch_runs_24h"] = total_runs
                health["total_batch_failures_24h"] = total_failures
                health["critical_path_risk"] = total_failures > 0
            else:
                health["critical_path_risk"] = None  # F1_BATCH_RUN not present or no runs
        except Exception as e:
            err = str(e).upper()
            if "ORA-00942" in err or "TABLE OR VIEW DOES NOT EXIST" in err:
                health["critical_path_risk"] = None  # Table not present
            else:
                health["error"] = str(e)
        return health if health else None
    except Exception as e:
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_code_translation(field_name: str) -> dict | None:
    """
    F1 Metadata Layer: Code Translation (F1_EXT_LOOKUP).
    Translate technical codes (BO_STATUS_CD, BUS_OBJ_CD) into business-friendly descriptions.
    """
    from sqlalchemy import text
    engine = _create_oracle_engine()
    try:
        df = pd.read_sql(
            text(getattr(_q, "QUERY_F1_LOOKUP_CODE_TRANSLATION", "SELECT 1 FROM DUAL WHERE 1=0")),
            engine,
            params={"field_name": field_name},
        )
        if df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        # Return as dict: code -> description
        translation = {}
        for _, row in df.iterrows():
            code = row.get("field_value")
            desc = row.get("business_description")
            if code and desc:
                translation[str(code)] = str(desc)
        return translation if translation else None
    except Exception as e:
        err = str(e).upper()
        if "ORA-00942" in err or "TABLE OR VIEW DOES NOT EXIST" in err:
            return None  # F1_EXT_LOOKUP not present
        _raise_if_encryption_required(e)
        raise
    finally:
        engine.dispose()


def fetch_bi_summary() -> dict:
    """
    Run the three governed BI queries (Arrears, Duplicate Payment, Bankruptcy), aggregate,
    and return one metrics dict for the narrative generator. Uses a single Oracle connection.
    All SQL is SELECT-only; no database changes. No SQL is generated at runtime.
    When RISK_DATA_ENABLED=1, also runs Risk Data queries and merges revenue_leakage_*,
    liquidity_*_amt, liquidity_*_count_48h, and stale_pending_sa_count into the returned dict.
    """
    df_arrears, df_duplicate, df_bankruptcy = _run_bi_queries()
    metrics = _aggregate_bi_results(df_arrears, df_duplicate, df_bankruptcy)
    risk_result = _run_risk_queries()
    if risk_result is not None:
        df_leakage, df_pending, df_unfrozen_ft, df_stale_sa = risk_result
        risk_metrics = _aggregate_risk_results(df_leakage, df_pending, df_unfrozen_ft, df_stale_sa)
        metrics.update(risk_metrics)
    return metrics


def fetch_bi_summary_with_raw() -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Run the three BI queries and return both the aggregated metrics and the raw DataFrames.
    For testing and validation only. All queries are read-only SELECT.
    When RISK_DATA_ENABLED=1, risk metrics are merged into the returned metrics dict.
    """
    df_arrears, df_duplicate, df_bankruptcy = _run_bi_queries()
    metrics = _aggregate_bi_results(df_arrears, df_duplicate, df_bankruptcy)
    risk_result = _run_risk_queries()
    if risk_result is not None:
        df_leakage, df_pending, df_unfrozen_ft, df_stale_sa = risk_result
        risk_metrics = _aggregate_risk_results(df_leakage, df_pending, df_unfrozen_ft, df_stale_sa)
        metrics.update(risk_metrics)
    return metrics, df_arrears, df_duplicate, df_bankruptcy


def fetch_usage_and_summarize(csv_path: str | Path | None = None) -> dict:
    """
    Load usage and return a summary dict for the narrative generator.
    Uses Oracle C2M if ORACLE_USER, ORACLE_PASSWORD, and ORACLE_DSN are set; otherwise CSV.
    When Oracle is available, use fetch_bi_summary() for BI (arrears, payment integrity, bankruptcy) metrics.
    """
    if _oracle_available():
        df = fetch_usage_from_oracle()
    else:
        df = fetch_usage_from_csv(csv_path)
    return get_monthly_summary(df)
