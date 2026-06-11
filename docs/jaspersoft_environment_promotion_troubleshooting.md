# Jaspersoft Environment Promotion Troubleshooting

## Demo server uses tenant `Origin_DEMO` (not `organizations/.../Origin_Demo`)

A demo export from Jaspersoft shows:

- `index.xml` property `rootTenantId` = `Origin_DEMO`
- ZIP paths like `resources/SmartCity/Report/Workstreams/...` (no `organizations/organization_1/...` prefix)
- Datasource at `resources/DataSource/Origin_DEMO_DS.xml` with `<folder>/DataSource</folder>`
- Artifact folders like `/SmartCity/Report/Workstreams/Billing_and_Rates/Bill_Segment`

Environment packages must use `repository_layout: tenant_root` in
`environment_profiles.json`. The pipeline repackages DEV exports into this layout
before import.

## Error: Provided zip file is not valid JasperReports Server export file

Jaspersoft rejects the ZIP before import when the export manifest does not match a
real server export.

Required contract:

1. `index.xml` element order:
   - `property keyalias`
   - `module repositoryResources`
   - `module favorites`
   - `property pathProcessorId`
   - `property jsVersion`
   - `property encrypted`
   - omit `rootTenantId` when importing inside an existing tenant
2. Empty `favorites/` directory at ZIP root (ZIP entry must use `ZIP_DEFLATED`, not `ZIP_STORED`)
3. `index.xml` must be the **last** ZIP entry
4. `index.xml` must use compact JRS formatting (`<module id="favorites"/>`, not spaced self-closing tags)
5. Internal servers (`Origin_STAGE`, `Origin_DEV`) use a different export encryption key
   than demo/test exports. For those environments, set `use_canonical_index_encryption:
   true` and `light_touch_tenant_root: true` in the profile so the package keeps the
   source ZIP entry order and uses the target server's `keyalias`/`encrypted` metadata
6. Demo/external promotions can keep the source export `keyalias`/`encrypted` values when
   importing onto the same server family that produced the export

Pipeline mistakes to avoid:

- Setting `rootTenantId=Origin_STAGE` on a tenant-root content ZIP and importing from
  server root → `Import of an organization to the root is not allowed`
- Replacing source-export `keyalias`/`encrypted` with canonical datasource index metadata
  on a large content ZIP

## Error: Import of an organization to the root is not allowed (Origin_STAGE)

### Meaning

The ZIP includes `rootTenantId=Origin_STAGE` in `index.xml`. JRS interprets that as
“import the `Origin_STAGE` organization into server root,” which is blocked.

Tenant-root Standard Offering packages are **content imports** (folders under
`/SmartCity/Report/Standard_Offering`), not organization imports.

### Fix

1. Rebuild with `import_into_existing_tenant: true` for `origin_stage` (omits
   `rootTenantId` from `index.xml`).
2. Import **while scoped to the `Origin_STAGE` tenant**:
   - Log in as a user with access to `Origin_STAGE`
   - Open **Repository** inside that tenant (not server-root Manage → Organizations)
   - **Import** `standard_offering_Origin_STAGE_import.zip`

Do not use server-root organization import for this package shape. The legacy 102-report
package worked from root because it used `rootTenantId=organizations` and the full
`organizations/organization_1/...` tree — a different import contract.

Rebuild after fixing:

```bash
python3 scripts/jaspersoft/run_internal_standard_offering_pipeline.py \
  --source-zip "/path/to/standard offering.zip"
```

## Warning: Reference resource /public/templates/actual_size.820.jrxml not found (dashboards)

Dashboards reference a shared JRXML layout template at `/public/templates/actual_size.820.jrxml`.
That path is **not** part of the SmartCity export tree. Even if the template already exists in
the repository UI under Public, the import batch only resolves references that are **included in
the same ZIP** (listed in `index.xml`).

The environment pipelines bundle the template from
`deploy/jaspersoft_environment_promotion/bundled/public_dashboard_template/` and add:

```xml
<resource>/public/templates/actual_size.820.jrxml</resource>
```

to `index.xml` before the Standard Offering folder entry.

Rebuild:

```bash
python3 scripts/jaspersoft/run_environment_import_pipeline.py \
  --environment origin_demo \
  --source-zip path/to/full_export.zip
```

