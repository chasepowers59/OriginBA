# Current Snapshot Repository Path Truth

## Purpose

This document captures the actual Jaspersoft Server repository paths observed in the exported package:

- `C:\Users\cvpow\Downloads\Snapshot Folder.zip`

Extracted inspection workspace:

- `C:\Users\cvpow\OneDrive\Desktop\OriginBA\tmp\snapshot_folder_zip_inspect`

Use this file as the current source of truth for:

- snapshot Domain URIs
- report-unit folder placement
- workstream subfolder naming
- future import package pathing

This corrects earlier inferred paths where needed.

## Top-Level Snapshot Root

All current snapshot artifacts in this export live under:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots`

## Domain Truth By Snapshot

### Payments / Cashiering

Actual Domain URI:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Payments/Tender___Payments_Snapshot___Domain`

Important correction:

- The payments Domain is under `Cashiering/Payments`
- It is not directly under `Cashiering`

Observed report folders using this Domain:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Payments`
- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Deposit_Control`
- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Tender_Control`
- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Auto_Pay`

Representative saved views:

- `Payments___Tender_Source`
- `Deposit_Control___Detailed_View`
- `Tender_Controls___Balancing_Details`
- `Auto_Pay___Recent_Tenders`

### GL Distribution

Actual Domain URI:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Financial_Transaction/General_Ledger/FT_and_GL_Snapshot___Domain`

Observed report folder:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Financial_Transaction/General_Ledger`

Representative saved views:

- `General_Ledger___GL_Account_and_Distribution`
- `General_Ledger___Revenue_Totals`
- `General_Ledger___Accounts_Receivable`
- `test_GL`

### Financial Transaction Header

Actual Domain URI:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Financial_Transaction/Financial_Transaction/Financial_Transaction_Snapshot___Domain`

Important correction:

- The FT header Domain is under `Financial_Transaction/Financial_Transaction`
- It is not at the parent `Financial_Transaction` folder level

Observed report folder:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Financial_Transaction/Financial_Transaction`

Representative saved views:

- `Financial_Transactions___Service_Type_FT_Summary`

### Billed Usage Amount / Bill Segment Grain

Actual Domain URI:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Billed_Usage/Amount_Billed/Billed_Usage_Snapshot___Domain`

Observed report folder:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Billed_Usage/Amount_Billed`

Representative saved views:

- `Billed_Usage___By_Service_Type`
- `Billed_Usage___Customer_Class_Summary`
- `Billed_Usage___Estimated_Segment`
- `Billed_Amount___Canceled_Segments`
- `Billed_Amount___Amount_Billed_by_Budget_Plan`
- `Billed_revenue_by_Rate_Schedule`
- `Billed_Totals___Rebills`

### Billed Usage Determinant / SQ Grain

Actual Domain URI:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Billed_Usage/Billed_Usage/Billed_Usage_SQ_Snapshot___Domain`

Observed report folder:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Billed_Usage/Billed_Usage`

Representative saved views:

- `Billed_Usage___Segment_Determinant`
- `Billed_Usage___Tiered_Billed_Usage`

Important note:

- `Billed_Usage_and_Amount_Charged` is a composite dashboard/report artifact that references both billed-amount and billed-determinant Domains

### Usage Header / Usage Transactions

Actual Domain URI:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Usage_Transactions/Usage_Transactions_Snapshot___Domain`

Observed report folder:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Usage_Transactions`

Representative saved views:

- `Usage_Transaction___By_SA_Type`
- `Usage_Transaction___by_Subscription_Type`

### Scalar Usage

Actual Domain URI:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Scalar_Usage/Usage_Scalar_Snapshot___Domain`

Observed report folder:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Scalar_Usage`

Representative saved views:

- `Usage___Account_View`
- `Usage___by_Measuring_Component`
- `Usage___Customer_Class`
- `Usage___Highest_Usage_Premises`
- `Usage___Premise_Consumption`

### Measurements

Actual Domain URI:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Measurements/Measurement_Snapshot___Domain`

Observed report folder:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Measurements`

Representative saved views:

- `Measurement___By_Component_Type`
- `Measurement___IMD_Summary`
- `Measurement___Measurement_Conditions`
- `Measurement___Measuring_Component_Health`
- `Measurement___Reads_and_Totals_by_Cycle`
- `Measurements___Estimated`
- `Measurements___by_Service_Point`
- `Meter_Reads___Counts_by_Route`

## Folder Naming Truth

The export shows these actual snapshot workstream folder names:

- `Cashiering`
- `Cashiering/Payments`
- `Cashiering/Deposit_Control`
- `Cashiering/Tender_Control`
- `Cashiering/Auto_Pay`
- `Financial_Transaction/General_Ledger`
- `Financial_Transaction/Financial_Transaction`
- `Financial_Transaction/Adjustments`
- `Billed_Usage/Amount_Billed`
- `Billed_Usage/Billed_Usage`
- `Meter_Operations/Usage_Transactions`
- `Meter_Operations/Scalar_Usage`
- `Meter_Operations/Measurements`
- `Meter_Operations/Assets_and_Devices`

These should be preferred over inferred folder names like:

- `Billing_and_Rates`
- `Usage`
- `Measurements` without the `Meter_Operations` parent
- `Cashiering` report units directly beside the payments Domain when the export clearly uses `Cashiering/Payments`

## Import Packaging Rules Confirmed By This Export

- Report units and Ad Hoc views are stored in subfolders beneath the workstream snapshot folders
- Each Domain has a paired `_files/schema.data`
- The export included `Origin_DEV_DS.xml` and `/public/templates/actual_size.820.jrxml`, but those are dependency artifacts from the server export
- For curated self-contained report-unit packages, the safer repo pattern is still:
  - local `main_jrxml`
  - direct `dataSource` URI to the snapshot Domain
  - no dependence on `/public/templates/actual_size.820.jrxml`

## What To Use Going Forward

Use these URIs when building future import packages unless a newer export proves otherwise:

- Payments:
  `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Payments/Tender___Payments_Snapshot___Domain`
- GL:
  `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Financial_Transaction/General_Ledger/FT_and_GL_Snapshot___Domain`
- FT:
  `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Financial_Transaction/Financial_Transaction/Financial_Transaction_Snapshot___Domain`
- Usage header:
  `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Usage_Transactions/Usage_Transactions_Snapshot___Domain`
- Scalar usage:
  `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Scalar_Usage/Usage_Scalar_Snapshot___Domain`
- Measurements:
  `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Measurements/Measurement_Snapshot___Domain`
- Billed amount:
  `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Billed_Usage/Amount_Billed/Billed_Usage_Snapshot___Domain`
- Billed determinant:
  `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Billed_Usage/Billed_Usage/Billed_Usage_SQ_Snapshot___Domain`

## Next Packaging Impact

For the pending backlog report packages, the key path fixes are:

- move payments report packages under `Cashiering/Payments`, `Cashiering/Deposit_Control`, or `Cashiering/Tender_Control` depending on the artifact
- use `Financial_Transaction/Financial_Transaction` for FT-header report units
- use `Billed_Usage/Amount_Billed` for bill-segment-grain billed amount reports
- use `Billed_Usage/Billed_Usage` for determinant-grain billed usage reports
- use `Meter_Operations/Usage_Transactions` for usage-header reports
- use `Meter_Operations/Measurements` for measurement reports

This file should be referenced before building the next import-ready ZIP batch.
