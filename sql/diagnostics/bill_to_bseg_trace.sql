-- PURPOSE:
--   Show the bill segments that belong to one bill, with light billed-usage
--   and calc context so you can see the segment population quickly.
--
-- BINDS:
--   :P_BILL_ID   required bill id

-- 1) Bill header
SELECT
    bill.bill_id,
    bill.acct_id,
    bill.bill_dt,
    bill.due_dt,
    bill.bill_stat_flg,
    bill.bill_cyc_cd
FROM cisadm.ci_bill bill
WHERE TRIM(bill.bill_id) = TRIM(:P_BILL_ID);

-- 2) One row per bill segment on that bill
WITH sq_agg AS (
    SELECT
        sq.bseg_id,
        COUNT(*) AS sq_line_count,
        COUNT(DISTINCT NVL(sq.uom_cd, '~') || ':' || NVL(sq.tou_cd, '~') || ':' || NVL(sq.sqi_cd, '~')) AS determinant_count,
        SUM(NVL(sq.bill_sq, 0)) AS total_bill_sq
    FROM cisadm.ci_bseg_sq sq
    GROUP BY
        sq.bseg_id
),
calc_agg AS (
    SELECT
        calc.bseg_id,
        COUNT(*) AS calc_header_count,
        SUM(NVL(calc.calc_amt, 0)) AS total_calc_amt
    FROM cisadm.ci_bseg_calc calc
    GROUP BY
        calc.bseg_id
)
SELECT
    bseg.bill_id,
    bseg.bseg_id,
    bseg.sa_id,
    sa.sa_type_cd,
    bseg.bseg_stat_flg,
    bseg.start_dt AS bseg_start_dt,
    bseg.end_dt AS bseg_end_dt,
    bseg.bill_cyc_cd AS bseg_bill_cyc_cd,
    bseg.prem_id,
    bseg.est_sw,
    bseg.closing_bseg_sw,
    sq_agg.sq_line_count,
    sq_agg.determinant_count,
    sq_agg.total_bill_sq,
    calc_agg.calc_header_count,
    calc_agg.total_calc_amt
FROM cisadm.ci_bseg bseg
LEFT JOIN cisadm.ci_sa sa
    ON TRIM(sa.sa_id) = TRIM(bseg.sa_id)
LEFT JOIN sq_agg
    ON TRIM(sq_agg.bseg_id) = TRIM(bseg.bseg_id)
LEFT JOIN calc_agg
    ON TRIM(calc_agg.bseg_id) = TRIM(bseg.bseg_id)
WHERE TRIM(bseg.bill_id) = TRIM(:P_BILL_ID)
ORDER BY
    bseg.start_dt,
    bseg.end_dt,
    bseg.bseg_id;

-- 3) Optional determinant rows under all bill segments on that bill
SELECT
    bseg.bill_id,
    sq.bseg_id,
    sq.uom_cd,
    uom_l.descr AS uom_desc,
    sq.tou_cd,
    tou_l.descr AS tou_desc,
    sq.sqi_cd,
    sqi_l.descr AS sqi_desc,
    sq.init_sq,
    sq.bill_sq
FROM cisadm.ci_bseg bseg
JOIN cisadm.ci_bseg_sq sq
    ON TRIM(sq.bseg_id) = TRIM(bseg.bseg_id)
LEFT JOIN cisadm.ci_uom_l uom_l
    ON uom_l.uom_cd = sq.uom_cd
   AND uom_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_tou_l tou_l
    ON tou_l.tou_cd = sq.tou_cd
   AND tou_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_sqi_l sqi_l
    ON sqi_l.sqi_cd = sq.sqi_cd
   AND sqi_l.language_cd = 'ENG'
WHERE TRIM(bseg.bill_id) = TRIM(:P_BILL_ID)
ORDER BY
    sq.bseg_id,
    NVL(sq.uom_cd, '~'),
    NVL(sq.tou_cd, '~'),
    NVL(sq.sqi_cd, '~');
