-- Intensive QA pack for CISADM.FT_GL_DISTRIBUTION_RPT_CURR
-- Read-only. Use after refresh to prove source parity, lookup coverage,
-- optional-feature behavior, and end-user readiness.

-- 5a) Source vs snapshot GL-line baseline
SELECT
    (SELECT COUNT(*)
     FROM cisadm.ci_ft_gl gl
     INNER JOIN cisadm.ci_ft ft
         ON ft.ft_id = gl.ft_id
        AND ft.redundant_sw = 'N') AS source_gl_line_count,
    (SELECT COUNT(*) FROM cisadm.ft_gl_distribution_rpt_curr) AS snapshot_gl_line_count,
    (SELECT COUNT(*) FROM cisadm.ft_gl_distribution_rpt_curr) -
    (SELECT COUNT(*)
     FROM cisadm.ci_ft_gl gl
     INNER JOIN cisadm.ci_ft ft
         ON ft.ft_id = gl.ft_id
        AND ft.redundant_sw = 'N') AS snapshot_minus_source
FROM dual;

-- 5b) Anti-join counts
SELECT COUNT(*) AS source_gl_lines_missing_in_snapshot
FROM (
    SELECT gl.ft_id, gl.gl_seq_nbr
    FROM cisadm.ci_ft_gl gl
    INNER JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
       AND ft.redundant_sw = 'N'
    MINUS
    SELECT s.ft_id, s.gl_seq_nbr
    FROM cisadm.ft_gl_distribution_rpt_curr s
);

SELECT COUNT(*) AS snapshot_gl_lines_not_in_source
FROM (
    SELECT s.ft_id, s.gl_seq_nbr
    FROM cisadm.ft_gl_distribution_rpt_curr s
    MINUS
    SELECT gl.ft_id, gl.gl_seq_nbr
    FROM cisadm.ci_ft_gl gl
    INNER JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
       AND ft.redundant_sw = 'N'
);

-- 5c) Overall line and amount parity
WITH src AS (
    SELECT
        COUNT(*) AS src_row_count,
        COUNT(DISTINCT gl.ft_id) AS src_distinct_ft_count,
        SUM(NVL(gl.amount, 0)) AS src_gl_amount,
        SUM(CASE WHEN NVL(gl.amount, 0) >= 0 THEN NVL(gl.amount, 0) ELSE 0 END) AS src_debit_amt,
        SUM(CASE WHEN NVL(gl.amount, 0) < 0 THEN ABS(gl.amount) ELSE 0 END) AS src_credit_amt,
        SUM(NVL(gl.statistic_amount, 0)) AS src_statistic_amount
    FROM cisadm.ci_ft_gl gl
    INNER JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
       AND ft.redundant_sw = 'N'
),
snap AS (
    SELECT
        COUNT(*) AS snap_row_count,
        COUNT(DISTINCT s.ft_id) AS snap_distinct_ft_count,
        SUM(NVL(s.gl_amount, 0)) AS snap_gl_amount,
        SUM(NVL(s.debit_amt, 0)) AS snap_debit_amt,
        SUM(NVL(s.credit_amt, 0)) AS snap_credit_amt,
        SUM(NVL(s.statistic_amount, 0)) AS snap_statistic_amount
    FROM cisadm.ft_gl_distribution_rpt_curr s
)
SELECT
    src.src_row_count,
    snap.snap_row_count,
    snap.snap_row_count - src.src_row_count AS row_count_diff,
    src.src_distinct_ft_count,
    snap.snap_distinct_ft_count,
    snap.snap_distinct_ft_count - src.src_distinct_ft_count AS distinct_ft_diff,
    src.src_gl_amount,
    snap.snap_gl_amount,
    snap.snap_gl_amount - src.src_gl_amount AS gl_amount_diff,
    src.src_debit_amt,
    snap.snap_debit_amt,
    snap.snap_debit_amt - src.src_debit_amt AS debit_amt_diff,
    src.src_credit_amt,
    snap.snap_credit_amt,
    snap.snap_credit_amt - src.src_credit_amt AS credit_amt_diff,
    src.src_statistic_amount,
    snap.snap_statistic_amount,
    snap.snap_statistic_amount - src.src_statistic_amount AS statistic_amount_diff
FROM src
CROSS JOIN snap;

