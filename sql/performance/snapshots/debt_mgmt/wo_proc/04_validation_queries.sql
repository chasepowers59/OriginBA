-- 4a) Manual first run (full-history baseline)
BEGIN
    cisadm.refresh_wo_proc_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.wo_proc_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.ci_wo_proc;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    wo_proc_id,
    COUNT(*) AS row_count
FROM cisadm.wo_proc_rpt_curr
GROUP BY wo_proc_id
HAVING COUNT(*) > 1;

-- 4d) Null coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN wo_proc_tmpl_desc IS NULL AND wo_proc_tmpl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_wo_proc_tmpl_desc,
    SUM(CASE WHEN wo_cntl_desc IS NULL AND wo_cntl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_wo_cntl_desc,
    SUM(CASE WHEN wo_status_desc IS NULL AND wo_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_wo_status_desc,
    SUM(CASE WHEN wo_stat_rsn_desc IS NULL AND wo_stat_rsn_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_wo_stat_rsn_desc,
    SUM(CASE WHEN uncoll_proc_stat_desc IS NULL AND uncoll_proc_stat_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_uncoll_proc_stat_desc,
    SUM(CASE WHEN crit_prio_desc IS NULL AND crit_prio_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_crit_prio_desc,
    SUM(CASE WHEN bill_cyc_desc IS NULL AND bill_cyc_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_cyc_desc,
    SUM(CASE WHEN coll_cl_desc IS NULL AND coll_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_cl_desc,
    SUM(CASE WHEN cust_cl_desc IS NULL AND cust_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_cust_cl_desc,
    SUM(CASE WHEN next_event_type_desc IS NULL AND next_event_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_next_event_type_desc,
    SUM(CASE WHEN next_event_status_desc IS NULL AND next_event_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_next_event_status_desc,
    SUM(CASE WHEN latest_event_type_desc IS NULL AND latest_event_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_latest_event_type_desc,
    SUM(CASE WHEN latest_event_status_desc IS NULL AND latest_event_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_latest_event_status_desc,
    SUM(CASE WHEN customer_name IS NULL THEN 1 ELSE 0 END) AS missing_customer_name
FROM cisadm.wo_proc_rpt_curr;

-- 4e) Event reconciliation
SELECT
    SUM(event_count) AS snap_event_count,
    SUM(open_event_count) AS snap_open_event_count,
    SUM(completed_event_count) AS snap_completed_event_count
FROM cisadm.wo_proc_rpt_curr;

SELECT
    COUNT(*) AS src_event_count,
    SUM(CASE WHEN completion_dt IS NULL THEN 1 ELSE 0 END) AS src_open_event_count,
    SUM(CASE WHEN completion_dt IS NOT NULL THEN 1 ELSE 0 END) AS src_completed_event_count
FROM cisadm.ci_wo_evt;

-- 4f) BI view overlay coverage
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN ars_at_start IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_ars_at_start,
    SUM(CASE WHEN ars_at_end IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_ars_at_end,
    SUM(CASE WHEN process_duration_days IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_process_duration_days,
    SUM(CASE WHEN uncoll_proc_stat_flg IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_uncoll_proc_stat_flg
FROM cisadm.wo_proc_rpt_curr;

-- 4g) Status profile
SELECT
    wo_status_flg,
    wo_status_desc,
    COUNT(*) AS proc_count,
    SUM(ars_at_start) AS total_ars_at_start,
    SUM(ars_at_end) AS total_ars_at_end
FROM cisadm.wo_proc_rpt_curr
GROUP BY
    wo_status_flg,
    wo_status_desc
ORDER BY
    proc_count DESC,
    wo_status_flg;

-- 4h) WO SA amount reconciliation
SELECT
    SUM(wo_sa_active_amt) AS snap_wo_sa_active_amt,
    SUM(wo_sa_inactive_amt) AS snap_wo_sa_inactive_amt,
    SUM(wo_sa_count) AS snap_wo_sa_count_total
FROM cisadm.wo_proc_rpt_curr;

SELECT
    SUM(CASE WHEN NULLIF(TRIM(wo_sa_stat_flg), '') = '10' THEN NVL(ars_amt, 0) ELSE 0 END) AS src_wo_sa_active_amt,
    SUM(CASE WHEN NULLIF(TRIM(wo_sa_stat_flg), '') = '20' THEN NVL(ars_amt, 0) ELSE 0 END) AS src_wo_sa_inactive_amt,
    COUNT(*) AS src_wo_sa_count_total
FROM cisadm.ci_wo_proc_sa;

-- 4i) Rolling-window profile
SELECT
    COUNT(*) AS rows_in_6mo_window
FROM cisadm.wo_proc_rpt_curr
WHERE wo_proc_cre_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
   OR wo_proc_compl_dt IS NULL
   OR wo_proc_compl_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6);

-- 4j) Spot-check recent write-off processes
SELECT *
FROM (
    SELECT *
    FROM cisadm.wo_proc_rpt_curr
    ORDER BY wo_proc_cre_dttm DESC NULLS LAST
)
WHERE ROWNUM <= 10;
