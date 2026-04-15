-- PURPOSE:
--   Trace one bill segment from billed determinants and calc headers
--   back to the linked usage transaction, scalar detail, and processed
--   measurement rows.
--
-- GRAIN / SAFETY:
--   Read-only diagnostic SQL.
--   Uses the repo's canonical billing bridge:
--     CI_BSEG.BSEG_ID -> C1_USAGE.BSEG_ID
--     C1_USAGE.USAGE_ID -> D1_USAGE.USG_EXT_ID
--     D1_USAGE.D1_USAGE_ID -> D1_USAGE_SCALAR_DTL.D1_USAGE_ID
--
-- IMPORTANT:
--   The scalar-detail join is exact.
--   The processed-measurement section is a best-effort trace by
--   MEASR_COMP_ID plus scalar time window. It is useful for inspection,
--   but it is not presented as a guaranteed one-to-one scalar-to-measurement key.
--
-- BINDS:
--   :P_BSEG_ID   required bill segment id

-- 1) Bill segment header and service agreement context
SELECT
    bseg.bseg_id,
    bseg.bill_id,
    bill.bill_dt,
    bill.bill_stat_flg,
    bseg.bseg_stat_flg,
    bseg.sa_id AS bseg_sa_id,
    sa.acct_id,
    sa.sa_type_cd,
    bseg.start_dt AS bseg_start_dt,
    bseg.end_dt AS bseg_end_dt,
    bseg.bill_cyc_cd AS bseg_bill_cyc_cd,
    bseg.prem_id,
    bseg.est_sw,
    bseg.closing_bseg_sw,
    bseg.sq_override_sw,
    bseg.item_override_sw
FROM cisadm.ci_bseg bseg
LEFT JOIN cisadm.ci_bill bill
    ON TRIM(bill.bill_id) = TRIM(bseg.bill_id)
LEFT JOIN cisadm.ci_sa sa
    ON TRIM(sa.sa_id) = TRIM(bseg.sa_id)
WHERE TRIM(bseg.bseg_id) = TRIM(:P_BSEG_ID);

-- 2) Billed service quantity rows under the segment
SELECT
    sq.bseg_id,
    sq.uom_cd,
    uom_l.descr AS uom_desc,
    sq.tou_cd,
    tou_l.descr AS tou_desc,
    sq.sqi_cd,
    sqi_l.descr AS sqi_desc,
    sq.init_sq,
    sq.bill_sq
FROM cisadm.ci_bseg_sq sq
LEFT JOIN cisadm.ci_uom_l uom_l
    ON uom_l.uom_cd = sq.uom_cd
   AND uom_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_tou_l tou_l
    ON tou_l.tou_cd = sq.tou_cd
   AND tou_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_sqi_l sqi_l
    ON sqi_l.sqi_cd = sq.sqi_cd
   AND sqi_l.language_cd = 'ENG'
WHERE TRIM(sq.bseg_id) = TRIM(:P_BSEG_ID)
ORDER BY
    NVL(sq.uom_cd, '~'),
    NVL(sq.tou_cd, '~'),
    NVL(sq.sqi_cd, '~');

-- 3) Calc headers under the segment
SELECT
    calc.bseg_id,
    calc.header_seq,
    calc.rs_cd,
    rs_l.descr AS rs_desc,
    calc.effdt,
    calc.calc_amt
FROM cisadm.ci_bseg_calc calc
LEFT JOIN cisadm.ci_rs_l rs_l
    ON rs_l.rs_cd = calc.rs_cd
   AND rs_l.language_cd = 'ENG'
WHERE TRIM(calc.bseg_id) = TRIM(:P_BSEG_ID)
ORDER BY
    calc.header_seq,
    calc.effdt,
    calc.rs_cd;

