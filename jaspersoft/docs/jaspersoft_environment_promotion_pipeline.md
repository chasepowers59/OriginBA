# Jaspersoft Environment Promotion Pipeline

## Purpose

Prepare import ZIPs for **non-client** Jaspersoft environments where:

- repository org paths remain `Origin_DEV`
- only datasource aliases/endpoints change (for example `Origin_DEV_DS` -> `Origin_DEMO_DS`)
- output ZIP names use the datasource stem (for example `Origin_DEMO_import.zip`)

This is intentionally simpler than the SmartCity client promotion flow documented in
[jaspersoft_client_promotion_pipeline.md](jaspersoft_client_promotion_pipeline.md).

## Repo locations

Scripts:

- [promotion_environments.py](/Users/chase/OriginBA-3/scripts/jaspersoft/promotion_environments.py)
- [build_environment_datasource_export.py](/Users/chase/OriginBA-3/scripts/jaspersoft/build_environment_datasource_export.py)
- [prepare_client_imports.py](/Users/chase/OriginBA-3/scripts/jaspersoft/prepare_client_imports.py) (`--promotion-mode datasource`)
- [run_environment_import_pipeline.py](/Users/chase/OriginBA-3/scripts/jaspersoft/run_environment_import_pipeline.py)
- [verify_prepared_import.py](/Users/chase/OriginBA-3/scripts/jaspersoft/verify_prepared_import.py)

Staging and profiles:

- [deploy/jaspersoft_environment_promotion](/Users/chase/OriginBA-3/deploy/jaspersoft_environment_promotion)
- [environment_profiles.json](/Users/chase/OriginBA-3/deploy/jaspersoft_environment_promotion/environment_profiles.json)

## Standard promotion contract (all environments)

**Validated on Origin_STAGE and Origin_DEV (2026-06).** Use this for every
promotion going forward — internal and client.

### Import location

Always import **from inside the client’s tenant** (logged into that org →
**Repository** → Import). This is the client’s repository root: paths like
`/SmartCity/Report/Standard_Offering/...` and `/DataSource/<alias>`.

Do **not** import Standard Offering tenant-root ZIPs from server root
(Manage → Organizations). That path expects a different package shape
(`organizations` tree + `rootTenantId=organizations`) and causes
`not valid export file` or `import of an organization to the root is not allowed`.

### Package build flags (environment profile)

Every tenant-root promotion profile must set:

| Setting | Value | Why |
| --- | --- | --- |
| `repository_layout` | `tenant_root` | Matches export/import path style |
| `repository_uri_style` | `org_relative` | `/SmartCity/...`, `/DataSource/...` |
| `import_into_existing_tenant` | `true` | Omits `rootTenantId` from `index.xml` |
| `light_touch_tenant_root` | `true` | Preserves source ZIP entry order and export envelope |
| `use_canonical_index_encryption` | `true` (internal servers) | `keyalias`/`encrypted` from target JRS server |

### What the pipeline does (light-touch)

1. Rewrites datasource references in package XML (`Origin_DEV_DS` → target alias)
2. Injects canonical datasource XML from `deploy/jaspersoft_datasources/canonical/`
3. Patches `index.xml` in place (adds datasource + public template resources)
4. Repackages using **source ZIP entry order** (not a full folder-metadata rebuild)
5. Bundles `/public/templates/actual_size.820.jrxml` when dashboards are included

### Datasource policy

- **Do not override** an existing tenant datasource when adding snapshot-backed
  content. Add a **new alias** (for example `Training_DB` on `Origin_STAGE`) and
  point the import package at that alias only. Keep `Origin_STAGE_DS` on pstgdb.
- Store canonical exports per alias under `deploy/jaspersoft_datasources/canonical/`.

### Rebuild command (internal)

```bash
python3 scripts/jaspersoft/run_internal_standard_offering_pipeline.py \
  --source-zip "/path/to/standard offering.zip"
```

Single environment:

```bash
python3 scripts/jaspersoft/run_environment_import_pipeline.py \
  --environment origin_stage \
  --source-zip "/path/to/standard offering.zip" \
  --datasource-export-dir deploy/jaspersoft_datasources/canonical \
  --skip-archive
```

### Legacy: server-root / organizations tree

The old 102-report `organizations/organization_1/...` packages and server-root
client imports remain documented in
[jaspersoft_client_promotion_pipeline.md](jaspersoft_client_promotion_pipeline.md)
for reference only. **New promotions use the tenant-root contract above.**

## Current environments

| Environment ID | Target datasource | Output ZIP | Import inside tenant |
| --- | --- | --- | --- |
| `origin_demo` | `Origin_DEMO_DS` | `standard_offering_Origin_DEMO_import.zip` | `Origin_DEMO` |
| `origin_stage` | `Training_DB` (ptrndb snapshots) | `standard_offering_Origin_STAGE_import.zip` | `Origin_STAGE` |
| `origin_dev` | `Origin_DEV_DS` | `standard_offering_Origin_DEV_import.zip` | `Origin_DEV` |

`Origin_STAGE_DS` (pstgdb) is **not** replaced by Stage Standard Offering imports.

