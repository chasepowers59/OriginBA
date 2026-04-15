-- Intensive QA pack for CISADM.FT_RPT_CURR
-- Read-only. Use after refresh to prove source parity, lookup coverage,
-- optional-feature behavior, and end-user readiness.

-- 6a) Source vs snapshot population baseline
SELECT
    (SELECT COUNT(*) FROM cisadm.ci_ft ft WHERE ft.redundant_sw = 'N') AS source_ft_count,
    (SELECT COUNT(*) FROM cisadm.ft_rpt_curr) AS snapshot_ft_count,
    (SELECT COUNT(*) FROM cisadm.ft_rpt_curr) -
    (SELECT COUNT(*) FROM cisadm.ci_ft ft WHERE ft.redundant_sw = 'N') AS snapshot_minus_source
FROM dual;

-- 6b) Anti-join counts
SELECT COUNT(*) AS source_rows_missing_in_snapshot
FROM (
    SELECT ft.ft_id
    FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N'
    MINUS
    SELECT s.ft_id
    FROM cisadm.ft_rpt_curr s
);

SELECT COUNT(*) AS snapshot_rows_not_in_source
FROM (
    SELECT s.ft_id
    FROM cisadm.ft_rpt_curr s
    MINUS
    SELECT ft.ft_id
    FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N'
);

-- 6c) Overall amount parity
WITH src AS (
    SELECT
        COUNT(*) AS src_row_count,
        SUM(NVL(ft.cur_amt, 0)) AS src_cur_amt,
        SUM(NVL(ft.tot_amt, 0)) AS src_tot_amt
    FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N'
),
snap AS (
    SELECT
        COUNT(*) AS snap_row_count,
        SUM(NVL(s.cur_amt, 0)) AS snap_cur_amt,
        SUM(NVL(s.tot_amt, 0)) AS snap_tot_amt
    FROM cisadm.ft_rpt_curr s
)
SELECT
    src.src_row_count,
    snap.snap_row_count,
    snap.snap_row_count - src.src_row_count AS row_count_diff,
    src.src_cur_amt,
    snap.snap_cur_amt,
    snap.snap_cur_amt - src.src_cur_amt AS cur_amt_diff,
    src.src_tot_amt,
    snap.snap_tot_amt,
    snap.snap_tot_amt - src.src_tot_amt AS tot_amt_diff
FROM src
CROSS JOIN snap;

-- 6d) FT-type-level parity
WITH src AS (
    SELECT
        ft.ft_type_flg,
        COUNT(*) AS src_row_count,
        SUM(NVL(ft.cur_amt, 0)) AS src_cur_amt,
        SUM(NVL(ft.tot_amt, 0)) AS src_tot_amt
    FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N'
    GROUP BY ft.ft_type_flg
),
snap AS (
    SELECT
        s.ft_type_flg,
        s.ft_type_flg_desc,
        COUNT(*) AS snap_row_count,
        SUM(NVL(s.cur_amt, 0)) AS snap_cur_amt,
        SUM(NVL(s.tot_amt, 0)) AS snap_tot_amt
    FROM cisadm.ft_rpt_curr s
    GROUP BY s.ft_type_flg, s.ft_type_flg_desc
)
SELECT
    NVL(src.ft_type_flg, snap.ft_type_flg) AS ft_type_flg,
    snap.ft_type_flg_desc,
    NVL(src.src_row_count, 0) AS src_row_count,
    NVL(snap.snap_row_count, 0) AS snap_row_count,
    NVL(snap.snap_row_count, 0) - NVL(src.src_row_count, 0) AS row_count_diff,
    NVL(src.src_cur_amt, 0) AS src_cur_amt,
    NVL(snap.snap_cur_amt, 0) AS snap_cur_amt,
    NVL(snap.snap_cur_amt, 0) - NVL(src.src_cur_amt, 0) AS cur_amt_diff,
    NVL(src.src_tot_amt, 0) AS src_tot_amt,
    NVL(snap.snap_tot_amt, 0) AS snap_tot_amt,
    NVL(snap.snap_tot_amt, 0) - NVL(src.src_tot_amt, 0) AS tot_amt_diff
