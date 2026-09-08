-- Intensive QA pack for CISADM.PAY_TNDR_CASH_RPT_CURR
-- Focused on deposit-control parity and the tender-safe overlays added to the snapshot.

-- 6a) Distinct deposit-control parity against source
WITH snap AS (
    SELECT
        dep_ctl_id,
        MAX(dep_ctl_cre_dttm) AS snap_dep_ctl_cre_dttm,
        MAX(dep_ctl_status_flg) AS snap_dep_ctl_status_flg,
        MAX(dep_ctl_srce_type_flg) AS snap_dep_ctl_srce_type_flg,
        MAX(dep_ctl_start_balance) AS snap_dep_ctl_start_balance,
        MAX(dep_ctl_end_balance) AS snap_dep_ctl_end_balance,
        MAX(dep_ctl_tndr_dep_count) AS snap_dep_ctl_tndr_dep_count,
        MAX(dep_ctl_tndr_dep_amt) AS snap_dep_ctl_tndr_dep_amt
    FROM cisadm.pay_tndr_cash_rpt_curr
    WHERE dep_ctl_id IS NOT NULL
    GROUP BY dep_ctl_id
),
src_dep_amt AS (
    SELECT
        td.dep_ctl_id,
        COUNT(*) AS src_dep_ctl_tndr_dep_count,
        SUM(td.deposit_amt) AS src_dep_ctl_tndr_dep_amt
    FROM cisadm.ci_tndr_dep td
    GROUP BY td.dep_ctl_id
)
SELECT
    COUNT(*) AS paired_dep_ctl_rows,
    SUM(CASE WHEN NVL(dc.cre_dttm, DATE '1900-01-01') <> NVL(snap.snap_dep_ctl_cre_dttm, DATE '1900-01-01') THEN 1 ELSE 0 END) AS dep_ctl_create_dttm_mismatch_rows,
    SUM(CASE WHEN NVL(dc.dep_ctl_status_flg, '#NULL#') <> NVL(snap.snap_dep_ctl_status_flg, '#NULL#') THEN 1 ELSE 0 END) AS dep_ctl_status_mismatch_rows,
    SUM(CASE WHEN NVL(dc.tndr_srce_type_flg, '#NULL#') <> NVL(snap.snap_dep_ctl_srce_type_flg, '#NULL#') THEN 1 ELSE 0 END) AS dep_ctl_source_type_mismatch_rows,
    SUM(CASE WHEN NVL(dc.start_balance, 0) <> NVL(snap.snap_dep_ctl_start_balance, 0) THEN 1 ELSE 0 END) AS dep_ctl_start_balance_mismatch_rows,
    SUM(CASE WHEN NVL(dc.end_balance, 0) <> NVL(snap.snap_dep_ctl_end_balance, 0) THEN 1 ELSE 0 END) AS dep_ctl_end_balance_mismatch_rows,
    SUM(CASE WHEN NVL(src_dep_amt.src_dep_ctl_tndr_dep_count, 0) <> NVL(snap.snap_dep_ctl_tndr_dep_count, 0) THEN 1 ELSE 0 END) AS dep_ctl_dep_count_mismatch_rows,
    SUM(CASE WHEN NVL(src_dep_amt.src_dep_ctl_tndr_dep_amt, 0) <> NVL(snap.snap_dep_ctl_tndr_dep_amt, 0) THEN 1 ELSE 0 END) AS dep_ctl_dep_amt_mismatch_rows
FROM snap
INNER JOIN cisadm.ci_dep_ctl dc
    ON dc.dep_ctl_id = snap.dep_ctl_id
LEFT JOIN src_dep_amt
    ON src_dep_amt.dep_ctl_id = snap.dep_ctl_id;

-- 6b) Snapshot deposit controls not found in source
SELECT COUNT(*) AS snapshot_dep_ctls_not_in_source
FROM (
    SELECT DISTINCT dep_ctl_id
    FROM cisadm.pay_tndr_cash_rpt_curr
    WHERE dep_ctl_id IS NOT NULL
    MINUS
    SELECT dc.dep_ctl_id
    FROM cisadm.ci_dep_ctl dc
);

-- 6c) Sample mismatches for investigation
WITH snap AS (
    SELECT
        dep_ctl_id,
        MAX(dep_ctl_status_flg) AS snap_dep_ctl_status_flg,
        MAX(dep_ctl_srce_type_flg) AS snap_dep_ctl_srce_type_flg,
        MAX(dep_ctl_start_balance) AS snap_dep_ctl_start_balance,
        MAX(dep_ctl_end_balance) AS snap_dep_ctl_end_balance
    FROM cisadm.pay_tndr_cash_rpt_curr
    WHERE dep_ctl_id IS NOT NULL
    GROUP BY dep_ctl_id
)
SELECT *
FROM (
    SELECT
        snap.dep_ctl_id,
        dc.dep_ctl_status_flg AS src_dep_ctl_status_flg,
        snap.snap_dep_ctl_status_flg,
        dc.tndr_srce_type_flg AS src_dep_ctl_srce_type_flg,
        snap.snap_dep_ctl_srce_type_flg,
        dc.start_balance AS src_dep_ctl_start_balance,
        snap.snap_dep_ctl_start_balance,
        dc.end_balance AS src_dep_ctl_end_balance,
        snap.snap_dep_ctl_end_balance
    FROM snap
    INNER JOIN cisadm.ci_dep_ctl dc
        ON dc.dep_ctl_id = snap.dep_ctl_id
    WHERE NVL(dc.dep_ctl_status_flg, '#NULL#') <> NVL(snap.snap_dep_ctl_status_flg, '#NULL#')
       OR NVL(dc.tndr_srce_type_flg, '#NULL#') <> NVL(snap.snap_dep_ctl_srce_type_flg, '#NULL#')
       OR NVL(dc.start_balance, 0) <> NVL(snap.snap_dep_ctl_start_balance, 0)
       OR NVL(dc.end_balance, 0) <> NVL(snap.snap_dep_ctl_end_balance, 0)
    ORDER BY snap.dep_ctl_id
)
WHERE ROWNUM <= 25;
