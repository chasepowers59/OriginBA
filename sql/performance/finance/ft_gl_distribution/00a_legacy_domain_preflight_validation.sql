-- Purpose:
--   Read-only preflight checks for the legacy FT / GL distribution domain.
--
-- Goal:
--   Prove whether the legacy domain preserves FT grain, where it duplicates
--   rows, and whether the business subject should be standardized at
--   FT-header grain or FT-GL-line grain.

-- 1) Source baseline: FT grain
SELECT COUNT(*) AS source_ft_rows
FROM cisadm.ci_ft
WHERE redundant_sw = 'N';

SELECT
    ft_id,
    COUNT(*) AS source_ft_key_count
FROM cisadm.ci_ft
WHERE redundant_sw = 'N'
GROUP BY
    ft_id
HAVING COUNT(*) > 1;

-- 2) Source baseline: FT GL grain
SELECT COUNT(*) AS source_ft_gl_rows
FROM cisadm.ci_ft_gl;

SELECT
    ft_id,
    gl_seq_nbr,
    COUNT(*) AS source_ft_gl_key_count
FROM cisadm.ci_ft_gl
GROUP BY
    ft_id,
    gl_seq_nbr
HAVING COUNT(*) > 1;

SELECT
    COUNT(DISTINCT ft_id) AS ft_ids_present_in_ft_gl
FROM cisadm.ci_ft_gl;

-- 3) Fan-out from FT to FT GL
SELECT
    COUNT(*) AS ft_with_gl_count,
    SUM(gl_line_count) AS total_gl_lines,
    AVG(gl_line_count) AS avg_gl_lines_per_ft,
    MAX(gl_line_count) AS max_gl_lines_per_ft
FROM (
    SELECT
        ft_id,
        COUNT(*) AS gl_line_count
    FROM cisadm.ci_ft_gl
    GROUP BY
        ft_id
);

SELECT *
FROM (
    SELECT
        ft_id,
        COUNT(*) AS gl_line_count
    FROM cisadm.ci_ft_gl
    GROUP BY
        ft_id
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC, ft_id
)
WHERE ROWNUM <= 50;

-- 4) Legacy-domain row count at the XML join shape
SELECT COUNT(*) AS legacy_domain_rows
FROM cisadm.ci_ft ft
LEFT JOIN cisadm.ci_bseg bseg
    ON ft.sibling_id = bseg.bseg_id
   AND ft.bill_id = bseg.bill_id
LEFT JOIN cisadm.ci_pay_seg pay_seg
    ON ft.sibling_id = pay_seg.pay_seg_id
   AND ft.parent_id = pay_seg.pay_id
LEFT JOIN cisadm.ci_adj adj
    ON ft.sibling_id = adj.adj_id
   AND ft.parent_id = adj.adj_type_cd
INNER JOIN cisadm.ci_sa sa
    ON ft.sa_id = sa.sa_id
INNER JOIN cisadm.ci_acct acct
    ON sa.acct_id = acct.acct_id
LEFT JOIN cisadm.ci_acct_per acct_per
    ON acct.acct_id = acct_per.acct_id
   AND acct_per.main_cust_sw = 'Y'
LEFT JOIN cisadm.ci_per_name per_name
    ON acct_per.per_id = per_name.per_id
   AND per_name.name_type_flg = 'PRIM'
INNER JOIN cisadm.ci_sa_type_l sa_type_l
    ON sa.cis_division = sa_type_l.cis_division
   AND sa.sa_type_cd = sa_type_l.sa_type_cd
   AND sa_type_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_prem prem
    ON sa.char_prem_id = prem.prem_id
INNER JOIN cisadm.ci_gl_division_l gl_div_l
    ON ft.gl_division = gl_div_l.gl_division
   AND gl_div_l.language_cd = 'ENG'
LEFT JOIN cisadm.sc_user freeze_user
    ON ft.freeze_user_id = freeze_user.user_id
INNER JOIN cisadm.ci_lookup_val_l sa_status_l
    ON sa_status_l.field_name = 'SA_STATUS_FLG'
   AND sa_status_l.field_value = sa.sa_status_flg
   AND sa_status_l.language_cd = 'ENG'
