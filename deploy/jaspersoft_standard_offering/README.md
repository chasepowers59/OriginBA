# Standard Offering Import Package

Artifacts:

- `Standard_Offering_import.zip`
- `standard_offering_package_audit.json`
- `standard_offering_verification.json`
- detailed runbook:
  - [jaspersoft_standard_offering_build_and_import_runbook_2026-04-24.md](/Users/chase/OriginBA-3/docs/jaspersoft_standard_offering_build_and_import_runbook_2026-04-24.md)
- one-command rebuild wrapper:
  - [run_standard_offering_pipeline.py](/Users/chase/OriginBA-3/scripts/jaspersoft/run_standard_offering_pipeline.py)

Purpose:

- Creates a new Jaspersoft folder at:
  - `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Standard_Offering`
- Keeps the original `Workstreams` export untouched
- Reorganizes the selected SmartCity standard offering into the new `Standard_Offering` tree

What is included:

- `102` curated report / Ad Hoc / dashboard objects
- `35` assigned Domain resources
- the required datasource resource:
  - `/organizations/organization_1/organizations/Origin_DEV/DataSource/Origin_DEV_DS`

Selection rule:

- Reports were matched by the exported outer report label, not by internal field names or generic Ad Hoc file names.

Important assumptions:

- The latest provided standard offering document says the offering contains `103` reports total, but its Meter Operations section lists `19` lines while the overview says `18`.
- This package excludes:
  - `Measurement - SP Type`
  - `Billed Usage and Amount Charged`
    - removed intentionally because it is a dashboard carrying a shared public-template dependency not needed in this `Standard_Offering` package

Audit:

- `standard_offering_package_audit.json` lists each selected report, its source resource path, target resource path, and assigned Domain URI.

Verification:

- `standard_offering_verification.json` is the package-level verification result.
- Current result:
  - `102` packaged items
  - `35` unique Domain resources
  - required datasource resource included in the ZIP
  - Domain resources reference `Origin_DEV_DS`
  - expected workstream counts matched
  - all report endpoints point into `Standard_Offering`
  - no duplicate Domain XML resource names in the ZIP
  - no `/public/templates/actual_size.820.jrxml` dependencies remain

One-command rebuild:

```bash
python3 /Users/chase/OriginBA-3/scripts/jaspersoft/run_standard_offering_pipeline.py
```
