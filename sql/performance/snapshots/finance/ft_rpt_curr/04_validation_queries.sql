-- 4a) Manual first run
BEGIN
    cisadm.refresh_ft_rpt_curr;
END;
/

-- 4b) Snapshot baseline row count
SELECT COUNT(*) AS snapshot_row_count
FROM cisadm.ft_rpt_curr;

-- 4c) Natural-key uniqueness check (should return 0 rows)
SELECT
    ft_id,
    COUNT(*) AS row_count
FROM cisadm.ft_rpt_curr
GROUP BY
    ft_id
HAVING COUNT(*) > 1;

-- 4d) Null key check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN ft_id IS NULL THEN 1 ELSE 0 END) AS null_ft_id_rows,
    SUM(CASE WHEN ft_type_flg IS NULL THEN 1 ELSE 0 END) AS null_ft_type_rows,
    SUM(CASE WHEN acct_id IS NULL THEN 1 ELSE 0 END) AS null_acct_id_rows,
    SUM(CASE WHEN sa_id IS NULL THEN 1 ELSE 0 END) AS null_sa_id_rows
FROM cisadm.ft_rpt_curr;

-- 4e) Description coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN ft_type_flg_desc IS NULL AND ft_type_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_ft_type_desc,
    SUM(CASE WHEN gl_distrib_status_desc IS NULL AND gl_distrib_status IS NOT NULL THEN 1 ELSE 0 END) AS missing_gl_status_desc,
    SUM(CASE WHEN sa_status_desc IS NULL AND sa_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_status_desc,
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_type_desc,
    SUM(CASE WHEN cust_cl_desc IS NULL AND cust_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_cust_cl_desc,
    SUM(CASE WHEN coll_cl_desc IS NULL AND coll_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_cl_desc,
    SUM(CASE WHEN bill_cyc_desc IS NULL AND bill_cyc_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_cyc_desc,
    SUM(CASE WHEN acct_mgmt_grp_desc IS NULL AND acct_mgmt_grp_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_acct_mgmt_grp_desc,
    SUM(CASE WHEN bseg_stat_desc IS NULL AND bseg_stat_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_bseg_status_desc,
    SUM(CASE WHEN adj_status_desc IS NULL AND adj_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_adj_status_desc,
    SUM(CASE WHEN adj_type_desc IS NULL AND adj_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_adj_type_desc
FROM cisadm.ft_rpt_curr;

-- 4f) FT type profile
SELECT
    ft_type_flg,
    ft_type_flg_desc,
    COUNT(*) AS ft_count,
    SUM(NVL(cur_amt, 0)) AS total_cur_amt,
    SUM(NVL(tot_amt, 0)) AS total_tot_amt
FROM cisadm.ft_rpt_curr
GROUP BY
    ft_type_flg,
    ft_type_flg_desc
ORDER BY
    ft_type_flg;

-- 4g) Optional child coverage by FT type
SELECT
    ft_type_flg,
    COUNT(*) AS ft_rows,
    SUM(CASE WHEN bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_bseg,
    SUM(CASE WHEN adj_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_adj,
    SUM(CASE WHEN pay_seg_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_pay_seg
FROM cisadm.ft_rpt_curr
GROUP BY
    ft_type_flg
ORDER BY
    ft_type_flg;

-- 4h) Amount population by FT type
SELECT
    ft_type_flg,
    COUNT(*) AS ft_rows,
    SUM(CASE WHEN cur_amt IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_cur_amt,
    SUM(CASE WHEN tot_amt IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_tot_amt,
    SUM(CASE WHEN adj_amt IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_adj_amt,
    SUM(CASE WHEN pay_seg_amt IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_pay_seg_amt
FROM cisadm.ft_rpt_curr
GROUP BY
    ft_type_flg
ORDER BY
    ft_type_flg;

-- 4i) Bill-segment date sanity
SELECT
    COUNT(*) AS rows_with_bseg_dates,
    SUM(CASE WHEN start_dt IS NOT NULL AND end_dt IS NOT NULL AND start_dt > end_dt THEN 1 ELSE 0 END) AS invalid_bseg_date_ranges
FROM cisadm.ft_rpt_curr
WHERE bseg_id IS NOT NULL;

-- 4j) Freeze-date sanity
SELECT
    COUNT(*) AS rows_with_freeze_dttm,
    SUM(CASE WHEN cre_dttm IS NOT NULL AND freeze_dttm IS NOT NULL AND freeze_dttm < cre_dttm THEN 1 ELSE 0 END) AS freeze_before_create_rows
FROM cisadm.ft_rpt_curr
WHERE freeze_dttm IS NOT NULL;

-- 4k) Quick user-facing spot check sample
SELECT *
FROM (
    SELECT
        ft_id,
        ft_type_flg_desc,
        accounting_dt,
        acct_id,
        sa_id,
        sa_type_desc,
        cust_cl_desc,
        coll_cl_desc,
        bill_cyc_desc,
        acct_mgmt_grp_desc,
        cur_amt,
        tot_amt,
        gl_distrib_status_desc,
        freeze_user_name
    FROM cisadm.ft_rpt_curr
    ORDER BY load_dttm DESC, accounting_dt DESC, ft_id
)
WHERE ROWNUM <= 25;
