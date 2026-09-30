-- 4a) Manual first run (use 02a for baseline, 02 for scheduled rolling refresh)
BEGIN
    cisadm.refresh_crew_ops_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. representative source population)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.crew_ops_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.c1_representative rep
INNER JOIN cisadm.cms_c1_representative_boda_vw boda
    ON boda.c1_representative_cd = rep.c1_representative_cd;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    crew_id,
    COUNT(*) AS row_count
FROM cisadm.crew_ops_rpt_curr
GROUP BY crew_id
HAVING COUNT(*) > 1;

-- 4d) Rolling window coverage (6-month policy on linked field-activity dates)
SELECT
    MIN(latest_fa_cre_dttm) AS min_latest_fa_cre_dttm,
    MAX(latest_fa_cre_dttm) AS max_latest_fa_cre_dttm,
    COUNT(*) AS row_count
FROM cisadm.crew_ops_rpt_curr;

SELECT
    COUNT(*) AS crews_with_no_recent_fa_in_rolling_mode
FROM cisadm.crew_ops_rpt_curr snap
WHERE NOT EXISTS (
    SELECT 1
    FROM cisadm.d1_activity_char ch
    INNER JOIN cisadm.d1_activity act
        ON act.d1_activity_id = ch.d1_activity_id
    INNER JOIN cisadm.d1_activity_type act_type
        ON act_type.activity_type_cd = act.activity_type_cd
       AND act_type.activity_type_cat_flg = 'D1FA'
    WHERE ch.char_type_cd = 'CMFAREP'
      AND ch.srch_char_val = snap.crew_id
      AND (
          act.cre_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
          OR act.start_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
          OR act.status_upd_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
          OR act.end_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
      )
);

-- 4e) Null coverage check for governed descriptions
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN crew_name IS NULL THEN 1 ELSE 0 END) AS missing_crew_name,
    SUM(CASE WHEN crew_type_desc IS NULL AND crew_type_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_crew_type_desc,
    SUM(CASE WHEN bo_status_desc IS NULL AND bo_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bo_status_desc,
    SUM(CASE WHEN nt_xid_desc IS NULL AND nt_xid_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_nt_xid_desc,
    SUM(CASE WHEN latest_fa_status_desc IS NULL AND latest_fa_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_latest_fa_status_desc,
    SUM(CASE WHEN latest_fa_type_desc IS NULL AND latest_fa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_latest_fa_type_desc
FROM cisadm.crew_ops_rpt_curr;

-- 4f) Crew status profile
SELECT
    bo_status_cd,
    bo_status_desc,
    crew_type_flg,
    crew_type_desc,
    COUNT(*) AS crew_count
FROM cisadm.crew_ops_rpt_curr
GROUP BY
    bo_status_cd,
    bo_status_desc,
    crew_type_flg,
    crew_type_desc
ORDER BY
    crew_count DESC,
    bo_status_cd,
    crew_type_flg;

-- 4g) Field-activity rollup reconciliation
SELECT
    SUM(fa_activity_count) AS snap_total_fa_count,
    SUM(completed_fa_count) AS snap_completed_fa_count,
    SUM(open_fa_count) AS snap_open_fa_count
FROM cisadm.crew_ops_rpt_curr;

WITH fa_crew_link AS (
    SELECT
        ch.srch_char_val AS crew_id,
        act.d1_activity_id,
        CASE
            WHEN act.bo_status_cd IN ('COMPLETED', 'DISCARDED') THEN 1
            ELSE 0
        END AS is_completed
    FROM cisadm.d1_activity_char ch
    INNER JOIN cisadm.d1_activity act
        ON act.d1_activity_id = ch.d1_activity_id
    INNER JOIN cisadm.d1_activity_type act_type
        ON act_type.activity_type_cd = act.activity_type_cd
       AND act_type.activity_type_cat_flg = 'D1FA'
    WHERE ch.char_type_cd = 'CMFAREP'
)
SELECT
    COUNT(DISTINCT crew_id || '|' || d1_activity_id) AS src_total_fa_links,
    COUNT(DISTINCT CASE WHEN is_completed = 1 THEN crew_id || '|' || d1_activity_id END) AS src_completed_fa_links,
    COUNT(DISTINCT CASE WHEN is_completed = 0 THEN crew_id || '|' || d1_activity_id END) AS src_open_fa_links
FROM fa_crew_link;

-- 4h) Rollup integrity checks
SELECT
    COUNT(*) AS rows_where_completed_plus_open_exceeds_total
FROM cisadm.crew_ops_rpt_curr
WHERE NVL(completed_fa_count, 0) + NVL(open_fa_count, 0) > NVL(fa_activity_count, 0);

SELECT
    COUNT(*) AS rows_with_fa_count_but_no_latest_fa
FROM cisadm.crew_ops_rpt_curr
WHERE NVL(fa_activity_count, 0) > 0
  AND latest_fa_id IS NULL;

-- 4i) Service-area / capability profile
SELECT
    svc_area,
    worker_capability,
    COUNT(*) AS crew_count,
    SUM(NVL(open_fa_count, 0)) AS total_open_fa_count
FROM cisadm.crew_ops_rpt_curr
GROUP BY
    svc_area,
    worker_capability
ORDER BY
    total_open_fa_count DESC NULLS LAST,
    crew_count DESC;

-- 4j) Spot-check busiest crews
SELECT *
FROM (
    SELECT
        crew_id,
        crew_name,
        svc_area,
        worker_capability,
        fa_activity_count,
        completed_fa_count,
        open_fa_count,
        oldest_open_fa_days,
        latest_fa_id,
        latest_fa_status_desc,
        latest_fa_type_desc
    FROM cisadm.crew_ops_rpt_curr
    ORDER BY open_fa_count DESC NULLS LAST, fa_activity_count DESC, crew_id
)
WHERE ROWNUM <= 25;
