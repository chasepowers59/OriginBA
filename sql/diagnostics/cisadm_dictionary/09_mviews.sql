-- 09_mviews.sql
-- Read-only materialized view metadata for a schema owner.
-- Expected define variable:
--   schema_owner = CISADM

SELECT
  m.owner,
  m.mview_name,
  m.refresh_mode,
  m.refresh_method,
  m.build_mode,
  m.last_refresh_type,
  m.last_refresh_date,
  m.staleness
FROM ALL_MVIEWS m
WHERE m.owner = UPPER('&schema_owner')
ORDER BY m.mview_name;

