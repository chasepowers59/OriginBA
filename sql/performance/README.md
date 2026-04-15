# SQL Performance Workspace

This area is organized by workload, with governed snapshot build assets centralized under `snapshots/<workstream>/<subset>/`.

## Snapshot Workspaces
- `snapshots/billed_usage/bseg_billed_usage/`: bill-segment billed-usage snapshot workspace where `CI_BSEG_SQ`, `CI_BSEG_READ`, and `CI_BSEG_CALC` can multiply `CI_BSEG`.
- `snapshots/billed_usage/bseg_sq_usage/`: determinant-grain billed-usage snapshot workspace for safe `UOM` / `TOU` / `SQI` analysis from `CI_BSEG_SQ`.
- `snapshots/debt_mgmt/`: debt-management snapshot discovery workspace and implemented subsets.
  - `snapshots/debt_mgmt/acct_debt/`: account-level debt snapshot SQL using governed `CI_FT` arrears logic with latest collections and write-off context.
  - `snapshots/debt_mgmt/coll_proc/`: collection-process snapshot SQL at one row per `COLL_PROC_ID`.
- `snapshots/finance/ft_rpt_curr/`: FT header snapshot SQL at one row per `FT_ID` for finance reporting and trace views.
- `snapshots/finance/ft_gl_distribution/`: snapshot workspace for the legacy FT / GL distribution domain, including preflight grain validation.
- `snapshots/meter_ops/d1_msrmt/`: final processed measurement snapshot DDL, refresh procedure, scheduler job, and validation SQL.
- `snapshots/meter_ops/d1_usage/`: lean usage-header snapshot DDL, refresh procedure, scheduler job, and validation SQL at one row per `D1_USAGE`.
- `snapshots/meter_ops/d1_usage_scalar_dtl/`: scalar-detail usage snapshot DDL, refresh procedure, scheduler job, and validation SQL at one row per `D1_USAGE_SCALAR_DTL`.
- `snapshots/payments_cashiering/`: payments and cashiering discovery workspace and implemented subsets.
  - `snapshots/payments_cashiering/pay_tndr_cashier/`: tender-centered payments/cashiering snapshot SQL at one row per `PAY_TENDER_ID`, with tender/deposit control context and staged-source overlays.

## Supporting Workspaces
- `bill_cycle/`: bill-cycle KPI/performance SQL.
- `billed_usage/validation/`: optimized-domain parity/performance validation pack.
- `billed_revenue/`: billed revenue + tax split and FT/GL reconciliation SQL.
  - `billed_revenue/domain_core_benchmark_30d.sql`: read-only benchmark SQL for the 6 updated usage/billing domains.
  - `billed_revenue/tax_code_description_lookup.sql`: RC/FT tax code dictionary + in-data usage/amount profiling.
  - `billed_revenue/tax_ft_gl_diagnostics.sql`: diagnostics for FT tax amount availability/null keys by time window.
- `finance/ft_rpt_curr_domain_validation.sql`: read-only validation checks for the snapshot-backed `FT_RPT_CURR` financial-transaction domain.
- `unbilled_revenue/`: daily unbilled revenue estimation snapshot SQL (usage + non-usage + tax estimate).
- `write_off/`: write-off process volume, debt, effectiveness, duration, and payment-recovery estimates.
- `fund_balance/`: GL/fund-balance detail, summary, account rollup, and view-vs-raw reconciliation SQL.
- `INDEX_COVERAGE_USAGE_BILLING_DOMAINS.md`: index coverage map for the six active usage/billing domains.
- `DBA_INDEX_REQUEST_DOMAIN_QUERIES.md`: prioritized DBA index creation request for slow domain query paths.

## Automation
- `scripts/performance/run_billed_usage_validation.ps1`: read-only parity/performance validation for billed usage.
- `scripts/performance/run_cisadm_dictionary_discovery.ps1`: read-only CISADM dictionary extraction + coverage outputs.
- `scripts/performance/run_sql_quality_workflow.ps1`: orchestrates static quality gates and optional DB read-only checks.
- `scripts/performance/run_domain_core_benchmarks.py`: read-only row-count/timing benchmark for six updated usage/billing domains (last 30 days).
