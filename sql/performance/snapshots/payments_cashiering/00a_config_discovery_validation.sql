-- Payments & Cashiering discovery / tenant-shape validation
--
-- Purpose:
--   Determine whether this tenant is best modeled at payment-event grain,
--   payment grain, tender grain, or deposit/tender-control grain.
--
-- Run with F5 in SQL Developer.

--------------------------------------------------------------------------------
-- 1) Core object population and date coverage
--------------------------------------------------------------------------------
SELECT *
FROM (
    SELECT
        'CI_PAY_EVENT' AS object_name,
        COUNT(*) AS row_count,
        COUNT(DISTINCT pay_event_id) AS distinct_id_count,
        MIN(pay_dt) AS min_business_dt,
        MAX(pay_dt) AS max_business_dt,
        MIN(cre_dttm) AS min_create_dttm,
        MAX(cre_dttm) AS max_create_dttm
    FROM cisadm.ci_pay_event
    UNION ALL
    SELECT
        'CI_PAY',
        COUNT(*),
        COUNT(DISTINCT pay_id),
        NULL,
        NULL,
        NULL,
        NULL
    FROM cisadm.ci_pay
    UNION ALL
    SELECT
        'CI_PAY_TNDR',
        COUNT(*),
        COUNT(DISTINCT pay_tender_id),
        NULL,
        NULL,
        NULL,
        NULL
    FROM cisadm.ci_pay_tndr
    UNION ALL
    SELECT
        'CI_PAY_SEG',
        COUNT(*),
        COUNT(DISTINCT pay_seg_id),
        NULL,
        NULL,
        NULL,
        NULL
    FROM cisadm.ci_pay_seg
    UNION ALL
    SELECT
        'CI_TNDR_CTL',
        COUNT(*),
        COUNT(DISTINCT tndr_ctl_id),
        NULL,
        NULL,
        MIN(cre_dttm),
        MAX(cre_dttm)
    FROM cisadm.ci_tndr_ctl
    UNION ALL
    SELECT
        'CI_DEP_CTL',
        COUNT(*),
        COUNT(DISTINCT dep_ctl_id),
        NULL,
        NULL,
        MIN(cre_dttm),
        MAX(cre_dttm)
    FROM cisadm.ci_dep_ctl
    UNION ALL
    SELECT
        'CI_TNDR_DEP',
        COUNT(*),
        COUNT(DISTINCT tndr_dep_id),
        NULL,
        NULL,
        NULL,
        NULL
    FROM cisadm.ci_tndr_dep
    UNION ALL
    SELECT
        'CI_PAY_TNDR_ST',
        COUNT(*),
        COUNT(DISTINCT pay_tender_id),
        MIN(accounting_dt),
        MAX(accounting_dt),
        NULL,
        NULL
    FROM cisadm.ci_pay_tndr_st
    UNION ALL
    SELECT
        'CI_PEVT_DST_DTL',
        COUNT(*),
        COUNT(DISTINCT pay_event_id),
        NULL,
        NULL,
        NULL,
        NULL
    FROM cisadm.ci_pevt_dst_dtl
    UNION ALL
    SELECT
        'CI_APAY_SRC',
        COUNT(*),
        COUNT(DISTINCT apay_src_cd),
        NULL,
        NULL,
        NULL,
        NULL
    FROM cisadm.ci_apay_src
)
ORDER BY object_name;

--------------------------------------------------------------------------------
-- 2) Payment status distribution
--------------------------------------------------------------------------------
SELECT
    pay_status_flg,
    COUNT(*) AS row_count,
    COUNT(DISTINCT pay_id) AS pay_count,
    COUNT(DISTINCT acct_id) AS acct_count,
    SUM(pay_amt) AS total_pay_amt
FROM cisadm.ci_pay
GROUP BY pay_status_flg
ORDER BY row_count DESC, pay_status_flg;

--------------------------------------------------------------------------------
-- 3) Payment event -> payment cardinality
--------------------------------------------------------------------------------
SELECT
    payments_per_event,
    COUNT(*) AS event_count
FROM (
    SELECT
        p.pay_event_id,
        COUNT(*) AS payments_per_event
    FROM cisadm.ci_pay p
    GROUP BY p.pay_event_id
)
GROUP BY payments_per_event
ORDER BY payments_per_event;

--------------------------------------------------------------------------------
-- 4) Payment event -> tender cardinality
--------------------------------------------------------------------------------
SELECT
    tenders_per_event,
    COUNT(*) AS event_count
FROM (
    SELECT
        pt.pay_event_id,
        COUNT(*) AS tenders_per_event
    FROM cisadm.ci_pay_tndr pt
    GROUP BY pt.pay_event_id
)
GROUP BY tenders_per_event
ORDER BY tenders_per_event;

