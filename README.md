# OriginBA Repository Guide

## Purpose
Professional workspace for Oracle Utilities C2M (CISADM schema), Jaspersoft Domain/JRXML engineering, SQL performance tuning, and business analytics delivery.

## Core Structure
- `api/` API entry points
- `ci/` CI pipelines and smoke SQL
- `db_schema/` staging schema and DDL
- `deploy/` deployment/build scripts only (generated report-unit artifacts are not tracked)
- `docs/` runbooks, standards, and implementation guides
- `docs/roadmap/` professional development and capability plans
- `domains/exports/` exported Jaspersoft domain packages (`.zip`)
- `domains/working/` local extracted domain working copies
- `output/` curated generated metadata used by pipeline/reporting dictionary
- `pipeline/` Python ETL/NLQ/data validation logic
- `reports/` JRXML source templates
- `reports/templates/` base reusable JRXML templates
- `reports/subreports/` JRXML subreports
- `reports/subreports/common/` reusable subreport components
- `sample_data/` small seeds for smoke testing
- `scripts/` utility validation and metadata scripts
- `scripts/performance/` validation runners and perf automation
- `scripts/repo/` repo hygiene and structure checks
- `server/input_controls/` JRS input control payloads
- `sql/` SQL assets
- `sql/performance/bill_cycle/` bill-cycle performance and parity SQL
- `sql/performance/billed_usage/validation/` billed-usage optimized-domain validation SQL
- `sql/reconciliation/billing/` billing reconciliation SQL
- `sql/diagnostics/` diagnostic SQL
- `sql/analytics/` analytics/reporting SQL by domain

## Jaspersoft Assets
- Concrete report: `reports/billing_customer_statement.jrxml`
- Billing verification flow: `reports/billing_verification_flow.jrxml`
- Billing verification v2 validation runbook: `docs/billing_verification_v2_validation_runbook.md`
- Usage/device dashboard: `reports/usage_device_dashboard.jrxml`
- Base template: `reports/templates/base_customer_bill_template.jrxml`
- Controls: `server/input_controls/billing_customer_statement_input_controls.json`
- Billing verification controls: `server/input_controls/billing_verification_flow_input_controls.json`
- Usage/device controls: `server/input_controls/usage_device_dashboard_input_controls.json`
- Bundle build:
  - `deploy/build_report_unit_billing_statement.sh`
  - `deploy/build_report_unit_billing_statement.ps1`

## Domain Packages
- Current exported packages:
  - `domains/exports/billed_usage_domain.zip`
  - `domains/exports/billed_usage_domain_optimized_v1_copy.zip`
  - `domains/exports/bill_segment_domain_legacy_1.zip`
- Working billing verification v2 domain package:
  - `domains/working/billing_requirements_domain_v2/`
- Manual import bundles retained from prior root-level exports:
  - `domains/exports/manual_imports/FinalDomain.zip`
  - `domains/exports/manual_imports/New Bill Cycle Domain.zip`
  - `domains/exports/manual_imports/New Export Billing.zip`
- Archived one-off ZIP bundles and patch variants:
  - `archive/2026-03-10/root_zip_cleanup/`

## Regenerate Deployment Bundles
- PowerShell: `pwsh -File deploy/build_report_units.ps1`
- Bash: run each script under `deploy/build_report_unit*.sh`

## Validation Commands
- `git clean -ndX`
- `git clean -nd`
- `python scripts/validate_source_of_truth_sql.py`
- `python scripts/validate_source_of_truth_sql.py sql/smartcity_9_workstream_kpis.sql`
- `python scripts/repo/sql_read_only_guard.py sql/performance/billed_usage/validation`
- `python scripts/repo/sql_read_only_guard.py sql/diagnostics/cisadm_dictionary`
- `pwsh -File scripts/repo/repo_structure_audit.ps1`
- `pwsh -File scripts/performance/run_sql_quality_workflow.ps1`
- `pwsh -File scripts/repo/pre_merge_sql_gate.ps1`
- `python scripts/performance/close_workstream_table_gaps.py --write --emit-provisional-dictionary-seed`
- `python scripts/performance/build_cisadm_dictionary_coverage.py --dictionary-dir output/cisadm_dictionary`
- `python -m pipeline.validate_tables` (requires Oracle env vars)

## Domain Report Standards
- Build/checklist guide: `docs/jaspersoft_domain_report_build_standards.md`
- Origin 2025 styling implementation: `docs/jaspersoft_origin_2025_style_implementation.md`
- Delivery playbook: `docs/c2m_jaspersoft_delivery_playbook.md`

