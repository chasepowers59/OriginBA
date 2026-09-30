# JasperReports Server Deployment Compliance Guide (Strict Mode)

This guide is the mandatory deployment path for this repository.
No alternative workflows are permitted.

## 1. Pre-deployment verification
- Confirm review status before deployment.
- SmartCity: Jira review approval is required.
- Internal initiatives: peer review is required for domain changes.

## 2. Component enumeration
- Enumerate every object in scope:
  - Reports
  - Ad hoc views
  - Domains
  - Dashboards
  - Data sources affected
  - Dependencies included by JRS export behavior

## 3. Export (exact flags)
- Export changed objects only.
- Export settings:
  - Legacy Key
  - Include repository permissions
  - Include dependencies
  - Include full resource path
- Verify exported zip contains only expected folders.

## 4. Backup target datasource
- Mandatory backup before import.
- Backup location: Temp folder.
- Naming format: `YYYY-MM-DD INITIALS`.

## 5. Backup target JRS objects
- Mandatory backup of target JRS objects before import.
- Backup location and naming follow Step 4.

## 6. Import extracted file (Update only)
- Import using Legacy Key.
- Import mode: UPDATE only.
- Verify import status is SUCCESS.

## 7. Re-import target datasource
- Re-import original target datasource backup after object import.
- Required to preserve target datasource credentials and prevent overwrite.

## 8. City Checker validation (SmartCity required)
- Validate organization-to-city isolation:
  - Newark -> Newark
  - Fond du Lac -> Fond du Lac
  - Ellensburg -> Ellensburg
  - College Station -> College Station
  - CityCorp -> Russelville
- Any mismatch is a security breach.

## 9. Smoke test and verify create dates
- Verify Create Date is today for deployed objects.
- Launch each object.
- Execute reports.
- Run ad hoc views.
- Complete smoke test before announcing completion.

## Additional mandatory constraints
- Never embed credentials in JRXML, SQL, scripts, or JSON payloads.
- Never hardcode cross-client schema or datasource references.
- Never overwrite target datasource credentials.
- For org name mismatch migrations:
  - Rename organization paths and datasource references across all extracted files.
  - Re-zip package after replacement.
