-- Active 8 snapshot integrity audit (read-only).
-- Reference environment: Ellensburg.
-- Schema rule: validate only CISADM source and snapshot objects.
--
-- Purpose:
-- 1) confirm each snapshot preserves its intended grain;
-- 2) identify snapshot nulls where the CISADM source/fallback has a value;
-- 3) compare high-value counts and totals back to source rows at snapshot grain.
--
-- Keep this audit investigative. If it flags a mismatch, review the procedure
-- source and C2M grain before changing any table, procedure, or schedule.

PROMPT === Active 8 grain duplicate check ===

SELECT snapshot_name,
       grain_key,
       duplicate_key_count
FROM (
    SELECT 'FT_RPT_CURR' AS snapshot_name,
           'FT_ID' AS grain_key,
           COUNT(*) AS duplicate_key_count
    FROM (
        SELECT ft_id
        FROM cisadm.ft_rpt_curr
        GROUP BY ft_id
        HAVING COUNT(*) > 1
    )
    UNION ALL
    SELECT 'FT_GL_DISTRIBUTION_RPT_CURR',
           'FT_ID + GL_SEQ_NBR',
           COUNT(*)
    FROM (
        SELECT ft_id, gl_seq_nbr
        FROM cisadm.ft_gl_distribution_rpt_curr
        GROUP BY ft_id, gl_seq_nbr
        HAVING COUNT(*) > 1
    )
    UNION ALL
    SELECT 'BSEG_BILLED_USAGE_RPT_CURR',
           'BSEG_ID',
           COUNT(*)
    FROM (
        SELECT bseg_id
        FROM cisadm.bseg_billed_usage_rpt_curr
        GROUP BY bseg_id
        HAVING COUNT(*) > 1
    )
    UNION ALL
    SELECT 'BSEG_SQ_USAGE_RPT_CURR',
           'BSEG_ID + UOM + TOU + SQI',
           COUNT(*)
    FROM (
        SELECT bseg_id, uom_cd, tou_cd, sqi_cd
        FROM cisadm.bseg_sq_usage_rpt_curr
        GROUP BY bseg_id, uom_cd, tou_cd, sqi_cd
        HAVING COUNT(*) > 1
    )
    UNION ALL
    SELECT 'D1_MSRMT_RPT_CURR',
           'MEASR_COMP_ID + MSRMT_DTTM',
           COUNT(*)
    FROM (
        SELECT measr_comp_id, msrmt_dttm
        FROM cisadm.d1_msrmt_rpt_curr
        GROUP BY measr_comp_id, msrmt_dttm
        HAVING COUNT(*) > 1
    )
    UNION ALL
    SELECT 'D1_USAGE_RPT_CURR',
           'D1_USAGE_ID',
           COUNT(*)
    FROM (
        SELECT d1_usage_id
        FROM cisadm.d1_usage_rpt_curr
        GROUP BY d1_usage_id
        HAVING COUNT(*) > 1
    )
    UNION ALL
    SELECT 'D1_USAGE_SCALAR_DTL_RPT_CURR',
           'D1_USAGE_ID + SEQ_NUM',
           COUNT(*)
    FROM (
        SELECT d1_usage_id, seq_num
        FROM cisadm.d1_usage_scalar_dtl_rpt_curr
        GROUP BY d1_usage_id, seq_num
        HAVING COUNT(*) > 1
    )
    UNION ALL
    SELECT 'CMS_SA_SNAPSHOT',
           'SA_ID + C1_SNAPSHOT_DT + CM_SNAPSHOT_TYPE_FLG',
           COUNT(*)
    FROM (
        SELECT sa_id, c1_snapshot_dt, cm_snapshot_type_flg
        FROM cisadm.cms_sa_snapshot
        GROUP BY sa_id, c1_snapshot_dt, cm_snapshot_type_flg
        HAVING COUNT(*) > 1
    )
)
ORDER BY snapshot_name;

PROMPT === Snapshot rows missing their CISADM source row ===

SELECT 'FT_RPT_CURR' AS snapshot_name,
       COUNT(*) AS snapshot_rows,
       SUM(CASE WHEN ft.ft_id IS NULL THEN 1 ELSE 0 END) AS missing_source_rows
FROM cisadm.ft_rpt_curr s
LEFT JOIN cisadm.ci_ft ft
    ON ft.ft_id = s.ft_id
UNION ALL
SELECT 'FT_GL_DISTRIBUTION_RPT_CURR',
       COUNT(*),
       SUM(CASE WHEN gl.ft_id IS NULL THEN 1 ELSE 0 END)