--------------------------------------------------------------------------------
-- 5) Payment -> payment segment cardinality
--------------------------------------------------------------------------------
SELECT
    pay_segments_per_pay,
    COUNT(*) AS pay_count
FROM (
    SELECT
        ps.pay_id,
        COUNT(*) AS pay_segments_per_pay
    FROM cisadm.ci_pay_seg ps
    GROUP BY ps.pay_id
)
GROUP BY pay_segments_per_pay
ORDER BY pay_segments_per_pay;

--------------------------------------------------------------------------------
-- 6) Standard bridge coverage by payment event
--------------------------------------------------------------------------------
SELECT
    COUNT(DISTINCT pe.pay_event_id) AS pay_event_count,
    COUNT(DISTINCT p.pay_event_id) AS pay_events_with_pay,
    COUNT(DISTINCT pt.pay_event_id) AS pay_events_with_tender,
    COUNT(DISTINCT CASE WHEN p.pay_event_id IS NOT NULL AND pt.pay_event_id IS NOT NULL THEN pe.pay_event_id END) AS pay_events_with_pay_and_tender
FROM cisadm.ci_pay_event pe
LEFT JOIN cisadm.ci_pay p
    ON p.pay_event_id = pe.pay_event_id
LEFT JOIN cisadm.ci_pay_tndr pt
    ON pt.pay_event_id = pe.pay_event_id;

--------------------------------------------------------------------------------
-- 7) Tender type and status distribution
--------------------------------------------------------------------------------
SELECT
    pt.tender_type_cd,
    ttl.descr AS tender_type_desc,
    pt.tndr_status_flg,
    COUNT(*) AS tender_count,
    COUNT(DISTINCT pt.pay_event_id) AS pay_event_count,
    COUNT(DISTINCT pt.payor_acct_id) AS acct_count,
    SUM(pt.tender_amt) AS total_tender_amt
FROM cisadm.ci_pay_tndr pt
LEFT JOIN cisadm.ci_tender_type_l ttl
    ON ttl.tender_type_cd = pt.tender_type_cd
   AND ttl.language_cd = 'ENG'
GROUP BY
    pt.tender_type_cd,
    ttl.descr,
    pt.tndr_status_flg
ORDER BY
    tender_count DESC,
    pt.tender_type_cd,
    pt.tndr_status_flg;

--------------------------------------------------------------------------------
-- 8) Tender control and tender source distribution
--------------------------------------------------------------------------------
SELECT
    tc.tndr_source_cd,
    tsl.descr AS tndr_source_desc,
    ts.tndr_srce_type_flg,
    COUNT(*) AS tender_control_count,
    COUNT(DISTINCT tc.dep_ctl_id) AS dep_ctl_count,
    SUM(tc.start_balance) AS total_start_balance,
    SUM(tc.end_balance) AS total_end_balance
FROM cisadm.ci_tndr_ctl tc
LEFT JOIN cisadm.ci_tndr_srce ts
    ON ts.tndr_source_cd = tc.tndr_source_cd
LEFT JOIN cisadm.ci_tndr_srce_l tsl
    ON tsl.tndr_source_cd = tc.tndr_source_cd
   AND tsl.language_cd = 'ENG'
GROUP BY
    tc.tndr_source_cd,
    tsl.descr,
    ts.tndr_srce_type_flg
ORDER BY
    tender_control_count DESC,
    tc.tndr_source_cd;

--------------------------------------------------------------------------------
-- 9) Tender -> tender control -> deposit linkage coverage
--------------------------------------------------------------------------------
SELECT
    COUNT(*) AS tender_rows,
    COUNT(CASE WHEN pt.tndr_ctl_id IS NOT NULL THEN 1 END) AS tender_rows_with_tndr_ctl,
    COUNT(CASE WHEN tc.tndr_ctl_id IS NOT NULL THEN 1 END) AS tender_rows_joining_tndr_ctl,
    COUNT(CASE WHEN tc.dep_ctl_id IS NOT NULL THEN 1 END) AS tender_rows_with_dep_ctl,
    COUNT(CASE WHEN dc.dep_ctl_id IS NOT NULL THEN 1 END) AS tender_rows_joining_dep_ctl
FROM cisadm.ci_pay_tndr pt
LEFT JOIN cisadm.ci_tndr_ctl tc
    ON tc.tndr_ctl_id = pt.tndr_ctl_id
LEFT JOIN cisadm.ci_dep_ctl dc
    ON dc.dep_ctl_id = tc.dep_ctl_id;

--------------------------------------------------------------------------------
-- 10) Deposit control status / source-type distribution
--------------------------------------------------------------------------------
SELECT
    dc.dep_ctl_status_flg,
    dc.tndr_srce_type_flg,
    COUNT(*) AS dep_ctl_count,
    SUM(dc.end_balance) AS total_end_balance
