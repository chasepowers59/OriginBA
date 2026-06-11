# Jaspersoft Client Promotion Pipeline

## Purpose

This runbook documents the local promotion-preparation flow used to rewrite a
Jaspersoft Server export from `Origin_DEV` into client-specific import bundles.

This capability is intentionally separate from:

- Oracle database work
- snapshot refresh procedures
- SQL validation packs
- Domain design and semantic-layer engineering

Its scope is limited to Jaspersoft repository package preparation and
verification.

## Import location (standard as of 2026-06)

**Import every prepared ZIP from inside the client’s tenant** (logged into that
org → Repository → Import). This matches the validated Origin_STAGE / Origin_DEV
flow (light-touch tenant-root packages, no `rootTenantId` in `index.xml`).

Server-root import (`Manage` → `Organizations`) is legacy only for old
`organizations/organization_1/...` packages.

Package builds for new client promotions should use the same tenant-root +
light-touch flags documented in
[jaspersoft_environment_promotion_pipeline.md](jaspersoft_environment_promotion_pipeline.md)
(**Standard promotion contract**), with per-client datasource aliases from
`client_org_mapping.csv`.

It is designed for SmartCity client promotions where:

- the source export comes from the `Origin_DEV` organization
- repository paths must be rewritten to the target client organization
- datasource aliases must be rewritten from `Origin_DEV_DS` to the target alias
- the final package must preserve Jaspersoft repository export structure

This pipeline prepares packages only. It does not perform the server import.

It also does not depend on:

- Oracle connectivity
- snapshot tables
- local SQL runners
- the active 7-snapshot performance workstream

## Related: environment-only promotions

For non-client targets that keep `Origin_DEV` org paths and only swap datasource
aliases (for example `Origin_DEMO_DS`), use:

- [jaspersoft_environment_promotion_pipeline.md](jaspersoft_environment_promotion_pipeline.md)

## Repo Locations

Scripts:

- [prepare_client_imports.py](/Users/chase/OriginBA-3/scripts/jaspersoft/prepare_client_imports.py)
- [run_client_import_pipeline.py](/Users/chase/OriginBA-3/scripts/jaspersoft/run_client_import_pipeline.py)
- [archive_processed_export.py](/Users/chase/OriginBA-3/scripts/jaspersoft/archive_processed_export.py)
- [verify_prepared_import.py](/Users/chase/OriginBA-3/scripts/jaspersoft/verify_prepared_import.py)

Staging area:

- [deploy/jaspersoft_client_promotion](/Users/chase/OriginBA-3/deploy/jaspersoft_client_promotion)

Repository path truth references:

- [current_snapshot_repository_path_truth.md](/Users/chase/OriginBA-3/docs/current_snapshot_repository_path_truth.md)
- [jaspersoft_repository_export_structure.md](/Users/chase/OriginBA-3/docs/jaspersoft_repository_export_structure.md)
- [jaspersoft_repository_import_debugging_runbook.md](/Users/chase/OriginBA-3/docs/jaspersoft_repository_import_debugging_runbook.md)
- [jaspersoft_promotion_endpoint_dependency_contract.md](/Users/chase/OriginBA-3/docs/jaspersoft_promotion_endpoint_dependency_contract.md)

## SmartCity Client Mapping

Current client org-to-datasource template:

- `Ellensburg -> Ellensburg_DS`
- `CityCorp -> CityCorp_DS`
- `College_Station -> CollegeStation_DS`
- `Fond_Du_Lac -> FondDuLac_DS`
- `Newark1 -> Newark1_DS`
- `Odessa -> Odessa_DS`

Tracked template file:

- [client_org_mapping.csv](/Users/chase/OriginBA-3/deploy/jaspersoft_client_promotion/client_org_mapping.csv)

Important rule:

- the first column must be the Jaspersoft repository organization resource ID,
  not the UI display label

## Folder Layout

Use the staging folders exactly like this:

- `incoming_exports/`
  - untouched ZIPs exported from Jaspersoft Server
- `incoming_datasources/`
  - one datasource export ZIP or extracted folder per target org
- `prepared_imports/`
  - final rewritten ZIPs ready for import
- `prepared_imports/_tmp/`
  - temporary script workspace only
- `archive/`
  - original export ZIPs after successful rewrite

## What The Pipeline Does

For each target org in the mapping file, the rewrite pipeline:

1. extracts the source export package
2. rewrites content references from source org and datasource to target org and
   datasource
3. renames file and folder paths containing those identifiers
4. strips datasource resources by default
5. optionally overlays the target datasource export back into the package
6. validates that:
   - the target org root exists
   - favorites, if present, point at the target org
   - target datasource strings exist in package contents
   - no leftover source org or source datasource identifiers remain
7. emits one `<TARGET_ORG>_import.zip` per target
8. archives the original export ZIP only if every target succeeded

## Repository Pathing Assumptions

This pipeline preserves the full exported repository hierarchy.

That matters because Jaspersoft import behavior is sensitive to:

- `index.xml` at ZIP root
- `resources/`
- `favorites/` when present
- `.folder.xml` files
- `_files/` companion folders
- full org-scoped pathing under:
  - `resources/organizations/organization_1/organizations/<TARGET_ORG>/...`

For current snapshot artifacts, use the repository truth in:

- [current_snapshot_repository_path_truth.md](/Users/chase/OriginBA-3/docs/current_snapshot_repository_path_truth.md)

## Recommended commands

### Standard Offering — all six clients

Canonical JDBC exports: `deploy/jaspersoft_datasources/clients/`

