-- 07_run_all_ranges.sql
-- Runs all comparison checks for three fixed ranges.

set define on
set echo on
set timing on
whenever sqlerror exit failure

spool billed_usage_validation_output.log

prompt === Read-only DB preflight ===
@00_read_only_preflight.sql

prompt === Range A: 2026-01-01 to 2026-01-08 ===
define start_ts = 2026-01-01
define end_ts   = 2026-01-08
@07_run_single_range.sql

prompt === Range B: 2026-01-01 to 2026-02-01 ===
define start_ts = 2026-01-01
define end_ts   = 2026-02-01
@07_run_single_range.sql

prompt === Range C: 2025-11-01 to 2026-02-01 ===
define start_ts = 2025-11-01
define end_ts   = 2026-02-01
@07_run_single_range.sql

spool off

prompt Validation run complete. Review billed_usage_validation_output.log for totals and diffs.
