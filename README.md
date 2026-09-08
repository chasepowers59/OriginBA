# OriginBA Repository Guide

Rewritten 2026-09-08 with the repository reorganization. `docs/roadmap/repository_structure_standard.md`
is the structure contract; `scripts/repo/repo_structure_audit.ps1` and `tests/test_repo_structure.py` enforce it.

## Purpose
The Origin BA analytics portal (FastAPI + Next.js) and the Jaspersoft DELIVERY side for Oracle
Utilities C2M (CISADM): domains, JRXML reports, client promotion, DataSources, the active snapshot
operations, and per-client SQL. The data layer -- CISADM -> dbt reporting canvases, and the
Jaspersoft domains generated from them -- is the sibling repo `~/originba_dbt`.

## Core Structure
- `api/` FastAPI backend (`api.app`); `apps/analytics-portal/` Next.js portal (Vercel root); `config/` runtime config (`portal_organizations.json`, `dq_rules.yml`, the generated `clients.export.json`); `data/` runtime state; `output/catalog_dbt.json` the one canvas catalog (generated in `~/originba_dbt`)
- `jaspersoft/` the Jaspersoft delivery home: `jaspersoft/README.md` is the index, `jaspersoft/docs/` the standards and runbooks, `jaspersoft/dashboards/` the dashboard packs
- `reports/`, `reports/templates/`, `reports/subreports/` JRXML; `server/input_controls/` the paired input-control JSON per report
- `domains/` hand-built domains and client deliverables (`domains/README.md`)
- `deploy/` the API image (`deploy/Dockerfile.api`), Jaspersoft DataSources, client and environment promotion, the shipped Standard Offering package, snapshot rollout logs
- `sql/performance/snapshots/` the active-8 snapshot estate (DDL, procedures, schedulers, QA, its `docs/`); `sql/clients/<client>/` per-client deliverables; `sql/performance/bill_cycle/`, `sql/performance/billed_usage/validation/`, `sql/reconciliation/billing/`, `sql/diagnostics/cisadm_dictionary/` the governed packs `.github/workflows/sql-quality.yml` gates; `sql/analytics/` analytics SQL
- `scripts/` automation: `scripts/jaspersoft/` promotion and domain tooling, `scripts/local/` client SQL runner, MCP, rollout steps, `scripts/performance/` validation runners, `scripts/repo/` hygiene gates, `scripts/doc/` signoff documents
- `knowledge_base/` and `docs/` the CISADM reference corpus, runbooks and standards (`docs/assistant_skills/` the JRXML and SQL guardrails)
- `.claude/skills/` the one loadable skill home (`originba-*`, `jaspersoft-client-tenant-import`, `originba-frontend`, `originba-security`)
- `tests/` pytest (`api-ci.yml`); `ci/jrxml-smoke.yml` parked by design (needs the VCN)
- `archive/<date>/` superseded files with `INDEX.md` and a pointer at every old path; `pipeline/`, `db_schema/`, `sample_data/` the older ETL/smoke pieces the parked CI file pins

## Jaspersoft Assets
Indexed in `jaspersoft/README.md`. Report bundles are built by `deploy/build_report_unit*.sh` from `reports/*.jrxml` and `server/input_controls/*.json`.

## Domain Packages
Indexed in `domains/README.md`: the seven active-8 domain XMLs and retained bundles under `domains/exports/manual_imports/`, the Newark deliverables under `domains/manual_imports/`, working copies under `domains/working/`. Generated domains live in `~/originba_dbt/jaspersoft/domains/`.

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
- `python scripts/jaspersoft/run_client_import_pipeline.py --help`
- `python scripts/jaspersoft/verify_prepared_import.py --help`
- `python scripts/jaspersoft/inventory_jaspersoft_artifacts.py --help`
- `pwsh -File scripts/repo/repo_structure_audit.ps1`
- `pwsh -File scripts/performance/run_sql_quality_workflow.ps1`
- `pwsh -File scripts/repo/pre_merge_sql_gate.ps1`
- `python scripts/performance/close_workstream_table_gaps.py --write --emit-provisional-dictionary-seed`
- `python scripts/performance/build_cisadm_dictionary_coverage.py --dictionary-dir output/cisadm_dictionary`
- `python -m pipeline.validate_tables` (requires Oracle env vars)

## Domain Report Standards
- Build/checklist guide: `jaspersoft/docs/jaspersoft_domain_report_build_standards.md`
- Origin 2025 styling implementation: `jaspersoft/docs/jaspersoft_origin_2025_style_implementation.md`
- Delivery playbook: `jaspersoft/docs/c2m_jaspersoft_delivery_playbook.md`
- Client promotion pipeline: `jaspersoft/docs/jaspersoft_client_promotion_pipeline.md`

## Jaspersoft Repository Promotion
- Scope: standalone Jaspersoft repository export rewrite and client import preparation
- Scripts: `scripts/jaspersoft/`
- Staging area: `deploy/jaspersoft_client_promotion/`
- Not part of the DB / SQL / snapshot optimization workflow
- Artifact inventory: `jaspersoft/docs/jaspersoft_artifact_inventory.md`

## SQL + Jaspersoft Skills Workflow
- Workflow runbook: `docs/sql_jaspersoft_workflow_implementation.md`
- Local skills: `.claude/skills/` (one `SKILL.md` per skill; `skills/` archived 2026-09-08)
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
