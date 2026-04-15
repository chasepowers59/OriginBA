-- Purpose:
--   Cross-validate usage status values in the lean snapshot against raw D1_USAGE.
--
-- Use this when:
--   - users see unexpected non-SENT usage transactions in D1_USAGE_RPT_CURR
--   - you need to prove whether the snapshot is faithfully preserving raw status
--   - you want a recent-month trend and bridge impact view for status populations

-- 5a) Raw D1_USAGE status distribution
SELECT
    u.bo_status_cd,
    COUNT(*) AS raw_usage_rows
FROM cisadm.d1_usage u
GROUP BY
    u.bo_status_cd
ORDER BY
    raw_usage_rows DESC,
    u.bo_status_cd;

-- 5b) Snapshot status distribution
SELECT
    s.bo_status_cd,
    s.bo_status_desc,
    COUNT(*) AS snapshot_usage_rows
FROM cisadm.d1_usage_rpt_curr s
GROUP BY
    s.bo_status_cd,
    s.bo_status_desc
ORDER BY
    snapshot_usage_rows DESC,
    s.bo_status_cd;

-- 5c) Raw vs snapshot parity by status code
WITH
raw_status AS (
    SELECT
        u.bo_status_cd,
        COUNT(*) AS raw_usage_rows
    FROM cisadm.d1_usage u
    GROUP BY
        u.bo_status_cd
),
snap_status AS (
    SELECT
        s.bo_status_cd,
        COUNT(*) AS snapshot_usage_rows
    FROM cisadm.d1_usage_rpt_curr s
    GROUP BY
        s.bo_status_cd
)
SELECT
    COALESCE(raw_status.bo_status_cd, snap_status.bo_status_cd) AS bo_status_cd,
    NVL(raw_status.raw_usage_rows, 0) AS raw_usage_rows,
    NVL(snap_status.snapshot_usage_rows, 0) AS snapshot_usage_rows,
    NVL(snap_status.snapshot_usage_rows, 0) - NVL(raw_status.raw_usage_rows, 0) AS snapshot_minus_raw
FROM raw_status
FULL OUTER JOIN snap_status
    ON snap_status.bo_status_cd = raw_status.bo_status_cd
ORDER BY
    raw_usage_rows DESC,
    bo_status_cd;

-- 5d) Recent monthly raw status trend
SELECT
    TRUNC(NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)), 'MM') AS usage_month,
    u.bo_status_cd,
    COUNT(*) AS raw_usage_rows
FROM cisadm.d1_usage u
WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
GROUP BY
    TRUNC(NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)), 'MM'),
    u.bo_status_cd
ORDER BY
    usage_month DESC,
    raw_usage_rows DESC,
    u.bo_status_cd;

-- 5e) Recent monthly snapshot status trend
SELECT
    TRUNC(NVL(s.start_dttm, NVL(s.usage_cre_dttm, s.status_upd_dttm)), 'MM') AS usage_month,
    s.bo_status_cd,
    s.bo_status_desc,
    COUNT(*) AS snapshot_usage_rows
FROM cisadm.d1_usage_rpt_curr s
WHERE NVL(s.start_dttm, NVL(s.usage_cre_dttm, s.status_upd_dttm)) >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
GROUP BY
    TRUNC(NVL(s.start_dttm, NVL(s.usage_cre_dttm, s.status_upd_dttm)), 'MM'),
    s.bo_status_cd,
    s.bo_status_desc
ORDER BY
    usage_month DESC,
    snapshot_usage_rows DESC,
    s.bo_status_cd;

-- 5f) Status by billing bridge coverage in the snapshot
SELECT
    s.bo_status_cd,
    s.bo_status_desc,
    NVL(s.bridge_method, 'NO_C1_MATCH') AS bridge_method,
    COUNT(*) AS usage_rows
FROM cisadm.d1_usage_rpt_curr s
GROUP BY
    s.bo_status_cd,
    s.bo_status_desc,
    NVL(s.bridge_method, 'NO_C1_MATCH')
ORDER BY
    s.bo_status_cd,
    usage_rows DESC,
    bridge_method;

-- 5g) Recent non-SENT raw examples
SELECT *
FROM (
    SELECT
        u.d1_usage_id,
        u.us_id,
        u.usg_ext_id,
        u.bo_status_cd,
        u.bo_status_reason_cd,
        u.start_dttm,
        u.end_dttm,
        u.status_upd_dttm,
        u.cre_dttm,
        u.usg_grp_cd,
        u.d1_usg_cal_type_cd,
        u.usg_src_flg,
        u.d1_spr_cd,
        u.msrmt_cyc_cd,
        u.msrmt_cyc_rte_cd,
        u.used_on_bill_flg,
        u.linked_to_frzn_bseg_flg
    FROM cisadm.d1_usage u
    WHERE NVL(TRIM(u.bo_status_cd), '~') <> 'SENT'
    ORDER BY
        NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) DESC,
        u.d1_usage_id
)
WHERE ROWNUM <= 50;

-- 5h) Matching snapshot examples for non-SENT rows
SELECT *
FROM (
    SELECT
        s.d1_usage_id,
        s.us_id,
        s.usg_ext_id,
        s.bo_status_cd,
        s.bo_status_desc,
        s.bo_status_reason_cd,
        s.start_dttm,
        s.end_dttm,
        s.status_upd_dttm,
        s.usage_cre_dttm,
        s.usg_grp_cd,
        s.usg_grp_desc,
        s.d1_usg_cal_type_cd,
        s.d1_usg_cal_type_desc,
        s.usg_src_flg,
        s.usg_src_desc,
        s.d1_spr_cd,
        s.d1_spr_desc,
        s.msrmt_cyc_cd,
        s.msrmt_cyc_rte_cd,
        s.used_on_bill_flg,
        s.linked_to_frzn_bseg_flg,
        s.bridge_method,
        s.c1_usage_id,
        s.sa_id,
        s.acct_id,
        s.cust_cl_desc,
        s.prem_id
    FROM cisadm.d1_usage_rpt_curr s
    WHERE NVL(TRIM(s.bo_status_cd), '~') <> 'SENT'
    ORDER BY
        NVL(s.start_dttm, NVL(s.usage_cre_dttm, s.status_upd_dttm)) DESC,
        s.d1_usage_id
)
WHERE ROWNUM <= 50;

-- 5i) Direct raw-to-snapshot row check for non-SENT statuses
SELECT
    u.bo_status_cd,
    COUNT(*) AS matched_rows
FROM cisadm.d1_usage u
JOIN cisadm.d1_usage_rpt_curr s
    ON s.d1_usage_id = u.d1_usage_id
   AND NVL(s.bo_status_cd, '~') = NVL(u.bo_status_cd, '~')
WHERE NVL(TRIM(u.bo_status_cd), '~') <> 'SENT'
GROUP BY
    u.bo_status_cd
ORDER BY
    matched_rows DESC,
    u.bo_status_cd;
