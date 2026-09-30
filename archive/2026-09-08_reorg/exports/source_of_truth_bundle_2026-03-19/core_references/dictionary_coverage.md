# CISADM Dictionary Coverage

## Current Repository Coverage (Curated Metadata)
- Source metadata files:
  - `output/workstream_reporting_dictionary.json`
  - `output/domain_designs_metadata.json`
- Workstreams represented: 10
- Curated workstream table union: 73 tables

## Important Limitation
Curated metadata is not a full physical CISADM schema dictionary.

## Full Dictionary Discovery (Read-Only)
Run:

```powershell
pwsh -File scripts/performance/run_cisadm_dictionary_discovery.ps1 `
  -ConnectString "user/password@host:1521/service" `
  -SchemaOwner CISADM
```

This produces:
- `output/cisadm_dictionary/tables.csv`
- `output/cisadm_dictionary/columns.csv`
- `output/cisadm_dictionary/constraints.csv`
- `output/cisadm_dictionary/constraint_columns.csv`
- `output/cisadm_dictionary/indexes.csv`
- `output/cisadm_dictionary/index_columns.csv`
- `output/cisadm_dictionary/workstream_coverage.csv`
- `output/cisadm_dictionary/coverage_summary.md`
- `output/cisadm_dictionary/index_columns_enriched.csv`
- `output/cisadm_dictionary/prefilter_candidates.csv`
- `output/cisadm_dictionary/prefilter_candidates_summary.md`
- `output/cisadm_dictionary/prefilter_top_by_table.md`

## Read-Only Guarantee
- Discovery SQL uses `ALL_*` dictionary views only.
- No DDL, DML, grants, stats, or transactional writes.