-- 5d) FT-type-level parity
WITH src AS (
    SELECT
        ft.ft_type_flg,
        COUNT(*) AS src_row_count,
        SUM(NVL(gl.amount, 0)) AS src_gl_amount,
        SUM(NVL(gl.statistic_amount, 0)) AS src_statistic_amount
    FROM cisadm.ci_ft_gl gl
    INNER JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
       AND ft.redundant_sw = 'N'
    GROUP BY ft.ft_type_flg
),
snap AS (
    SELECT
        s.ft_type_flg,
        s.ft_type_flg_desc,
        COUNT(*) AS snap_row_count,
        SUM(NVL(s.gl_amount, 0)) AS snap_gl_amount,
        SUM(NVL(s.statistic_amount, 0)) AS snap_statistic_amount
    FROM cisadm.ft_gl_distribution_rpt_curr s
    GROUP BY s.ft_type_flg, s.ft_type_flg_desc
)
SELECT
    NVL(src.ft_type_flg, snap.ft_type_flg) AS ft_type_flg,
    snap.ft_type_flg_desc,
    NVL(src.src_row_count, 0) AS src_row_count,
    NVL(snap.snap_row_count, 0) AS snap_row_count,
    NVL(snap.snap_row_count, 0) - NVL(src.src_row_count, 0) AS row_count_diff,
    NVL(src.src_gl_amount, 0) AS src_gl_amount,
    NVL(snap.snap_gl_amount, 0) AS snap_gl_amount,
    NVL(snap.snap_gl_amount, 0) - NVL(src.src_gl_amount, 0) AS gl_amount_diff,
    NVL(src.src_statistic_amount, 0) AS src_statistic_amount,
    NVL(snap.snap_statistic_amount, 0) AS snap_statistic_amount,
    NVL(snap.snap_statistic_amount, 0) - NVL(src.src_statistic_amount, 0) AS statistic_amount_diff
FROM src
FULL OUTER JOIN snap
    ON snap.ft_type_flg = src.ft_type_flg
ORDER BY NVL(src.ft_type_flg, snap.ft_type_flg);

-- 5e) GL account / distribution-code parity
WITH src AS (
    SELECT
        gl.gl_acct,
        gl.dst_id,
        COUNT(*) AS src_row_count,
        SUM(NVL(gl.amount, 0)) AS src_gl_amount,
        SUM(NVL(gl.statistic_amount, 0)) AS src_statistic_amount
    FROM cisadm.ci_ft_gl gl
    INNER JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
       AND ft.redundant_sw = 'N'
    GROUP BY gl.gl_acct, gl.dst_id
),
snap AS (
    SELECT
        s.gl_acct,
        s.dst_id,
        COUNT(*) AS snap_row_count,
        SUM(NVL(s.gl_amount, 0)) AS snap_gl_amount,
        SUM(NVL(s.statistic_amount, 0)) AS snap_statistic_amount
    FROM cisadm.ft_gl_distribution_rpt_curr s
    GROUP BY s.gl_acct, s.dst_id
)
SELECT
    NVL(src.gl_acct, snap.gl_acct) AS gl_acct,
    NVL(src.dst_id, snap.dst_id) AS dst_id,
    NVL(src.src_row_count, 0) AS src_row_count,
    NVL(snap.snap_row_count, 0) AS snap_row_count,
    NVL(snap.snap_row_count, 0) - NVL(src.src_row_count, 0) AS row_count_diff,
    NVL(src.src_gl_amount, 0) AS src_gl_amount,
    NVL(snap.snap_gl_amount, 0) AS snap_gl_amount,
    NVL(snap.snap_gl_amount, 0) - NVL(src.src_gl_amount, 0) AS gl_amount_diff,
    NVL(src.src_statistic_amount, 0) AS src_statistic_amount,
    NVL(snap.snap_statistic_amount, 0) AS snap_statistic_amount,
    NVL(snap.snap_statistic_amount, 0) - NVL(src.src_statistic_amount, 0) AS statistic_amount_diff
FROM src
FULL OUTER JOIN snap
    ON snap.gl_acct = src.gl_acct
   AND NVL(snap.dst_id, '#NULL#') = NVL(src.dst_id, '#NULL#')
