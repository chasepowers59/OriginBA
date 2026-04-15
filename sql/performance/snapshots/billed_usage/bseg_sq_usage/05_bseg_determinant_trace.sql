-- Purpose:
--   Inspect one bill segment and the determinant rows under it.
--
-- How to use:
--   Replace :P_BSEG_ID with the bill segment you want to inspect.
--
-- Mental model:
--   A billed-usage determinant is the combination of:
--     UOM_CD + TOU_CD + SQI_CD
--   A single bill segment can have one or many determinant combinations.

-- 5a) Segment summary from raw CI_BSEG_SQ
SELECT
    sq.bseg_id,
    COUNT(*) AS raw_sq_row_count,
    COUNT(DISTINCT NVL(sq.uom_cd, '~') || ':' || NVL(sq.tou_cd, '~') || ':' || NVL(sq.sqi_cd, '~')) AS determinant_count,
    SUM(NVL(sq.init_sq, 0)) AS total_init_sq,
    SUM(NVL(sq.bill_sq, 0)) AS total_bill_sq
FROM cisadm.ci_bseg_sq sq
WHERE sq.bseg_id = :P_BSEG_ID
GROUP BY
    sq.bseg_id;

-- 5b) Segment summary from the segment-grain snapshot
SELECT
    bseg_id,
    sq_line_count,
    determinant_count,
    total_init_sq,
    total_bill_sq,
    sole_uom_cd,
    sole_uom_desc,
    sole_tou_cd,
    sole_tou_desc,
    sole_sqi_cd,
    sole_sqi_desc
FROM cisadm.bseg_billed_usage_rpt_curr
WHERE bseg_id = :P_BSEG_ID;

-- 5c) Determinant rows under that one bill segment from raw CI_BSEG_SQ
SELECT
    sq.bseg_id,
    sq.uom_cd,
    uom_l.descr AS uom_desc,
    sq.tou_cd,
    tou_l.descr AS tou_desc,
    sq.sqi_cd,
    sqi_l.descr AS sqi_desc,
    COUNT(*) AS raw_sq_row_count,
    SUM(NVL(sq.init_sq, 0)) AS total_init_sq,
    SUM(NVL(sq.bill_sq, 0)) AS total_bill_sq
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
WHERE sq.bseg_id = :P_BSEG_ID
GROUP BY
    sq.bseg_id,
    sq.uom_cd,
    uom_l.descr,
    sq.tou_cd,
    tou_l.descr,
    sq.sqi_cd,
    sqi_l.descr
ORDER BY
    NVL(sq.uom_cd, '~'),
    NVL(sq.tou_cd, '~'),
    NVL(sq.sqi_cd, '~');

-- 5d) Same determinant rows from the determinant-grain snapshot
SELECT
    bseg_id,
    uom_cd,
    uom_desc,
    tou_cd,
    tou_desc,
    sqi_cd,
    sqi_desc,
    sq_line_count,
    bseg_determinant_count,
    total_init_sq,
    total_bill_sq
FROM cisadm.bseg_sq_usage_rpt_curr
WHERE bseg_id = :P_BSEG_ID
ORDER BY
    NVL(uom_cd, '~'),
    NVL(tou_cd, '~'),
    NVL(sqi_cd, '~');