INNER JOIN cisadm.ci_prem_type_l prem_type_l
    ON prem.prem_type_cd = prem_type_l.prem_type_cd
   AND prem_type_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_mr_instr_l mr_instr_l
    ON prem.mr_instr_cd = mr_instr_l.mr_instr_cd
   AND mr_instr_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_mr_warn_l mr_warn_l
    ON prem.mr_warn_cd = mr_warn_l.mr_warn_cd
   AND mr_warn_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_trend_area_l trend_area_l
    ON prem.trend_area_cd = trend_area_l.descr
   AND trend_area_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_state_l state_l
    ON prem.country = state_l.country
   AND prem.state = state_l.state
   AND state_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_time_zone_l prem_tz_l
    ON prem.time_zone_cd = prem_tz_l.time_zone_cd
   AND prem_tz_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt_l
    ON acct.acct_mgmt_grp_cd = acct_mgmt_l.acct_mgmt_grp_cd
   AND acct_mgmt_l.language_cd = 'ENG'
INNER JOIN cisadm.ci_coll_cl_l coll_cl_l
    ON acct.coll_cl_cd = coll_cl_l.coll_cl_cd
   AND coll_cl_l.language_cd = 'ENG'
INNER JOIN cisadm.ci_cust_cl_l cust_cl_l
    ON acct.cust_cl_cd = cust_cl_l.cust_cl_cd
   AND cust_cl_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_bud_plan_l bud_plan_l
    ON acct.bud_plan_cd = bud_plan_l.bud_plan_cd
   AND bud_plan_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_bill_cyc_l acct_bill_cyc_l
    ON acct.bill_cyc_cd = acct_bill_cyc_l.bill_cyc_cd
   AND acct_bill_cyc_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_bill_cyc_l bseg_bill_cyc_l
    ON bseg.bill_cyc_cd = bseg_bill_cyc_l.bill_cyc_cd
   AND bseg_bill_cyc_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_bill_can_rsn_l bseg_can_rsn_l
    ON bseg.can_rsn_cd = bseg_can_rsn_l.can_rsn_cd
   AND bseg_can_rsn_l.language_cd = 'ENG'
INNER JOIN cisadm.ci_lookup_val_l bseg_status_l
    ON bseg_status_l.field_name = 'BSEG_STAT_FLG'
   AND bseg_status_l.field_value = bseg.bseg_stat_flg
   AND bseg_status_l.language_cd = 'ENG'
INNER JOIN cisadm.ci_adj_type_l adj_type_l
    ON adj.adj_type_cd = adj_type_l.adj_type_cd
   AND adj_type_l.language_cd = 'ENG'
INNER JOIN cisadm.ci_lookup_val_l adj_status_l
    ON adj_status_l.field_name = 'ADJ_STATUS_FLG'
   AND adj_status_l.field_value = adj.adj_status_flg
   AND adj_status_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_adj_can_rsn_l adj_can_rsn_l
    ON adj.can_rsn_cd = adj_can_rsn_l.can_rsn_cd
   AND adj_can_rsn_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_bal_ctl_grp bcg
    ON ft.bal_ctl_grp_id = bcg.bal_ctl_grp_id
LEFT JOIN cisadm.ci_lookup_val_l bcg_status_l
    ON bcg_status_l.field_name = 'BALANCING_STAT_FLG'
   AND bcg_status_l.field_value = bcg.balancing_stat_flg
   AND bcg_status_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_ft_gl ft_gl
    ON ft.ft_id = ft_gl.ft_id
LEFT JOIN cisadm.ci_dst_code_l dst_l
    ON ft_gl.dst_id = dst_l.dst_id
   AND dst_l.language_cd = 'ENG'
WHERE ft.redundant_sw = 'N';