WHERE NVL(snap.snap_row_count, 0) <> NVL(src.src_row_count, 0)
   OR NVL(snap.snap_gl_amount, 0) <> NVL(src.src_gl_amount, 0)
   OR NVL(snap.snap_statistic_amount, 0) <> NVL(src.src_statistic_amount, 0)
ORDER BY NVL(src.gl_acct, snap.gl_acct), NVL(src.dst_id, snap.dst_id);

-- 5f) GL-line count parity by FT
WITH src AS (
    SELECT
        gl.ft_id,
        COUNT(*) AS src_gl_line_count,
        SUM(NVL(gl.amount, 0)) AS src_gl_amount,
        SUM(NVL(gl.statistic_amount, 0)) AS src_statistic_amount
    FROM cisadm.ci_ft_gl gl
    INNER JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
       AND ft.redundant_sw = 'N'
    GROUP BY gl.ft_id
),
snap AS (
    SELECT
        s.ft_id,
        COUNT(*) AS snap_gl_line_count,
        SUM(NVL(s.gl_amount, 0)) AS snap_gl_amount,
        SUM(NVL(s.statistic_amount, 0)) AS snap_statistic_amount
    FROM cisadm.ft_gl_distribution_rpt_curr s
    GROUP BY s.ft_id
)
SELECT
    NVL(src.ft_id, snap.ft_id) AS ft_id,
    NVL(src.src_gl_line_count, 0) AS src_gl_line_count,
    NVL(snap.snap_gl_line_count, 0) AS snap_gl_line_count,
    NVL(snap.snap_gl_line_count, 0) - NVL(src.src_gl_line_count, 0) AS gl_line_count_diff,
    NVL(src.src_gl_amount, 0) AS src_gl_amount,
    NVL(snap.snap_gl_amount, 0) AS snap_gl_amount,
    NVL(snap.snap_gl_amount, 0) - NVL(src.src_gl_amount, 0) AS gl_amount_diff,
    NVL(src.src_statistic_amount, 0) AS src_statistic_amount,
    NVL(snap.snap_statistic_amount, 0) AS snap_statistic_amount,
    NVL(snap.snap_statistic_amount, 0) - NVL(src.src_statistic_amount, 0) AS statistic_amount_diff
FROM src
FULL OUTER JOIN snap
    ON snap.ft_id = src.ft_id
WHERE NVL(snap.snap_gl_line_count, 0) <> NVL(src.src_gl_line_count, 0)
   OR NVL(snap.snap_gl_amount, 0) <> NVL(src.src_gl_amount, 0)
   OR NVL(snap.snap_statistic_amount, 0) <> NVL(src.src_statistic_amount, 0)
ORDER BY NVL(src.ft_id, snap.ft_id);

