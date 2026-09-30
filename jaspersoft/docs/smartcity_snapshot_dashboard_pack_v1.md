# SmartCity Snapshot Dashboard Pack V1

## Purpose

This document defines the highest-value next dashboard deliverable for the SmartCity reporting library: an importable dashboard pack built only on the governed snapshot reporting assets already in this repository.

This is the best next build because it gives clients something they can import and use immediately without depending on:

- ungoverned live-domain behavior
- temporary Ad Hoc wrappers
- public-template dependencies
- direct SQL embedded into server-side dashboard objects

The recommended delivery model for V1 is:

- JRXML-backed dashboard-style reports as the visible client entry points
- existing governed Ad Hoc views and snapshot Domains as the drill and detail layer underneath
- matching input controls for each dashboard report

This keeps the package importable, maintainable, and portable across client environments.

## Why This Is The Highest-Value Next Build

The current repo already has the two foundations needed for a strong first dashboard product:

- governed snapshot datasets and validated refresh procedures
- a curated standard-offering package and promotion workflow

The next best step is not more loose report count growth. It is turning the best governed snapshot content into a polished front-door client experience.

What V1 should optimize for:

- strong first impression in demos
- simple operational review for business users
- clear drill path from KPI to governed detail
- easy packaging and promotion
- low dependency risk

## Delivery Recommendation

### Build Type

For V1, use report-based dashboards rather than native Jaspersoft `dashboardModelResource` objects.

Reason:

- JRXML dashboards are easier to version in git
- they are easier to validate before import
- they avoid the hidden nested dependencies often found in exported dashboard and Ad Hoc artifacts
- they are easier to promote client-to-client with the tooling already built in this repo

### Visual Style

The dashboards should feel client-ready, not like exported default Ad Hoc views.

Recommended visual direction:

- clean executive header
- bold KPI cards
- 2-row grid layout
- strong sectioning
- low-noise tables
- limited, intentional color palette
- clear exception highlighting

Recommended palette:

- navy / deep blue for finance and control surfaces
- slate / soft gray for neutral surfaces
- one alert orange
- one exception red
- one success green

Do not use:

- generic default Ad Hoc chart colors
- crowded dashboards
- more than one primary subject per canvas

## V1 Dashboard Pack

V1 should ship as three dashboard-style reports.

### 1. Billing Integrity Dashboard

Primary audience:

- billing operations
- revenue assurance
- billing support

Purpose:

- show billed amount, billed usage, exception categories, and determinant drill paths from the governed billed-usage snapshots

Main governed sources:

- `BSEG_BILLED_USAGE_RPT_CURR`
- `BSEG_SQ_USAGE_RPT_CURR`

Primary dashboard report:

- `billing_integrity_dashboard.jrxml`

Recommended top KPI strip:

- total billed amount
- total billed usage
- bill segment count
- canceled segment count
- rebill count
- estimated segment count

Recommended visual row:

- billed amount trend by month
- billed usage trend by month
- billed amount by service type or utility type

Recommended operational row:

- billed amount by customer class
- billed amount by bill cycle
- top accounts / SAs by billed amount

Recommended drill targets:

- `Billed Amount - Canceled Segments`
- `Billed Amount - Rebills`
- `Billed Amount - Estimated Segment`
- `Billed Usage - Segment Determinant`
- `Billed Usage - Account Level View`

### 2. Usage And Meter Health Dashboard

Primary audience:

- meter operations
- usage support
- billing support

Purpose:

- show usage health, measurement health, and high-value exception indicators before they turn into billing defects

Main governed sources:

- `D1_USAGE_RPT_CURR`
- `D1_MSRMT_RPT_CURR`
- `D1_USAGE_SCALAR_DTL_RPT_CURR` for drill only

Primary dashboard report:

- `usage_meter_health_dashboard.jrxml`

Recommended top KPI strip:

- usage row count
- distinct accounts
- distinct service agreements
- distinct service points
- estimated measurement count
- latest usage date

Recommended visual row:

- usage trend by month
- measurement trend by cycle
- usage by customer class / UOM

Recommended operational row:

- measurement conditions trend
- reads by component type
- high-usage outlier table

Recommended drill targets:

- `Measurement - IMD Summary`
- `Measurement - Measurement Conditions`
- `Measurements - Estimated`
- `Usage - Account View`
- `Usage - Highest Usage Customers`
- `Usage - by Measuring Component ID`

### 3. Finance Reconciliation Dashboard

Primary audience:

- finance analysts
- GL reconciliation
- controllers

Purpose:

- show top-line FT and GL behavior with a clean drill path into batch, account, distribution, and payment detail

Main governed sources:

- `FT_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`

Primary dashboard report:

- `finance_reconciliation_dashboard.jrxml`

Recommended top KPI strip:

- total FT amount
- FT count
- GL line count
- AR balance
- write-off amount
- payment FT amount

Recommended visual row:

- billed revenue trend
- transactions by type
- GL amount by distribution or account

Recommended operational row:

- FT distribution status
- GL by batch number
- revenue by customer class
- payment account detail exceptions

Recommended drill targets:

- `Financial Transaction - Bill Cycle Transactions`
- `Financial Transaction - GL Distribution Status`
- `Financial Transaction - Total Transactions by Type`
- `Financial Transaction - Payment Account Detail`
- `General Ledger - Accounts Receivable`
- `General Ledger - GL Account and Distribution`
- `General Ledger - by Batch Number`

