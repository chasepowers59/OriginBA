# Skill: C2M Usage Performance Validation

## Goal
Validate optimized vs original C2M usage-reporting logic with deterministic, read-only SQL parity checks.

## Inputs
- Date ranges (`start_ts`, `end_ts`)
- CISADM access for:
  - `CI_ACCT`
  - `CI_SA`
  - `C1_USAGE`
  - `D1_USAGE`
  - `D1_USAGE_SCALAR_DTL`
- Read-only DB credentials only.

## Runbook
1. Run read-only preflight: `sql/performance/billed_usage/validation/00_read_only_preflight.sql`
2. Run original aggregation: `sql/performance/billed_usage/validation/01_original_agg.sql`
3. Run optimized aggregation: `sql/performance/billed_usage/validation/02_optimized_agg.sql`
4. Compare results: `sql/performance/billed_usage/validation/03_compare_original_vs_optimized.sql`
5. Validate sample IDs: `sql/performance/billed_usage/validation/04_sample_usg_ext_id_check.sql`
6. Execute complete cycle: `07_run_all_ranges.sql`

## Pass Criteria
- All per-class differences = 0
- Sample-level differences = 0
- Queries run successfully in read-only mode.

## Automation
- Runner: `scripts/performance/run_billed_usage_validation.ps1`