-- 5g) Child-overlay and context coverage parity by FT type
WITH src AS (
    SELECT
        ft.ft_type_flg,
        COUNT(*) AS src_rows,
        SUM(CASE WHEN sa.acct_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_acct,
        SUM(CASE WHEN cust.per_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_per,
        SUM(CASE WHEN bseg.bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_bseg,
        SUM(CASE WHEN adj.adj_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_adj,
        SUM(CASE WHEN pay_seg.pay_seg_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_pay_seg,
        SUM(CASE WHEN ft.bal_ctl_grp_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_bcg
    FROM cisadm.ci_ft_gl gl
    INNER JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
       AND ft.redundant_sw = 'N'
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = ft.sa_id
    LEFT JOIN (
        SELECT
            ap.acct_id,
            ap.per_id,
            ROW_NUMBER() OVER (
                PARTITION BY ap.acct_id
                ORDER BY
                    CASE WHEN ap.fin_resp_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN ap.main_cust_sw = 'Y' THEN 0 ELSE 1 END,
                    ap.per_id
            ) AS rn
        FROM cisadm.ci_acct_per ap
        WHERE ap.main_cust_sw = 'Y'
           OR ap.fin_resp_sw = 'Y'
    ) cust
        ON cust.acct_id = sa.acct_id
       AND cust.rn = 1
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = ft.sibling_id
       AND bseg.bill_id = ft.bill_id
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_adj adj
        ON adj.adj_id = ft.sibling_id
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_pay_seg pay_seg
        ON pay_seg.pay_seg_id = ft.sibling_id
       AND pay_seg.pay_id = ft.parent_id
       AND ft.ft_type_flg IN ('PS', 'PX')
    LEFT JOIN cisadm.ci_bal_ctl_grp bcg
        ON bcg.bal_ctl_grp_id = ft.bal_ctl_grp_id
    GROUP BY ft.ft_type_flg
),
snap AS (
    SELECT
        s.ft_type_flg,
        COUNT(*) AS snap_rows,
        SUM(CASE WHEN s.acct_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_acct,
        SUM(CASE WHEN s.per_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_per,
        SUM(CASE WHEN s.bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_bseg,
        SUM(CASE WHEN s.adj_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_adj,
        SUM(CASE WHEN s.pay_seg_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_pay_seg,
        SUM(CASE WHEN s.bal_ctl_grp_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_bcg
    FROM cisadm.ft_gl_distribution_rpt_curr s
    GROUP BY s.ft_type_flg
)
SELECT
    NVL(src.ft_type_flg, snap.ft_type_flg) AS ft_type_flg,
    NVL(src.src_rows, 0) AS src_rows,
    NVL(snap.snap_rows, 0) AS snap_rows,
    NVL(snap.snap_rows, 0) - NVL(src.src_rows, 0) AS row_diff,
    NVL(src.src_rows_with_acct, 0) AS src_rows_with_acct,
    NVL(snap.snap_rows_with_acct, 0) AS snap_rows_with_acct,
    NVL(snap.snap_rows_with_acct, 0) - NVL(src.src_rows_with_acct, 0) AS acct_diff,
    NVL(src.src_rows_with_per, 0) AS src_rows_with_per,
    NVL(snap.snap_rows_with_per, 0) AS snap_rows_with_per,
    NVL(snap.snap_rows_with_per, 0) - NVL(src.src_rows_with_per, 0) AS per_diff,
    NVL(src.src_rows_with_bseg, 0) AS src_rows_with_bseg,
    NVL(snap.snap_rows_with_bseg, 0) AS snap_rows_with_bseg,
    NVL(snap.snap_rows_with_bseg, 0) - NVL(src.src_rows_with_bseg, 0) AS bseg_diff,
    NVL(src.src_rows_with_adj, 0) AS src_rows_with_adj,
    NVL(snap.snap_rows_with_adj, 0) AS snap_rows_with_adj,
    NVL(snap.snap_rows_with_adj, 0) - NVL(src.src_rows_with_adj, 0) AS adj_diff,
    NVL(src.src_rows_with_pay_seg, 0) AS src_rows_with_pay_seg,
    NVL(snap.snap_rows_with_pay_seg, 0) AS snap_rows_with_pay_seg,
    NVL(snap.snap_rows_with_pay_seg, 0) - NVL(src.src_rows_with_pay_seg, 0) AS pay_seg_diff,
    NVL(src.src_rows_with_bcg, 0) AS src_rows_with_bcg,
    NVL(snap.snap_rows_with_bcg, 0) AS snap_rows_with_bcg,
    NVL(snap.snap_rows_with_bcg, 0) - NVL(src.src_rows_with_bcg, 0) AS bcg_diff
FROM src
FULL OUTER JOIN snap
    ON snap.ft_type_flg = src.ft_type_flg
ORDER BY NVL(src.ft_type_flg, snap.ft_type_flg);

-- 5h) Description parity and lookup-gap counts
WITH src AS (
    SELECT
        gl.ft_id,
        gl.gl_seq_nbr,
        ft.ft_type_flg,
        ft.gl_distrib_status,
        ft.gl_division,
        sa.sa_status_flg,
        sa.sa_type_cd,
        acct.bill_cyc_cd,
        acct.cust_cl_cd,
        acct.coll_cl_cd,
        acct.acct_mgmt_grp_cd,
        bcg.balancing_stat_flg,
        bseg.bseg_stat_flg,
        bseg.bill_cyc_cd AS bseg_bill_cyc_cd,
        bseg.can_rsn_cd AS bseg_can_rsn_cd,
        adj.adj_status_flg,
        adj.adj_type_cd,
        adj.can_rsn_cd AS adj_can_rsn_cd,
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
        dst_l.descr AS exp_dst_desc,
        gl_div_l.descr AS exp_gl_division_desc,
        sa_status_l.descr AS exp_sa_status_desc,
        sa_type_l.descr AS exp_sa_type_desc,
        acct_bill_cyc_l.descr AS exp_bill_cyc_desc,
        cust_cl_l.descr AS exp_cust_cl_desc,
        coll_cl_l.descr AS exp_coll_cl_desc,
        acct_mgmt_l.descr AS exp_acct_mgmt_desc,
        bcg_status_l.descr AS exp_balancing_status_desc,
        bseg_status_l.descr AS exp_bseg_status_desc,
        bseg_bill_cyc_l.descr AS exp_bseg_bill_cyc_desc,
        bseg_can_rsn_l.descr AS exp_bseg_can_rsn_desc,
        adj_status_l.descr AS exp_adj_status_desc,
        adj_type_l.descr AS exp_adj_type_desc,
        adj_can_rsn_l.descr AS exp_adj_can_rsn_desc,
        TRIM(sc_user.first_name || ' ' || sc_user.last_name) AS exp_freeze_user_name
    FROM cisadm.ci_ft_gl gl
    INNER JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
       AND ft.redundant_sw = 'N'
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = ft.sa_id
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = sa.acct_id
    LEFT JOIN cisadm.ci_bal_ctl_grp bcg
        ON bcg.bal_ctl_grp_id = ft.bal_ctl_grp_id
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = ft.sibling_id
       AND bseg.bill_id = ft.bill_id
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_adj adj
        ON adj.adj_id = ft.sibling_id
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.sc_user sc_user
        ON sc_user.user_id = ft.freeze_user_id
    LEFT JOIN cisadm.ci_dst_code_l dst_l
        ON dst_l.dst_id = gl.dst_id
       AND dst_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_gl_division_l gl_div_l
        ON gl_div_l.gl_division = ft.gl_division
       AND gl_div_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l sa_status_l
        ON sa_status_l.field_name = 'SA_STATUS_FLG'
       AND sa_status_l.field_value = sa.sa_status_flg
       AND sa_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_sa_type_l sa_type_l
        ON sa_type_l.cis_division = sa.cis_division
       AND sa_type_l.sa_type_cd = sa.sa_type_cd
       AND sa_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l acct_bill_cyc_l
        ON acct_bill_cyc_l.bill_cyc_cd = acct.bill_cyc_cd
       AND acct_bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON cust_cl_l.cust_cl_cd = acct.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON coll_cl_l.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt_l
        ON acct_mgmt_l.acct_mgmt_grp_cd = acct.acct_mgmt_grp_cd
       AND acct_mgmt_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l bcg_status_l
        ON bcg_status_l.field_name = 'BALANCING_STAT_FLG'
       AND bcg_status_l.field_value = bcg.balancing_stat_flg
       AND bcg_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l bseg_status_l
        ON bseg_status_l.field_name = 'BSEG_STAT_FLG'
       AND bseg_status_l.field_value = bseg.bseg_stat_flg
       AND bseg_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l bseg_bill_cyc_l
        ON bseg_bill_cyc_l.bill_cyc_cd = bseg.bill_cyc_cd
       AND bseg_bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_can_rsn_l bseg_can_rsn_l
        ON bseg_can_rsn_l.can_rsn_cd = bseg.can_rsn_cd
       AND bseg_can_rsn_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l adj_status_l
        ON adj_status_l.field_name = 'ADJ_STATUS_FLG'
       AND adj_status_l.field_value = adj.adj_status_flg
       AND adj_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_adj_type_l adj_type_l
        ON adj_type_l.adj_type_cd = adj.adj_type_cd
       AND adj_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_adj_can_rsn_l adj_can_rsn_l
        ON adj_can_rsn_l.can_rsn_cd = adj.can_rsn_cd
       AND adj_can_rsn_l.language_cd = 'ENG'
)
SELECT
    COUNT(*) AS paired_rows,
    SUM(CASE WHEN NVL(src.exp_ft_type_desc, '#NULL#') <> NVL(s.ft_type_flg_desc, '#NULL#') THEN 1 ELSE 0 END) AS ft_type_desc_mismatch_rows,
    SUM(CASE WHEN src.gl_distrib_status IS NOT NULL AND src.exp_gl_status_desc IS NULL THEN 1 ELSE 0 END) AS gl_status_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_gl_status_desc, '#NULL#') <> NVL(s.gl_distrib_status_desc, '#NULL#') THEN 1 ELSE 0 END) AS gl_status_desc_mismatch_rows,
    SUM(CASE WHEN s.dst_id IS NOT NULL AND src.exp_dst_desc IS NULL THEN 1 ELSE 0 END) AS dst_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_dst_desc, '#NULL#') <> NVL(s.dst_desc, '#NULL#') THEN 1 ELSE 0 END) AS dst_desc_mismatch_rows,
    SUM(CASE WHEN src.gl_division IS NOT NULL AND src.exp_gl_division_desc IS NULL THEN 1 ELSE 0 END) AS gl_div_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_gl_division_desc, '#NULL#') <> NVL(s.gl_division_desc, '#NULL#') THEN 1 ELSE 0 END) AS gl_div_desc_mismatch_rows,
    SUM(CASE WHEN src.sa_status_flg IS NOT NULL AND src.exp_sa_status_desc IS NULL THEN 1 ELSE 0 END) AS sa_status_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_sa_status_desc, '#NULL#') <> NVL(s.sa_status_desc, '#NULL#') THEN 1 ELSE 0 END) AS sa_status_desc_mismatch_rows,
    SUM(CASE WHEN src.sa_type_cd IS NOT NULL AND src.exp_sa_type_desc IS NULL THEN 1 ELSE 0 END) AS sa_type_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_sa_type_desc, '#NULL#') <> NVL(s.sa_type_desc, '#NULL#') THEN 1 ELSE 0 END) AS sa_type_desc_mismatch_rows,
    SUM(CASE WHEN src.bill_cyc_cd IS NOT NULL AND src.exp_bill_cyc_desc IS NULL THEN 1 ELSE 0 END) AS bill_cyc_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_bill_cyc_desc, '#NULL#') <> NVL(s.bill_cyc_desc, '#NULL#') THEN 1 ELSE 0 END) AS bill_cyc_desc_mismatch_rows,
    SUM(CASE WHEN src.cust_cl_cd IS NOT NULL AND src.exp_cust_cl_desc IS NULL THEN 1 ELSE 0 END) AS cust_cl_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_cust_cl_desc, '#NULL#') <> NVL(s.cust_cl_desc, '#NULL#') THEN 1 ELSE 0 END) AS cust_cl_desc_mismatch_rows,
    SUM(CASE WHEN src.coll_cl_cd IS NOT NULL AND src.exp_coll_cl_desc IS NULL THEN 1 ELSE 0 END) AS coll_cl_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_coll_cl_desc, '#NULL#') <> NVL(s.coll_cl_desc, '#NULL#') THEN 1 ELSE 0 END) AS coll_cl_desc_mismatch_rows,
    SUM(CASE WHEN src.acct_mgmt_grp_cd IS NOT NULL AND src.exp_acct_mgmt_desc IS NULL THEN 1 ELSE 0 END) AS acct_mgmt_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_acct_mgmt_desc, '#NULL#') <> NVL(s.acct_mgmt_grp_desc, '#NULL#') THEN 1 ELSE 0 END) AS acct_mgmt_desc_mismatch_rows,
    SUM(CASE WHEN src.balancing_stat_flg IS NOT NULL AND src.exp_balancing_status_desc IS NULL THEN 1 ELSE 0 END) AS balancing_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_balancing_status_desc, '#NULL#') <> NVL(s.balancing_stat_desc, '#NULL#') THEN 1 ELSE 0 END) AS balancing_desc_mismatch_rows,
    SUM(CASE WHEN src.bseg_stat_flg IS NOT NULL AND src.exp_bseg_status_desc IS NULL THEN 1 ELSE 0 END) AS bseg_status_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_bseg_status_desc, '#NULL#') <> NVL(s.bseg_stat_desc, '#NULL#') THEN 1 ELSE 0 END) AS bseg_status_desc_mismatch_rows,
    SUM(CASE WHEN src.bseg_bill_cyc_cd IS NOT NULL AND src.exp_bseg_bill_cyc_desc IS NULL THEN 1 ELSE 0 END) AS bseg_bill_cyc_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_bseg_bill_cyc_desc, '#NULL#') <> NVL(s.bseg_bill_cyc_desc, '#NULL#') THEN 1 ELSE 0 END) AS bseg_bill_cyc_desc_mismatch_rows,
    SUM(CASE WHEN src.bseg_can_rsn_cd IS NOT NULL AND src.exp_bseg_can_rsn_desc IS NULL THEN 1 ELSE 0 END) AS bseg_can_rsn_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_bseg_can_rsn_desc, '#NULL#') <> NVL(s.bseg_can_rsn_desc, '#NULL#') THEN 1 ELSE 0 END) AS bseg_can_rsn_desc_mismatch_rows,
    SUM(CASE WHEN src.adj_status_flg IS NOT NULL AND src.exp_adj_status_desc IS NULL THEN 1 ELSE 0 END) AS adj_status_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_adj_status_desc, '#NULL#') <> NVL(s.adj_status_desc, '#NULL#') THEN 1 ELSE 0 END) AS adj_status_desc_mismatch_rows,
    SUM(CASE WHEN src.adj_type_cd IS NOT NULL AND src.exp_adj_type_desc IS NULL THEN 1 ELSE 0 END) AS adj_type_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_adj_type_desc, '#NULL#') <> NVL(s.adj_type_desc, '#NULL#') THEN 1 ELSE 0 END) AS adj_type_desc_mismatch_rows,
    SUM(CASE WHEN src.adj_can_rsn_cd IS NOT NULL AND src.exp_adj_can_rsn_desc IS NULL THEN 1 ELSE 0 END) AS adj_can_rsn_lookup_gap_rows,
    SUM(CASE WHEN NVL(src.exp_adj_can_rsn_desc, '#NULL#') <> NVL(s.adj_can_rsn_desc, '#NULL#') THEN 1 ELSE 0 END) AS adj_can_rsn_desc_mismatch_rows,
    SUM(CASE WHEN NVL(src.exp_freeze_user_name, '#NULL#') <> NVL(s.freeze_user_name, '#NULL#') THEN 1 ELSE 0 END) AS freeze_user_name_mismatch_rows
