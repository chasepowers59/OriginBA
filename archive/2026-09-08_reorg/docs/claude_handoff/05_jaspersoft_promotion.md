# 05 — Jaspersoft promotion pipelines

## Two pipelines

| Pipeline | Purpose | Docs |
|----------|---------|------|
| **Client promotion** | Origin_DEV → SmartCity client org + client DS | `docs/jaspersoft_client_promotion_pipeline.md` |
| **Environment promotion** | Same org paths; change DS only (DEMO/STAGE) | `docs/jaspersoft_environment_promotion_pipeline.md` |

## Standard import contract (all)

1. Build **tenant-root** light-touch packages
2. Omit `rootTenantId` when importing into an **existing tenant**
3. Import **inside** the tenant Repository (not server-root Organizations)
4. Inject real client JDBC overlay from `deploy/jaspersoft_datasources/clients/<Alias>_DS/`
5. Verify with `scripts/jaspersoft/verify_prepared_import.py`

## Client Standard Offering

```bash
# Optional: patch VEE To Do joins to left outer first
python3 scripts/jaspersoft/patch_vee_exception_todo_joins.py \
  --source "/path/to/standard offering.zip" \
  --output "/path/to/patched.zip"

python3 scripts/jaspersoft/run_client_standard_offering_pipeline.py \
  --source-zip "/path/to/patched.zip" \
  --clients Newark1 \
  --skip-archive
```

Outputs: `deploy/jaspersoft_client_promotion/prepared_imports/<Client>_Standard_Offering_import.zip`

Mapping: `deploy/jaspersoft_client_promotion/client_org_mapping.csv`

## Partial folder example (Device → Newark)

Pattern used 2026-08:
1. Strip Workstreams noise; keep Standard Offering Device folder
2. `prepare_client_imports.py` with tenant-root light-touch + Newark1_DS overlay
3. `verify_prepared_import.py` PASS
4. Import inside Newark1 tenant

## Known defect classes (Jira-ready)

1. JRXML element order (filterExpression / pageFooter)
2. Forbidden chart tags (seriesColor, etc.)
3. Empty domain queryFields
4. Shared `/public/templates/actual_size.820.jrxml` breakage
5. Datasource URI / overlay mismatch
6. Invalid export / rootTenantId / org ID casing
7. Add-on wrapper folder-details drift
8. VEE Exception inner-join To Do population drop

## Key scripts

- `scripts/jaspersoft/prepare_client_imports.py`
- `scripts/jaspersoft/run_client_import_pipeline.py`
- `scripts/jaspersoft/run_client_standard_offering_pipeline.py`
- `scripts/jaspersoft/run_environment_import_pipeline.py`
- `scripts/jaspersoft/verify_prepared_import.py`
- `scripts/jaspersoft/tenant_root_layout.py`
- `scripts/jaspersoft/patch_vee_exception_todo_joins.py`

Troubleshooting: `docs/jaspersoft_environment_promotion_troubleshooting.md`,  
`docs/jaspersoft_repository_import_debugging_runbook.md`
