# SQL Performance Workspace

This area is organized by workload:
- `bill_cycle/`: bill-cycle KPI/performance SQL.
- `billed_usage/validation/`: optimized-domain parity/performance validation pack.
- `billed_revenue/`: billed revenue + tax split and FT/GL reconciliation SQL.
  - `billed_revenue/domain_core_benchmark_30d.sql`: read-only benchmark SQL for the 6 updated usage/billing domains.
  - `billed_revenue/tax_code_description_lookup.sql`: RC/FT tax code dictionary + in-data usage/amount profiling.
  - `billed_revenue/tax_ft_gl_diagnostics.sql`: diagnostics for FT tax amount availability/null keys by time window.
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