FROM src
FULL OUTER JOIN snap
    ON snap.ft_type_flg = src.ft_type_flg
ORDER BY NVL(src.ft_type_flg, snap.ft_type_flg);

-- 6e) Optional-child and context coverage parity by FT type
WITH src AS (
    SELECT
        ft.ft_type_flg,
        COUNT(*) AS src_ft_rows,
        SUM(CASE WHEN sa.sa_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_sa,
        SUM(CASE WHEN acct.acct_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_acct,
        SUM(CASE WHEN bseg.bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_bseg,
        SUM(CASE WHEN adj.adj_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_adj,
        SUM(CASE WHEN pay.pay_seg_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_pay_seg
    FROM cisadm.ci_ft ft
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = ft.sa_id
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = sa.acct_id
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = ft.sibling_id
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_adj adj
        ON adj.adj_id = ft.sibling_id
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_pay_seg pay
        ON pay.pay_seg_id = ft.sibling_id
       AND pay.pay_id = ft.parent_id
       AND ft.ft_type_flg IN ('PS', 'PX')
    WHERE ft.redundant_sw = 'N'
    GROUP BY ft.ft_type_flg
),
snap AS (
    SELECT
        s.ft_type_flg,
        COUNT(*) AS snap_ft_rows,
        SUM(CASE WHEN s.sa_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_sa,
        SUM(CASE WHEN s.acct_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_acct,
        SUM(CASE WHEN s.bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_bseg,
        SUM(CASE WHEN s.adj_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_adj,
        SUM(CASE WHEN s.pay_seg_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_pay_seg
    FROM cisadm.ft_rpt_curr s
    GROUP BY s.ft_type_flg
)
SELECT
    NVL(src.ft_type_flg, snap.ft_type_flg) AS ft_type_flg,
    NVL(src.src_ft_rows, 0) AS src_ft_rows,
    NVL(snap.snap_ft_rows, 0) AS snap_ft_rows,
    NVL(snap.snap_ft_rows, 0) - NVL(src.src_ft_rows, 0) AS ft_row_diff,
    NVL(src.src_rows_with_sa, 0) AS src_rows_with_sa,
    NVL(snap.snap_rows_with_sa, 0) AS snap_rows_with_sa,
    NVL(snap.snap_rows_with_sa, 0) - NVL(src.src_rows_with_sa, 0) AS sa_diff,
    NVL(src.src_rows_with_acct, 0) AS src_rows_with_acct,
    NVL(snap.snap_rows_with_acct, 0) AS snap_rows_with_acct,
    NVL(snap.snap_rows_with_acct, 0) - NVL(src.src_rows_with_acct, 0) AS acct_diff,
    NVL(src.src_rows_with_bseg, 0) AS src_rows_with_bseg,
    NVL(snap.snap_rows_with_bseg, 0) AS snap_rows_with_bseg,
    NVL(snap.snap_rows_with_bseg, 0) - NVL(src.src_rows_with_bseg, 0) AS bseg_diff,
    NVL(src.src_rows_with_adj, 0) AS src_rows_with_adj,
    NVL(snap.snap_rows_with_adj, 0) AS snap_rows_with_adj,
    NVL(snap.snap_rows_with_adj, 0) - NVL(src.src_rows_with_adj, 0) AS adj_diff,
    NVL(src.src_rows_with_pay_seg, 0) AS src_rows_with_pay_seg,
    NVL(snap.snap_rows_with_pay_seg, 0) AS snap_rows_with_pay_seg,
    NVL(snap.snap_rows_with_pay_seg, 0) - NVL(src.src_rows_with_pay_seg, 0) AS pay_seg_diff
FROM src
FULL OUTER JOIN snap
    ON snap.ft_type_flg = src.ft_type_flg
ORDER BY NVL(src.ft_type_flg, snap.ft_type_flg);

-- 6f) Identifier mismatch counts for key child/context fields
WITH paired AS (
    SELECT
        ft.ft_id,
        sa.acct_id AS src_acct_id,
        bseg.bseg_id AS src_bseg_id,
        adj.adj_id AS src_adj_id,
        pay.pay_seg_id AS src_pay_seg_id,
        s.acct_id AS snap_acct_id,
        s.bseg_id AS snap_bseg_id,
        s.adj_id AS snap_adj_id,
        s.pay_seg_id AS snap_pay_seg_id
    FROM cisadm.ci_ft ft
    INNER JOIN cisadm.ft_rpt_curr s
        ON s.ft_id = ft.ft_id
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = ft.sa_id
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = ft.sibling_id
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_adj adj
        ON adj.adj_id = ft.sibling_id
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_pay_seg pay
        ON pay.pay_seg_id = ft.sibling_id
       AND pay.pay_id = ft.parent_id
       AND ft.ft_type_flg IN ('PS', 'PX')
    WHERE ft.redundant_sw = 'N'
)
SELECT
    SUM(CASE WHEN NVL(src_acct_id, '#NULL#') <> NVL(snap_acct_id, '#NULL#') THEN 1 ELSE 0 END) AS acct_id_mismatch_rows,
    SUM(CASE WHEN NVL(src_bseg_id, '#NULL#') <> NVL(snap_bseg_id, '#NULL#') THEN 1 ELSE 0 END) AS bseg_id_mismatch_rows,
    SUM(CASE WHEN NVL(src_adj_id, '#NULL#') <> NVL(snap_adj_id, '#NULL#') THEN 1 ELSE 0 END) AS adj_id_mismatch_rows,
    SUM(CASE WHEN NVL(src_pay_seg_id, '#NULL#') <> NVL(snap_pay_seg_id, '#NULL#') THEN 1 ELSE 0 END) AS pay_seg_id_mismatch_rows
FROM paired;

-- 6g) Description parity and lookup-gap counts
WITH src AS (
    SELECT
        ft.ft_id,
        ft.ft_type_flg,
        ft.gl_distrib_status,
        sa.sa_status_flg,
        sa.sa_type_cd,
        acct.cust_cl_cd,
        acct.coll_cl_cd,
        acct.bill_cyc_cd,
        acct.acct_mgmt_grp_cd,
        bseg.bseg_stat_flg,
        adj.adj_status_flg,
        adj.adj_type_cd,
        CASE ft.ft_type_flg
            WHEN 'AD' THEN 'Adjustment'
            WHEN 'AX' THEN 'Adjustment Cancellation'
            WHEN 'BS' THEN 'Bill Segment'
            WHEN 'BX' THEN 'Bill Segment Cancellation'
            WHEN 'PS' THEN 'Pay Segment'
            WHEN 'PX' THEN 'Pay Segment Cancellation'
        END AS exp_ft_type_desc,
        CASE ft.gl_distrib_status
            WHEN 'D' THEN 'Distributed'
            WHEN 'G' THEN 'Generated'
            WHEN 'M' THEN 'Modified'
            WHEN 'N' THEN 'Pending'
        END AS exp_gl_status_desc,
        COALESCE(NULLIF(TRIM(u.first_name || ' ' || u.last_name), ''), u.user_id) AS exp_freeze_user_name,
        sa_stat.descr AS exp_sa_status_desc,
        sa_type.descr AS exp_sa_type_desc,
        cust_cl_l.descr AS exp_cust_cl_desc,
        coll_cl_l.descr AS exp_coll_cl_desc,
        bill_cyc_l.descr AS exp_bill_cyc_desc,
        acct_mgmt_l.descr AS exp_acct_mgmt_grp_desc,
        bseg_stat.descr AS exp_bseg_status_desc,
        adj_stat.descr AS exp_adj_status_desc,
        adj_type.descr AS exp_adj_type_desc
    FROM cisadm.ci_ft ft
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = ft.sa_id
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = sa.acct_id
    LEFT JOIN cisadm.sc_user u
        ON u.user_id = ft.freeze_user_id
       AND u.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = ft.sibling_id
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_adj adj
        ON adj.adj_id = ft.sibling_id
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_lookup_val_l sa_stat
        ON sa_stat.field_name = 'SA_STATUS_FLG'
       AND sa_stat.field_value = sa.sa_status_flg
       AND sa_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_sa_type_l sa_type
        ON sa_type.sa_type_cd = sa.sa_type_cd
       AND sa_type.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON cust_cl_l.cust_cl_cd = acct.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON coll_cl_l.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l bill_cyc_l
        ON bill_cyc_l.bill_cyc_cd = acct.bill_cyc_cd
       AND bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt_l
        ON acct_mgmt_l.acct_mgmt_grp_cd = acct.acct_mgmt_grp_cd
       AND acct_mgmt_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l bseg_stat
        ON bseg_stat.field_name = 'BSEG_STAT_FLG'
       AND bseg_stat.field_value = bseg.bseg_stat_flg
       AND bseg_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l adj_stat
        ON adj_stat.field_name = 'ADJ_STATUS_FLG'
       AND adj_stat.field_value = adj.adj_status_flg
       AND adj_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_adj_type_l adj_type
        ON adj_type.adj_type_cd = adj.adj_type_cd
       AND adj_type.language_cd = 'ENG'
    WHERE ft.redundant_sw = 'N'
)
SELECT
    COUNT(*) AS paired_rows,
    SUM(CASE WHEN NVL(src.exp_ft_type_desc, '#NULL#') <> NVL(s.ft_type_flg_desc, '#NULL#') THEN 1 ELSE 0 END) AS ft_type_desc_mismatch_rows,
    SUM(CASE WHEN src.gl_distrib_status IS NOT NULL AND src.exp_gl_status_desc IS NULL THEN 1 ELSE 0 END) AS gl_status_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_gl_status_desc, '#NULL#') <> NVL(s.gl_distrib_status_desc, '#NULL#') THEN 1 ELSE 0 END) AS gl_status_desc_mismatch_rows,
    SUM(CASE WHEN src.sa_status_flg IS NOT NULL AND src.exp_sa_status_desc IS NULL THEN 1 ELSE 0 END) AS sa_status_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_sa_status_desc, '#NULL#') <> NVL(s.sa_status_desc, '#NULL#') THEN 1 ELSE 0 END) AS sa_status_desc_mismatch_rows,
    SUM(CASE WHEN src.sa_type_cd IS NOT NULL AND src.exp_sa_type_desc IS NULL THEN 1 ELSE 0 END) AS sa_type_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_sa_type_desc, '#NULL#') <> NVL(s.sa_type_desc, '#NULL#') THEN 1 ELSE 0 END) AS sa_type_desc_mismatch_rows,
    SUM(CASE WHEN src.cust_cl_cd IS NOT NULL AND src.exp_cust_cl_desc IS NULL THEN 1 ELSE 0 END) AS cust_cl_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_cust_cl_desc, '#NULL#') <> NVL(s.cust_cl_desc, '#NULL#') THEN 1 ELSE 0 END) AS cust_cl_desc_mismatch_rows,
    SUM(CASE WHEN src.coll_cl_cd IS NOT NULL AND src.exp_coll_cl_desc IS NULL THEN 1 ELSE 0 END) AS coll_cl_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_coll_cl_desc, '#NULL#') <> NVL(s.coll_cl_desc, '#NULL#') THEN 1 ELSE 0 END) AS coll_cl_desc_mismatch_rows,
    SUM(CASE WHEN src.bill_cyc_cd IS NOT NULL AND src.exp_bill_cyc_desc IS NULL THEN 1 ELSE 0 END) AS bill_cyc_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_bill_cyc_desc, '#NULL#') <> NVL(s.bill_cyc_desc, '#NULL#') THEN 1 ELSE 0 END) AS bill_cyc_desc_mismatch_rows,
    SUM(CASE WHEN src.acct_mgmt_grp_cd IS NOT NULL AND src.exp_acct_mgmt_grp_desc IS NULL THEN 1 ELSE 0 END) AS acct_mgmt_grp_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_acct_mgmt_grp_desc, '#NULL#') <> NVL(s.acct_mgmt_grp_desc, '#NULL#') THEN 1 ELSE 0 END) AS acct_mgmt_grp_desc_mismatch_rows,
    SUM(CASE WHEN src.bseg_stat_flg IS NOT NULL AND src.exp_bseg_status_desc IS NULL THEN 1 ELSE 0 END) AS bseg_status_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_bseg_status_desc, '#NULL#') <> NVL(s.bseg_stat_desc, '#NULL#') THEN 1 ELSE 0 END) AS bseg_status_desc_mismatch_rows,
    SUM(CASE WHEN src.adj_status_flg IS NOT NULL AND src.exp_adj_status_desc IS NULL THEN 1 ELSE 0 END) AS adj_status_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_adj_status_desc, '#NULL#') <> NVL(s.adj_status_desc, '#NULL#') THEN 1 ELSE 0 END) AS adj_status_desc_mismatch_rows,
    SUM(CASE WHEN src.adj_type_cd IS NOT NULL AND src.exp_adj_type_desc IS NULL THEN 1 ELSE 0 END) AS adj_type_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_adj_type_desc, '#NULL#') <> NVL(s.adj_type_desc, '#NULL#') THEN 1 ELSE 0 END) AS adj_type_desc_mismatch_rows,
    SUM(CASE WHEN NVL(src.exp_freeze_user_name, '#NULL#') <> NVL(s.freeze_user_name, '#NULL#') THEN 1 ELSE 0 END) AS freeze_user_name_mismatch_rows