-- 5) Legacy-domain FT distinctness check
SELECT COUNT(*) AS legacy_distinct_ft_count
FROM (
    SELECT
        ft.ft_id
    FROM cisadm.ci_ft ft
    LEFT JOIN cisadm.ci_bseg bseg
        ON ft.sibling_id = bseg.bseg_id
       AND ft.bill_id = bseg.bill_id
    LEFT JOIN cisadm.ci_pay_seg pay_seg
        ON ft.sibling_id = pay_seg.pay_seg_id
       AND ft.parent_id = pay_seg.pay_id
    LEFT JOIN cisadm.ci_adj adj
        ON ft.sibling_id = adj.adj_id
       AND ft.parent_id = adj.adj_type_cd
    INNER JOIN cisadm.ci_sa sa
        ON ft.sa_id = sa.sa_id
    INNER JOIN cisadm.ci_acct acct
        ON sa.acct_id = acct.acct_id
    INNER JOIN cisadm.ci_sa_type_l sa_type_l
        ON sa.cis_division = sa_type_l.cis_division
       AND sa.sa_type_cd = sa_type_l.sa_type_cd
       AND sa_type_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_gl_division_l gl_div_l
        ON ft.gl_division = gl_div_l.gl_division
       AND gl_div_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_lookup_val_l sa_status_l
        ON sa_status_l.field_name = 'SA_STATUS_FLG'
       AND sa_status_l.field_value = sa.sa_status_flg
       AND sa_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_prem prem
        ON sa.char_prem_id = prem.prem_id
    INNER JOIN cisadm.ci_prem_type_l prem_type_l
        ON prem.prem_type_cd = prem_type_l.prem_type_cd
       AND prem_type_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON acct.coll_cl_cd = coll_cl_l.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON acct.cust_cl_cd = cust_cl_l.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_lookup_val_l bseg_status_l
        ON bseg_status_l.field_name = 'BSEG_STAT_FLG'
       AND bseg_status_l.field_value = bseg.bseg_stat_flg
       AND bseg_status_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_adj_type_l adj_type_l
        ON adj.adj_type_cd = adj_type_l.adj_type_cd
       AND adj_type_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_lookup_val_l adj_status_l
        ON adj_status_l.field_name = 'ADJ_STATUS_FLG'
       AND adj_status_l.field_value = adj.adj_status_flg
       AND adj_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_ft_gl ft_gl
        ON ft.ft_id = ft_gl.ft_id
    LEFT JOIN cisadm.ci_dst_code_l dst_l
        ON ft_gl.dst_id = dst_l.dst_id
       AND dst_l.language_cd = 'ENG'
    WHERE ft.redundant_sw = 'N'
    GROUP BY
        ft.ft_id
);

-- 6) FTs dropped by the legacy XML join shape
SELECT COUNT(*) AS source_fts_missing_from_legacy_domain
FROM cisadm.ci_ft src
LEFT JOIN (
    SELECT
        ft.ft_id
    FROM cisadm.ci_ft ft
    LEFT JOIN cisadm.ci_bseg bseg
        ON ft.sibling_id = bseg.bseg_id
       AND ft.bill_id = bseg.bill_id
    LEFT JOIN cisadm.ci_pay_seg pay_seg
        ON ft.sibling_id = pay_seg.pay_seg_id
       AND ft.parent_id = pay_seg.pay_id
    LEFT JOIN cisadm.ci_adj adj
        ON ft.sibling_id = adj.adj_id
       AND ft.parent_id = adj.adj_type_cd
    INNER JOIN cisadm.ci_sa sa
        ON ft.sa_id = sa.sa_id
    INNER JOIN cisadm.ci_acct acct
        ON sa.acct_id = acct.acct_id
    INNER JOIN cisadm.ci_sa_type_l sa_type_l
        ON sa.cis_division = sa_type_l.cis_division
       AND sa.sa_type_cd = sa_type_l.sa_type_cd
       AND sa_type_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_gl_division_l gl_div_l
        ON ft.gl_division = gl_div_l.gl_division
       AND gl_div_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_lookup_val_l sa_status_l
        ON sa_status_l.field_name = 'SA_STATUS_FLG'
       AND sa_status_l.field_value = sa.sa_status_flg
       AND sa_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_prem prem
        ON sa.char_prem_id = prem.prem_id
    INNER JOIN cisadm.ci_prem_type_l prem_type_l
        ON prem.prem_type_cd = prem_type_l.prem_type_cd
       AND prem_type_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON acct.coll_cl_cd = coll_cl_l.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON acct.cust_cl_cd = cust_cl_l.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_lookup_val_l bseg_status_l
        ON bseg_status_l.field_name = 'BSEG_STAT_FLG'
       AND bseg_status_l.field_value = bseg.bseg_stat_flg
       AND bseg_status_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_adj_type_l adj_type_l
        ON adj.adj_type_cd = adj_type_l.adj_type_cd
       AND adj_type_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_lookup_val_l adj_status_l
        ON adj_status_l.field_name = 'ADJ_STATUS_FLG'
       AND adj_status_l.field_value = adj.adj_status_flg
       AND adj_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_ft_gl ft_gl
        ON ft.ft_id = ft_gl.ft_id
    LEFT JOIN cisadm.ci_dst_code_l dst_l
        ON ft_gl.dst_id = dst_l.dst_id
       AND dst_l.language_cd = 'ENG'
    WHERE ft.redundant_sw = 'N'
    GROUP BY
        ft.ft_id
) legacy
    ON legacy.ft_id = src.ft_id
WHERE src.redundant_sw = 'N'
  AND legacy.ft_id IS NULL;

