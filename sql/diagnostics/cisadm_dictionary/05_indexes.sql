-- 05_indexes.sql
-- Read-only index metadata for a schema owner.
-- Expected define variable:
--   schema_owner = CISADM

SELECT
  i.owner,
  i.table_name,
  i.index_name,
  i.uniqueness,
  i.index_type,
  i.status,
  i.visibility,
  i.tablespace_name,
  i.partitioned,
  i.last_analyzed
FROM ALL_INDEXES i
WHERE i.table_owner = UPPER('&schema_owner')
ORDER BY i.table_name, i.index_name;
