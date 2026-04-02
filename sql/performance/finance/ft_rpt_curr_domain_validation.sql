-- Purpose:
--   Read-only validation checks for the FT_RPT_CURR snapshot-backed domain.
--
-- Goal:
--   Prove the domain source table is row-safe at FT grain and that the
--   business-friendly domain labels are only a presentation change.

-- 1) Snapshot baseline row count
SELECT COUNT(*) AS snapshot_row_count
FROM cisadm.ft_rpt_curr;

-- 2) Natural-key uniqueness check
-- Should return 0 rows if the snapshot is truly one row per FT
SELECT
    ft_id,
    COUNT(*) AS row_count
FROM cisadm.ft_rpt_curr
GROUP BY
    ft_id
HAVING COUNT(*) > 1;

-- 3) Null key check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN ft_id IS NULL THEN 1 ELSE 0 END) AS null_ft_id_rows,
    SUM(CASE WHEN ft_type_flg IS NULL THEN 1 ELSE 0 END) AS null_ft_type_rows,
    SUM(CASE WHEN acct_id IS NULL THEN 1 ELSE 0 END) AS null_acct_id_rows,
    SUM(CASE WHEN sa_id IS NULL THEN 1 ELSE 0 END) AS null_sa_id_rows
FROM cisadm.ft_rpt_curr;

-- 4) Description coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN ft_type_flg_desc IS NULL AND ft_type_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_ft_type_desc,
    SUM(CASE WHEN gl_distrib_status_desc IS NULL AND gl_distrib_status IS NOT NULL THEN 1 ELSE 0 END) AS missing_gl_status_desc,
    SUM(CASE WHEN sa_status_desc IS NULL AND sa_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_status_desc,
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_type_desc,
    SUM(CASE WHEN bseg_stat_desc IS NULL AND bseg_stat_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_bseg_status_desc,
    SUM(CASE WHEN adj_status_desc IS NULL AND adj_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_adj_status_desc,
    SUM(CASE WHEN adj_type_desc IS NULL AND adj_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_adj_type_desc
FROM cisadm.ft_rpt_curr;

-- 5) FT type profile
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

-- 6) Optional child coverage by FT type
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

-- 7) Amount population by FT type
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

-- 8) Bill-segment date sanity
SELECT
    COUNT(*) AS rows_with_bseg_dates,
    SUM(CASE WHEN start_dt IS NOT NULL AND end_dt IS NOT NULL AND start_dt > end_dt THEN 1 ELSE 0 END) AS invalid_bseg_date_ranges
FROM cisadm.ft_rpt_curr
WHERE bseg_id IS NOT NULL;

-- 9) Freeze-date sanity
SELECT
    COUNT(*) AS rows_with_freeze_dttm,
    SUM(CASE WHEN cre_dttm IS NOT NULL AND freeze_dttm IS NOT NULL AND freeze_dttm < cre_dttm THEN 1 ELSE 0 END) AS freeze_before_create_rows
FROM cisadm.ft_rpt_curr
WHERE freeze_dttm IS NOT NULL;

-- 10) Quick user-facing spot check sample
SELECT *
FROM (
    SELECT
        ft_id,
        ft_type_flg_desc,
        accounting_dt,
        acct_id,
        sa_id,
        sa_type_desc,
        cur_amt,
        tot_amt,
        gl_distrib_status_desc,
        freeze_user_name
    FROM cisadm.ft_rpt_curr
    ORDER BY load_dttm DESC, accounting_dt DESC, ft_id
)
WHERE ROWNUM <= 25;
