-- 01_tables.sql
-- Read-only table-level metadata for a schema owner.
-- Expected define variable:
--   schema_owner = CISADM

SELECT
  t.owner,
  t.table_name,
  tc.comments AS table_comment,
  t.tablespace_name,
  t.temporary,
  t.partitioned,
  t.num_rows,
  t.blocks,
  t.avg_row_len,
  t.last_analyzed
FROM ALL_TABLES t
LEFT JOIN ALL_TAB_COMMENTS tc
  ON tc.owner = t.owner
 AND tc.table_name = t.table_name
WHERE t.owner = UPPER('&schema_owner')
ORDER BY t.table_name;