FROM src
INNER JOIN cisadm.ft_rpt_curr s
    ON s.ft_id = src.ft_id;

-- 6h) Raw-code-only business-context audit
WITH expected AS (
    SELECT 'CUST_CL_CD' AS code_column, 'CUST_CL_DESC' AS expected_desc_column, 'CI_CUST_CL_L' AS lookup_object FROM dual UNION ALL
    SELECT 'COLL_CL_CD', 'COLL_CL_DESC', 'CI_COLL_CL_L' FROM dual UNION ALL
    SELECT 'BILL_CYC_CD', 'BILL_CYC_DESC', 'CI_BILL_CYC_L' FROM dual UNION ALL
    SELECT 'ACCT_MGMT_GRP_CD', 'ACCT_MGMT_GRP_DESC', 'CI_ACCT_MGMT_GR_L' FROM dual
)
SELECT
    e.code_column,
    e.expected_desc_column,
    e.lookup_object,
    CASE
        WHEN c.column_name IS NULL THEN 'MISSING_DESC_COLUMN'
        ELSE 'DESC_COLUMN_PRESENT'
    END AS status
FROM expected e
LEFT JOIN all_tab_columns c
    ON c.owner = 'CISADM'
   AND c.table_name = 'FT_RPT_CURR'
   AND c.column_name = e.expected_desc_column
