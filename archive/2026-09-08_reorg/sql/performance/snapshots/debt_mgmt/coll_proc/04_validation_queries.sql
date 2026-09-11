-- 4a) Manual first run
BEGIN
    cisadm.refresh_coll_proc_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.coll_proc_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.ci_coll_proc;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    coll_proc_id,
    COUNT(*) AS row_count
FROM cisadm.coll_proc_rpt_curr
GROUP BY coll_proc_id
HAVING COUNT(*) > 1;

-- 4d) Null coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN coll_proc_tmpl_desc IS NULL AND coll_proc_tmpl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_proc_tmpl_desc,
    SUM(CASE WHEN coll_cl_cntl_desc IS NULL AND coll_cl_cntl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_cl_cntl_desc,
    SUM(CASE WHEN coll_status_desc IS NULL AND coll_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_status_desc,
    SUM(CASE WHEN coll_stat_rsn_desc IS NULL AND coll_stat_rsn_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_stat_rsn_desc,
    SUM(CASE WHEN coll_cat_prio_desc IS NULL AND coll_cat_prio_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_cat_prio_desc,
    SUM(CASE WHEN crit_prio_desc IS NULL AND crit_prio_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_crit_prio_desc,
    SUM(CASE WHEN bill_cyc_desc IS NULL AND bill_cyc_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_cyc_desc,
    SUM(CASE WHEN coll_cl_desc IS NULL AND coll_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_cl_desc,
    SUM(CASE WHEN cust_cl_desc IS NULL AND cust_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_cust_cl_desc,
    SUM(CASE WHEN acct_mgmt_grp_desc IS NULL AND acct_mgmt_grp_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_acct_mgmt_grp_desc,
    SUM(CASE WHEN bud_plan_desc IS NULL AND bud_plan_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bud_plan_desc,
    SUM(CASE WHEN next_event_type_desc IS NULL AND next_event_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_next_event_type_desc,
    SUM(CASE WHEN next_event_status_desc IS NULL AND next_event_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_next_event_status_desc,
    SUM(CASE WHEN latest_event_type_desc IS NULL AND latest_event_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_latest_event_type_desc,
    SUM(CASE WHEN latest_event_status_desc IS NULL AND latest_event_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_latest_event_status_desc,
    SUM(CASE WHEN customer_name IS NULL THEN 1 ELSE 0 END) AS missing_customer_name
FROM cisadm.coll_proc_rpt_curr;

-- 4e) Event reconciliation
SELECT
    SUM(event_count) AS snap_event_count,
    SUM(open_event_count) AS snap_open_event_count,
    SUM(completed_event_count) AS snap_completed_event_count
FROM cisadm.coll_proc_rpt_curr;

SELECT
    COUNT(*) AS src_event_count,
    SUM(CASE WHEN completion_dt IS NULL THEN 1 ELSE 0 END) AS src_open_event_count,
    SUM(CASE WHEN completion_dt IS NOT NULL THEN 1 ELSE 0 END) AS src_completed_event_count
FROM cisadm.ci_coll_evt;

-- 4f) Status profile
SELECT
    coll_status_flg,
    coll_status_desc,
    COUNT(*) AS proc_count,
    SUM(ars_amt) AS total_ars_amt
FROM cisadm.coll_proc_rpt_curr
GROUP BY
    coll_status_flg,
    coll_status_desc
ORDER BY
    proc_count DESC,
    coll_status_flg;

-- 4g) Template profile
SELECT
    coll_proc_tmpl_cd,
    coll_proc_tmpl_desc,
    COUNT(*) AS proc_count,
    SUM(ars_amt) AS total_ars_amt
FROM cisadm.coll_proc_rpt_curr
GROUP BY
    coll_proc_tmpl_cd,
    coll_proc_tmpl_desc
ORDER BY
    proc_count DESC,
    coll_proc_tmpl_cd;

-- 4h) Spot-check open next events
SELECT *
FROM cisadm.coll_proc_rpt_curr
WHERE next_event_seq IS NOT NULL
  AND ROWNUM <= 10;
