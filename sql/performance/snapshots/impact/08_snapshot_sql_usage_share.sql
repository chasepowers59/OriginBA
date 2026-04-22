-- Purpose:
--   Measure each snapshot table's observed share of CPU, logical I/O, and physical I/O
--   within the governed snapshot family.
--
-- Use this when:
--   - comparing relative demand across workstreams
--   - identifying which snapshots dominate CPU or read pressure
--   - supporting capacity planning with observed workload share
--
-- Notes:
--   - results are relative to the observed SQL sample in V$SQLAREA
--   - share percentages are only as complete as the available cache/history
--
-- Requirements:
--   - read access to V$SQLAREA

WITH snapshot_map AS (
    SELECT 'billing' AS workstream, 'BSEG_BILLED_USAGE_RPT_CURR' AS table_name FROM dual UNION ALL
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
matched_sql AS (
    SELECT
        m.workstream,
        m.table_name,
        s.executions,
        s.elapsed_time,
        s.cpu_time,
        s.buffer_gets,
        s.disk_reads
    FROM snapshot_map m
    JOIN v$sqlarea s
      ON LOWER(s.sql_text) LIKE '%' || LOWER(m.table_name) || '%'
    WHERE NVL(s.executions, 0) > 0
),
agg AS (
    SELECT
        workstream,
        table_name,
        SUM(executions) AS total_executions,
        SUM(elapsed_time) / 1000000 AS total_elapsed_seconds,
        SUM(cpu_time) / 1000000 AS total_cpu_seconds,
        SUM(buffer_gets) AS total_buffer_gets,
        SUM(disk_reads) AS total_disk_reads
    FROM matched_sql
    GROUP BY workstream, table_name
)
SELECT
    workstream,
    table_name,
    total_executions,
    ROUND(total_elapsed_seconds, 2) AS total_elapsed_seconds,
    ROUND(total_cpu_seconds, 2) AS total_cpu_seconds,
    ROUND(total_buffer_gets / 1000000, 2) AS total_buffer_gets_millions,
    ROUND(total_disk_reads / 1000000, 2) AS total_disk_reads_millions,
    ROUND(100 * total_cpu_seconds / NULLIF(SUM(total_cpu_seconds) OVER (), 0), 2) AS cpu_share_pct,
    ROUND(100 * total_buffer_gets / NULLIF(SUM(total_buffer_gets) OVER (), 0), 2) AS logical_io_share_pct,
    ROUND(100 * total_disk_reads / NULLIF(SUM(total_disk_reads) OVER (), 0), 2) AS physical_io_share_pct
FROM agg
ORDER BY
    cpu_share_pct DESC NULLS LAST,
    physical_io_share_pct DESC NULLS LAST,
    logical_io_share_pct DESC NULLS LAST;
