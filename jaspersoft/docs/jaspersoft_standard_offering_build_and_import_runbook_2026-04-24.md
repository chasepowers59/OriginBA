# Jaspersoft Standard Offering Build And Import Runbook

## Purpose

This runbook documents how the `Standard_Offering` Jaspersoft import package was built from the exported `Workstreams` folder, what issues were encountered during import, how those issues were resolved, and what to keep in mind the next time this package is rebuilt or promoted.

Primary package artifacts:

- [Standard_Offering_import.zip](/Users/chase/OriginBA-3/deploy/jaspersoft_standard_offering/Standard_Offering_import.zip)
- [standard_offering_package_audit.json](/Users/chase/OriginBA-3/deploy/jaspersoft_standard_offering/standard_offering_package_audit.json)
- [standard_offering_verification.json](/Users/chase/OriginBA-3/deploy/jaspersoft_standard_offering/standard_offering_verification.json)

Primary builder and verifier:

- [build_standard_offering_package.py](/Users/chase/OriginBA-3/scripts/jaspersoft/build_standard_offering_package.py)
- [verify_standard_offering_package.py](/Users/chase/OriginBA-3/scripts/jaspersoft/verify_standard_offering_package.py)
- [run_standard_offering_pipeline.py](/Users/chase/OriginBA-3/scripts/jaspersoft/run_standard_offering_pipeline.py)

## Source Inputs

Source export used for this build:

- `/Users/chase/Downloads/Workstream folder.zip`

Source-of-truth report list used for selection:

- the SmartCity standard offering list provided in chat for `103` reports across `9` workstreams

Selection rule used:

- match by exported outer report label
- do not trust generic internal file names like `Ad_Hoc_View_1`

## Final Package Outcome

Final packaged content:

- `102` packaged items
- `35` unique Domain resources
- `1` required datasource resource:
  - `/organizations/organization_1/organizations/Origin_DEV/DataSource/Origin_DEV_DS`

Final packaged workstream counts:

- Finance: `13`
- Billing and Rates: `12`
- Meter Operations: `18`
- Cashiering: `14`
- Common: `8`
- Customer Operations: `14`
- New Services: `4`
- Debt Management: `12`
- Field Operations: `7`

Items intentionally excluded:

- `Measurement - SP Type`
  - excluded because the user-provided offering document said Meter Operations had `18` total reports, but listed `19` lines
- `Billed Usage and Amount Charged`
  - excluded because it is a dashboard carrying a shared public-template dependency not wanted in this package

## What Was Built

The package creates a separate folder tree:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Standard_Offering`

It does not move or delete anything from:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams`

This means import creates a curated parallel copy, not a move.

## Main Steps Performed

### 1. Inventory And Classify The Export

The source ZIP was scanned to identify:

- `reportUnit`
- `adhocDataView`
- `dashboardModelResource`
- `semanticLayerDataSource`
- datasource resources

The package builder uses exported outer labels as the matching key so the final selection aligns to business-facing report names rather than generic internal IDs.

### 2. Select Only The Standard Offering

The builder selected the desired report/ad hoc/dashboard objects from the full `Workstreams` export and remapped them into a curated `Standard_Offering` folder tree by workstream and business process.

### 3. Carry Only The Required Domains

For each selected report or Ad Hoc view, the assigned Domain was carried into the package.

Rules used:

- keep only one packaged copy of each Domain
- choose a single business-process home for that Domain inside `Standard_Offering`
- rewrite report and Ad Hoc references so they point to the packaged Domain location

### 4. Carry The Required Datasource

The source export already contained:

- `resources/organizations/organization_1/organizations/Origin_DEV/DataSource/.folder.xml`
- `resources/organizations/organization_1/organizations/Origin_DEV/DataSource/Origin_DEV_DS.xml`

Those members were added to the package because Domain imports referenced:

- `/organizations/organization_1/organizations/Origin_DEV/DataSource/Origin_DEV_DS`

Without that datasource resource, import failed.

### 5. Rewrite Repository Paths

The builder rewrote:

- `/Workstreams/...` references to `/Standard_Offering/...`
- report folder URIs
- Domain folder URIs
- local resource folders inside packaged report/ad hoc payloads
- report-to-Domain datasource references

### 6. Build Folder Metadata

The builder generated `.folder.xml` metadata for the new `Standard_Offering` tree so Jaspersoft imports the new hierarchy cleanly.

### 7. Build A Valid `index.xml`

The final import manifest was narrowed to:

- folder:
  - `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Standard_Offering`
- resource:
  - `/organizations/organization_1/organizations/Origin_DEV/DataSource/Origin_DEV_DS`

This was important. A broader root import declaration caused server import failures.

### 8. Remove Unwanted Ad Hoc Wrapper Reports

Many saved `adhocDataView` resources contained nested `<reports>...</reports>` blocks. Those nested blocks pointed to:

- `/public/templates/actual_size.820.jrxml`

Those wrapper reports exist for dashboard/print/export rendering and are not required when the goal is to keep only the saved Ad Hoc view.

The builder now strips those nested wrapper reports from saved Ad Hoc views while preserving:

- the Ad Hoc view itself
- its Domain link
- its input controls
- its saved query state

### 9. Remove One Unwanted Dashboard

After stripping Ad Hoc wrappers, one remaining dependency on `/public/templates/actual_size.820.jrxml` still existed.

That remaining object was:

- `Billed Usage and Amount Charged`

