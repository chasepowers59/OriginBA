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
- `reports/subreports/` JRXML subreports
- `sample_data/` small seeds for smoke testing
- `scripts/` utility validation and metadata scripts
- `server/input_controls/` JRS input control payloads
- `sql/` production SQL and harness scripts

## Cleanup Changes
- Removed tracked generated deployment bundles from `deploy/*_report_unit*`.
- Added ignore rules for generated Jasper artifacts and coverage/log outputs.
- Added map report import/test guide in `docs/jaspersoft_map_report_import_and_test.md`.

## Regenerate Deployment Bundles
- PowerShell: `pwsh -File deploy/build_report_units.ps1`
- Bash: run each script under `deploy/build_report_unit*.sh`

## Validation Commands
- `git clean -ndX`
- `git clean -nd`
- `python scripts/validate_source_of_truth_sql.py sql/smartcity_9_workstream_kpis.sql`
- `python -m pipeline.validate_tables` (requires Oracle env vars)
