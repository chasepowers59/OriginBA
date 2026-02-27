# OriginBA Repository Guide

## Purpose
Repository for Oracle C2M reporting SQL, Jaspersoft JRXML templates, deployment scripts, and governance checks.

## Standard Structure
- `api/` API entry points
- `ci/` CI pipelines and smoke SQL
- `db_schema/` staging schema and DDL
- `deploy/` deployment/build scripts only (generated report-unit artifacts are not tracked)
- `docs/` runbooks, standards, and implementation guides
- `output/` curated generated metadata used by pipeline/reporting dictionary
- `pipeline/` Python ETL/NLQ/data validation logic
- `reports/` JRXML source templates
- `reports/templates/` base reusable JRXML templates
- `reports/subreports/` JRXML subreports
- `reports/subreports/common/` reusable subreport components
- `sample_data/` small seeds for smoke testing
- `scripts/` utility validation and metadata scripts
- `server/input_controls/` JRS input control payloads
- `sql/` production SQL and harness scripts

## New Bill Template Path
- Concrete report: `reports/billing_customer_statement.jrxml`
- Base template: `reports/templates/base_customer_bill_template.jrxml`
- Controls: `server/input_controls/billing_customer_statement_input_controls.json`
- Bundle build:
  - `deploy/build_report_unit_billing_statement.sh`
  - `deploy/build_report_unit_billing_statement.ps1`

## Cleanup Changes
- Removed tracked generated deployment bundles from `deploy/*_report_unit*`.
- Added ignore rules for generated Jasper artifacts and coverage/log outputs.
- Added map report import/test guide in `docs/jaspersoft_map_report_import_and_test.md`.
- Removed temporary domain export zips and local extraction workspace (`tmp/`).
- Archived legacy SQL views to `archive/2026-02-19/sql/`:
  - `vw_billing_summary.sql`
  - `vw_debt_mgmt_account.sql`

## Regenerate Deployment Bundles
- PowerShell: `pwsh -File deploy/build_report_units.ps1`
- Bash: run each script under `deploy/build_report_unit*.sh`

## Validation Commands
- `git clean -ndX`
- `git clean -nd`
- `python scripts/validate_source_of_truth_sql.py sql/smartcity_9_workstream_kpis.sql`
- `python -m pipeline.validate_tables` (requires Oracle env vars)

## Domain Report Standards
- Build/checklist guide: `docs/jaspersoft_domain_report_build_standards.md`
- Origin 2025 styling implementation: `docs/jaspersoft_origin_2025_style_implementation.md`

## Billed Usage Domain Optimization (2026-02-27)
- Package: `Billed Usage Domain.zip`
- Added domain query subject `usage_qty_per_usage` to pre-aggregate scalar quantity by `D1_USAGE_ID`.
- Added `D1_USAGE.USAGE_MONTH` as `trunc(END_DTTM, 'MM')` for month-level slicing.
- Replaced JoinTree scalar join with `D1_USAGE -> usage_qty_per_usage` using `leftOuter`.
- Kept `D1_USAGE_SCALAR_DTL` resources and joins for rollback, but removed scalar-detail presentation items from exposed item groups.

## SQL + Jaspersoft Skills Workflow
- Workflow runbook: `docs/sql_jaspersoft_workflow_implementation.md`
- Local skills: `skills/README.md`
- Knowledge base: `knowledge_base/README.md`

## Bill Cycle Numbers Query
- Single reusable query: `sql/bill_cycle_numbers_single_report_query.sql`
- Purpose: return in-use bill cycle numbers with description and counts per environment.
- Source of cycle code: `CISADM.CI_BSEG.BILL_CYC_CD` (do not hardcode cycle values).
- Filters: active service agreements only (`CI_SA.SA_STATUS_FLG = '20'`); active accounts are counted via those active SAs.

## Bill Cycle Drilldown Query
- Drilldown detail: `sql/bill_cycle_segment_status_drilldown.sql`
- Purpose: per bill segment, show bill status, segment status, and error indicator/reason.
- Scope: active service agreements only (`CI_SA.SA_STATUS_FLG = '20'`).

## Bill Cycle Validation Query
- Validation SQL: `sql/bill_cycle_active_validation.sql`
- Purpose: compares summary vs drilldown counts by bill cycle and returns PASS/FAIL with deltas for:
  - bill segment count
  - bill count
  - active SA count
  - active account count

## Jasper Parity Check
- Parity SQL: `sql/bill_cycle_jaspersoft_parity_check.sql`
- Purpose: generate control totals and row fingerprints to compare DB output with Jasper CSV export for the same parameter slice.

## Bill Cycle Expected vs Actual
- Reconciliation derived table: `sql/bill_cycle_expected_vs_actual_reconciliation.sql`
- Purpose: compares expected active SA/account population to actual billed SA/account counts at latest event per cycle.

## Performance-Optimized SQL (V2 + FAST)
- `sql/bill_cycle_numbers_single_report_query_v2.sql`
- `sql/bill_cycle_segment_status_drilldown_v2.sql`
- `sql/bill_cycle_expected_vs_actual_reconciliation_v2.sql`
- FAST variants (reduced joins/columns for speed-first usage):
  - `sql/bill_cycle_numbers_single_report_query_fast.sql`
  - `sql/bill_cycle_segment_status_drilldown_fast.sql`
  - `sql/bill_cycle_expected_vs_actual_reconciliation_fast.sql`
