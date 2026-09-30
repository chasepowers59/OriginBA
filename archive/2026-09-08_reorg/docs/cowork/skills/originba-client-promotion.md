---
name: originba-client-promotion
description: Prepare Jaspersoft Standard Offering or folder import ZIPs for SmartCity client tenants.
---

# OriginBA Client Promotion

## When to use

- Rewriting Origin_DEV exports for client TEST/PROD tenants
- Device folder, VEE patch, or partial Standard Offering re-imports
- Validating prepared import ZIPs before manual Repository import

## Required references

- `docs/jaspersoft_client_promotion_pipeline.md`
- `deploy/jaspersoft_client_promotion/README.md`
- `deploy/jaspersoft_client_promotion/client_org_mapping.csv`
- `deploy/jaspersoft_datasources/clients/README.md`
- `docs/jaspersoft_environment_promotion_troubleshooting.md`

## Steps

1. Source from Origin_DEV; rewrite org paths and datasource to client alias (inject JDBC overlay, not rename-only).
2. Use tenant-root light-touch packaging; omit `rootTenantId` for existing-tenant import.
3. Inject canonical datasource from `deploy/jaspersoft_datasources/clients/<Client>_DS/`.
4. Patch VEE Exception To Do joins to left outer before promotion when needed:
   ```bash
   python3 scripts/jaspersoft/patch_vee_exception_todo_joins.py --source ... --output ...
   ```
5. Build package:
   ```bash
   python3 scripts/jaspersoft/prepare_client_imports.py ...
   ```
6. Validate:
   ```bash
   python3 scripts/jaspersoft/verify_prepared_import.py --zip ... --target-org ... --target-ds ...
   ```
7. Import inside client tenant Repository (not server root).

## Output contract

- Prepared ZIP under `deploy/jaspersoft_client_promotion/prepared_imports/`
- Verification JSON with no leftover `Origin_DEV` / `Origin_DEV_DS`
- Import folder URI documented
