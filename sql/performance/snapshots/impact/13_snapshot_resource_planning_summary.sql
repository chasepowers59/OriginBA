-- Purpose:
--   Produce a single summary view combining observed SQL averages and storage footprint
--   for high-level resource planning.
--
-- Use this when:
--   - preparing client/internal capacity discussions
--   - ranking snapshots by average CPU, read pressure, and storage
--   - building a one-page summary after running the detailed tests
--
-- Notes:
--   - this depends on V$SQLAREA visibility for observed query usage
--   - storage is drawn from ALL_SEGMENTS and ALL_INDEXES

WITH snapshot_map AS (
    SELECT 'billing' AS workstream, 'BSEG_BILLED_USAGE_RPT_CURR' AS snapshot_table_name FROM dual UNION ALL
    SELECT 'billing', 'BSEG_SQ_USAGE_RPT_CURR' FROM dual UNION ALL
    SELECT 'finance', 'FT_RPT_CURR' FROM dual UNION ALL
    SELECT 'finance', 'FT_GL_DISTRIBUTION_RPT_CURR' FROM dual UNION ALL
    SELECT 'debt_mgmt', 'ACCT_DEBT_RPT_CURR' FROM dual UNION ALL
    SELECT 'debt_mgmt', 'COLL_PROC_RPT_CURR' FROM dual UNION ALL
    SELECT 'meter_ops', 'D1_USAGE_RPT_CURR' FROM dual UNION ALL
    SELECT 'meter_ops', 'D1_USAGE_SCALAR_DTL_RPT_CURR' FROM dual UNION ALL
    SELECT 'meter_ops', 'D1_MSRMT_RPT_CURR' FROM dual UNION ALL
    SELECT 'payments_cashiering', 'PAY_TNDR_CASH_RPT_CURR' FROM dual
),
sql_usage AS (
    SELECT
        m.workstream,
        m.snapshot_table_name,
        SUM(s.executions) AS total_execs,
        SUM(s.elapsed_time) / 1000000 AS total_elapsed_seconds,
        SUM(s.cpu_time) / 1000000 AS total_cpu_seconds,
        SUM(s.buffer_gets) AS total_buffer_gets,
        SUM(s.disk_reads) AS total_disk_reads
    FROM snapshot_map m
    JOIN v$sqlarea s
      ON LOWER(s.sql_text) LIKE '%' || LOWER(m.snapshot_table_name) || '%'
    WHERE NVL(s.executions, 0) > 0
    GROUP BY m.workstream, m.snapshot_table_name
),
table_seg AS (
    SELECT
        s.segment_name AS snapshot_table_name,
        SUM(s.bytes) / 1024 / 1024 AS table_mb
    FROM all_segments s
    JOIN snapshot_map t
      ON t.snapshot_table_name = s.segment_name
    WHERE s.owner = 'CISADM'
      AND s.segment_type IN ('TABLE', 'TABLE PARTITION', 'TABLE SUBPARTITION')
    GROUP BY s.segment_name
),
index_seg AS (
    SELECT
        i.table_name AS snapshot_table_name,
        SUM(s.bytes) / 1024 / 1024 AS index_mb
    FROM all_indexes i
    JOIN all_segments s
      ON s.owner = i.owner
     AND s.segment_name = i.index_name
    JOIN snapshot_map t
      ON t.snapshot_table_name = i.table_name
    WHERE i.owner = 'CISADM'
    GROUP BY i.table_name
)
SELECT
    m.workstream,
    m.snapshot_table_name AS table_name,
    NVL(u.total_execs, 0) AS total_execs,
    ROUND(NVL(u.total_elapsed_seconds, 0) / NULLIF(u.total_execs, 0), 2) AS avg_elapsed_sec_per_exec,
    ROUND(NVL(u.total_cpu_seconds, 0) / NULLIF(u.total_execs, 0), 2) AS avg_cpu_sec_per_exec,
    ROUND(NVL(u.total_buffer_gets, 0) / NULLIF(u.total_execs, 0), 2) AS avg_buffer_gets_per_exec,
    ROUND(NVL(u.total_disk_reads, 0) / NULLIF(u.total_execs, 0), 2) AS avg_disk_reads_per_exec,
    ROUND(NVL(ts.table_mb, 0), 2) AS table_mb,
    ROUND(NVL(ix.index_mb, 0), 2) AS index_mb,
    ROUND(NVL(ts.table_mb, 0) + NVL(ix.index_mb, 0), 2) AS total_storage_mb
FROM snapshot_map m
LEFT JOIN sql_usage u
  ON u.workstream = m.workstream
 AND u.snapshot_table_name = m.snapshot_table_name
LEFT JOIN table_seg ts
  ON ts.snapshot_table_name = m.snapshot_table_name
LEFT JOIN index_seg ix
  ON ix.snapshot_table_name = m.snapshot_table_name
ORDER BY
    avg_cpu_sec_per_exec DESC NULLS LAST,
    avg_disk_reads_per_exec DESC NULLS LAST,
    total_storage_mb DESC NULLS LAST;