## Warning: Reference resource .../Development/Snapshots/... not found (reports)

Some Standard Offering reports reference snapshot Domains under
`/SmartCity/Report/Standard_Offering/Development/Snapshots/...`. Those Domains often live only
under the legacy `Workstreams/Development` tree in the source export. The demo repackage step
now merges `Workstreams/Development` into `Standard_Offering/Development` before removing the
Workstreams tree.

If this warning persists after rebuilding the import ZIP, confirm the source export still
contains the Development snapshot Domains.

## Error: import.organization.into.root.not.allowed (Origin_DEMO)

### Meaning

You are importing **while already inside** the `Origin_DEMO` tenant. The ZIP must
import **content only** (folders under `/SmartCity/...`), not the organization itself.

If `index.xml` contains `<property name="rootTenantId" value="Origin_DEMO" />`, JRS
can interpret the package as “import organization Origin_DEMO into root” and reject it.

### Fix

Set in `environment_profiles.json`:

```json
"import_into_existing_tenant": true
```

The pipeline omits `rootTenantId` from `index.xml` for those packages. Rebuild and
re-import while scoped to `Origin_DEMO`.

Use `import_into_existing_tenant: false` only when importing from the server root
into a net-new tenant (uncommon for demo).

## Warning: organization does not exist in the target server

Example:

```text
The folder /organizations/organization_1/organizations/Origin_Demo/SmartCity/Report/Standard_Offering/Field_Operations
belongs to an organization that does not exist in the target server. Skipping this folder.
```

### Meaning

The import ZIP names an organization resource ID that Jaspersoft cannot find on the demo server. When that happens, JRS **skips the entire folder tree** under that org, so domains/ad hoc views in the package are not imported to the intended location.

This is almost always an **organization resource ID mismatch** (spelling/casing), not a report defect.

### Fix

1. In demo Jaspersoft Server, open **Repository** and find the organization you import into.
2. Copy the exact resource ID from the path (case-sensitive). Common variants:
   - `Origin_Demo`
   - `Origin_DEMO`
   - `Origin_DEV` (if demo still uses the DEV org name)
3. Update `target_org` and `import_module_folder_uri` in
   `deploy/jaspersoft_environment_promotion/environment_profiles.json`.
4. Rebuild the import ZIP with `run_environment_import_pipeline.py`.
5. Re-import.

If no suitable organization exists yet, create it on the demo server first, then rebuild the package.

## Warning: Reference resource null (datasource)

Example:

```text
Reference resource null not found when importing resource
/organizations/organization_1/organizations/Origin_Demo/DataSource/Origin_DEMO_DS
```

### Meaning

JRS tried to import `Origin_DEMO_DS` under `DataSource`, but the parent organization folder was skipped (see above), so the datasource has **no parent org** to attach to. The reference resolves to `null`.

### Fix options

**Option A — fix organization first (recommended)**

Correct `target_org`, rebuild, re-import. The datasource can be included in the ZIP once the org exists.

**Option B — include datasource in the same import ZIP (recommended)**

If you see `import.reference.resource.not.found` for `/DataSource/Origin_DEMO_DS`, the content package references that datasource but the import batch did not contain it. JRS resolves references from the **current import package**, not only pre-existing repository objects.

Set in the environment profile:

```json
"skip_datasource_import": false
```

Rebuild so the ZIP includes `resources/DataSource/Origin_DEMO_DS.xml` and `index.xml` lists the datasource **before** the Field Operations folder.

## Verify after import

Under the correct organization in Repository, confirm:

- `SmartCity/Report/Workstreams/Field_Operations/` (or Standard Offering path, depending on server layout)
- Domains and ad hoc views open without `Data source not found`
- Domain datasource alias is `Origin_DEMO_DS`

## Quick checklist

| Check | Action |
| --- | --- |
| Org ID exact match | Compare JRS Repository path to `target_org` in profile |
| Datasource on server | Use `skip_datasource_import: true` if already present |
| Import index folder | Must match packaged `.folder.xml` tree under that org |
| Artifact URIs | Short `/SmartCity/Report/Workstreams/...` paths are OK after org exists |
