-- 13_column_stats.sql
-- Read-only optimizer column stats for a schema owner.
-- Expected define variable:
--   schema_owner = CISADM

SELECT
  s.owner,
  s.table_name,
  s.column_name,
  s.num_distinct,
  s.num_nulls,
  s.density,
  s.num_buckets,
  s.histogram,
  s.sample_size,
  s.last_analyzed
FROM ALL_TAB_COL_STATISTICS s
WHERE s.owner = UPPER('&schema_owner')
ORDER BY s.table_name, s.column_name;