FROM cisadm.ft_gl_distribution_rpt_curr s
LEFT JOIN cisadm.ci_ft_gl gl
    ON gl.ft_id = s.ft_id
   AND gl.gl_seq_nbr = s.gl_seq_nbr
UNION ALL
SELECT 'BSEG_BILLED_USAGE_RPT_CURR',
       COUNT(*),
       SUM(CASE WHEN bseg.bseg_id IS NULL THEN 1 ELSE 0 END)
FROM cisadm.bseg_billed_usage_rpt_curr s
LEFT JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = s.bseg_id
UNION ALL
SELECT 'BSEG_SQ_USAGE_RPT_CURR',
       COUNT(*),
       SUM(CASE WHEN sq.bseg_id IS NULL THEN 1 ELSE 0 END)
FROM cisadm.bseg_sq_usage_rpt_curr s
LEFT JOIN (
    SELECT sq.bseg_id, sq.uom_cd, sq.tou_cd, sq.sqi_cd
    FROM cisadm.ci_bseg_sq sq
    GROUP BY sq.bseg_id, sq.uom_cd, sq.tou_cd, sq.sqi_cd
) sq
    ON sq.bseg_id = s.bseg_id
   AND NVL(TRIM(sq.uom_cd), '~') = NVL(TRIM(s.uom_cd), '~')
   AND NVL(TRIM(sq.tou_cd), '~') = NVL(TRIM(s.tou_cd), '~')
   AND NVL(TRIM(sq.sqi_cd), '~') = NVL(TRIM(s.sqi_cd), '~')
UNION ALL
SELECT 'D1_MSRMT_RPT_CURR',
       COUNT(*),
       SUM(CASE WHEN m.measr_comp_id IS NULL THEN 1 ELSE 0 END)
FROM cisadm.d1_msrmt_rpt_curr s
LEFT JOIN cisadm.d1_msrmt m
    ON m.measr_comp_id = s.measr_comp_id
   AND m.msrmt_dttm = s.msrmt_dttm
UNION ALL
SELECT 'D1_USAGE_RPT_CURR',
       COUNT(*),
       SUM(CASE WHEN u.d1_usage_id IS NULL THEN 1 ELSE 0 END)
FROM cisadm.d1_usage_rpt_curr s
LEFT JOIN cisadm.d1_usage u
    ON u.d1_usage_id = s.d1_usage_id
UNION ALL
SELECT 'D1_USAGE_SCALAR_DTL_RPT_CURR',
       COUNT(*),
       SUM(CASE WHEN dtl.d1_usage_id IS NULL THEN 1 ELSE 0 END)
FROM cisadm.d1_usage_scalar_dtl_rpt_curr s
LEFT JOIN cisadm.d1_usage_scalar_dtl dtl
    ON dtl.d1_usage_id = s.d1_usage_id
   AND dtl.seq_num = s.seq_num
   AND NVL(TRIM(dtl.measr_comp_id), '~') = NVL(TRIM(s.measr_comp_id), '~')
   AND NVL(TRIM(dtl.d1_sp_id), '~') = NVL(TRIM(s.d1_sp_id), '~')
UNION ALL
SELECT 'CMS_SA_SNAPSHOT',
       COUNT(*),
       SUM(CASE WHEN sa.sa_id IS NULL THEN 1 ELSE 0 END)
FROM cisadm.cms_sa_snapshot s
LEFT JOIN cisadm.ci_sa sa
    ON sa.sa_id = s.sa_id
ORDER BY 1;

PROMPT === Cycle fallback gaps where CISADM source has a value ===

SELECT 'BSEG_BILLED_USAGE_RPT_CURR' AS snapshot_name,
       COUNT(*) AS checked_rows,
       SUM(CASE
               WHEN COALESCE(NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), '')) IS NOT NULL
                AND NULLIF(TRIM(s.bill_bill_cyc_cd), '') IS NULL
               THEN 1 ELSE 0
           END) AS cycle_snapshot_null_with_source_value_1,
       SUM(CASE
               WHEN COALESCE(NULLIF(TRIM(bseg.bill_cyc_cd), ''), NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), '')) IS NOT NULL
                AND NULLIF(TRIM(s.bseg_bill_cyc_cd), '') IS NULL
               THEN 1 ELSE 0
           END) AS cycle_snapshot_null_with_source_value_2
FROM cisadm.bseg_billed_usage_rpt_curr s
JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = s.bseg_id
JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
LEFT JOIN cisadm.ci_acct acct
    ON acct.acct_id = bill.acct_id
