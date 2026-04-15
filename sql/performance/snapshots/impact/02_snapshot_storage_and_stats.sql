-- Purpose:
--   Show table and index segment footprint for the governed snapshot tables.

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
),
table_segments AS (
    SELECT
        owner,
        segment_name AS table_name,
        SUM(bytes) AS table_bytes
    FROM all_segments
    WHERE owner = 'CISADM'
      AND segment_type IN ('TABLE', 'TABLE PARTITION', 'TABLE SUBPARTITION')
    GROUP BY
        owner,
        segment_name
),
index_segments AS (
    SELECT
        ai.table_owner AS owner,
        ai.table_name,
        COUNT(DISTINCT ai.index_name) AS index_count,
        SUM(s.bytes) AS index_bytes
    FROM all_indexes ai
    LEFT JOIN all_segments s
        ON s.owner = ai.owner
       AND s.segment_name = ai.index_name
       AND s.segment_type LIKE 'INDEX%'
    WHERE ai.table_owner = 'CISADM'
    GROUP BY
        ai.table_owner,
        ai.table_name
)
SELECT
    st.workstream,
    st.table_name,
    ROUND(NVL(ts.table_bytes, 0) / 1024 / 1024, 2) AS table_mb,
    NVL(ix.index_count, 0) AS index_count,
    ROUND(NVL(ix.index_bytes, 0) / 1024 / 1024, 2) AS index_mb,
    ROUND((NVL(ts.table_bytes, 0) + NVL(ix.index_bytes, 0)) / 1024 / 1024, 2) AS total_mb
FROM snapshot_tables st
LEFT JOIN table_segments ts
    ON ts.owner = 'CISADM'
   AND ts.table_name = st.table_name
LEFT JOIN index_segments ix
    ON ix.owner = 'CISADM'
   AND ix.table_name = st.table_name
ORDER BY
    total_mb DESC,
    st.table_name;