FROM cisadm.ci_dep_ctl dc
GROUP BY
    dc.dep_ctl_status_flg,
    dc.tndr_srce_type_flg
ORDER BY
    dep_ctl_count DESC,
    dc.dep_ctl_status_flg,
    dc.tndr_srce_type_flg;

--------------------------------------------------------------------------------
-- 11) Tender deposit population
--------------------------------------------------------------------------------
SELECT
    COUNT(*) AS tndr_dep_rows,
    COUNT(DISTINCT dep_ctl_id) AS dep_ctl_count,
    SUM(deposit_amt) AS total_deposit_amt
FROM cisadm.ci_tndr_dep;

--------------------------------------------------------------------------------
-- 12) Payment-event distribution detail usage
--------------------------------------------------------------------------------
SELECT
    dst_rule_cd,
    COUNT(*) AS row_count,
    COUNT(DISTINCT pay_event_id) AS pay_event_count,
    SUM(amount) AS total_amount
FROM cisadm.ci_pevt_dst_dtl
GROUP BY dst_rule_cd
ORDER BY row_count DESC, dst_rule_cd;

--------------------------------------------------------------------------------
-- 13) Distribution-rule description coverage
--------------------------------------------------------------------------------
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN drl.descr IS NULL AND d.dst_rule_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_dst_rule_desc
FROM cisadm.ci_pevt_dst_dtl d
LEFT JOIN cisadm.ci_dst_rule_l drl
    ON drl.dst_rule_cd = d.dst_rule_cd
   AND drl.language_cd = 'ENG';

--------------------------------------------------------------------------------
-- 14) Staged tender feed usage
--------------------------------------------------------------------------------
SELECT
    pts.ext_source_id,
    aps.apay_src_cd,
    apsl.apay_src_name,
    pts.pay_tnd_stg_st_flg,
    COUNT(*) AS staged_tender_count,
    SUM(pts.tender_amt) AS total_tender_amt
FROM cisadm.ci_pay_tndr_st pts
LEFT JOIN cisadm.ci_apay_src aps
    ON aps.ext_source_id = pts.ext_source_id
LEFT JOIN cisadm.ci_apay_src_l apsl
    ON apsl.apay_src_cd = aps.apay_src_cd
   AND apsl.language_cd = 'ENG'
GROUP BY
    pts.ext_source_id,
    aps.apay_src_cd,
    apsl.apay_src_name,
    pts.pay_tnd_stg_st_flg
ORDER BY
    staged_tender_count DESC,
    pts.ext_source_id,
    aps.apay_src_cd;

--------------------------------------------------------------------------------
-- 15) APAY source configuration
--------------------------------------------------------------------------------
SELECT
    aps.apay_src_cd,
    apsl.apay_src_name,
    aps.tender_type_cd,
    ttl.descr AS tender_type_desc,
    aps.apay_rte_type_cd,
    aps.ext_source_id
FROM cisadm.ci_apay_src aps
LEFT JOIN cisadm.ci_apay_src_l apsl
    ON apsl.apay_src_cd = aps.apay_src_cd
   AND apsl.language_cd = 'ENG'
LEFT JOIN cisadm.ci_tender_type_l ttl
    ON ttl.tender_type_cd = aps.tender_type_cd
   AND ttl.language_cd = 'ENG'
ORDER BY aps.apay_src_cd;

--------------------------------------------------------------------------------
-- 16) Recent tender-source usage by month
--------------------------------------------------------------------------------
SELECT
    TRUNC(pe.pay_dt, 'MM') AS pay_month,
    tc.tndr_source_cd,
    tsl.descr AS tndr_source_desc,
    COUNT(*) AS tender_count,
    SUM(pt.tender_amt) AS total_tender_amt
FROM cisadm.ci_pay_event pe
JOIN cisadm.ci_pay_tndr pt
    ON pt.pay_event_id = pe.pay_event_id
LEFT JOIN cisadm.ci_tndr_ctl tc
    ON tc.tndr_ctl_id = pt.tndr_ctl_id
LEFT JOIN cisadm.ci_tndr_srce_l tsl
    ON tsl.tndr_source_cd = tc.tndr_source_cd
   AND tsl.language_cd = 'ENG'
WHERE pe.pay_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
GROUP BY
    TRUNC(pe.pay_dt, 'MM'),
    tc.tndr_source_cd,
    tsl.descr
ORDER BY
    pay_month DESC,
    tender_count DESC,
    tc.tndr_source_cd;