UNION ALL
SELECT 'BSEG_SQ_USAGE_RPT_CURR',
       COUNT(*),
       SUM(CASE
               WHEN COALESCE(NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), '')) IS NOT NULL
                AND NULLIF(TRIM(s.bill_bill_cyc_cd), '') IS NULL
               THEN 1 ELSE 0
           END),
       SUM(CASE
               WHEN COALESCE(NULLIF(TRIM(bseg.bill_cyc_cd), ''), NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), '')) IS NOT NULL
                AND NULLIF(TRIM(s.bseg_bill_cyc_cd), '') IS NULL
               THEN 1 ELSE 0
           END)
FROM cisadm.bseg_sq_usage_rpt_curr s
JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = s.bseg_id
JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
LEFT JOIN cisadm.ci_acct acct
    ON acct.acct_id = bill.acct_id
UNION ALL
SELECT 'FT_RPT_CURR',
       COUNT(*),
       SUM(CASE
               WHEN NULLIF(TRIM(acct.bill_cyc_cd), '') IS NOT NULL
                AND NULLIF(TRIM(s.bill_cyc_cd), '') IS NULL
               THEN 1 ELSE 0
           END),
       NULL
FROM cisadm.ft_rpt_curr s
JOIN cisadm.ci_ft ft
    ON ft.ft_id = s.ft_id
LEFT JOIN cisadm.ci_sa sa
    ON sa.sa_id = ft.sa_id
LEFT JOIN cisadm.ci_acct acct
    ON acct.acct_id = sa.acct_id
UNION ALL
SELECT 'FT_GL_DISTRIBUTION_RPT_CURR',
       COUNT(*),
       SUM(CASE
               WHEN NULLIF(TRIM(acct.bill_cyc_cd), '') IS NOT NULL
                AND NULLIF(TRIM(s.bill_cyc_cd), '') IS NULL
               THEN 1 ELSE 0
           END),
       SUM(CASE
               WHEN COALESCE(NULLIF(TRIM(bseg.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), '')) IS NOT NULL
                AND NULLIF(TRIM(s.bseg_bill_cyc_cd), '') IS NULL
               THEN 1 ELSE 0
           END)
FROM cisadm.ft_gl_distribution_rpt_curr s
JOIN cisadm.ci_ft ft
    ON ft.ft_id = s.ft_id
LEFT JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = ft.sibling_id
   AND bseg.bill_id = ft.bill_id
   AND ft.ft_type_flg IN ('BS', 'BX')
LEFT JOIN cisadm.ci_sa sa
    ON sa.sa_id = ft.sa_id
LEFT JOIN cisadm.ci_acct acct
    ON acct.acct_id = sa.acct_id
UNION ALL
SELECT 'D1_USAGE_RPT_CURR',
       COUNT(*),
       SUM(CASE
               WHEN NULLIF(TRIM(us.d1_bill_cyc_cd), '') IS NOT NULL
                AND NULLIF(TRIM(s.d1_bill_cyc_cd), '') IS NULL
               THEN 1 ELSE 0
           END),
       NULL
FROM cisadm.d1_usage_rpt_curr s
JOIN cisadm.d1_usage u
    ON u.d1_usage_id = s.d1_usage_id
LEFT JOIN cisadm.d1_us us
    ON us.us_id = u.us_id
UNION ALL
SELECT 'D1_USAGE_SCALAR_DTL_RPT_CURR',
       COUNT(*),
       SUM(CASE
               WHEN NULLIF(TRIM(us.d1_bill_cyc_cd), '') IS NOT NULL
                AND NULLIF(TRIM(s.d1_bill_cyc_cd), '') IS NULL
               THEN 1 ELSE 0
           END),
       NULL
FROM cisadm.d1_usage_scalar_dtl_rpt_curr s
JOIN cisadm.d1_usage u
    ON u.d1_usage_id = s.d1_usage_id
LEFT JOIN cisadm.d1_us us
    ON us.us_id = u.us_id;

PROMPT === High-value measure parity at snapshot grain ===