FROM src
INNER JOIN cisadm.ft_gl_distribution_rpt_curr s
    ON s.ft_id = src.ft_id
   AND s.gl_seq_nbr = src.gl_seq_nbr;

-- 5i) Raw-code-only audit for Domain-exposed fields that need business-friendly translations
WITH expected AS (
    SELECT 'CURRENCY_CD' AS code_column, 'CURRENCY_DESC' AS expected_desc_column, 'business translation required' AS note FROM dual UNION ALL
    SELECT 'CIS_DIVISION', 'CIS_DIVISION_DESC', 'business translation required' FROM dual UNION ALL
    SELECT 'CHAR_TYPE_CD', 'CHAR_TYPE_DESC', 'business translation required' FROM dual UNION ALL
    SELECT 'TOT_AMT_SW', 'TOT_AMT_SW_DESC', 'switch translation required' FROM dual UNION ALL
    SELECT 'FREEZE_SW', 'FREEZE_SW_DESC', 'switch translation required' FROM dual UNION ALL
    SELECT 'XFERRED_OUT_SW', 'XFERRED_OUT_SW_DESC', 'switch translation required' FROM dual UNION ALL
    SELECT 'CORRECTION_SW', 'CORRECTION_SW_DESC', 'switch translation required' FROM dual UNION ALL
    SELECT 'NEW_DEBIT_SW', 'NEW_DEBIT_SW_DESC', 'switch translation required' FROM dual UNION ALL
    SELECT 'SHOW_ON_BILL_SW', 'SHOW_ON_BILL_SW_DESC', 'switch translation required' FROM dual UNION ALL
    SELECT 'NOT_IN_ARS_SW', 'NOT_IN_ARS_SW_DESC', 'switch translation required' FROM dual
)
SELECT
    e.code_column,
    e.expected_desc_column,
    e.note,
    CASE
        WHEN c.column_name IS NULL THEN 'MISSING_DESC_COLUMN'
        ELSE 'DESC_COLUMN_PRESENT'
    END AS status
