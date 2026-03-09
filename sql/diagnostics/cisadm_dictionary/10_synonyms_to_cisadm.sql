-- 10_synonyms_to_cisadm.sql
-- Read-only synonym mapping that points to schema owner objects.
-- Expected define variable:
--   schema_owner = CISADM

SELECT
  s.owner,
  s.synonym_name,
  s.table_owner,
  s.table_name,
  s.db_link
FROM ALL_SYNONYMS s
WHERE s.table_owner = UPPER('&schema_owner')
   OR s.owner = UPPER('&schema_owner')
ORDER BY s.owner, s.synonym_name;

