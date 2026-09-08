# Jaspersoft client-tenant report import ZIPs

Validated on **Newark REP8** (2026-09-02). Use this pattern for single-report (or small-folder) imports while logged into a **client tenant** — same contract as Standard Offering tenant-relative packages.

## When to use

- Update an existing client report (JRXML / report unit) on JRS TEST/PROD
- Import from **inside the client org** (e.g. Newark1) → Repository → Import
- **Not** server-root import (`Manage` → `Organizations`) unless explicitly migrating orgs

## Working package shape

| Include | Why |
|---------|-----|
| `resources/DataSource/{Client}_DS.xml` | Same-batch DS reference; avoids `Reference resource ... not found` |
| `resources/public/templates/actual_size.820.jrxml.*` | Standard Offering index convention |
| `resources/SmartCity/Admin/Parameters/Report_Date.xml` | Only if report unit references it |
| Report folder under `resources/SmartCity/Report/...` | Must match `index.xml` **folder** URI exactly |
| Patched `main_jrxml.data` | Query / layout changes |

| Exclude | Why |
|---------|-----|
| `rootTenantId` in `index.xml` | Causes `import.organization.into.root.not.allowed` when inside tenant |
| `organizations/organization_1/...` paths | Wrong layout for client tenant import |
| `favorites/` tree | Stale user-specific IDs; can confuse import |
| `Standard_Offering/` copy of Workstreams report | Path mismatch (see pitfalls) |

## `index.xml` template (in-tenant)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<export>
  <property name="keyalias" value="..."/>
  <module id="repositoryResources">
    <resource>/DataSource/Newark1_DS</resource>
    <resource>/public/templates/actual_size.820.jrxml</resource>
    <folder>/SmartCity/Report/Workstreams/Debt_Management</folder>
  </module>
  <module id="favorites"/>
  <property name="pathProcessorId" value="zip"/>
  <property name="jsVersion" value="8.1.0 PRO"/>
  <property name="encrypted" value="..."/>
</export>
```

- **No** `rootTenantId`
- Datasource resource **before** folder
- `folder` URI must match report unit `<folder>` and zip tree **exactly**

## Build (automated)

Generic builder:

```bash
python3 scripts/jaspersoft/build_client_tenant_report_import.py \
  --source-zip /path/to/source_export.zip \
  --client-org Newark1 \
  --target-ds Newark1_DS \
  --import-folder-uri "/SmartCity/Report/Workstreams/Debt_Management" \
  --keep-prefix resources/DataSource/ \
  --keep-prefix resources/SmartCity/Report/Workstreams/ \
  --staging-dir domains/manual_imports/my_report/_import_staging \
  --output-zip domains/manual_imports/my_report/my_report_client_import.zip \
  --patch-jrxml resources/SmartCity/Report/Workstreams/Debt_Management/REP8_Aged_Balance_files/main_jrxml.data \
  --patch-sql-file sql/clients/newark/rep8_aged_balance/rep8_vw_jrxml_query.sql \
  --report-unit-xml resources/SmartCity/Report/Workstreams/Debt_Management/REP8_Aged_Balance.xml \
  --include-report-date
```

Newark REP8 wrapper (canonical example):

```bash
python3 scripts/jaspersoft/build_newark_rep8_report_import.py
```

Output: `domains/manual_imports/newark_rep8_aged_balance_report/REP8_Aged_Balance_staging_client_import.zip`

## Verify before import

Builder runs `verify_prepared_import.py` automatically. Manual check:

```bash
python3 scripts/jaspersoft/verify_prepared_import.py \
  --zip domains/manual_imports/newark_rep8_aged_balance_report/REP8_Aged_Balance_staging_client_import.zip \
  --target-org Newark1 \
  --target-ds Newark1_DS \
  --repository-uri-style org_relative \
  --repository-layout tenant_root \
  --expect-datasource-overlay \
  --import-module-folder-uri "/SmartCity/Report/Workstreams/Debt_Management"
```

Must show `status: PASS`.

## Import steps

1. Log into JRS as client tenant (breadcrumb shows org, e.g. **Newark1**)
2. Repository → Import → upload zip
3. Overwrite existing resources when prompted
4. Run report after any DB staging refresh completes

## Pitfalls (Newark REP8 lessons)

| Symptom | Cause | Fix |
|---------|-------|-----|
| `organization_1 ... does not exist` | `rootTenantId`, org-tree zip, or DS-only/report-only mismatch | Use tenant-relative builder; include DS in same zip |
| `Reference resource ... Newark1_DS not found` | Report-only zip without DS in batch | Include `DataSource/{Client}_DS` + index resource |
| `no.such.export.process` | Stale browser session **or** invalid JRXML (e.g. missing `</queryString>` after SQL patch) | Hard-refresh / incognito; rebuild zip with `build_newark_rep8_report_import.py`; re-import |
| Report at `Standard_Offering` but index says `Workstreams` | `promote_tenant_root_export_light_touch` rewrote paths | **Do not** use light-touch for Workstreams reports; use `build_client_tenant_report_import.py` |
| Import “succeeds” with warnings | Skipped folders — nothing updated | Read warnings; fix paths before assuming deploy worked |

## Fallback

Jaspersoft Studio: publish `REP8_Aged_Balance_staging_publish.jrxml` to the same repository path (no zip).

## Related

- [jaspersoft_client_promotion_pipeline.md](jaspersoft_client_promotion_pipeline.md) — full client SO promotion
- [jaspersoft_environment_promotion_troubleshooting.md](jaspersoft_environment_promotion_troubleshooting.md) — org / DS reference errors
- Skill: `.claude/skills/jaspersoft-client-tenant-import/SKILL.md`
- Newark DB staging: `sql/clients/newark/rep8_aged_balance/README.md`