FROM expected e
LEFT JOIN all_tab_columns c
    ON c.owner = 'CISADM'
   AND c.table_name = 'FT_GL_DISTRIBUTION_RPT_CURR'
   AND c.column_name = e.expected_desc_column
ORDER BY e.code_column;

-- 5j) Sample rows for raw-code-only end-user fields
SELECT *
FROM (
    SELECT
        s.ft_id,
        s.gl_seq_nbr,
        s.gl_acct,
        s.dst_id,
        s.dst_desc,
        s.currency_cd,
        s.cis_division,
        s.char_type_cd,
        s.tot_amt_sw,
        s.freeze_sw,
        s.xferred_out_sw,
        s.correction_sw,
        s.new_debit_sw,
        s.show_on_bill_sw,
        s.not_in_ars_sw
    FROM cisadm.ft_gl_distribution_rpt_curr s
    WHERE s.currency_cd IS NOT NULL
       OR s.cis_division IS NOT NULL
       OR s.char_type_cd IS NOT NULL
       OR s.tot_amt_sw IS NOT NULL
       OR s.freeze_sw IS NOT NULL
       OR s.xferred_out_sw IS NOT NULL
       OR s.correction_sw IS NOT NULL
       OR s.new_debit_sw IS NOT NULL
       OR s.show_on_bill_sw IS NOT NULL
       OR s.not_in_ars_sw IS NOT NULL
    ORDER BY s.load_dttm DESC, s.accounting_dt DESC, s.ft_id, s.gl_seq_nbr
)
WHERE ROWNUM <= 25;