-- 4) Billing bridge rows from C1 usage into D1 usage
SELECT
    bseg.bseg_id,
    bseg.sa_id AS bseg_sa_id,
    cu.usage_id AS c1_usage_id,
    cu.master_usage_id AS c1_master_usage_id,
    cu.sa_id AS c1_sa_id,
    cu.sp_id AS c1_sp_id,
    cu.bseg_id AS c1_bseg_id,
    cu.bill_cyc_cd AS c1_bill_cyc_cd,
    cu.bo_status_cd AS c1_bo_status_cd,
    cu.start_dttm AS c1_start_dttm,
    cu.end_dttm AS c1_end_dttm,
    du.d1_usage_id,
    du.us_id,
    du.usg_ext_id,
    du.bo_status_cd AS d1_bo_status_cd,
    du.start_dttm AS d1_start_dttm,
    du.end_dttm AS d1_end_dttm,
    du.used_on_bill_flg,
    du.linked_to_frzn_bseg_flg,
    CASE
        WHEN TRIM(cu.sa_id) = TRIM(bseg.sa_id) THEN 'Y'
        ELSE 'N'
    END AS sa_match_sw
FROM cisadm.ci_bseg bseg
LEFT JOIN cisadm.c1_usage cu
    ON TRIM(cu.bseg_id) = TRIM(bseg.bseg_id)
   AND cu.bo_status_cd = 'BD-PROC'
LEFT JOIN cisadm.d1_usage du
    ON TRIM(du.usg_ext_id) = TRIM(cu.usage_id)
WHERE TRIM(bseg.bseg_id) = TRIM(:P_BSEG_ID)
ORDER BY
    cu.usage_id,
    du.d1_usage_id;

-- 5) Scalar detail linked to the bill segment through the canonical bridge
WITH usage_bridge AS (
    SELECT
        bseg.bseg_id,
        bseg.sa_id AS bseg_sa_id,
        cu.usage_id AS c1_usage_id,
        cu.sa_id AS c1_sa_id,
        cu.sp_id AS c1_sp_id,
        du.d1_usage_id,
        du.us_id,
        du.start_dttm AS usage_start_dttm,
        du.end_dttm AS usage_end_dttm
    FROM cisadm.ci_bseg bseg
    JOIN cisadm.c1_usage cu
        ON TRIM(cu.bseg_id) = TRIM(bseg.bseg_id)
       AND cu.bo_status_cd = 'BD-PROC'
    JOIN cisadm.d1_usage du
        ON TRIM(du.usg_ext_id) = TRIM(cu.usage_id)
    WHERE TRIM(bseg.bseg_id) = TRIM(:P_BSEG_ID)
)
SELECT
    ub.bseg_id,
    ub.bseg_sa_id,
    ub.c1_usage_id,
    ub.c1_sa_id,
    ub.c1_sp_id,
    ub.d1_usage_id,
    ub.us_id,
    ub.usage_start_dttm,
    ub.usage_end_dttm,
    sd.seq_num,
    sd.d1_sp_id,
    sd.measr_comp_id,
    sd.d1_uom_cd,
    raw_uom.descr100 AS d1_uom_desc,
    sd.d1_tou_cd,
    raw_tou.descr100 AS d1_tou_desc,
    sd.d1_sqi_cd,
    raw_sqi.descr100 AS d1_sqi_desc,
    sd.start_dttm AS scalar_start_dttm,
    sd.end_dttm AS scalar_end_dttm,
    sd.start_msrmt,
    sd.end_msrmt,
    sd.quantity,
    sd.d1_final_uom_cd,
    final_uom.descr100 AS d1_final_uom_desc,
    sd.d1_final_tou_cd,
    final_tou.descr100 AS d1_final_tou_desc,
    sd.d1_final_sqi_cd,
    final_sqi.descr100 AS d1_final_sqi_desc,
    sd.final_quantity,
    sd.usg_rule_cd,
    sd.applied_mltr,
    sd.use_percent,
    sd.msrmt_cond_flg
FROM usage_bridge ub
JOIN cisadm.d1_usage_scalar_dtl sd
    ON TRIM(sd.d1_usage_id) = TRIM(ub.d1_usage_id)
