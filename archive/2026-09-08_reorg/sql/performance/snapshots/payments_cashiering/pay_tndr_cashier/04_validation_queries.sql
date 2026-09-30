-- 4a) Manual first run
BEGIN
    cisadm.refresh_pay_tndr_cash_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.pay_tndr_cash_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.ci_pay_tndr;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    pay_tender_id,
    COUNT(*) AS row_count
FROM cisadm.pay_tndr_cash_rpt_curr
GROUP BY pay_tender_id
HAVING COUNT(*) > 1;

-- 4d) Null coverage for descriptive fields
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN tender_type_desc IS NULL AND tender_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_tender_type_desc,
    SUM(CASE WHEN tndr_source_desc IS NULL AND tndr_source_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_tndr_source_desc,
    SUM(CASE WHEN event_pay_status_desc IS NULL AND event_pay_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_event_pay_status_desc,
    SUM(CASE WHEN apay_src_name IS NULL AND apay_src_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_apay_src_name,
    SUM(CASE WHEN source_family_desc IS NULL AND source_family_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_source_family_desc,
    SUM(CASE WHEN customer_name IS NULL AND payor_acct_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_customer_name
FROM cisadm.pay_tndr_cash_rpt_curr;

-- 4e) Tender amount reconciliation
SELECT
    COUNT(*) AS snap_tender_rows,
    SUM(tender_amt) AS snap_tender_amt
FROM cisadm.pay_tndr_cash_rpt_curr;

SELECT
    COUNT(*) AS src_tender_rows,
    SUM(tender_amt) AS src_tender_amt
FROM cisadm.ci_pay_tndr;

-- 4f) Stage linkage reconciliation
SELECT
    COUNT(*) AS snap_staged_rows
FROM cisadm.pay_tndr_cash_rpt_curr
WHERE staged_tender_sw = 'Y';

SELECT
    COUNT(DISTINCT pts.pay_tender_id) AS src_staged_rows_joining_base_tender
FROM cisadm.ci_pay_tndr_st pts
JOIN cisadm.ci_pay_tndr pt
    ON pt.pay_tender_id = pts.pay_tender_id;

SELECT
    COUNT(*) AS orphan_stage_rows_not_in_base_tender
FROM (
    SELECT DISTINCT pts.pay_tender_id
    FROM cisadm.ci_pay_tndr_st pts
    LEFT JOIN cisadm.ci_pay_tndr pt
        ON pt.pay_tender_id = pts.pay_tender_id
    WHERE pt.pay_tender_id IS NULL
) orphan_stage;

-- 4g) Tender control / deposit control coverage
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN tndr_ctl_id IS NULL THEN 1 ELSE 0 END) AS missing_tndr_ctl_id,
    SUM(CASE WHEN dep_ctl_id IS NULL THEN 1 ELSE 0 END) AS missing_dep_ctl_id
FROM cisadm.pay_tndr_cash_rpt_curr;

-- 4g1) Deposit-control balance coverage inside the snapshot
SELECT
    COUNT(*) AS rows_with_dep_ctl,
    SUM(CASE WHEN dep_ctl_start_balance IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_dep_ctl_start_balance,
    SUM(CASE WHEN dep_ctl_end_balance IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_dep_ctl_end_balance
FROM cisadm.pay_tndr_cash_rpt_curr
WHERE dep_ctl_id IS NOT NULL;

-- 4g2) Deposit-control balance parity by distinct deposit control
WITH snap AS (
    SELECT
        dep_ctl_id,
        MAX(dep_ctl_status_flg) AS snap_dep_ctl_status_flg,
        MAX(dep_ctl_srce_type_flg) AS snap_dep_ctl_srce_type_flg,
        MAX(dep_ctl_start_balance) AS snap_dep_ctl_start_balance,
        MAX(dep_ctl_end_balance) AS snap_dep_ctl_end_balance
    FROM cisadm.pay_tndr_cash_rpt_curr
    WHERE dep_ctl_id IS NOT NULL
    GROUP BY dep_ctl_id
)
SELECT
    COUNT(*) AS paired_dep_ctl_rows,
    SUM(CASE WHEN NVL(dc.dep_ctl_status_flg, '#NULL#') <> NVL(snap.snap_dep_ctl_status_flg, '#NULL#') THEN 1 ELSE 0 END) AS dep_ctl_status_mismatch_rows,
    SUM(CASE WHEN NVL(dc.tndr_srce_type_flg, '#NULL#') <> NVL(snap.snap_dep_ctl_srce_type_flg, '#NULL#') THEN 1 ELSE 0 END) AS dep_ctl_source_type_mismatch_rows,
    SUM(CASE WHEN NVL(dc.start_balance, 0) <> NVL(snap.snap_dep_ctl_start_balance, 0) THEN 1 ELSE 0 END) AS dep_ctl_start_balance_mismatch_rows,
    SUM(CASE WHEN NVL(dc.end_balance, 0) <> NVL(snap.snap_dep_ctl_end_balance, 0) THEN 1 ELSE 0 END) AS dep_ctl_end_balance_mismatch_rows
FROM snap
INNER JOIN cisadm.ci_dep_ctl dc
    ON dc.dep_ctl_id = snap.dep_ctl_id;

-- 4h) Tender type profile
SELECT
    tender_type_cd,
    tender_type_desc,
    tndr_status_flg,
    COUNT(*) AS tender_count,
    SUM(tender_amt) AS total_tender_amt
FROM cisadm.pay_tndr_cash_rpt_curr
GROUP BY
    tender_type_cd,
    tender_type_desc,
    tndr_status_flg
ORDER BY
    tender_count DESC,
    tender_type_cd,
    tndr_status_flg;

-- 4i) Tender source profile
SELECT
    tndr_source_cd,
    tndr_source_desc,
    tndr_srce_type_flg,
    COUNT(*) AS tender_count,
    SUM(tender_amt) AS total_tender_amt
FROM cisadm.pay_tndr_cash_rpt_curr
GROUP BY
    tndr_source_cd,
    tndr_source_desc,
    tndr_srce_type_flg
ORDER BY
    tender_count DESC,
    tndr_source_cd;

-- 4j) Derived source-family profile
SELECT
    source_family_cd,
    source_family_desc,
    COUNT(*) AS tender_count,
    SUM(tender_amt) AS total_tender_amt
FROM cisadm.pay_tndr_cash_rpt_curr
GROUP BY
    source_family_cd,
    source_family_desc
ORDER BY
    total_tender_amt DESC,
    source_family_cd;

-- 4k) Source-family exception checks
SELECT
    COUNT(*) AS ach_rows_not_classified_legacy_apay
FROM cisadm.pay_tndr_cash_rpt_curr
WHERE TRIM(tndr_source_cd) = 'ACH'
  AND source_family_cd <> 'LEGACY_APAY';

SELECT
    COUNT(*) AS originp_rows_not_classified_originpay
FROM cisadm.pay_tndr_cash_rpt_curr
WHERE (
        TRIM(tndr_source_cd) = 'ORIGINP'
     OR TRIM(tender_type_cd) IN ('OPCC', 'OPOC')
      )
  AND source_family_cd <> 'ORIGINPAY'
  AND staged_tender_sw <> 'Y';

-- 4l) Spot-check recent staged or external tenders
SELECT *
FROM cisadm.pay_tndr_cash_rpt_curr
WHERE staged_tender_sw = 'Y'
   OR ext_source_id IS NOT NULL
FETCH FIRST 10 ROWS ONLY;