--------------------------------------------------------------------------------
-- 17) Recent OriginPay vs legacy auto-pay style activity
--------------------------------------------------------------------------------
SELECT
    x.source_family,
    COUNT(*) AS tender_count,
    COUNT(DISTINCT x.pay_event_id) AS pay_event_count,
    SUM(x.tender_amt) AS total_tender_amt,
    MIN(x.pay_dt) AS min_pay_dt,
    MAX(x.pay_dt) AS max_pay_dt
FROM (
    SELECT
        pt.pay_event_id,
        pt.tender_amt,
        pe.pay_dt,
        CASE
            WHEN pt.tender_type_cd IN ('OPCC', 'OPOC') THEN 'ORIGINPAY'
            WHEN tc.tndr_source_cd = 'ACH' THEN 'LEGACY_APAY_TNDR_SOURCE'
            WHEN pts.ext_source_id IS NOT NULL THEN 'STAGED_EXTERNAL_TENDER'
            ELSE 'OTHER'
        END AS source_family
    FROM cisadm.ci_pay_tndr pt
    JOIN cisadm.ci_pay_event pe
        ON pe.pay_event_id = pt.pay_event_id
    LEFT JOIN cisadm.ci_tndr_ctl tc
        ON tc.tndr_ctl_id = pt.tndr_ctl_id
    LEFT JOIN cisadm.ci_pay_tndr_st pts
        ON pts.pay_tender_id = pt.pay_tender_id
    WHERE pe.pay_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -24)
) x
GROUP BY x.source_family
ORDER BY total_tender_amt DESC, x.source_family;

--------------------------------------------------------------------------------
-- 18) Active account auto-pay configuration footprint
--------------------------------------------------------------------------------
SELECT
    aap.apay_src_cd,
    apsl.apay_src_name,
    COUNT(*) AS acct_apay_count
FROM cisadm.ci_acct_apay aap
LEFT JOIN cisadm.ci_apay_src_l apsl
    ON apsl.apay_src_cd = aap.apay_src_cd
   AND apsl.language_cd = 'ENG'
GROUP BY
    aap.apay_src_cd,
    apsl.apay_src_name
ORDER BY acct_apay_count DESC, aap.apay_src_cd;

--------------------------------------------------------------------------------
-- 19) Finance snapshot coverage for payment FT rows
--------------------------------------------------------------------------------
SELECT
    ft_type_flg,
    COUNT(*) AS row_count,
    COUNT(DISTINCT pay_seg_id) AS pay_seg_count,
    SUM(pay_seg_amt) AS total_pay_seg_amt
FROM cisadm.ft_gl_distribution_rpt_curr
WHERE ft_type_flg IN ('PS', 'PX')
GROUP BY ft_type_flg
ORDER BY ft_type_flg;

--------------------------------------------------------------------------------
-- 20) Direct raw FT -> payment-segment linkage population
--------------------------------------------------------------------------------
SELECT
    COUNT(*) AS ft_rows,
    COUNT(CASE WHEN pay_seg.pay_seg_id IS NOT NULL THEN 1 END) AS ft_rows_with_pay_seg,
    COUNT(DISTINCT pay_seg.pay_id) AS pay_count
FROM cisadm.ci_ft ft
LEFT JOIN cisadm.ci_pay_seg pay_seg
    ON pay_seg.pay_seg_id = ft.sibling_id
   AND pay_seg.pay_id = ft.parent_id
WHERE ft.ft_type_flg IN ('PS', 'PX');

--------------------------------------------------------------------------------
-- 21) Candidate snapshot grain scorecard
--------------------------------------------------------------------------------
SELECT *
FROM (
    SELECT
        'PAY_EVENT' AS candidate_grain,
        COUNT(*) AS row_count,
        COUNT(DISTINCT pay_event_id) AS distinct_key_count
    FROM cisadm.ci_pay_event
    UNION ALL
    SELECT
        'PAY',
        COUNT(*),
        COUNT(DISTINCT pay_id)
    FROM cisadm.ci_pay
    UNION ALL
    SELECT
        'PAY_TNDR',
        COUNT(*),
        COUNT(DISTINCT pay_tender_id)
    FROM cisadm.ci_pay_tndr
    UNION ALL
    SELECT
        'PAY_SEG',
        COUNT(*),
        COUNT(DISTINCT pay_seg_id)
    FROM cisadm.ci_pay_seg
    UNION ALL
    SELECT
        'TNDR_CTL',
        COUNT(*),
        COUNT(DISTINCT tndr_ctl_id)
    FROM cisadm.ci_tndr_ctl
    UNION ALL
    SELECT
        'DEP_CTL',
        COUNT(*),
        COUNT(DISTINCT dep_ctl_id)
    FROM cisadm.ci_dep_ctl
)
ORDER BY candidate_grain;
