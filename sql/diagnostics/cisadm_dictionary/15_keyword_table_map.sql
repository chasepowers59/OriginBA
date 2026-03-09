-- 15_keyword_table_map.sql
-- Read-only keyword-based table mapping to accelerate use-case discovery.
-- Expected define variable:
--   schema_owner = CISADM

WITH KEYWORDS AS (
  SELECT 'BILLING' AS keyword_bucket, 'BILL' AS pattern FROM DUAL UNION ALL
  SELECT 'BILLING', 'BSEG' FROM DUAL UNION ALL
  SELECT 'USAGE', 'USAGE' FROM DUAL UNION ALL
  SELECT 'USAGE', 'MSR' FROM DUAL UNION ALL
  SELECT 'FINANCE', 'FT_' FROM DUAL UNION ALL
  SELECT 'FINANCE', 'GL_' FROM DUAL UNION ALL
  SELECT 'TAX', 'TAX' FROM DUAL UNION ALL
  SELECT 'WRITE_OFF', 'WO_' FROM DUAL UNION ALL
  SELECT 'PAYMENTS', 'PAY_' FROM DUAL UNION ALL
  SELECT 'CUSTOMER', 'ACCT' FROM DUAL UNION ALL
  SELECT 'CUSTOMER', 'PER_' FROM DUAL UNION ALL
  SELECT 'SERVICE', 'SA_' FROM DUAL UNION ALL
  SELECT 'PREMISE', 'PREM' FROM DUAL UNION ALL
  SELECT 'METER', 'METER' FROM DUAL UNION ALL
  SELECT 'RATE', 'RS_' FROM DUAL UNION ALL
  SELECT 'RATE', 'RC_' FROM DUAL UNION ALL
  SELECT 'COLLECTIONS', 'COLL' FROM DUAL UNION ALL
  SELECT 'FUND', 'FUND' FROM DUAL
),
MATCHES AS (
  SELECT
    k.keyword_bucket,
    c.table_name,
    c.column_name
  FROM ALL_TAB_COLUMNS c
  JOIN KEYWORDS k
    ON UPPER(c.column_name) LIKE '%' || k.pattern || '%'
  WHERE c.owner = UPPER('&schema_owner')
)
SELECT
  m.keyword_bucket,
  m.table_name,
  COUNT(*) AS matched_column_count,
  MIN(m.column_name) AS example_column
FROM MATCHES m
GROUP BY
  m.keyword_bucket,
  m.table_name
ORDER BY
  m.keyword_bucket,
  matched_column_count DESC,
  m.table_name;

