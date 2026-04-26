# Jaspersoft Ad Hoc `stateXML` Guide

## Purpose

This guide explains how `stateXML.data` stores Ad Hoc view behavior and how OriginBA add-on views were customized with distinct business logic.

`stateXML.data` is the runtime state for an `adhocDataView` resource and controls:

- selected measures
- selected groups/dimensions
- filter rules and prompt parameter bindings
- table/crosstab/chart mode
- chart style and title

## Where `stateXML` lives

For each Ad Hoc view:

- XML wrapper: `<view_name>.xml`
- state file: `<view_name>_files/stateXML.data`

Example:

- `.../Billed_Usage___Estimate_and_Rebill.xml`
- `.../Billed_Usage___Estimate_and_Rebill_files/stateXML.data`

## Core `stateXML` sections

### `unifiedState` (root attributes)

Controls global presentation behavior.

Important attributes:

- `mode="table|crosstab|ichart"`  
  - `table`: row-level table
  - `crosstab`: pivot/crosstab layout
  - `ichart`: intelligent chart mode

### `chartState` and `intelligentChartState`

Controls chart rendering when mode is chart/crosstab.

Key nodes:

- `<chartType>` (e.g. `1_bar`, `3_line`)
- legend/location/stacking options

### `measures`

Defines metrics and aggregation functions.

Each `<measure>` includes:

- `fieldName` (domain field)
- `function` (`Sum`, `Average`, `CountAll`, `CountDistinct`)
- `name` (metric token used in state)

### `groups`

Defines row/series grouping dimensions.

Each `<queryDimension>` includes:

- `fieldName`
- `name`
- visible/expanded levels

### `subFilterList`

Defines default filters and prompt bindings.

Each `<subFilter>` carries:

- `expressionString` (default logic)
- `parameterizedExpressionString` (input-control binding logic)

This is where date windows, status filters, and exception-only logic are usually encoded.

### `title`

User-facing Ad Hoc title shown in view.

## Oracle-inspired utility question set used

The add-ons were redesigned around utility analytics patterns documented in Oracle Utilities Analytics content references:

- Credit and collections concentration and write-off risk segmentation
- meter exception hotspot diagnostics by condition/component
- backlog aging and duration bottleneck monitoring
- case lifecycle workload and state-duration analysis
- GL distribution diagnostics by FT/SA/customer segment

Reference sources used for design direction:

- <https://docs.oracle.com/en/industries/energy-water/analytics/2900/ouaw-ccb-metric/OUAW-CCB-METRIC/CCB_BI_Content.2.2.html>
- <https://docs.oracle.com/cd/E83817_01/UDMRF/reports.htm>
- <https://docs.oracle.com/en/industries/energy-water/analytics/2801/ouaw-mdm-metric/OUAW-MDM-METRIC-REF-GUIDE-28010/MDM_BI_Content.2.9.html>
- <https://docs.oracle.com/en/industries/energy-water/analytics/2801/ouaw-mdm-metric/OUAW-MDM-METRIC-REF-GUIDE-28010/MDM_BI_Content.2.8.html>
- <https://docs.oracle.com/en/industries/energy-water/analytics/2802/ouaw-ea-metric/OUEA-METRIC-REFERENCE-GUIDE/OUEA_BI_Content.2.1.html>

## Add-on logic changes applied

Package:

- `deploy/standard_offering_add_ons/Standard_Offering_Add_Ons_import.zip`

### 1) `Billed Usage - Estimate and Rebill`

File:

- `.../Billed_Usage___Estimate_and_Rebill_files/stateXML.data`

Business question:

- Which bill cycles and rate schedules produce the highest estimate-to-rebill leakage risk?

Logic updates:

- changed mode to `table` for operational ranking and triage
- changed dimensions to:
  - bill cycle (`BSEG_BILLING.BILL_BILL_CYC_DESC`)
  - rate schedule (`BSEG_DETERMINANTS.SOLE_RS_DESC`)
  - customer class (`BSEG_SEGMENTATION.CUST_CL_DESC`)
- changed measures to:
  - distinct billed segments
  - rebill segment count
  - billed amount sum
  - determinant count sum
- changed default window to 12 months and preserved estimate filter (`EST_SW='Y'`)

### 2) `Collection Process - Arrears and Write Off`

File:

- `.../Collection_Process___Arrears_and_Write_Off_files/stateXML.data`

Business question:

- Where are chronic 61+ day arrears concentrated by class, account segment, and cycle?

Logic updates:

