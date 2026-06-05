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

## Warning: Reference resource /public/templates/actual_size.820.jrxml not found (dashboards)

Dashboards reference a shared JRXML layout template at `/public/templates/actual_size.820.jrxml`.
That path is **not** part of the SmartCity export tree. Even if the template already exists in
the repository UI under Public, the import batch only resolves references that are **included in
the same ZIP** (listed in `index.xml`).

The `origin_demo` pipeline now bundles the template from
`deploy/jaspersoft_environment_promotion/bundled/public_dashboard_template/` and adds:

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
