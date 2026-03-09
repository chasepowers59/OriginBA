-- 12_table_stats.sql
-- Read-only optimizer table stats for a schema owner.
-- Expected define variable:
--   schema_owner = CISADM

SELECT
  s.owner,
  s.table_name,
  s.partition_name,
  s.object_type,
  s.num_rows,
  s.blocks,
  s.avg_row_len,
  s.sample_size,
  s.last_analyzed,
  s.stale_stats,
  s.global_stats,
  s.user_stats
FROM ALL_TAB_STATISTICS s
WHERE s.owner = UPPER('&schema_owner')
ORDER BY s.table_name, s.partition_name;

