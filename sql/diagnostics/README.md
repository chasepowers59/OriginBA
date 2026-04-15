# Diagnostics SQL

Low-level troubleshooting SQL for mappings, lineage checks, row-level diagnostics, and read-only CISADM metadata discovery.

## Key Areas
- `cisadm_dictionary/`: full read-only schema dictionary extraction pack (tables/columns/constraints/indexes/views/dependencies/stats/keyword maps).
- `bill_to_bseg_trace.sql`: one-bill trace showing the bill header, its bill segments, and optional determinant rows under those segments.
- `bseg_to_usage_scalar_measurement_trace.sql`: one-bill-segment lineage trace from `CI_BSEG_SQ` / `CI_BSEG_CALC` through `CI_SA`, `C1_USAGE`, `D1_USAGE`, `D1_USAGE_SCALAR_DTL`, and best-effort processed measurement rows.
- `cisadm_data_dictionary_extract.sql`: legacy one-shot extract kept for compatibility.
- `d1_usage_to_sa_mapping_diagnostic.sql`: deep usage-to-SA lineage and join diagnostics.
- `find_bill_cycle_numbers.sql`: bill-cycle lookup diagnostics.

## Discovery Automation
Run dictionary extraction + coverage summary with:

```powershell
pwsh -File scripts/performance/run_cisadm_dictionary_discovery.ps1 `
  -ConnectString "user/password@host:1521/service" `
  -SchemaOwner CISADM
```

Outputs are written to `output/cisadm_dictionary/`.
