-- 09_assert_zero_diff_samples.sql
-- Read-only gate: sample USG_EXT_ID check must have zero differences.
-- Required vars:
--   define start_ts = 2026-01-01
--   define end_ts   = 2026-01-08

set pagesize 50000
set linesize 220
set trimspool on

WITH sample_ids AS (
  SELECT d1.usg_ext_id
  FROM CISADM.D1_USAGE d1
  WHERE d1.start_dttm >= TO_DATE('&start_ts','YYYY-MM-DD')
    AND d1.start_dttm <  TO_DATE('&end_ts','YYYY-MM-DD')
    AND d1.bo_status_cd = 'SENT'
  ORDER BY d1.usg_ext_id
  FETCH FIRST 5 ROWS ONLY
),
raw_qty AS (
  SELECT d1.usg_ext_id, NVL(SUM(sd.quantity),0) AS raw_qty
  FROM CISADM.D1_USAGE d1
  LEFT JOIN CISADM.D1_USAGE_SCALAR_DTL sd
    ON d1.d1_usage_id = sd.d1_usage_id
  WHERE d1.usg_ext_id IN (SELECT usg_ext_id FROM sample_ids)
  GROUP BY d1.usg_ext_id
),
optimized_qty AS (
  WITH scalar_per_usage AS (
    SELECT d1_usage_id, NVL(SUM(quantity),0) AS qty_per_usage
    FROM CISADM.D1_USAGE_SCALAR_DTL
    GROUP BY d1_usage_id
  )
  SELECT d1.usg_ext_id, NVL(SUM(spu.qty_per_usage),0) AS optimized_qty
  FROM CISADM.D1_USAGE d1
  LEFT JOIN scalar_per_usage spu
    ON d1.d1_usage_id = spu.d1_usage_id
  WHERE d1.usg_ext_id IN (SELECT usg_ext_id FROM sample_ids)
  GROUP BY d1.usg_ext_id
),
diffs AS (
  SELECT
    s.usg_ext_id,
    NVL(o.optimized_qty,0) - NVL(r.raw_qty,0) AS difference
  FROM sample_ids s
  LEFT JOIN raw_qty r ON s.usg_ext_id = r.usg_ext_id
  LEFT JOIN optimized_qty o ON s.usg_ext_id = o.usg_ext_id
)
SELECT
  'SAMPLE_ZERO_DIFF_GATE' AS gate_name,
  CASE WHEN SUM(CASE WHEN difference <> 0 THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END AS gate_status,
  SUM(CASE WHEN difference <> 0 THEN 1 ELSE 0 END) AS mismatch_rows
FROM diffs;

WITH sample_ids AS (
  SELECT d1.usg_ext_id
  FROM CISADM.D1_USAGE d1
  WHERE d1.start_dttm >= TO_DATE('&start_ts','YYYY-MM-DD')
    AND d1.start_dttm <  TO_DATE('&end_ts','YYYY-MM-DD')
    AND d1.bo_status_cd = 'SENT'
  ORDER BY d1.usg_ext_id
  FETCH FIRST 5 ROWS ONLY
),
raw_qty AS (
  SELECT d1.usg_ext_id, NVL(SUM(sd.quantity),0) AS raw_qty
  FROM CISADM.D1_USAGE d1
  LEFT JOIN CISADM.D1_USAGE_SCALAR_DTL sd
    ON d1.d1_usage_id = sd.d1_usage_id
  WHERE d1.usg_ext_id IN (SELECT usg_ext_id FROM sample_ids)
  GROUP BY d1.usg_ext_id
),
optimized_qty AS (
  WITH scalar_per_usage AS (
    SELECT d1_usage_id, NVL(SUM(quantity),0) AS qty_per_usage
    FROM CISADM.D1_USAGE_SCALAR_DTL
    GROUP BY d1_usage_id
  )
  SELECT d1.usg_ext_id, NVL(SUM(spu.qty_per_usage),0) AS optimized_qty
  FROM CISADM.D1_USAGE d1
  LEFT JOIN scalar_per_usage spu
    ON d1.d1_usage_id = spu.d1_usage_id
  WHERE d1.usg_ext_id IN (SELECT usg_ext_id FROM sample_ids)
  GROUP BY d1.usg_ext_id
),
diffs AS (
  SELECT
    s.usg_ext_id,
    NVL(o.optimized_qty,0) - NVL(r.raw_qty,0) AS difference
  FROM sample_ids s
  LEFT JOIN raw_qty r ON s.usg_ext_id = r.usg_ext_id
  LEFT JOIN optimized_qty o ON s.usg_ext_id = o.usg_ext_id
)
SELECT 1 / CASE WHEN SUM(CASE WHEN difference <> 0 THEN 1 ELSE 0 END) = 0 THEN 1 ELSE 0 END AS assert_sample_zero_diff
FROM diffs;