-- 5k) Batch provenance parity against latest CI_FT_PROC row per FT
WITH src AS (
    SELECT
        p.ft_id,
        p.batch_cd,
        p.batch_nbr,
        ROW_NUMBER() OVER (
            PARTITION BY p.ft_id
            ORDER BY
                p.seq_num DESC,
                p.batch_nbr DESC NULLS LAST,
                p.batch_cd DESC NULLS LAST
        ) AS rn
    FROM cisadm.ci_ft_proc p
),
src_latest AS (
    SELECT
        ft_id,
        batch_cd,
        batch_nbr
    FROM src
    WHERE rn = 1
),
latest_batch AS (
    SELECT MAX(batch_nbr) AS latest_batch_nbr
    FROM src_latest
)
SELECT
    COUNT(*) AS paired_rows,
    SUM(CASE WHEN NVL(src_latest.batch_cd, '#NULL#') <> NVL(s.batch_cd, '#NULL#') THEN 1 ELSE 0 END) AS batch_cd_mismatch_rows,
    SUM(CASE WHEN NVL(src_latest.batch_nbr, -1) <> NVL(s.batch_nbr, -1) THEN 1 ELSE 0 END) AS batch_nbr_mismatch_rows,
    SUM(
        CASE
            WHEN NVL(s.is_latest_batch_nbr, 'N') <>
                 CASE
                     WHEN src_latest.batch_nbr IS NOT NULL
                      AND src_latest.batch_nbr = latest_batch.latest_batch_nbr
                     THEN 'Y'
                     ELSE 'N'
                 END
            THEN 1
            ELSE 0
        END
    ) AS latest_batch_flag_mismatch_rows