WITH bseg_sq AS (
    SELECT sq.bseg_id,
           SUM(NVL(sq.bill_sq, 0)) AS total_bill_sq
    FROM cisadm.ci_bseg_sq sq
    WHERE EXISTS (
        SELECT 1
        FROM cisadm.bseg_billed_usage_rpt_curr snap
        WHERE snap.bseg_id = sq.bseg_id
    )
    GROUP BY sq.bseg_id
),
bseg_calc AS (
    SELECT calc.bseg_id,
           SUM(NVL(calc.calc_amt, 0)) AS total_calc_amt
    FROM cisadm.ci_bseg_calc calc
    WHERE EXISTS (
        SELECT 1
        FROM cisadm.bseg_billed_usage_rpt_curr snap
        WHERE snap.bseg_id = calc.bseg_id
    )
    GROUP BY calc.bseg_id
),
sq_det AS (
    SELECT sq.bseg_id,
           sq.uom_cd,
           sq.tou_cd,
           sq.sqi_cd,
           SUM(NVL(sq.bill_sq, 0)) AS total_bill_sq,
           SUM(NVL(sq.init_sq, 0)) AS total_init_sq
    FROM cisadm.ci_bseg_sq sq
    WHERE EXISTS (
        SELECT 1
        FROM cisadm.bseg_sq_usage_rpt_curr snap
        WHERE snap.bseg_id = sq.bseg_id
          AND NVL(TRIM(snap.uom_cd), '~') = NVL(TRIM(sq.uom_cd), '~')
          AND NVL(TRIM(snap.tou_cd), '~') = NVL(TRIM(sq.tou_cd), '~')
          AND NVL(TRIM(snap.sqi_cd), '~') = NVL(TRIM(sq.sqi_cd), '~')
    )
    GROUP BY sq.bseg_id, sq.uom_cd, sq.tou_cd, sq.sqi_cd
),
cms_ft AS (
    SELECT ft.sa_id,
           SUM(NVL(ft.cur_amt, 0)) AS cur_bal,
           SUM(NVL(ft.tot_amt, 0)) AS tot_bal
    FROM cisadm.ci_ft ft
    WHERE ft.freeze_sw = 'Y'
      AND ft.not_in_ars_sw = 'N'
      AND ft.ars_dt IS NOT NULL
      AND TRUNC(ft.ars_dt) <= TRUNC(SYSDATE)
      AND EXISTS (
          SELECT 1
          FROM cisadm.cms_sa_snapshot snap
          WHERE snap.sa_id = ft.sa_id
      )
    GROUP BY ft.sa_id
)
SELECT 'FT_RPT_CURR' AS snapshot_name,
       COUNT(*) AS checked_rows,
       ROUND(SUM(NVL(s.cur_amt, 0)), 2) AS snapshot_amount_1,
       ROUND(SUM(NVL(ft.cur_amt, 0)), 2) AS source_amount_1,
       ROUND(SUM(NVL(s.cur_amt, 0)) - SUM(NVL(ft.cur_amt, 0)), 2) AS amount_1_delta,
       ROUND(SUM(NVL(s.tot_amt, 0)), 2) AS snapshot_amount_2,
       ROUND(SUM(NVL(ft.tot_amt, 0)), 2) AS source_amount_2,
       ROUND(SUM(NVL(s.tot_amt, 0)) - SUM(NVL(ft.tot_amt, 0)), 2) AS amount_2_delta
FROM cisadm.ft_rpt_curr s
JOIN cisadm.ci_ft ft
    ON ft.ft_id = s.ft_id
UNION ALL
SELECT 'FT_GL_DISTRIBUTION_RPT_CURR',
       COUNT(*),
       ROUND(SUM(NVL(s.gl_amount, 0)), 2),
       ROUND(SUM(NVL(gl.amount, 0)), 2),
       ROUND(SUM(NVL(s.gl_amount, 0)) - SUM(NVL(gl.amount, 0)), 2),
       ROUND(SUM(NVL(s.debit_amt, 0) - NVL(s.credit_amt, 0)), 2),
       ROUND(SUM(NVL(gl.amount, 0)), 2),
       ROUND(SUM(NVL(s.debit_amt, 0) - NVL(s.credit_amt, 0)) - SUM(NVL(gl.amount, 0)), 2)
FROM cisadm.ft_gl_distribution_rpt_curr s
JOIN cisadm.ci_ft_gl gl
    ON gl.ft_id = s.ft_id
   AND gl.gl_seq_nbr = s.gl_seq_nbr
UNION ALL
SELECT 'BSEG_BILLED_USAGE_RPT_CURR',
       COUNT(*),
       ROUND(SUM(NVL(s.total_bill_sq, 0)), 6),
       ROUND(SUM(NVL(bseg_sq.total_bill_sq, 0)), 6),
       ROUND(SUM(NVL(s.total_bill_sq, 0)) - SUM(NVL(bseg_sq.total_bill_sq, 0)), 6),
       ROUND(SUM(NVL(s.total_calc_amt, 0)), 2),
       ROUND(SUM(NVL(bseg_calc.total_calc_amt, 0)), 2),
       ROUND(SUM(NVL(s.total_calc_amt, 0)) - SUM(NVL(bseg_calc.total_calc_amt, 0)), 2)
