# Native Dashboard Pack V1

## Current Recommended Artifact

The current recommended finance dashboard package is the new snapshot-backed
native dashboard:

- [Financial_Operations_Dashboard_import.zip](/Users/chase/OriginBA-3/deploy/native_dashboard_pack_v1/Financial_Operations_Dashboard_import.zip)
- [Financial_Operations_Dashboard_manifest.json](/Users/chase/OriginBA-3/deploy/native_dashboard_pack_v1/Financial_Operations_Dashboard_manifest.json)
- [Financial_Operations_Dashboard_verification.json](/Users/chase/OriginBA-3/deploy/native_dashboard_pack_v1/Financial_Operations_Dashboard_verification.json)

This dashboard is designed to be imported into:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Standard_Offering/Finance/Financial_Transaction`

## What It Is

This is a native Jaspersoft `dashboardModelResource` built **from scratch** for
financial operations, using the existing snapshot-backed Finance/Financial
Transaction Ad Hoc views already curated into `Standard_Offering`.

It is not a repackaged legacy FT dashboard.

## Included Dashlets

- `Financial Transaction - Billed Revenue Trend`
- `Financial Transaction - GL Distribution Status`
- `Financial Transaction - Total Transactions by Type`
- `Financial Transaction - Revenue by Customer Class`
- `Financial Transaction - Bill Cycle Transactions`
- `Financial Transactions - Service Type FT Summary`

## Dashboard-Level Filters

- `ACCOUNTING_DT_1`
  - applied to all six dashlets
- `ACCOUNTING_DT_2`
  - applied only to:
    - billed revenue trend
    - revenue by customer class

## Validation Status

Current verification passed with:

- `1` dashboard
- no `/temp/...` references
- no `/public/templates/actual_size.820.jrxml` dependency
- all Ad Hoc references scoped to:
  - `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Standard_Offering/Finance/Financial_Transaction`

## Prerequisite

This package is an add-on package. It assumes the curated
[Standard_Offering_import.zip](/Users/chase/OriginBA-3/deploy/jaspersoft_standard_offering/Standard_Offering_import.zip)
has already been imported into the same environment.

## Supporting Scripts

- [audit_native_dashboards.py](/Users/chase/OriginBA-3/scripts/jaspersoft/audit_native_dashboards.py)
- [package_native_dashboard.py](/Users/chase/OriginBA-3/scripts/jaspersoft/package_native_dashboard.py)
- [verify_native_dashboard_package.py](/Users/chase/OriginBA-3/scripts/jaspersoft/verify_native_dashboard_package.py)
- [build_snapshot_financial_operations_dashboard.py](/Users/chase/OriginBA-3/scripts/jaspersoft/build_snapshot_financial_operations_dashboard.py)
- [verify_snapshot_dashboard_package.py](/Users/chase/OriginBA-3/scripts/jaspersoft/verify_snapshot_dashboard_package.py)

## Legacy Artifact

The earlier package below is retained for reference, but it is no longer the
recommended finance dashboard direction because it was based on the legacy FT
domain/dashboard pattern:

- [Financial_Transaction_Dashboard_import.zip](/Users/chase/OriginBA-3/deploy/native_dashboard_pack_v1/Financial_Transaction_Dashboard_import.zip)
- [Financial_Transaction_Dashboard_package_audit.json](/Users/chase/OriginBA-3/deploy/native_dashboard_pack_v1/Financial_Transaction_Dashboard_package_audit.json)
- [Financial_Transaction_Dashboard_verification.json](/Users/chase/OriginBA-3/deploy/native_dashboard_pack_v1/Financial_Transaction_Dashboard_verification.json)

## Additional References

- [native_dashboard_inventory_audit.json](/Users/chase/OriginBA-3/deploy/native_dashboard_pack_v1/native_dashboard_inventory_audit.json)
- [native_dashboard_pack_manifest.json](/Users/chase/OriginBA-3/deploy/native_dashboard_pack_v1/native_dashboard_pack_manifest.json)
- [snapshot_financial_operations_dashboard_v1.md](/Users/chase/OriginBA-3/docs/snapshot_financial_operations_dashboard_v1.md)
