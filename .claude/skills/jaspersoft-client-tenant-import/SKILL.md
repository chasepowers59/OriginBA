---
name: jaspersoft-client-tenant-import
description: >-
  Builds Jaspersoft client-tenant report import ZIPs using tenant-relative paths
  (Standard Offering layout). Use when packaging JRXML/report units for import
  inside a client org on JRS, fixing organization_1 or datasource reference
  import errors, or creating import bundles like Newark REP8.
---

# Jaspersoft client-tenant report import

## Quick rule

Import **inside the client tenant**. Package must use **tenant-relative** paths (`resources/SmartCity/...`, `/DataSource/{Client}_DS`) with **no** `rootTenantId` and **no** `organizations/organization_1/...`.

## Workflow

1. **Read** [docs/jaspersoft_client_tenant_report_import.md](../../../docs/jaspersoft_client_tenant_report_import.md) for full contract.
2. **Build** with `scripts/jaspersoft/build_client_tenant_report_import.py` (or a client wrapper like `build_newark_rep8_report_import.py`).
3. **Verify** output shows `verify_prepared_import.py` → `status: PASS`.
4. **Import** while logged into client org → Repository → Import → overwrite.

## Required package contents

- `resources/DataSource/{Client}_DS.xml` from `deploy/jaspersoft_datasources/clients/{Client}_DS/`
- `resources/public/templates/actual_size.820.jrxml.*` (bundled by builder)
- Report folder + `main_jrxml.data` under `resources/SmartCity/Report/...`
- `Report_Date` parameter folder **only if** report unit references it (`--include-report-date`)

## Required `index.xml` shape

```xml
<module id="repositoryResources">
  <resource>/DataSource/{Client}_DS</resource>
  <resource>/public/templates/actual_size.820.jrxml</resource>
  <folder>{exact repository folder URI}</folder>
</module>
<module id="favorites"/>
```

No `rootTenantId`. Folder URI must match report unit `<folder>` and zip paths **exactly**.

## Never include

- `favorites/` tree from source exports (user-specific stale metadata)
- `rootTenantId` for in-tenant import
- Duplicate report under `Standard_Offering/` when target path is `Workstreams/`

## Never use for Workstreams reports

`promote_tenant_root_export_light_touch()` — it rewrites URIs to `Standard_Offering` and breaks `index.xml` folder alignment.

Use `build_client_tenant_report_import.py` instead.

## Builder template

```bash
python3 scripts/jaspersoft/build_client_tenant_report_import.py \
  --source-zip PATH_TO_SOURCE_EXPORT.zip \
  --client-org {OrgId} \
  --target-ds {OrgId}_DS \
  --import-folder-uri "/SmartCity/Report/Workstreams/{Folder}" \
  --keep-prefix resources/DataSource/ \
  --keep-prefix resources/SmartCity/Report/Workstreams/ \
  --staging-dir domains/manual_imports/{bundle}/_import_staging \
  --output-zip domains/manual_imports/{bundle}/{name}_client_import.zip \
  --patch-jrxml resources/SmartCity/Report/Workstreams/{Folder}/{Report}_files/main_jrxml.data \
  --patch-sql-file PATH_TO_QUERY.sql \
  --report-unit-xml resources/SmartCity/Report/Workstreams/{Folder}/{Report}.xml \
  --include-report-date
```

## Canonical example

Newark REP8 (validated 2026-09-02):

```bash
python3 scripts/jaspersoft/build_newark_rep8_report_import.py
```

→ `domains/manual_imports/newark_rep8_aged_balance_report/REP8_Aged_Balance_staging_client_import.zip`

## Error triage

| Error | Action |
|-------|--------|
| `organization_1 ... does not exist` | Rebuild with tenant-relative builder; include DS |
| `Reference resource ... DS not found` | Add DS to zip + index first resource |
| `no.such.export.process` | Refresh JRS session; fix zip path mismatch; retry |
| Warnings + skipped folders | Treat as failed deploy |

## Fallback

Publish JRXML from Jaspersoft Studio to the same repository path.
