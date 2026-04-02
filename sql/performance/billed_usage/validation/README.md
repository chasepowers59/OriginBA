# Billed Usage Optimized Domain Validation Pack

This folder contains SQL*Plus-ready scripts to validate that optimized domain aggregation is result-equivalent to the original scalar-detail model.

## Date Ranges
- Range A: 2026-01-01 to 2026-01-08
- Range B: 2026-01-01 to 2026-02-01
- Range C: 2025-11-01 to 2026-02-01

## Script Order
1. `00_read_only_preflight.sql`
2. `01_original_agg.sql`
3. `02_optimized_agg.sql`
4. `03_compare_original_vs_optimized.sql`
5. `04_sample_usg_ext_id_check.sql`
6. `08_assert_zero_diff_per_class.sql`
7. `09_assert_zero_diff_samples.sql`
8. `10_amount_allocation_feasibility.sql` (read-only determinant allocation feasibility test)
9. `07_run_single_range.sql` (single range wrapper)
10. `07_run_all_ranges.sql` (all-ranges wrapper + fail-fast gates)

## Usage
- Set `start_ts` and `end_ts` in `YYYY-MM-DD` format.
- Run from SQL*Plus or SQLcl.
- For all ranges, run `@07_run_all_ranges.sql`.
- For billed-amount-to-determinant feasibility, run `@10_amount_allocation_feasibility.sql`.
- The PowerShell runner accepts credentials via explicit `ConnectString` parameter only; it does not auto-load `.env`.
- Automated run (read-only):
  - `pwsh -File scripts/performance/run_billed_usage_validation.ps1 -ConnectString "user/password@host:1521/service"`

## Performance Budget Gate
- The PowerShell runner enforces range runtime budgets by default:
  - Range A: 45 seconds
  - Range B: 90 seconds
  - Range C: 180 seconds
- Override with parameters in `scripts/performance/run_billed_usage_validation.ps1`.
- Disable budget enforcement only with explicit `-DisableBudgetEnforcement`.
- Budget output: `sql/performance/billed_usage/validation/performance_budget_summary.csv`.

## Read-Only Guarantee
- This pack is `SELECT`-only.
- It does not run `EXPLAIN PLAN`, DDL, DML, `DBMS_STATS`, or index/view creation.
- The wrapper uses read-only assertion queries to fail the run when differences are non-zero.
