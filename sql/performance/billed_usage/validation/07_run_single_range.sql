-- 07_run_single_range.sql
-- Executes full read-only validation for a single range.
-- Required vars:
--   define start_ts = 2026-01-01
--   define end_ts   = 2026-01-08

set define on
set echo on
set timing on
whenever sqlerror exit failure

prompt --- Single range validation start ---
prompt start_ts=&start_ts end_ts=&end_ts

@01_original_agg.sql
@02_optimized_agg.sql
@03_compare_original_vs_optimized.sql
@04_sample_usg_ext_id_check.sql
@08_assert_zero_diff_per_class.sql
@09_assert_zero_diff_samples.sql

prompt --- Single range validation complete ---