FROM cisadm.ft_gl_distribution_rpt_curr s
LEFT JOIN src_latest
    ON src_latest.ft_id = s.ft_id
CROSS JOIN latest_batch;

-- 5l) Debit / credit derivation row-rule audit
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN NVL(debit_amt, 0) > 0 AND NVL(credit_amt, 0) > 0 THEN 1 ELSE 0 END) AS rows_with_both_debit_and_credit,
    SUM(CASE WHEN NVL(gl_amount, 0) >= 0 AND NVL(debit_amt, 0) <> NVL(gl_amount, 0) THEN 1 ELSE 0 END) AS nonnegative_gl_rows_with_bad_debit_amt,
    SUM(CASE WHEN NVL(gl_amount, 0) >= 0 AND NVL(credit_amt, 0) <> 0 THEN 1 ELSE 0 END) AS nonnegative_gl_rows_with_bad_credit_amt,
    SUM(CASE WHEN NVL(gl_amount, 0) < 0 AND NVL(credit_amt, 0) <> ABS(gl_amount) THEN 1 ELSE 0 END) AS negative_gl_rows_with_bad_credit_amt,
    SUM(CASE WHEN NVL(gl_amount, 0) < 0 AND NVL(debit_amt, 0) <> 0 THEN 1 ELSE 0 END) AS negative_gl_rows_with_bad_debit_amt
FROM cisadm.ft_gl_distribution_rpt_curr;