-- 7) Duplicate inflation at FT grain from the legacy XML join shape
SELECT NVL(SUM(dup.row_count - 1), 0) AS legacy_duplicate_excess_rows
FROM (
    SELECT
        ft.ft_id,
        COUNT(*) AS row_count
    FROM cisadm.ci_ft ft
    LEFT JOIN cisadm.ci_bseg bseg
        ON ft.sibling_id = bseg.bseg_id
       AND ft.bill_id = bseg.bill_id
    LEFT JOIN cisadm.ci_pay_seg pay_seg
        ON ft.sibling_id = pay_seg.pay_seg_id
       AND ft.parent_id = pay_seg.pay_id
    LEFT JOIN cisadm.ci_adj adj
        ON ft.sibling_id = adj.adj_id
       AND ft.parent_id = adj.adj_type_cd
    INNER JOIN cisadm.ci_sa sa
        ON ft.sa_id = sa.sa_id
    INNER JOIN cisadm.ci_acct acct
        ON sa.acct_id = acct.acct_id
    INNER JOIN cisadm.ci_sa_type_l sa_type_l
        ON sa.cis_division = sa_type_l.cis_division
       AND sa.sa_type_cd = sa_type_l.sa_type_cd
       AND sa_type_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_gl_division_l gl_div_l
        ON ft.gl_division = gl_div_l.gl_division
       AND gl_div_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_lookup_val_l sa_status_l
        ON sa_status_l.field_name = 'SA_STATUS_FLG'
       AND sa_status_l.field_value = sa.sa_status_flg
       AND sa_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_prem prem
        ON sa.char_prem_id = prem.prem_id
    INNER JOIN cisadm.ci_prem_type_l prem_type_l
        ON prem.prem_type_cd = prem_type_l.prem_type_cd
       AND prem_type_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON acct.coll_cl_cd = coll_cl_l.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON acct.cust_cl_cd = cust_cl_l.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_lookup_val_l bseg_status_l
        ON bseg_status_l.field_name = 'BSEG_STAT_FLG'
       AND bseg_status_l.field_value = bseg.bseg_stat_flg
       AND bseg_status_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_adj_type_l adj_type_l
        ON adj.adj_type_cd = adj_type_l.adj_type_cd
       AND adj_type_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_lookup_val_l adj_status_l
        ON adj_status_l.field_name = 'ADJ_STATUS_FLG'
       AND adj_status_l.field_value = adj.adj_status_flg
       AND adj_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_ft_gl ft_gl
        ON ft.ft_id = ft_gl.ft_id
    LEFT JOIN cisadm.ci_dst_code_l dst_l
        ON ft_gl.dst_id = dst_l.dst_id
       AND dst_l.language_cd = 'ENG'
    WHERE ft.redundant_sw = 'N'
    GROUP BY
        ft.ft_id
    HAVING COUNT(*) > 1
) dup;

-- 8) Sample duplicated FTs from the legacy domain
SELECT *
FROM (
    SELECT
        ft.ft_id,
        COUNT(*) AS row_count
    FROM cisadm.ci_ft ft
    LEFT JOIN cisadm.ci_bseg bseg
        ON ft.sibling_id = bseg.bseg_id
       AND ft.bill_id = bseg.bill_id
    LEFT JOIN cisadm.ci_pay_seg pay_seg
        ON ft.sibling_id = pay_seg.pay_seg_id
       AND ft.parent_id = pay_seg.pay_id
    LEFT JOIN cisadm.ci_adj adj
        ON ft.sibling_id = adj.adj_id
       AND ft.parent_id = adj.adj_type_cd
    INNER JOIN cisadm.ci_sa sa
        ON ft.sa_id = sa.sa_id
    INNER JOIN cisadm.ci_acct acct
        ON sa.acct_id = acct.acct_id
    INNER JOIN cisadm.ci_sa_type_l sa_type_l
        ON sa.cis_division = sa_type_l.cis_division
       AND sa.sa_type_cd = sa_type_l.sa_type_cd
       AND sa_type_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_gl_division_l gl_div_l
        ON ft.gl_division = gl_div_l.gl_division
       AND gl_div_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_lookup_val_l sa_status_l
        ON sa_status_l.field_name = 'SA_STATUS_FLG'
       AND sa_status_l.field_value = sa.sa_status_flg
       AND sa_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_prem prem
        ON sa.char_prem_id = prem.prem_id
    INNER JOIN cisadm.ci_prem_type_l prem_type_l
        ON prem.prem_type_cd = prem_type_l.prem_type_cd
       AND prem_type_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON acct.coll_cl_cd = coll_cl_l.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON acct.cust_cl_cd = cust_cl_l.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_lookup_val_l bseg_status_l
        ON bseg_status_l.field_name = 'BSEG_STAT_FLG'
       AND bseg_status_l.field_value = bseg.bseg_stat_flg
       AND bseg_status_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_adj_type_l adj_type_l
        ON adj.adj_type_cd = adj_type_l.adj_type_cd
       AND adj_type_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_lookup_val_l adj_status_l
        ON adj_status_l.field_name = 'ADJ_STATUS_FLG'
       AND adj_status_l.field_value = adj.adj_status_flg
       AND adj_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_ft_gl ft_gl
        ON ft.ft_id = ft_gl.ft_id
    LEFT JOIN cisadm.ci_dst_code_l dst_l
        ON ft_gl.dst_id = dst_l.dst_id
       AND dst_l.language_cd = 'ENG'
    WHERE ft.redundant_sw = 'N'
    GROUP BY
        ft.ft_id
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC, ft.ft_id
)
WHERE ROWNUM <= 50;