ORDER BY e.code_column;

-- 6i) Lookup availability for business-context code fields
WITH cust_cl_codes AS (
    SELECT DISTINCT s.cust_cl_cd AS code FROM cisadm.ft_rpt_curr s WHERE s.cust_cl_cd IS NOT NULL
),
coll_cl_codes AS (
    SELECT DISTINCT s.coll_cl_cd AS code FROM cisadm.ft_rpt_curr s WHERE s.coll_cl_cd IS NOT NULL
),
bill_cyc_codes AS (
    SELECT DISTINCT s.bill_cyc_cd AS code FROM cisadm.ft_rpt_curr s WHERE s.bill_cyc_cd IS NOT NULL
),
acct_mgmt_codes AS (
    SELECT DISTINCT s.acct_mgmt_grp_cd AS code FROM cisadm.ft_rpt_curr s WHERE s.acct_mgmt_grp_cd IS NOT NULL
)
SELECT
    'CUST_CL_CD' AS code_column,
    COUNT(*) AS distinct_code_count,
    SUM(CASE WHEN l.cust_cl_cd IS NULL THEN 1 ELSE 0 END) AS codes_missing_lookup
FROM cust_cl_codes c
LEFT JOIN cisadm.ci_cust_cl_l l
    ON l.cust_cl_cd = c.code
   AND l.language_cd = 'ENG'
