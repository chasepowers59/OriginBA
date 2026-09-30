-- 4a) Manual first run (use 02a for baseline, 02 for scheduled rolling refresh)
BEGIN
    cisadm.refresh_ops_exception_rpt_curr;
END;
/

-- 4b) Snapshot population by source
SELECT
    excp_source,
    COUNT(*) AS row_count
FROM cisadm.ops_exception_rpt_curr
GROUP BY excp_source
ORDER BY excp_source;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    excp_source,
    excp_natural_key,
    COUNT(*) AS row_count
FROM cisadm.ops_exception_rpt_curr
GROUP BY
    excp_source,
    excp_natural_key
HAVING COUNT(*) > 1;

-- 4d) Source parity by exception type
SELECT COUNT(*) AS snapshot_bseg_count
FROM cisadm.ops_exception_rpt_curr
WHERE excp_source = 'BSEG';

SELECT COUNT(*) AS source_bseg_count
FROM cisadm.ci_bseg_excp;

SELECT COUNT(*) AS snapshot_usage_count
FROM cisadm.ops_exception_rpt_curr
WHERE excp_source = 'USAGE';

SELECT COUNT(*) AS source_usage_count
FROM cisadm.d1_usage_excp;

SELECT COUNT(*) AS snapshot_vee_count
FROM cisadm.ops_exception_rpt_curr
WHERE excp_source = 'VEE';

SELECT COUNT(*) AS source_vee_count
FROM cisadm.d1_vee_excp;

-- 4e) Null key check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN excp_source IS NULL OR excp_natural_key IS NULL THEN 1 ELSE 0 END) AS null_key_rows
FROM cisadm.ops_exception_rpt_curr;

-- 4f) Description coverage
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN bseg_excp_desc IS NULL AND bseg_excp_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_bseg_excp_desc,
    SUM(CASE WHEN usage_excp_type_desc IS NULL AND usage_excp_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_usage_excp_type_desc,
    SUM(CASE WHEN excp_type_desc IS NULL AND excp_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_vee_excp_type_desc,
    SUM(CASE WHEN td_type_desc IS NULL AND td_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_td_type_desc,
    SUM(CASE WHEN td_entry_status_desc IS NULL AND td_entry_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_td_status_desc
FROM cisadm.ops_exception_rpt_curr;

-- 4g) Open exception profile
SELECT
    excp_source,
    SUM(CASE
        WHEN excp_source = 'BSEG' AND NVL(bseg_review_comp, 'N') <> 'Y' THEN 1
        WHEN excp_source IN ('USAGE', 'VEE') AND open_close_flg = 'O' THEN 1
        ELSE 0
    END) AS open_exception_count,
    COUNT(*) AS total_count
FROM cisadm.ops_exception_rpt_curr
GROUP BY excp_source
ORDER BY excp_source;

-- 4h) To-do linkage profile (one ranked TD per driver key)
SELECT
    excp_source,
    SUM(CASE WHEN td_entry_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_td,
    COUNT(*) AS total_rows
FROM cisadm.ops_exception_rpt_curr
GROUP BY excp_source
ORDER BY excp_source;

-- 4i) Rolling-window retention sanity (closed exceptions older than 6 months)
SELECT COUNT(*) AS stale_closed_exceptions_still_present
FROM cisadm.ops_exception_rpt_curr snap
WHERE snap.excp_cre_dttm < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
  AND NVL(snap.bseg_review_comp, 'N') = 'Y'
  AND NVL(snap.open_close_flg, 'C') <> 'O'
  AND NVL(snap.td_entry_status_flg, 'C') <> 'O';

-- 4j) Spot-check open usage exceptions
SELECT *
FROM (
    SELECT *
    FROM cisadm.ops_exception_rpt_curr
    WHERE excp_source = 'USAGE'
      AND open_close_flg = 'O'
    ORDER BY excp_cre_dttm DESC
)
WHERE ROWNUM <= 10;

-- 4k) Spot-check unreviewed bill segment exceptions
SELECT *
FROM (
    SELECT *
    FROM cisadm.ops_exception_rpt_curr
    WHERE excp_source = 'BSEG'
      AND NVL(bseg_review_comp, 'N') <> 'Y'
    ORDER BY excp_cre_dttm DESC
)
WHERE ROWNUM <= 10;
