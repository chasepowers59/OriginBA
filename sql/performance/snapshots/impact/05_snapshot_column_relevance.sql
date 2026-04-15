-- Purpose:
--   Use table and column stats to flag sparse or low-value columns for review.
--
-- Notes:
--   - This depends on current optimizer stats.
--   - It is a review aid, not an automatic delete list.

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
col_profile AS (
    SELECT
        st.workstream,
        c.table_name,
        c.column_id,
        c.column_name,
        c.data_type,
        t.num_rows,
        cs.num_nulls,
        cs.num_distinct,
        cs.avg_col_len,
        cs.last_analyzed,
        CASE
            WHEN NVL(t.num_rows, 0) > 0 AND cs.num_nulls IS NOT NULL
            THEN ROUND(cs.num_nulls / t.num_rows * 100, 2)
        END AS null_pct,
        CASE
            WHEN NVL(t.num_rows, 0) > 0 AND cs.num_distinct IS NOT NULL
            THEN ROUND(cs.num_distinct / t.num_rows * 100, 4)
        END AS distinct_pct
    FROM snapshot_tables st
    JOIN all_tab_columns c
        ON c.owner = 'CISADM'
       AND c.table_name = st.table_name
    LEFT JOIN all_tables t
        ON t.owner = 'CISADM'
       AND t.table_name = st.table_name
    LEFT JOIN all_tab_col_statistics cs
        ON cs.owner = 'CISADM'
       AND cs.table_name = c.table_name
       AND cs.column_name = c.column_name
)
SELECT
    workstream,
    table_name,
    column_id,
    column_name,
    data_type,
    num_rows,
    num_nulls,
    null_pct,
    num_distinct,
    distinct_pct,
    avg_col_len,
    last_analyzed,
    CASE
        WHEN NVL(num_rows, 0) > 0 AND NVL(num_nulls, 0) = num_rows THEN 'ALL_NULL_REVIEW'
        WHEN null_pct >= 95 THEN 'MOSTLY_NULL_REVIEW'
        WHEN NVL(num_distinct, -1) <= 1 AND NVL(num_nulls, 0) < NVL(num_rows, 0) THEN 'CONSTANT_VALUE_REVIEW'
        WHEN NVL(avg_col_len, 0) >= 80 AND NVL(null_pct, 0) >= 80 THEN 'WIDE_AND_SPARSE_REVIEW'
        ELSE 'KEEP_OR_BUSINESS_REVIEW'
    END AS relevance_flag
FROM col_profile
ORDER BY
    table_name,
    column_id;