Canonical JDBC exports: `deploy/jaspersoft_datasources/canonical/`. Always inject
the target alias from canonical — never reuse `Origin_DEV_DS` JDBC from the source export.

Build both internal Standard Offering import ZIPs:

```bash
python3 scripts/jaspersoft/run_internal_standard_offering_pipeline.py \
  --source-zip "/path/to/Workstream folder.zip"
```

`origin_demo` uses **tenant-root** packaging for imports done **inside** `Origin_DEMO`:

- Artifact URIs stay `/SmartCity/Report/Standard_Offering/...` and `/DataSource/Origin_DEMO_DS`
- `index.xml` omits `rootTenantId` (avoids `import.organization.into.root.not.allowed`)
- `Origin_DEV_DS` is rewritten to `Origin_DEMO_DS` everywhere in package XML

## Standard packaging rules (required for every demo import)

Apply these on **every** `origin_demo` run (full Standard Offering or partial module export). They are implemented in [tenant_root_layout.py](/Users/chase/OriginBA-3/scripts/jaspersoft/tenant_root_layout.py), not manual post-steps.

| Rule | Why |
| --- | --- |
| Bundle `/public/templates/actual_size.820.jrxml` | Dashboards reference this shared JRXML; import only resolves templates listed in the same ZIP |
| Merge `Workstreams/Development` into `Standard_Offering/Development` before dropping Workstreams | Reports reference snapshot Domains under `.../Development/Snapshots/...` |
| Regenerate all `.folder.xml` under `resources/SmartCity/` | Prevents `Reference resource null` from stale org-scoped parents |
| Include `Origin_DEMO_DS` in ZIP and `index.xml` | Avoids datasource reference failures inside the tenant |
| Set `import_module_folder_uri` to the folder being imported | Full export: `/SmartCity/Report/Standard_Offering`; module export: that module path |

Bundled dashboard template source (committed):

- `deploy/jaspersoft_environment_promotion/bundled/public_dashboard_template/`

Prepared `index.xml` resource order:

1. `/DataSource/Origin_DEMO_DS`
2. `/public/templates/actual_size.820.jrxml`
3. `<folder>` for the import root (for example `/SmartCity/Report/Standard_Offering`)

## What the pipeline does

1. loads the environment profile (JDBC URL, user, encrypted password, target datasource name)
2. builds or reuses the `Origin_DEMO_DS` datasource export overlay
3. rewrites the source export with `--promotion-mode datasource`
4. repackages to tenant-root layout (rules above)
5. validates that `Origin_DEV_DS` is gone and `Origin_DEMO_DS` is present
6. writes `<output_zip_stem>_import.zip` (for example `standard_offering_Origin_DEMO_import.zip`)
7. archives the original source export ZIP on success

## Recommended commands

### Full pipeline

```bash
python3 scripts/jaspersoft/run_environment_import_pipeline.py \
  --environment origin_demo \
  --source-zip deploy/jaspersoft_environment_promotion/incoming_exports/example.zip \
  --rebuild-datasource
```

### Dry run

```bash
python3 scripts/jaspersoft/run_environment_import_pipeline.py \
  --environment origin_demo \
  --source-zip deploy/jaspersoft_environment_promotion/incoming_exports/example.zip \
  --rebuild-datasource \
  --dry-run
```

### Verify before server import

Quick ZIP checks:

```bash
unzip -p deploy/jaspersoft_environment_promotion/prepared_imports/standard_offering_Origin_DEMO_import.zip index.xml
unzip -l deploy/jaspersoft_environment_promotion/prepared_imports/standard_offering_Origin_DEMO_import.zip | grep -E "public/templates|Development/Snapshots"
```

Confirm `index.xml` lists both `/DataSource/Origin_DEMO_DS` and `/public/templates/actual_size.820.jrxml`, and that Development snapshot Domain XML is present under `Standard_Offering/Development/Snapshots/`.

## Add another environment

1. Add a new object to `environment_profiles.json`.
2. Set `src_org`, `src_ds`, `target_org`, `target_ds`, `output_zip_stem`, and JDBC `datasource` values.
3. Run the pipeline with `--environment <new_id>`.

Keep encrypted Jaspersoft passwords in the profile file only when they are already maintained in exported datasource XML elsewhere in the repo.

## Troubleshooting import warnings

See [jaspersoft_environment_promotion_troubleshooting.md](jaspersoft_environment_promotion_troubleshooting.md)
for dashboard template warnings, Development snapshot Domain warnings, `organization that does not exist`, and `Reference resource null` during datasource import.

## Related: Oracle snapshot tables on demo

Jaspersoft import and Oracle snapshot rollout are separate steps. After content import, use [smartcity_demo_snapshot_rollout_runbook.md](smartcity_demo_snapshot_rollout_runbook.md) for the seven `*_RPT_CURR` tables on the demo database (`--client demo`).

## Boundaries

This tooling does not:

- connect to Oracle for validation
- decrypt `ENC<...>` passwords for local SQL runners
- perform the Jaspersoft Server import itself

Use the deployment runbook for post-import smoke testing.
