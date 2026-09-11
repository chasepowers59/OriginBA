# SQL Quality Workflow (Read-Only)

This workflow enforces SQL safety and metadata quality for Oracle Utilities C2M reporting assets.

## Static Gates (No DB Connection Required)
Run:

```powershell
pwsh -File scripts/performance/run_sql_quality_workflow.ps1
```

Checks performed:
1. Source-of-truth table validation on governed SQL scopes.
2. Read-only keyword guard on governed read-only packs.
3. Repository structure audit.

Optional pre-DB workstream gap closure:

```powershell
python scripts/performance/close_workstream_table_gaps.py --write --emit-provisional-dictionary-seed
python scripts/performance/build_cisadm_dictionary_coverage.py --dictionary-dir output/cisadm_dictionary
```

Use this to reduce workstream coverage gaps before live DB dictionary extraction.

## Read-Only DB Checks (Optional)
Run:

```powershell
pwsh -File scripts/performance/run_sql_quality_workflow.ps1 `
  -RunDbChecks `
  -RunDictionaryDiscovery `
  -RunBilledUsageValidation `
  -ConnectString "user/password@host:1521/service"
```

Notes:
- All DB actions are `SELECT`-only.
- Credentials must be passed explicitly with `-ConnectString`.
- `.env` is not auto-loaded by this workflow.

## Outputs
- Billed usage validation logs and `performance_budget_summary.csv` in:
  - `sql/performance/billed_usage/validation/`
- CISADM dictionary outputs in:
  - `output/cisadm_dictionary/`
  - Includes indexed prefilter guidance artifacts:
    - `index_columns_enriched.csv`
    - `prefilter_candidates.csv`
    - `prefilter_candidates_summary.md`
    - `prefilter_top_by_table.md`
