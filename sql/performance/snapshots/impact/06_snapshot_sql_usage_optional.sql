-- 2026-09-08: ACCT_DEBT, COLL_PROC and PAY_TNDR_CASH removed from the list (archived; not part of the active-8).
-- Purpose:
--   Optional SQL usage check for snapshot tables using V$SQLAREA.
--
-- Requirements:
--   - access to V$SQLAREA or equivalent catalog views
--   - SQL text retention sufficient to observe snapshot usage

WITH snapshot_tables AS (
    SELECT 'billing' AS workstream, 'BSEG_BILLED_USAGE_RPT_CURR' AS table_name FROM dual UNION ALL
    SELECT 'billing', 'BSEG_SQ_USAGE_RPT_CURR' FROM dual UNION ALL
    SELECT 'finance', 'FT_RPT_CURR' FROM dual UNION ALL
    SELECT 'finance', 'FT_GL_DISTRIBUTION_RPT_CURR' FROM dual UNION ALL
    SELECT 'meter_ops', 'D1_USAGE_RPT_CURR' FROM dual UNION ALL
    SELECT 'meter_ops', 'D1_USAGE_SCALAR_DTL_RPT_CURR' FROM dual UNION ALL
    SELECT 'meter_ops', 'D1_MSRMT_RPT_CURR' FROM dual
)
SELECT
    st.workstream,
    st.table_name,
    COUNT(*) AS matching_sql_rows,
    SUM(NVL(v.executions, 0)) AS total_executions,
    ROUND(SUM(NVL(v.elapsed_time, 0)) / 1000000, 2) AS total_elapsed_seconds,
    ROUND(SUM(NVL(v.buffer_gets, 0)) / 1000000, 2) AS total_buffer_gets_millions,
    ROUND(SUM(NVL(v.disk_reads, 0)) / 1000000, 2) AS total_disk_reads_millions
FROM snapshot_tables st
JOIN v$sqlarea v
    ON UPPER(v.sql_text) LIKE '%' || st.table_name || '%'
GROUP BY
    st.workstream,
    st.table_name
ORDER BY
    total_elapsed_seconds DESC NULLS LAST,
    total_executions DESC NULLS LAST;
