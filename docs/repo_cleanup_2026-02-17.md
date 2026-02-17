# Repo Cleanup Log - 2026-02-17

## Scope
Repository organization cleanup focused on reducing tracked generated artifacts and improving maintainability.

## Applied
1. Added `.gitignore` entries for generated artifacts:
   - `*.jasper`
   - `deploy/*_report_unit/`
   - `deploy/*_report_unit.zip`
   - `.pytest_cache/`, `.mypy_cache/`, `coverage/`, `htmlcov/`, `*.log`
2. Removed tracked generated deployment report-unit directories and zip outputs under `deploy/`.
3. Added root `README.md` with current structure and regeneration/validation commands.

## Kept Intentionally
- `Domain Designs.xlsx` (source-of-truth workbook)
- `output/workstream_reporting_dictionary.json` and related output metadata files
- All SQL/JRXML/source scripts under `sql/`, `reports/`, `scripts/`, `pipeline/`

## Follow-up Recommendations
1. Keep generated report-unit files untracked; generate in CI/release only.
2. Continue using `git clean -ndX` before release to verify ignored build outputs.
3. If historical secrets were committed previously, rotate credentials and scrub history with `git filter-repo` in a controlled process.
