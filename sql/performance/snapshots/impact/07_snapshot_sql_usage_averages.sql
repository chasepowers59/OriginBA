-- Purpose:
--   Measure observed SQL workload against snapshot tables using average-per-execution
--   metrics from V$SQLAREA.
--
-- Use this when:
--   - estimating user/query pressure by snapshot table
--   - comparing average elapsed time, CPU time, logical reads, and physical reads
--   - identifying which governed snapshots drive the heaviest observed demand
--
-- Notes:
--   - results reflect the current SQL cache/history available through V$SQLAREA
--   - these are observed averages per execution, not theoretical estimates
--   - low-observed-usage rows should be treated as sample-limited, not intrinsically cheap
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
        s.sql_id,
        s.executions,
        s.elapsed_time,
        s.cpu_time,
        s.buffer_gets,
        s.disk_reads
    FROM snapshot_map m
    JOIN v$sqlarea s
      ON LOWER(s.sql_text) LIKE '%' || LOWER(m.table_name) || '%'
    WHERE NVL(s.executions, 0) > 0
)
SELECT
    workstream,
    table_name,
    COUNT(*) AS matching_sql_rows,
    SUM(executions) AS total_executions,
    ROUND(SUM(elapsed_time) / 1000000, 2) AS total_elapsed_seconds,
    ROUND(SUM(cpu_time) / 1000000, 2) AS total_cpu_seconds,
    ROUND(SUM(buffer_gets) / 1000000, 2) AS total_buffer_gets_millions,
    ROUND(SUM(disk_reads) / 1000000, 2) AS total_disk_reads_millions,
    ROUND((SUM(elapsed_time) / 1000000) / NULLIF(SUM(executions), 0), 2) AS avg_elapsed_seconds_per_exec,
    ROUND((SUM(cpu_time) / 1000000) / NULLIF(SUM(executions), 0), 2) AS avg_cpu_seconds_per_exec,
    ROUND(SUM(buffer_gets) / NULLIF(SUM(executions), 0), 2) AS avg_buffer_gets_per_exec,
    ROUND(SUM(disk_reads) / NULLIF(SUM(executions), 0), 2) AS avg_disk_reads_per_exec
FROM matched_sql
GROUP BY
    workstream,
    table_name
ORDER BY
    avg_elapsed_seconds_per_exec DESC NULLS LAST,
    avg_cpu_seconds_per_exec DESC NULLS LAST,
    avg_disk_reads_per_exec DESC NULLS LAST;
