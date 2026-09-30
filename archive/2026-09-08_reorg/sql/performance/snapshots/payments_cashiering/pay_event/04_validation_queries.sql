-- 4a) Manual first run (use 02a for initial full-history load)
BEGIN
    cisadm.refresh_pay_event_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.pay_event_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.ci_pay;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    pay_id,
    COUNT(*) AS row_count
FROM cisadm.pay_event_rpt_curr
GROUP BY pay_id
HAVING COUNT(*) > 1;

-- 4d) Null key check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN pay_id IS NULL THEN 1 ELSE 0 END) AS null_pay_id_rows,
    SUM(CASE WHEN pay_event_id IS NULL THEN 1 ELSE 0 END) AS null_pay_event_id_rows
FROM cisadm.pay_event_rpt_curr;

-- 4e) Description coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN pay_status_desc IS NULL AND pay_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_pay_status_desc,
    SUM(CASE WHEN can_rsn_desc IS NULL AND can_rsn_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_can_rsn_desc,
    SUM(CASE WHEN match_type_desc IS NULL AND match_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_match_type_desc,
    SUM(CASE WHEN sole_tender_type_desc IS NULL AND sole_tender_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sole_tender_type_desc,
    SUM(CASE WHEN primary_tndr_source_desc IS NULL AND primary_tndr_source_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_primary_tndr_source_desc,
    SUM(CASE WHEN primary_dep_ctl_status_desc IS NULL AND primary_dep_ctl_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_primary_dep_ctl_status_desc,
    SUM(CASE WHEN primary_pp_stat_desc IS NULL AND primary_pp_stat_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_primary_pp_stat_desc,
    SUM(CASE WHEN customer_name IS NULL AND acct_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_customer_name
FROM cisadm.pay_event_rpt_curr;

-- 4f) Payment amount reconciliation
SELECT
    COUNT(*) AS snap_pay_rows,
    SUM(pay_amt) AS snap_pay_amt
FROM cisadm.pay_event_rpt_curr;

SELECT
    COUNT(*) AS src_pay_rows,
    SUM(pay_amt) AS src_pay_amt
FROM cisadm.ci_pay;

-- 4g) Event tender aggregate reconciliation
WITH tender_src AS (
    SELECT
        pt.pay_event_id,
        COUNT(*) AS event_tender_count,
        SUM(pt.tender_amt) AS event_tender_amt
    FROM cisadm.ci_pay_tndr pt
    GROUP BY pt.pay_event_id
)
SELECT
    COUNT(*) AS mismatched_event_tender_rows
FROM cisadm.pay_event_rpt_curr snap
JOIN tender_src src
    ON src.pay_event_id = snap.pay_event_id
WHERE NVL(snap.event_tender_count, 0) <> NVL(src.event_tender_count, 0)
   OR NVL(snap.event_tender_amt, 0) <> NVL(src.event_tender_amt, 0);

-- 4h) Pay-plan aggregate reconciliation
WITH pp_src AS (
    SELECT
        pp.acct_id,
        COUNT(*) AS acct_pp_count,
        SUM(CASE WHEN NULLIF(TRIM(pp.pp_stat_flg), '') = '20' THEN 1 ELSE 0 END) AS active_pp_count
    FROM cisadm.ci_pp pp
    GROUP BY pp.acct_id
)
SELECT
    COUNT(*) AS mismatched_pp_accounts
FROM cisadm.pay_event_rpt_curr snap
JOIN pp_src src
    ON src.acct_id = snap.acct_id
WHERE NVL(snap.acct_pp_count, 0) <> NVL(src.acct_pp_count, 0)
   OR NVL(snap.active_pp_count, 0) <> NVL(src.active_pp_count, 0);

-- 4i) Payments in source missing from snapshot (should return 0 after full load)
SELECT pay.pay_id
FROM cisadm.ci_pay pay
LEFT JOIN cisadm.pay_event_rpt_curr snap
    ON snap.pay_id = pay.pay_id
WHERE snap.pay_id IS NULL
  AND ROWNUM <= 100;

-- 4j) Payment status distribution
SELECT
    pay_status_flg,
    pay_status_desc,
    COUNT(*) AS pay_count,
    SUM(NVL(pay_amt, 0)) AS pay_amt
FROM cisadm.pay_event_rpt_curr
GROUP BY
    pay_status_flg,
    pay_status_desc
ORDER BY
    pay_count DESC,
    pay_status_flg;

-- 4k) Spot-check recent payments with tender context
SELECT *
FROM (
    SELECT *
    FROM cisadm.pay_event_rpt_curr
    WHERE event_tender_count > 0
    ORDER BY pay_dt DESC NULLS LAST, pay_id
)
WHERE ROWNUM <= 10;

-- 4l) Rolling-window retention sanity (payments older than 6 months)
SELECT COUNT(*) AS stale_payments_still_present
FROM cisadm.pay_event_rpt_curr snap
WHERE snap.pay_dt < ADD_MONTHS(TRUNC(SYSDATE), -6);