## Parameter Contract

To keep packaging and promotion simple, the three V1 dashboards should share the same prompt contract wherever possible.

Required shared controls:

- `START_DT`
- `END_DT`

Recommended optional shared controls:

- `CIS_DIVISION`
- `BILL_CYCLE`
- `SERVICE_TYPE`
- `CUSTOMER_CLASS`

Dashboard-specific optional controls:

- Billing dashboard:
  - `UTILITY_TYPE`
  - `ESTIMATED_ONLY`
  - `EXCEPTION_ONLY`
- Usage dashboard:
  - `DEVICE_TYPE`
  - `HIGH_USAGE_THRESHOLD`
  - `ONLY_HIGH_USAGE`
- Finance dashboard:
  - `FT_TYPE`
  - `GL_STATUS`
  - `BATCH_NUMBER`

## Package Structure

Recommended repository structure:

- `/SmartCity/Report/Dashboard_Pack_V1/Billing/billing_integrity_dashboard`
- `/SmartCity/Report/Dashboard_Pack_V1/Meter_Operations/usage_meter_health_dashboard`
- `/SmartCity/Report/Dashboard_Pack_V1/Finance/finance_reconciliation_dashboard`

Recommended repo file structure:

- `reports/billing_integrity_dashboard.jrxml`
- `reports/usage_meter_health_dashboard.jrxml`
- `reports/finance_reconciliation_dashboard.jrxml`
- `server/input_controls/billing_integrity_dashboard_input_controls.json`
- `server/input_controls/usage_meter_health_dashboard_input_controls.json`
- `server/input_controls/finance_reconciliation_dashboard_input_controls.json`

## Source Asset Mapping

The V1 pack should reuse the existing governed detail assets already curated in `Standard_Offering`.

Billing drill assets:

- `Billed Amount - by Customer Class`
- `Billed Amount - Amount Billed by Budget Plan`
- `Billed Amount - By Utility Type`
- `Billed Amount - Canceled Segments`
- `Billed Amount - Estimated Segment`
- `Billed Amount - Rebills`
- `Billed Amount - Revenue by Rate Schedule`
- `Billed Usage - Account Level View`
- `Billed Usage - Across Customer Class & UOM`
- `Billed Usage - By SA type & Class`
- `Billed Usage - Segment Determinant`
- `Billed Usage - Tiered Billed Usage`

Usage and meter drill assets:

- `Measurement - IMD Summary`
- `Measurement - Measurement Conditions`
- `Measurement - Reads and Totals by Cycle`
- `Measurements - Estimated`
- `Measurements - by Service Point ID`
- `Meter Reads - Counts by Component Type`
- `Usage - Account View`
- `Usage - Customer Class and UOM`
- `Usage - Highest Usage Customers`
- `Usage - Premise Consumption`
- `Usage - by Measuring Component ID`
- `Usage Transaction - By SA Type`
- `Usage Transaction - by Subscription Type`

Finance drill assets:

- `General Ledger - Accounts Receivable`
- `General Ledger - Adjustments Review`
- `General Ledger - GL Account and Distribution`
- `General Ledger - Revenue Totals`
- `General Ledger - Write off Amounts`
- `General Ledger - by Batch Number`
- `Financial Transaction - Bill Cycle Transactions`
- `Financial Transaction - Billed Revenue Trend`
- `Financial Transaction - GL Distribution Status`
- `Financial Transaction - Revenue by Customer Class`
- `Financial Transaction - Total Transactions by Type`
- `Financial Transactions - Service Type FT Summary`
- `Financial Transaction - Payment Account Detail`

## Existing Repo Assets To Reuse

There are already two strong pattern references in the repo:

- [ops_hub_dashboard.jrxml](/Users/chase/OriginBA-3/reports/ops_hub_dashboard.jrxml)
- [usage_device_dashboard.jrxml](/Users/chase/OriginBA-3/reports/usage_device_dashboard.jrxml)

Use them as pattern references for:

- KPI strip layout
- title/header treatment
- summary-plus-detail structure
- parameter handling
- input control pairing

Do not reuse them as-is for the client pack because:

- `ops_hub_dashboard.jrxml` uses direct SQL and mixed subject areas
- `usage_device_dashboard.jrxml` points to an older domain path and is a narrower exception report

## Build Order

Recommended build order:

1. `finance_reconciliation_dashboard`
   - strongest controlled story for demos and reconciliations
2. `billing_integrity_dashboard`
   - broad business value and easy executive appeal
3. `usage_meter_health_dashboard`
   - strongest operational value for utility support teams

## Highest-Value Supporting Automation

The most valuable workflow improvement after the package importer is a reusable starter generator for report-based dashboards.

That generator should:

- scaffold a dashboard-style JRXML from a template
- scaffold matching input-control JSON
- accept a source Domain URI or a governed report subject
- emit repo-ready files in `reports/` and `server/input_controls/`

This is more valuable than a generic idea backlog because it reduces repeated report setup work every time a new client dashboard is needed.

## Recommended Next Implementation

The next concrete implementation should be:

- build `finance_reconciliation_dashboard.jrxml`
- build matching input controls
- keep it importable as a report unit
- use the existing curated `Standard_Offering` finance assets as the drill layer

That gives the fastest path to a client-usable, strong-looking dashboard with the least risk.