-- 9) FT-type child coverage using corrected type-conditional join logic
SELECT
    ft.ft_type_flg,
    COUNT(*) AS ft_rows,
    SUM(CASE WHEN ft.ft_type_flg IN ('BS', 'BX') AND bseg.bseg_id IS NULL THEN 1 ELSE 0 END) AS missing_bseg,
    SUM(CASE WHEN ft.ft_type_flg IN ('AD', 'AX') AND adj.adj_id IS NULL THEN 1 ELSE 0 END) AS missing_adj,
    SUM(CASE WHEN ft.ft_type_flg IN ('PS', 'PX') AND pay_seg.pay_seg_id IS NULL THEN 1 ELSE 0 END) AS missing_pay_seg
FROM cisadm.ci_ft ft
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
WHERE ft.redundant_sw = 'N'
GROUP BY
    ft.ft_type_flg
ORDER BY
    ft.ft_type_flg;

-- 10) Compare legacy adjustment join to corrected adjustment join
SELECT
    SUM(CASE WHEN legacy_adj.adj_id IS NOT NULL THEN 1 ELSE 0 END) AS legacy_adj_join_hits,
    SUM(CASE WHEN corrected_adj.adj_id IS NOT NULL THEN 1 ELSE 0 END) AS corrected_adj_join_hits
FROM cisadm.ci_ft ft
LEFT JOIN cisadm.ci_adj legacy_adj
    ON legacy_adj.adj_id = ft.sibling_id
   AND legacy_adj.adj_type_cd = ft.parent_id
LEFT JOIN cisadm.ci_adj corrected_adj
    ON corrected_adj.adj_id = ft.sibling_id
WHERE ft.redundant_sw = 'N'
  AND ft.ft_type_flg IN ('AD', 'AX');

-- 11) Trend-area join anomaly check
SELECT
    COUNT(*) AS premise_rows_with_trend_area_cd,
    SUM(CASE WHEN trend_by_code.trend_area_cd IS NOT NULL THEN 1 ELSE 0 END) AS matches_on_code,
    SUM(CASE WHEN trend_by_descr.trend_area_cd IS NOT NULL THEN 1 ELSE 0 END) AS matches_on_legacy_descr_join
FROM cisadm.ci_prem prem
LEFT JOIN cisadm.ci_trend_area_l trend_by_code
    ON trend_by_code.trend_area_cd = prem.trend_area_cd
   AND trend_by_code.language_cd = 'ENG'
LEFT JOIN cisadm.ci_trend_area_l trend_by_descr
    ON trend_by_descr.descr = prem.trend_area_cd
   AND trend_by_descr.language_cd = 'ENG'
WHERE prem.trend_area_cd IS NOT NULL;

-- 12) Proposed FT-GL-line grain baseline
SELECT
    COUNT(*) AS proposed_ft_gl_snapshot_rows,
    COUNT(DISTINCT ft.ft_id) AS ft_count_in_snapshot,
    COUNT(DISTINCT ft_gl.ft_id || ':' || TO_CHAR(ft_gl.gl_seq_nbr)) AS distinct_ft_gl_keys
FROM cisadm.ci_ft ft
INNER JOIN cisadm.ci_ft_gl ft_gl
    ON ft_gl.ft_id = ft.ft_id
WHERE ft.redundant_sw = 'N';