It was not a plain Ad Hoc view. It was a `dashboardModelResource` that embedded dashboard components depending on the shared public template path.

Because that dashboard was not needed in this curated package, it was removed entirely from the final package.

## Import Failures Encountered And Fixes

### Failure 1. Missing Datasource

Initial import error:

- `Reference resource /organizations/organization_1/organizations/Origin_DEV/DataSource/Origin_DEV_DS not found`

Cause:

- the package included Domains that referenced `Origin_DEV_DS`
- but the package did not carry the datasource resource itself

Fix:

- include `Origin_DEV_DS.xml` and its `.folder.xml`
- verify Domains reference the packaged datasource

### Failure 2. Invalid Import Root

Server error:

- `Folder details for folder "/organizations/organization_1/organizations/Origin_DEV" were not found in the import information`

Cause:

- the package `index.xml` was temporarily broadened to import from the whole `Origin_DEV` org root
- but the package did not contain folder metadata for that org root

Fix:

- narrow `index.xml` to import only:
  - the `Standard_Offering` folder
  - the datasource resource

### Warning 3. Missing Public Template

Import warnings:

- `Reference resource /public/templates/actual_size.820.jrxml not found`

Cause:

- many saved Ad Hoc views contained nested report wrappers pointing to Jasper public templates
- one dashboard also depended on that template

Fix:

- strip the nested report wrapper from saved Ad Hoc views
- remove the `Billed Usage and Amount Charged` dashboard from the package

Final result:

- no remaining `/public/templates/actual_size.820.jrxml` references in the package

## Import Settings Used

Recommended import choices for this package:

- import file: `Standard_Offering_import.zip`
- key: `Legacy Key` when prompted
- strategy: `Update`

Important:

- this import updates or creates `Standard_Offering`
- it does not move or delete anything in `Workstreams`

## Validation Performed

Validation was performed with:

- [verify_standard_offering_package.py](/Users/chase/OriginBA-3/scripts/jaspersoft/verify_standard_offering_package.py)

Checks performed:

- package contains expected item count
- package contains expected workstream counts
- package contains `35` unique Domain resources
- datasource resource is present
- `index.xml` includes the correct folder and datasource resource
- Domain resources point to `Origin_DEV_DS`
- report and Ad Hoc objects live under `Standard_Offering`
- no duplicate Domain XML names
- no leftover `/public/templates/actual_size.820.jrxml` dependencies

## What To Keep In Mind Next Time

### 1. Always Inventory The Export First

Do not assume a resource is only:

- a report
- an Ad Hoc view
- a Domain
- a dashboard

Exported Jaspersoft objects often contain nested dependencies.

### 2. Match By Outer Label, Not File Name

Saved Ad Hoc exports often use generic file names like:

- `Ad_Hoc_View_1`
- `Ad_Hoc_View_3`

The exported outer label is the reliable business-facing identifier.

### 3. Domains Are Not Enough By Themselves

If a Domain points to a datasource, the datasource must exist in the target server or be packaged with the import.

Check for:

- `/organizations/.../DataSource/...`

before import.

### 4. Keep Domains Single-Copy Inside The Curated Package

Do not duplicate Domains into multiple business-process folders just because multiple reports use them.

Instead:

- choose one home location
- rewrite all report references to that one packaged Domain URI

### 5. Keep The `index.xml` Manifest Narrow

Do not point the package at the entire org root unless the package truly carries that whole root tree.

For curated imports:

- include only the exact folder(s) and resource(s) the package needs

### 6. Saved Ad Hoc Views May Carry Report Dependencies

Even if an object is an `adhocDataView`, it may still contain:

- nested report wrappers
- dashboard report units
- public template references

If the business need is only the saved Ad Hoc view, those wrappers can be stripped.

### 7. Dashboards Need Separate Scrutiny

Dashboards are not equivalent to saved Ad Hoc views.

They may embed:

- temporary Ad Hoc views
- shared public templates
- dashboard component wiring

If dashboards are not needed in the package, exclude them explicitly.

### 8. Verify Before Import, Not After Failure

Before future imports, always verify:

- datasource included or already exists on target
- Domains point to valid datasource URIs
- no leftover `/Workstreams/` references
- no `/public/templates/...` dependencies unless intentionally accepted
- packaged counts match the intended curated offering

## Recommended Next-Time Workflow

1. Export source folder from Jaspersoft.
2. Run the one-command pipeline:

```bash
python3 /Users/chase/OriginBA-3/scripts/jaspersoft/run_standard_offering_pipeline.py
```

3. If the source ZIP or output directory differs, use:

```bash
python3 /Users/chase/OriginBA-3/scripts/jaspersoft/run_standard_offering_pipeline.py \
  --source-zip "/absolute/path/to/Workstream folder.zip" \
  --outdir /absolute/path/to/output_dir
```

4. Check the audit JSON for:
   - count
   - exclusions
   - datasource inclusion
5. Import with `Legacy Key` and `Update`.
6. Smoke-test a small sample of:
   - one snapshot report
   - one live Domain report
   - one saved Ad Hoc view
7. Confirm `Workstreams` remains untouched and `Standard_Offering` exists as a separate curated tree.

## Current Decision Record

The final decision for this package is:

- keep a curated `Standard_Offering` tree separate from `Workstreams`
- keep `102` packaged items
- keep `35` unique Domains
- include `Origin_DEV_DS`
- strip Ad Hoc wrapper reports
- exclude `Billed Usage and Amount Charged`

That is the current clean importable baseline.