UNION ALL
SELECT
    'COLL_CL_CD',
    COUNT(*),
    SUM(CASE WHEN l.coll_cl_cd IS NULL THEN 1 ELSE 0 END)
FROM coll_cl_codes c
LEFT JOIN cisadm.ci_coll_cl_l l
    ON l.coll_cl_cd = c.code
   AND l.language_cd = 'ENG'
UNION ALL
SELECT
    'BILL_CYC_CD',
    COUNT(*),
    SUM(CASE WHEN l.bill_cyc_cd IS NULL THEN 1 ELSE 0 END)
FROM bill_cyc_codes c
LEFT JOIN cisadm.ci_bill_cyc_l l
    ON l.bill_cyc_cd = c.code
   AND l.language_cd = 'ENG'
UNION ALL
SELECT
    'ACCT_MGMT_GRP_CD',
    COUNT(*),
    SUM(CASE WHEN l.acct_mgmt_grp_cd IS NULL THEN 1 ELSE 0 END)
FROM acct_mgmt_codes c
LEFT JOIN cisadm.ci_acct_mgmt_gr_l l
    ON l.acct_mgmt_grp_cd = c.code
   AND l.language_cd = 'ENG';

-- 6j) Sample rows showing snapshot descriptions vs. source lookup descriptions
SELECT *
FROM (
    SELECT
        s.ft_id,
        s.acct_id,
        s.sa_id,
        s.cust_cl_cd,
        s.cust_cl_desc,
        cust_cl_l.descr AS source_cust_cl_desc,
        s.coll_cl_cd,
        s.coll_cl_desc,
        coll_cl_l.descr AS source_coll_cl_desc,
        s.bill_cyc_cd,
        s.bill_cyc_desc,
        bill_cyc_l.descr AS source_bill_cyc_desc,
        s.acct_mgmt_grp_cd,
        s.acct_mgmt_grp_desc,
        acct_mgmt_l.descr AS source_acct_mgmt_desc
    FROM cisadm.ft_rpt_curr s
    LEFT JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON cust_cl_l.cust_cl_cd = s.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON coll_cl_l.coll_cl_cd = s.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l bill_cyc_l
        ON bill_cyc_l.bill_cyc_cd = s.bill_cyc_cd
       AND bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt_l
        ON acct_mgmt_l.acct_mgmt_grp_cd = s.acct_mgmt_grp_cd
       AND acct_mgmt_l.language_cd = 'ENG'
    WHERE s.cust_cl_cd IS NOT NULL
       OR s.coll_cl_cd IS NOT NULL
       OR s.bill_cyc_cd IS NOT NULL
       OR s.acct_mgmt_grp_cd IS NOT NULL
    ORDER BY s.load_dttm DESC, s.accounting_dt DESC, s.ft_id
)
WHERE ROWNUM <= 25;