LEFT JOIN cisadm.d1_uom_l raw_uom
    ON raw_uom.d1_uom_cd = sd.d1_uom_cd
   AND raw_uom.language_cd = 'ENG'
LEFT JOIN cisadm.d1_tou_l raw_tou
    ON raw_tou.d1_tou_cd = sd.d1_tou_cd
   AND raw_tou.language_cd = 'ENG'
LEFT JOIN cisadm.d1_sqi_l raw_sqi
    ON raw_sqi.d1_sqi_cd = sd.d1_sqi_cd
   AND raw_sqi.language_cd = 'ENG'
LEFT JOIN cisadm.d1_uom_l final_uom
    ON final_uom.d1_uom_cd = sd.d1_final_uom_cd
   AND final_uom.language_cd = 'ENG'
LEFT JOIN cisadm.d1_tou_l final_tou
    ON final_tou.d1_tou_cd = sd.d1_final_tou_cd
   AND final_tou.language_cd = 'ENG'
LEFT JOIN cisadm.d1_sqi_l final_sqi
    ON final_sqi.d1_sqi_cd = sd.d1_final_sqi_cd
   AND final_sqi.language_cd = 'ENG'
ORDER BY
    ub.c1_usage_id,
    ub.d1_usage_id,
    sd.seq_num;

-- 6) Best-effort processed measurement rows on the same measuring component
--    within the scalar-detail time window
WITH usage_bridge AS (
    SELECT
        bseg.bseg_id,
        cu.usage_id AS c1_usage_id,
        du.d1_usage_id
    FROM cisadm.ci_bseg bseg
    JOIN cisadm.c1_usage cu
        ON TRIM(cu.bseg_id) = TRIM(bseg.bseg_id)
       AND cu.bo_status_cd = 'BD-PROC'
    JOIN cisadm.d1_usage du
        ON TRIM(du.usg_ext_id) = TRIM(cu.usage_id)
    WHERE TRIM(bseg.bseg_id) = TRIM(:P_BSEG_ID)
),
scalar_rows AS (
    SELECT
        ub.bseg_id,
        ub.c1_usage_id,
        sd.d1_usage_id,
        sd.seq_num,
        sd.measr_comp_id,
        sd.start_dttm AS scalar_start_dttm,
        sd.end_dttm AS scalar_end_dttm,
        sd.start_msrmt,
        sd.end_msrmt,
        sd.quantity,
        sd.final_quantity
    FROM usage_bridge ub
    JOIN cisadm.d1_usage_scalar_dtl sd
        ON TRIM(sd.d1_usage_id) = TRIM(ub.d1_usage_id)
)
SELECT
    sr.bseg_id,
    sr.c1_usage_id,
    sr.d1_usage_id,
    sr.seq_num AS scalar_seq_num,
    sr.measr_comp_id,
    sr.scalar_start_dttm,
    sr.scalar_end_dttm,
    sr.start_msrmt,
    sr.end_msrmt,
    sr.quantity,
    sr.final_quantity,
    ms.measr_comp_id AS msrmt_measr_comp_id,
    ms.msrmt_dttm,
    ms.prev_msrmt_dttm,
    ms.msrmt_cond_flg,
    ms.reading_cond_flg,
    ms.reading_val,
    ms.msrmt_val,
    CASE
        WHEN ms.msrmt_dttm = sr.scalar_start_dttm THEN 'SCALAR_START_DTTM'
        WHEN ms.msrmt_dttm = sr.scalar_end_dttm THEN 'SCALAR_END_DTTM'
        ELSE 'IN_WINDOW'
    END AS msrmt_match_type
FROM scalar_rows sr
JOIN cisadm.d1_msrmt ms
    ON TRIM(ms.measr_comp_id) = TRIM(sr.measr_comp_id)
   AND ms.msrmt_dttm >= sr.scalar_start_dttm
   AND ms.msrmt_dttm <= sr.scalar_end_dttm
ORDER BY
    sr.c1_usage_id,
    sr.d1_usage_id,
    sr.seq_num,
    ms.msrmt_dttm;