```bash
python3 scripts/jaspersoft/run_client_standard_offering_pipeline.py \
  --source-zip "/path/to/standard offering.zip" \
  --skip-archive
```

One client:

```bash
python3 scripts/jaspersoft/run_client_standard_offering_pipeline.py \
  --source-zip "/path/to/standard offering.zip" \
  --clients Ellensburg \
  --skip-archive
```

Outputs: `prepared_imports/<Client>_Standard_Offering_import.zip`

Import **inside each client tenant** (Repository → Import).

Each package injects the full `{Client}_DS.xml` (JDBC URL, user, encrypted password)
and rewrites all Domains/Ad Hocs to `/DataSource/{Client}_DS`.

### Lower-level client pipeline

```bash
python3 scripts/jaspersoft/run_client_import_pipeline.py \
  --source-zip deploy/jaspersoft_client_promotion/incoming_exports/example.zip \
  --mapping deploy/jaspersoft_client_promotion/client_org_mapping.csv \
  --skip-archive
```

Defaults: tenant-root light-touch, datasource overlay from `deploy/jaspersoft_datasources/clients/`.

### 1. Full pipeline without datasource overlay (legacy — not recommended)

```bash
python3 scripts/jaspersoft/run_client_import_pipeline.py \
  --source-zip deploy/jaspersoft_client_promotion/incoming_exports/example.zip \
  --mapping deploy/jaspersoft_client_promotion/client_org_mapping.csv \
  --src-org Origin_DEV \
  --src-ds Origin_DEV_DS \
  --outdir deploy/jaspersoft_client_promotion/prepared_imports \
  --archive-dir deploy/jaspersoft_client_promotion/archive
```

### 2. Full pipeline with datasource overlay

Use this when the target import package must contain the target datasource
resource during import.

```bash
python3 scripts/jaspersoft/run_client_import_pipeline.py \
  --source-zip deploy/jaspersoft_client_promotion/incoming_exports/example.zip \
  --mapping deploy/jaspersoft_client_promotion/client_org_mapping.csv \
  --src-org Origin_DEV \
  --src-ds Origin_DEV_DS \
  --datasource-export-dir deploy/jaspersoft_client_promotion/incoming_datasources \
  --outdir deploy/jaspersoft_client_promotion/prepared_imports \
  --archive-dir deploy/jaspersoft_client_promotion/archive
```

### 3. Dry run

```bash
python3 scripts/jaspersoft/run_client_import_pipeline.py \
  --source-zip deploy/jaspersoft_client_promotion/incoming_exports/example.zip \
  --mapping deploy/jaspersoft_client_promotion/client_org_mapping.csv \
  --src-org Origin_DEV \
  --src-ds Origin_DEV_DS \
  --datasource-export-dir deploy/jaspersoft_client_promotion/incoming_datasources \
  --outdir deploy/jaspersoft_client_promotion/prepared_imports \
  --archive-dir deploy/jaspersoft_client_promotion/archive \
  --dry-run
```

## Verification Command

After a package is produced, verify the rewritten endpoints before import.

Example with datasource overlay:

```bash
python3 scripts/jaspersoft/verify_prepared_import.py \
  --zip deploy/jaspersoft_client_promotion/prepared_imports/Ellensburg_import.zip \
  --target-org Ellensburg \
  --target-ds Ellensburg_DS \
  --source-org Origin_DEV \
  --source-ds Origin_DEV_DS \
  --expect-datasource-overlay
```

Example without datasource overlay:

```bash
python3 scripts/jaspersoft/verify_prepared_import.py \
  --zip deploy/jaspersoft_client_promotion/prepared_imports/Ellensburg_import.zip \
  --target-org Ellensburg \
  --target-ds Ellensburg_DS \
  --source-org Origin_DEV \
  --source-ds Origin_DEV_DS
```

The verifier checks:

- target org root under `resources/organizations/organization_1/organizations/<TARGET_ORG>/`
- favorites root, if present
- datasource XML presence or absence depending on overlay mode
- `index.xml` repository resource entry when overlay mode is on
- target datasource string in readable contents
- target repository URIs in readable contents
- absence of leftover source org and source datasource identifiers

## Datasource Overlay Rules

- never reuse the `Origin_DEV` datasource XML in a client package
- put one target datasource export ZIP or extracted folder in
  `incoming_datasources/`
- name the export after the target datasource or target org when possible

Accepted naming patterns:

- `Ellensburg_DS.zip`
- `Ellensburg.zip`
- `FondDuLac_DS.zip`
- `Fond_Du_Lac.zip`
- extracted folders matching the same resource IDs

## Functional Boundaries

This tooling helps with:

- package rewrite
- repository path rewrite
- datasource alias rewrite
- datasource overlay
- leftover-source validation
- pre-import package verification

This tooling does not replace:

- database deployment
- SQL promotion
- Domain modeling
- snapshot QA
- export from source Jaspersoft
- backup of target objects
- actual server import
- datasource credential restore
- report smoke testing after import

Use the deployment runbook for that:

- [deployment-runbook-smartcity-new-packages.md](/Users/chase/OriginBA-3/docs/deployment-runbook-smartcity-new-packages.md)

## Why This Was Added To The Repo

This repository already had:

- repository path truth documents
- import-debugging runbooks
- report-unit packaging scripts

What it did not have was a maintained, repeatable client-promotion pipeline for
rewriting exported DEV packages into client-scoped import bundles. This closes
that gap and makes the client promotion process reproducible from the repo.
