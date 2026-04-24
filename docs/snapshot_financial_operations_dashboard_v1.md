# Snapshot Financial Operations Dashboard V1

## Purpose

This dashboard is a native Jaspersoft `dashboardModelResource` built from the
snapshot-backed Financial Transaction Ad Hoc views already curated into:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Standard_Offering/Finance/Financial_Transaction`

It is intended for **financial operations** users who need one place to review:

- billed revenue trend
- GL distribution status
- transaction mix by type
- revenue by customer class
- bill-cycle transaction activity
- service-type FT summary

## Business Use Case

The dashboard is meant for day-to-day finance monitoring and reconciliation,
especially when a lead analyst or supervisor needs a current operational view
before drilling into individual reports.

The specific use case is:

- review recent snapshot-backed FT activity
- confirm billed revenue trend direction
- spot GL posting backlog or status mix issues
- compare transaction volume across FT types
- review bill-cycle concentration
- review service-type concentration without leaving the Finance workstream

## Dashboard Design

The dashboard is built **from scratch** as a native dashboard, not by reusing
the old legacy `Financial Transaction Dashboard`.

It uses:

- direct references to existing snapshot Ad Hoc views
- dashboard-level date filters
- no `/temp/...` embedded Ad Hoc resources
- no `/public/templates/...` dependency

## Included Dashlets

1. `Financial Transaction - Billed Revenue Trend`
2. `Financial Transaction - GL Distribution Status`
3. `Financial Transaction - Total Transactions by Type`
4. `Financial Transaction - Revenue by Customer Class`
5. `Financial Transaction - Bill Cycle Transactions`
6. `Financial Transactions - Service Type FT Summary`

## Filters

Dashboard-level filters:

- `ACCOUNTING_DT_1`
  - applied to all dashlets
  - intended as the primary recent-period cutoff
- `ACCOUNTING_DT_2`
  - applied only to views that support a true between-date range
  - currently:
    - billed revenue trend
    - revenue by customer class

## Why This Approach

This design is safer than trying to repair the legacy dashboard because:

- it stays on the governed snapshot-backed finance semantic layer
- it reuses the curated Standard Offering assets already prepared for import
- it avoids hidden dashboard internals that came from `/temp/...`
- it keeps the dashboard in the same business-facing folder structure as the
  rest of the Standard Offering

## Assumptions

- `Standard_Offering_import.zip` has already been imported into `Origin_DEV`
- the snapshot-backed Financial Transaction Ad Hoc views already exist in the
  target environment
- the snapshot domain remains the correct governed finance semantic layer for
  this operational dashboard

## Jaspersoft Edge Cases

- saved Ad Hoc views may evolve their filter contracts later; if a view loses
  `ACCOUNTING_DT_1`, dashboard filter wiring must be updated
- dashboard-level controls should only be wired to views that actually expose
  the underlying parameter
- this package adds a dashboard to the existing folder and should not be used as
  a first-time replacement for the entire Standard Offering tree

## Validation Checks

Package-level checks:

- exactly one `dashboardModelResource`
- target folder is Finance/Financial_Transaction under `Standard_Offering`
- no `/temp/...` references
- no `/public/templates/...` references
- `components.data`, `wiring.data`, and `layout` all present

Runtime smoke checks after import:

1. open `Financial Operations - Dashboard`
2. confirm all six dashlets render
3. change `ACCOUNTING_DT_1` and apply
4. confirm all dashlets refresh
5. change `ACCOUNTING_DT_2` and confirm the two range-based dashlets refresh
6. export one chart and one table dashlet
