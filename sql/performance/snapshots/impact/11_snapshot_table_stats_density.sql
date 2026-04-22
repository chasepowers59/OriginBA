-- Purpose:
--   Review Oracle table stats for governed snapshots, including estimated data size
--   from row count and average row length.
--
-- Use this when:
--   - approximating data density
--   - comparing estimated payload size across snapshots
--   - validating that optimizer stats exist and are reasonably current

WITH snapshot_tables AS (
    SELECT 'BSEG_BILLED_USAGE_RPT_CURR' AS snapshot_table_name FROM dual UNION ALL
    SELECT 'BSEG_SQ_USAGE_RPT_CURR' FROM dual UNION ALL
    SELECT 'FT_RPT_CURR' FROM dual UNION ALL
    SELECT 'FT_GL_DISTRIBUTION_RPT_CURR' FROM dual UNION ALL
    SELECT 'ACCT_DEBT_RPT_CURR' FROM dual UNION ALL
    SELECT 'COLL_PROC_RPT_CURR' FROM dual UNION ALL
    SELECT 'D1_USAGE_RPT_CURR' FROM dual UNION ALL
    SELECT 'D1_USAGE_SCALAR_DTL_RPT_CURR' FROM dual UNION ALL
    SELECT 'D1_MSRMT_RPT_CURR' FROM dual UNION ALL
    SELECT 'PAY_TNDR_CASH_RPT_CURR' FROM dual
)
SELECT
    t.snapshot_table_name AS table_name,
    at.num_rows,
    at.avg_row_len,
    at.blocks,
    at.last_analyzed,
    ROUND((NVL(at.num_rows, 0) * NVL(at.avg_row_len, 0)) / 1024 / 1024, 2) AS estimated_data_mb
FROM snapshot_tables t
LEFT JOIN all_tables at
  ON at.owner = 'CISADM'
 AND at.table_name = t.snapshot_table_name
ORDER BY estimated_data_mb DESC NULLS LAST, t.snapshot_table_name;
