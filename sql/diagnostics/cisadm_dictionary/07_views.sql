-- 07_views.sql
-- Read-only view metadata for a schema owner.
-- Expected define variable:
--   schema_owner = CISADM

SELECT
  v.owner,
  v.view_name,
  v.text_length
FROM ALL_VIEWS v
WHERE v.owner = UPPER('&schema_owner')
ORDER BY v.view_name;

