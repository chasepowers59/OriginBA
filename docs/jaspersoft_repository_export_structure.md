# Jaspersoft Repository Export Structure

## Purpose
This document captures the repository-package structure observed in the exported `Deposit Control Report.zip` from Jaspersoft Server.

Use it as the source of truth for:
- repository object hierarchy
- resource naming conventions
- org-scoped folder layout
- Domain URI and report-unit packaging patterns

Do not use it as the direct source of truth for hand-authored JRXML internals. Ad Hoc-generated `topicJRXML.data` files are server-generated and much noisier than the maintained JRXML style used in this repository.

## Observed Package Hierarchy

The export package contains:
- `index.xml`
- `resources/`
- `favorites/`

Relevant object path observed in the export:

`/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/`

Within that folder, the package contained:
- `Deposit_Control___Detailed_View.xml`
- `Deposit_Control___Detailed_View_Report.xml`
- `Tender___Payments_Snapshot___Domain.xml`

Companion resource folders:
- `Deposit_Control___Detailed_View_files/`
- `Deposit_Control___Detailed_View_Report_files/`
- `Tender___Payments_Snapshot___Domain_files/`

## Object Types

### 1. Domain
Observed file:
- `Tender___Payments_Snapshot___Domain.xml`

Role:
- semantic layer definition
- references `schema.data`
- points to datasource alias `Origin_DEV_DS`

Observed server URI:
- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Tender___Payments_Snapshot___Domain`

Observed Studio-safe org-relative URI:
- `/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Tender___Payments_Snapshot___Domain`

### 2. Ad Hoc View
Observed file:
- `Deposit_Control___Detailed_View.xml`

Role:
- stores the saved Ad Hoc view
- contains local input controls
- references `topicJRXML.data`
- references `stateXML.data`
- points to the Domain URI

### 3. Wrapper Report Unit
Observed file:
- `Deposit_Control___Detailed_View_Report.xml`

Role:
- report unit wrapper around the Ad Hoc view
- points `mainReport` to `/public/templates/actual_size.820.jrxml`
- points `dataSource` to the saved Ad Hoc view, not directly to the Domain

## Embedded Files

### `schema.data`
Lives under the Domain `_files` folder.

Use as source of truth for:
- Domain item groups
- item IDs
- field types
- datasource alias and schema alias

### `topicJRXML.data`
Lives under the Ad Hoc view `_files` folder.

Use as source of truth for:
- how Jaspersoft serialized the saved Ad Hoc view
- the exact server-generated field/property payload for an Ad Hoc artifact

Do not use as the direct template for hand-maintained repo JRXML files because it includes:
- large volumes of Ad Hoc metadata
- server-generated semantic properties
- temporary topic-report properties
- verbose field property payloads that are not needed in hand-authored reports

### `stateXML.data`
Lives under the Ad Hoc view and wrapper report `_files` folders.

Use as source of truth for:
- Ad Hoc state
- saved grouping
- saved measures
- saved filters
- table/chart/crosstab display state

## Source-Of-Truth Rules For This Repo

### Use the export as source of truth for:
- repository path pattern
- org-scoped object packaging
- Domain URI
- naming style for exported Jaspersoft objects
- whether an artifact is a Domain, Ad Hoc view, or wrapper report

### Do not use the export as source of truth for:
- hand-authored JRXML formatting style
- top-level element ordering in maintained JRXML files
- input-control JSON shape used in this repo
- manual report design decisions where a cleaner curated JRXML is preferable

## Practical Rule For Future Builds

When building a maintained report in this repo:
1. Take the Domain URI and repository folder pattern from the server export.
2. Take field IDs and types from the exported Domain `schema.data`.
3. Build a clean hand-authored Domain JRXML in repo style.
4. Keep matching input-control JSON in `server/input_controls/`.
5. Use the full Ad Hoc export only when you intentionally want to preserve an Ad Hoc view as-is.

For the specific failure sequence and working repair pattern when imports break after packaging, also use:
- [jaspersoft_repository_import_debugging_runbook.md](/C:/Users/cvpow/OneDrive/Desktop/OriginBA/docs/jaspersoft_repository_import_debugging_runbook.md)