FROM cisadm.bseg_billed_usage_rpt_curr s
LEFT JOIN bseg_sq
    ON bseg_sq.bseg_id = s.bseg_id
LEFT JOIN bseg_calc
    ON bseg_calc.bseg_id = s.bseg_id
UNION ALL
SELECT 'BSEG_SQ_USAGE_RPT_CURR',
       COUNT(*),
       ROUND(SUM(NVL(s.total_bill_sq, 0)), 6),
       ROUND(SUM(NVL(sq_det.total_bill_sq, 0)), 6),
       ROUND(SUM(NVL(s.total_bill_sq, 0)) - SUM(NVL(sq_det.total_bill_sq, 0)), 6),
       ROUND(SUM(NVL(s.total_init_sq, 0)), 6),
       ROUND(SUM(NVL(sq_det.total_init_sq, 0)), 6),
       ROUND(SUM(NVL(s.total_init_sq, 0)) - SUM(NVL(sq_det.total_init_sq, 0)), 6)
FROM cisadm.bseg_sq_usage_rpt_curr s
LEFT JOIN sq_det
    ON sq_det.bseg_id = s.bseg_id
   AND NVL(TRIM(sq_det.uom_cd), '~') = NVL(TRIM(s.uom_cd), '~')
   AND NVL(TRIM(sq_det.tou_cd), '~') = NVL(TRIM(s.tou_cd), '~')
   AND NVL(TRIM(sq_det.sqi_cd), '~') = NVL(TRIM(s.sqi_cd), '~')
UNION ALL
SELECT 'D1_USAGE_SCALAR_DTL_RPT_CURR',
       COUNT(*),
       ROUND(SUM(NVL(s.final_quantity, 0)), 6),
       ROUND(SUM(NVL(dtl.final_quantity, 0)), 6),
       ROUND(SUM(NVL(s.final_quantity, 0)) - SUM(NVL(dtl.final_quantity, 0)), 6),
       ROUND(SUM(NVL(s.quantity, 0)), 6),
       ROUND(SUM(NVL(dtl.quantity, 0)), 6),
       ROUND(SUM(NVL(s.quantity, 0)) - SUM(NVL(dtl.quantity, 0)), 6)
FROM cisadm.d1_usage_scalar_dtl_rpt_curr s
JOIN cisadm.d1_usage_scalar_dtl dtl
    ON dtl.d1_usage_id = s.d1_usage_id
   AND dtl.seq_num = s.seq_num
   AND NVL(TRIM(dtl.measr_comp_id), '~') = NVL(TRIM(s.measr_comp_id), '~')
   AND NVL(TRIM(dtl.d1_sp_id), '~') = NVL(TRIM(s.d1_sp_id), '~')
UNION ALL
SELECT 'D1_MSRMT_RPT_CURR',
       COUNT(*),
       ROUND(SUM(NVL(s.msrmt_val, 0)), 6),
       ROUND(SUM(NVL(m.msrmt_val, 0)), 6),
       ROUND(SUM(NVL(s.msrmt_val, 0)) - SUM(NVL(m.msrmt_val, 0)), 6),
       ROUND(SUM(NVL(s.reading_val, 0)), 6),
       ROUND(SUM(NVL(m.reading_val, 0)), 6),
       ROUND(SUM(NVL(s.reading_val, 0)) - SUM(NVL(m.reading_val, 0)), 6)
FROM cisadm.d1_msrmt_rpt_curr s
JOIN cisadm.d1_msrmt m
    ON m.measr_comp_id = s.measr_comp_id
   AND m.msrmt_dttm = s.msrmt_dttm
UNION ALL
SELECT 'CMS_SA_SNAPSHOT',
       COUNT(*),
       ROUND(SUM(NVL(s.cur_bal, 0)), 2),
       ROUND(SUM(NVL(cms_ft.cur_bal, 0)), 2),
       ROUND(SUM(NVL(s.cur_bal, 0)) - SUM(NVL(cms_ft.cur_bal, 0)), 2),
       ROUND(SUM(NVL(s.tot_bal, 0)), 2),
       ROUND(SUM(NVL(cms_ft.tot_bal, 0)), 2),
       ROUND(SUM(NVL(s.tot_bal, 0)) - SUM(NVL(cms_ft.tot_bal, 0)), 2)
FROM cisadm.cms_sa_snapshot s
LEFT JOIN cms_ft
    ON cms_ft.sa_id = s.sa_id;