## SQL + Jaspersoft Skills Workflow
- Workflow runbook: `docs/sql_jaspersoft_workflow_implementation.md`
- Local skills: `skills/README.md`
- Knowledge base: `knowledge_base/README.md`
- CISADM vocabulary guide: `docs/cisadm_workstream_vocabulary_guide.md`
- CISADM SQL cheat sheet: `docs/cisadm_sql_cheat_sheet.md`
- CISADM workstream study deck: `docs/cisadm_workstream_study_deck.md`
- CISADM relationship map: `docs/cisadm_relationship_map.md`
- C2M CISADM analyst handbook: `docs/c2m_cisadm_analyst_handbook.md`
- CISADM starter SQL patterns: `docs/cisadm_starter_sql_patterns.md`

## SQL Quality Workflow
- Dedicated CI workflow: `.github/workflows/sql-quality.yml`
- Local runbook: `docs/sql_quality_workflow.md`
- Gates included:
  - source-of-truth SQL table validation on governed utility/performance scopes
  - read-only SQL guard for billed-usage + CISADM dictionary packs

## CISADM Dictionary Discovery
- SQL pack: `sql/diagnostics/cisadm_dictionary/`
- Runner: `scripts/performance/run_cisadm_dictionary_discovery.ps1`
- Coverage builder: `scripts/performance/build_cisadm_dictionary_coverage.py`
- Output folder (generated): `output/cisadm_dictionary/`
- Pre-DB workstream gap closure:
  - `scripts/performance/close_workstream_table_gaps.py` updates workstream dictionary from domain metadata and emits a provisional dictionary seed for coverage review.

## Database Safety Policy
- Validation and discovery SQL in this repo is read-only by policy.
- Billed usage validation runs include `00_read_only_preflight.sql` and fail if risky privileges are detected.
- PowerShell validation runner uses explicit `ConnectString` input; it does not auto-load credentials from `.env`.
- CISADM dictionary discovery runner also uses explicit `ConnectString` and read-only SQL guard checks.

## Bill Cycle Numbers Query
- Single reusable query: `sql/performance/bill_cycle/bill_cycle_numbers_single_report_query.sql`
- Purpose: return in-use bill cycle numbers with description and counts per environment.
- Source of cycle code: `CISADM.CI_BSEG.BILL_CYC_CD` (do not hardcode cycle values).
- Filters: active service agreements only (`CI_SA.SA_STATUS_FLG = '20'`); active accounts are counted via those active SAs.

## Bill Cycle Drilldown Query
- Drilldown detail: `sql/performance/bill_cycle/bill_cycle_segment_status_drilldown.sql`
- Purpose: per bill segment, show bill status, segment status, and error indicator/reason.
- Scope: active service agreements only (`CI_SA.SA_STATUS_FLG = '20'`).

## Bill Cycle Validation Query
- Validation SQL: `sql/performance/bill_cycle/bill_cycle_active_validation.sql`
- Purpose: compares summary vs drilldown counts by bill cycle and returns PASS/FAIL with deltas for:
  - bill segment count
  - bill count
  - active SA count
  - active account count

## Jasper Parity Check
- Parity SQL: `sql/performance/bill_cycle/bill_cycle_jaspersoft_parity_check.sql`
- Purpose: generate control totals and row fingerprints to compare DB output with Jasper CSV export for the same parameter slice.

## Bill Cycle Expected vs Actual
- Reconciliation derived table: `sql/performance/bill_cycle/bill_cycle_expected_vs_actual_reconciliation.sql`
- Purpose: compares expected active SA/account population to actual billed SA/account counts at latest event per cycle.

## Performance-Optimized SQL (V2 + FAST)
- `sql/performance/bill_cycle/bill_cycle_numbers_single_report_query_v2.sql`
- `sql/performance/bill_cycle/bill_cycle_segment_status_drilldown_v2.sql`
- `sql/performance/bill_cycle/bill_cycle_expected_vs_actual_reconciliation_v2.sql`
- FAST variants (reduced joins/columns for speed-first usage):
  - `sql/performance/bill_cycle/bill_cycle_numbers_single_report_query_fast.sql`
  - `sql/performance/bill_cycle/bill_cycle_segment_status_drilldown_fast.sql`
  - `sql/performance/bill_cycle/bill_cycle_expected_vs_actual_reconciliation_fast.sql`
