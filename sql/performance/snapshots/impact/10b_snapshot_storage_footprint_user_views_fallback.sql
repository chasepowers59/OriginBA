-- Purpose:
--   Fallback exact storage-footprint query for sessions connected directly as the
--   owning schema, typically CISADM, when ALL_SEGMENTS / ALL_INDEXES are not accessible.
--
-- Use this when:
--   - 10_snapshot_storage_footprint_summary.sql fails with ORA-00942 on ALL_SEGMENTS
--   - the session is connected as CISADM or another owner of the snapshot tables
--
-- Notes:
--   - if run from a non-owning schema, USER_SEGMENTS and USER_INDEXES will usually return
--     only objects in the current schema and may produce empty results

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
),
table_seg AS (
    SELECT
        s.segment_name AS snapshot_table_name,
        SUM(s.bytes) / 1024 / 1024 AS table_mb
    FROM user_segments s
    JOIN snapshot_tables t
      ON t.snapshot_table_name = s.segment_name
    WHERE s.segment_type IN ('TABLE', 'TABLE PARTITION', 'TABLE SUBPARTITION')
    GROUP BY s.segment_name
),
index_seg AS (
    SELECT
        i.table_name AS snapshot_table_name,
        SUM(s.bytes) / 1024 / 1024 AS index_mb
    FROM user_indexes i
    JOIN user_segments s
      ON s.segment_name = i.index_name
    JOIN snapshot_tables t
      ON t.snapshot_table_name = i.table_name
    GROUP BY i.table_name
)
SELECT
    t.snapshot_table_name AS table_name,
    ROUND(NVL(ts.table_mb, 0), 2) AS table_mb,
    ROUND(NVL(ix.index_mb, 0), 2) AS index_mb,
    ROUND(NVL(ts.table_mb, 0) + NVL(ix.index_mb, 0), 2) AS total_mb
FROM snapshot_tables t
LEFT JOIN table_seg ts
  ON ts.snapshot_table_name = t.snapshot_table_name
LEFT JOIN index_seg ix
  ON ix.snapshot_table_name = t.snapshot_table_name
ORDER BY total_mb DESC, t.snapshot_table_name;
