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

## Two import models (do not mix them)

### A. Import inside a tenant (demo — `Origin_DEMO`)

Use when you are already **inside** the org in JRS and demo is a **single** tenant.

You typically change only:

- Datasource alias/endpoints: `Origin_DEV_DS` → `Origin_DEMO_DS` (and JDBC URL/user/password in the datasource XML)
- Report root folder family: `Standard_Offering` (demo default) or `Workstreams` when `map_standard_offering_to_workstreams` is true

You do **not** need per-report org segments like `/organizations/organization_1/organizations/Ellensburg/...` in domain or ad hoc XML. Paths stay tenant-root style:

- `/SmartCity/Report/Standard_Offering/...` (demo)
- `/DataSource/Origin_DEMO_DS`

Pipeline flags: `repository_layout: tenant_root`, `import_into_existing_tenant: true`, import from **inside** `Origin_DEMO`.

### B. Import from server root (test — six clients)

Use the **client promotion** pipeline when importing from the **server root** into separate client orgs (`Ellensburg`, `CityCorp`, etc.).

That flow **does** rewrite org names in repository paths and `index.xml` (`rootTenantId` = `organizations`), and swaps each client’s datasource (`Ellensburg_DS`, `CityCorp_DS`, …).

See [jaspersoft_client_promotion_pipeline.md](jaspersoft_client_promotion_pipeline.md).

## Current environments

| Environment ID | Target datasource | Output ZIP | Org paths |
| --- | --- | --- | --- |
| `origin_demo` | `Origin_DEMO_DS` | `standard_offering_Origin_DEMO_import.zip` | Tenant-root `Standard_Offering` export |

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