- changed mode to `table`
- changed dimensions to:
  - customer class (`NewSet1.DESCR_4`)
  - account management group (`CI_ACCT.ACCT_MGMT_GRP_CD`)
  - bill cycle (`CI_ACCT.BILL_CYC_CD`)
- changed measures to:
  - distinct account count
  - `ARS_AMT3/4/5` sums (older-bucket concentration focus)
- retained latest-snapshot semantics and changed baseline window to 2024+
- changed arrears focus threshold from only 150+ to 61+ (`ARS_AMT3 > 0`)

### 3) `Measurements - Exceptions and Aging`

File:

- `.../Measurements___Exceptions_and_Aging_files/stateXML.data`

Business question:

- Which condition/component/service-point combinations generate recurring exception pressure?

Logic updates:

- changed mode to `table`
- changed dimensions to:
  - measurement condition
  - component type
  - service point type
- changed measures to:
  - distinct measurement components
  - IMD event count
  - measured value sum
- changed default date horizon to 6 months

### 4) `Field Activity - Backlog and Overdue`

File:

- `.../Field_Activity___Backlog_and_Overdue_files/stateXML.data`

Business question:

- Which priority/status/activity queues hold the oldest unresolved field backlog?

Logic updates:

- changed mode to `table`
- changed dimensions to:
  - activity type
  - FA priority
  - BO status
- changed measures to:
  - distinct activity workload volume
  - average days old
  - maximum days old
- changed overdue threshold to stricter long-tail backlog filter (`DAYS_OLD > 14`)

### 5) `Case - Workload and Duration`

Files:

- `.../Case___Workload_and_Duration_files/stateXML.data`
- `.../Case___Workload_and_Duration_files/dashboardReport_files/stateXML.data`

Business question:

- Which case types/statuses/customer segments are driving current and prior state duration bottlenecks?

Logic updates:

- changed mode to `table`
- changed dimensions to:
  - case type
  - status label
  - customer class segment
- changed measures to:
  - distinct case volume
  - average total case duration
  - average current-state duration
  - average prior-state duration
- added minimum aging floor (`CASE_DUR_DAYS > 2`) to de-noise short-cycle cases

### 6) `General Ledger - Status Diagnostics`

File:

- `.../General_Ledger___Status_Diagnostics_files/stateXML.data`

Business question:

- Where are GL distribution bottlenecks concentrated by FT type, SA status, and customer class?

Logic updates:

- changed mode to `table`
- changed dimensions to:
  - GL distribution status
  - FT type
  - SA status
  - customer class
- changed measures to:
  - FT volume count
  - current amount sum
  - total amount sum
- changed accounting horizon to 15 months for seasonality comparison

## Notes

- All add-ons remain under existing `Standard_Offering` folder endpoints.
- Domains remain in existing repository locations (no domain relocation).
- Changes are implemented in `stateXML` business state rather than only label/name metadata.

## Expanded add-on set (second wave)

Additional views were added under the same package structure and use existing Domain resources only:

- Billing:
  - `Billed Usage - Revenue Leakage Hotspots`
  - `Billed Usage - Determinant Anomaly Review`
- Debt Management:
  - `Collection Process - Top Arrears Accounts`
  - `Collection Process - Arrears Trend by Service Type`
- Meter Operations:
  - `Measurements - Missing Read Risk`
  - `Measurements - Cycle Volume Shift`
- Field Operations:
  - `Field Activity - Appointment SLA Risk`
  - `Field Activity - Cancelation Drivers`
- Customer Operations:
  - `Case - Resolution Throughput`
  - `Case - Contact Workload Concentration`
- Finance:
  - `Financial Transaction - Revenue Volatility`
  - `Financial Transaction - Distribution Backlog`

Packaging updates:

- new Ad Hoc wrapper XML + companion `_files` folder for each new view
- `index.xml` resource list updated to include each new repository URI
- rebuilt import package:
  - `deploy/standard_offering_add_ons/Standard_Offering_Add_Ons_import.zip`

## Packaging guardrails for future AI runs

To avoid repeat import failures, treat package wrapper integrity as a separate deliverable from Ad Hoc logic:

1. do not edit `stateXML` and wrapper structure in the same step without a full manifest revalidation pass
2. use a known-good package wrapper style (`Standard_Offering_import.zip`) as the baseline
3. keep only one active repository root in `_build` for a given target package
4. verify all `.folder.xml` and `index.xml` paths resolve before building ZIP
5. build a single-test ZIP first, validate import, then publish the full pack

Authoritative wrapper contract and checklist:

- `docs/jaspersoft_promotion_endpoint_dependency_contract.md` (see **Add-on import wrapper contract** section)
