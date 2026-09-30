-- 4a) Manual first run (use 02a for initial full-history load)
BEGIN
    cisadm.refresh_acct_customer_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.acct_customer_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.ci_acct;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    acct_id,
    COUNT(*) AS row_count
FROM cisadm.acct_customer_rpt_curr
GROUP BY acct_id
HAVING COUNT(*) > 1;

-- 4d) Null key check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN acct_id IS NULL THEN 1 ELSE 0 END) AS null_acct_id_rows
FROM cisadm.acct_customer_rpt_curr;

-- 4e) Description coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN bill_cyc_desc IS NULL AND bill_cyc_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_cyc_desc,
    SUM(CASE WHEN cust_cl_desc IS NULL AND cust_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_cust_cl_desc,
    SUM(CASE WHEN coll_cl_desc IS NULL AND coll_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_cl_desc,
    SUM(CASE WHEN acct_mgmt_grp_desc IS NULL AND acct_mgmt_grp_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_acct_mgmt_grp_desc,
    SUM(CASE WHEN bud_plan_desc IS NULL AND bud_plan_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bud_plan_desc,
    SUM(CASE WHEN cis_division_desc IS NULL AND cis_division IS NOT NULL THEN 1 ELSE 0 END) AS missing_cis_division_desc,
    SUM(CASE WHEN bill_rte_type_desc IS NULL AND bill_rte_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_rte_type_desc,
    SUM(CASE WHEN per_or_bus_desc IS NULL AND per_or_bus_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_per_or_bus_desc,
    SUM(CASE WHEN ls_sl_desc IS NULL AND ls_sl_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_ls_sl_desc,
    SUM(CASE WHEN latest_alert_type_desc IS NULL AND latest_alert_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_latest_alert_type_desc,
    SUM(CASE WHEN sole_active_sa_type_desc IS NULL AND sole_active_sa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sole_active_sa_type_desc,
    SUM(CASE WHEN customer_name IS NULL THEN 1 ELSE 0 END) AS missing_customer_name
FROM cisadm.acct_customer_rpt_curr;

-- 4f) Alert aggregate reconciliation (no bseg fan-out)
WITH alert_src AS (
    SELECT
        al.acct_id,
        COUNT(*) AS alert_count,
        SUM(
            CASE
                WHEN TRUNC(SYSDATE) >= al.start_dt
                 AND (al.end_dt IS NULL OR TRUNC(SYSDATE) <= al.end_dt)
                THEN 1
                ELSE 0
            END
        ) AS open_alert_count
    FROM cisadm.ci_acct_alert al
    GROUP BY al.acct_id
)
SELECT
    COUNT(*) AS mismatched_alert_accounts
FROM cisadm.acct_customer_rpt_curr snap
JOIN alert_src src
    ON src.acct_id = snap.acct_id
WHERE NVL(snap.alert_count, 0) <> NVL(src.alert_count, 0)
   OR NVL(snap.open_alert_count, 0) <> NVL(src.open_alert_count, 0);

-- 4g) SA aggregate reconciliation
WITH sa_src AS (
    SELECT
        sa.acct_id,
        COUNT(*) AS total_sa_count,
        SUM(CASE WHEN sa.sa_status_flg = '20' THEN 1 ELSE 0 END) AS active_sa_count
    FROM cisadm.ci_sa sa
    GROUP BY sa.acct_id
)
SELECT
    COUNT(*) AS mismatched_sa_accounts
FROM cisadm.acct_customer_rpt_curr snap
JOIN sa_src src
    ON src.acct_id = snap.acct_id
WHERE NVL(snap.total_sa_count, 0) <> NVL(src.total_sa_count, 0)
   OR NVL(snap.active_sa_count, 0) <> NVL(src.active_sa_count, 0);

-- 4h) Landlord summary reconciliation
WITH ll_src AS (
    SELECT
        ll.acct_id,
        COUNT(DISTINCT ll.ll_id) AS landlord_agreement_count
    FROM cisadm.ci_landlord ll
    GROUP BY ll.acct_id
)
SELECT
    COUNT(*) AS mismatched_landlord_accounts
FROM cisadm.acct_customer_rpt_curr snap
JOIN ll_src src
    ON src.acct_id = snap.acct_id
WHERE NVL(snap.landlord_agreement_count, 0) <> NVL(src.landlord_agreement_count, 0);

-- 4i) Accounts with alerts in source but zero counts in snapshot (should return 0)
SELECT snap.acct_id
FROM cisadm.acct_customer_rpt_curr snap
WHERE NVL(snap.alert_count, 0) = 0
  AND EXISTS (
      SELECT 1
      FROM cisadm.ci_acct_alert al
      WHERE al.acct_id = snap.acct_id
  );

-- 4j) Customer class distribution
SELECT
    cust_cl_cd,
    cust_cl_desc,
    COUNT(*) AS acct_count,
    SUM(NVL(active_sa_count, 0)) AS active_sa_count,
    SUM(NVL(open_alert_count, 0)) AS open_alert_count
FROM cisadm.acct_customer_rpt_curr
GROUP BY
    cust_cl_cd,
    cust_cl_desc
ORDER BY
    acct_count DESC,
    cust_cl_cd;

-- 4k) Open-alert profile
SELECT
    CASE
        WHEN open_alert_count = 0 THEN 'No open alerts'
        WHEN open_alert_count = 1 THEN 'One open alert'
        ELSE 'Multiple open alerts'
    END AS open_alert_bucket,
    COUNT(*) AS acct_count
FROM cisadm.acct_customer_rpt_curr
GROUP BY
    CASE
        WHEN open_alert_count = 0 THEN 'No open alerts'
        WHEN open_alert_count = 1 THEN 'One open alert'
        ELSE 'Multiple open alerts'
    END
ORDER BY
    acct_count DESC;

-- 4l) Spot-check accounts with open alerts
SELECT *
FROM (
    SELECT *
    FROM cisadm.acct_customer_rpt_curr
    WHERE open_alert_count > 0
    ORDER BY open_alert_count DESC, acct_id
)
WHERE ROWNUM <= 10;

-- 4m) Spot-check landlord accounts
SELECT *
FROM (
    SELECT *
    FROM cisadm.acct_customer_rpt_curr
    WHERE landlord_agreement_count > 0
    ORDER BY landlord_agreement_count DESC, acct_id
)
WHERE ROWNUM <= 10;

-- 4n) Rolling-window retention sanity (accounts older than 6 months with no activity)
SELECT COUNT(*) AS stale_accounts_still_present
FROM cisadm.acct_customer_rpt_curr snap
WHERE snap.setup_dt < ADD_MONTHS(TRUNC(SYSDATE), -6)
  AND NOT EXISTS (
      SELECT 1
      FROM cisadm.ci_sa sa
      WHERE sa.acct_id = snap.acct_id
        AND (
            sa.start_dt >= ADD_MONTHS(TRUNC(SYSDATE), -6)
            OR sa.end_dt >= ADD_MONTHS(TRUNC(SYSDATE), -6)
            OR sa.sa_status_flg = '20'
        )
  )
  AND NOT EXISTS (
      SELECT 1
      FROM cisadm.ci_acct_alert al
      WHERE al.acct_id = snap.acct_id
        AND (
            al.start_dt >= ADD_MONTHS(TRUNC(SYSDATE), -6)
            OR al.end_dt >= ADD_MONTHS(TRUNC(SYSDATE), -6)
            OR (
                TRUNC(SYSDATE) >= al.start_dt
                AND (al.end_dt IS NULL OR TRUNC(SYSDATE) <= al.end_dt)
            )
        )
  );
