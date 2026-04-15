-- Purpose:
--   Inventory the governed snapshot tables and show basic object and stats state.

WITH snapshot_tables AS (
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
)
SELECT
    st.workstream,
    st.table_name,
    o.status AS object_status,
    t.num_rows,
    t.blocks,
    t.avg_row_len,
    ROUND(NVL(t.num_rows, 0) * NVL(t.avg_row_len, 0) / 1024 / 1024, 2) AS est_table_mb_from_stats,
    t.last_analyzed
FROM snapshot_tables st
LEFT JOIN all_objects o
    ON o.owner = 'CISADM'
   AND o.object_name = st.table_name
   AND o.object_type = 'TABLE'
LEFT JOIN all_tables t
    ON t.owner = 'CISADM'
   AND t.table_name = st.table_name
ORDER BY
    st.workstream,
    st.table_name;
