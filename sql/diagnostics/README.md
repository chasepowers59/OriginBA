# Diagnostics SQL

Low-level troubleshooting SQL for mappings, lineage checks, row-level diagnostics, and read-only CISADM metadata discovery.

## Key Areas
- `cisadm_dictionary/`: full read-only schema dictionary extraction pack (tables/columns/constraints/indexes/views/dependencies/stats/keyword maps).
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
