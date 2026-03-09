-- 11_table_partitions.sql
-- Read-only partition metadata for a schema owner tables.
-- Expected define variable:
--   schema_owner = CISADM

SELECT
  p.table_owner,
  p.table_name,
  p.partition_name,
  p.partition_position,
  p.high_value_length,
  p.tablespace_name,
  p.num_rows,
  p.blocks,
  p.last_analyzed
FROM ALL_TAB_PARTITIONS p
WHERE p.table_owner = UPPER('&schema_owner')
ORDER BY p.table_name, p.partition_position;

