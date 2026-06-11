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

Or export pending outputs from a named client:

```bash
python3 scripts/local/export_cisadm_dictionary_outputs.py --client demo
```

## Workstream Table Health (Live Population)
```bash
python3 scripts/local/run_workstream_table_health.sh demo
python3 scripts/build_ai_cisadm_context.py --client demo
```

Outputs:
- `deploy/snapshot_rollout_logs/<client>/table_health.json`
- `sql/diagnostics/cisadm_workstream_table_health.sql` (generated)

## AI Context Bundle
```bash
python3 scripts/build_ai_cisadm_context.py
python3 scripts/build_domain_field_index.py
```

Primary output: `output/ai_cisadm_context.json`

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
