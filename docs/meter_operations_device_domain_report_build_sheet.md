# Meter Operations Device Domain Report Build Sheet

## Build Rules

Use `1.)` reports from `JoinTree_1` for current-state inventory, install, and customer/location context.

Use `2.)` reports from `JoinTree_2` for device event history.

For `JoinTree_1`, default filters should be:

- `Is Effective (Device Config) = 'Y'`
- `Is Latest (Install Event) = 'Y'`

For `JoinTree_2`, only use `Is Latest (Device Event) = 'Y'` on "latest event per device" reports. Do not use it on trend reports.

Use distinct measures rather than raw row counts:

- `Distinct Device ID`
- `Distinct Device Configuration`
- `Distinct Install Event ID`
- `Distinct Device Event ID`

## Report Build Sheet

### 1. Device Fleet Overview

- Island: `JoinTree_1`
- Visuals: KPI tiles, stacked bar, summary table
- Dimensions:
  - `Device Type Description (Device)`
  - `Manufacturer Description (Device)`
  - `Model Description (Device)`
  - `Service Provider Description`
  - `Latest Device Status`
  - `Premise Type Description`
  - `Trend Area Description`
- Measures:
  - `Distinct Device ID`
  - `Distinct Install Event ID`
- Prompts:
  - `Service Provider (Device)`
  - `Device Type (Device)`
  - `Manufacturer (Device)`
  - `Model (Device)`
  - `Premise Type`
  - `Trend Area`
- Sort/group:
  - Group by device type, then manufacturer/model
  - Sort by `Distinct Device ID` descending
- Value:
  - Shows the installed base, active fleet mix, vendor/model footprint, and where the fleet sits geographically

### 2. Current Installed Meter Inventory

- Island: `JoinTree_1`
- Visuals: detail table
- Columns:
  - `Device ID (Device)`
  - `Asset ID`
  - `Serial Number`
  - `Internal Meter Number`
  - `Utility Device ID`
  - `Latest Device Status`
  - `Manufacturer Description (Device)`
  - `Model Description (Device)`
  - `Device Type Description (Device)`
  - `Service Provider Description`
  - `Installation Date/Time (Install Event)`
  - `Service Point ID (Install Event)`
  - `Account ID`
  - `Name`
  - `Premise ID`
  - `Address`
  - `City`
  - `Trend Area Description`
  - `Retirement Date/Time`
- Measures:
  - `Distinct Device ID`
- Prompts:
  - `Device ID`
  - `Serial Number`
  - `Asset ID`
  - `Latest Device Status`
  - `Manufacturer (Device)`
  - `Model (Device)`
  - `City`
  - `Trend Area`
  - Installation date range
- Sort/group:
  - Sort by `City`, `Address`, `Device ID`
  - Alternate exception sort by `Retirement Date/Time` descending
- Value:
  - Operational lookup for what meter is installed where, tied to asset and customer context

### 3. Install / Removal Activity

- Island: `JoinTree_1`
- Visuals: monthly column trend, detail table
- Dimensions:
  - Month of `Installation Date/Time (Install Event)`
  - Month of `Removal Date/Time (Install Event)`
  - `Device Type Description (Device)`
  - `Manufacturer Description (Device)`
  - `Model Description (Device)`
  - `Trend Area Description`
- Measures:
  - `Distinct Install Event ID`
  - `Distinct Device ID`
- Prompts:
  - Install date range
  - Removal date range
  - Service provider
  - Manufacturer
  - Model
  - Trend area
- Sort/group:
  - Trend by month ascending
  - Detail sorted by latest install/remove date descending
- Value:
  - Tracks deployment pace, exchange/removal waves, and replacement program progress

### 4. Latest Device Event Watchlist

- Island: `JoinTree_2`
- Visuals: exception table
- Columns:
  - `Device Event ID`
  - `Device Event Date/Time`
  - `Device Event Type Description`
  - `Status Description (Device Event)`
  - `Status Reason Description (Device Event)`
  - `Device ID`
  - `Asset ID`
  - `Serial Number`
  - `Utility Device ID`
  - `Manufacturer Description`
  - `Model Description`
  - `Service Provider Description (Device Event)`
  - `Latest Device Event Date/Time`
  - `Latest Status`
- Measures:
  - `Distinct Device Event ID`
- Filters:
  - `Is Latest (Device Event) = 'Y'`
- Prompts:
  - Event date range
  - `Device Event Type`
  - `Status (Device Event)`
  - Service provider
  - Manufacturer
  - Model
- Sort/group:
  - Sort by `Device Event Date/Time` descending
- Value:
  - Daily or weekly view of the newest device issues by meter, model, and event type

### 5. Device Event Volume Trend

- Island: `JoinTree_2`
- Visuals: line chart or stacked area, summary table
- Dimensions:
  - Day, week, or month of `Device Event Date/Time`
  - `Device Event Type Description`
  - `Status Description (Device Event)`
  - `Service Provider Description (Device Event)`
- Measures:
  - `Distinct Device Event ID`
  - `Distinct Device ID`
- Prompts:
  - Event date range
  - Device event type
  - Service provider
  - Manufacturer
  - Model
  - Device type
- Sort/group:
  - Time ascending
  - Optional split by top 5 event types
- Value:
  - Shows whether bad ERT, underwater, damaged-meter, and removed-meter events are trending up or down

### 6. Bad ERT / High-Failure Type Analysis

- Island: `JoinTree_2`
- Visuals: ranked horizontal bar, manufacturer/model table
- Dimensions:
  - `Device Event Type Description`
  - `Manufacturer Description`
  - `Model Description`
  - `Device Type Description`
  - `Service Provider Description (Device Event)`
- Measures:
  - `Distinct Device Event ID`
  - `Distinct Device ID`
- Prompts:
  - Event date range
  - Multi-select event types
- Recommended default prompt values:
  - `W-Bad ERT`
  - `E-Bad ERT`
  - `G-Bad ERT`
- Sort/group:
  - Sort by `Distinct Device Event ID` descending, then manufacturer/model
- Value:
  - Isolates the exact failure populations meter ops cares about and shows which models/vendors are driving them

### 7. Model / Manufacturer Performance

- Build this as a dashboard with two separate components because the Domain uses two islands
- Component A, `Installed Base by Model`
  - Island: `JoinTree_1`
  - Fields:
    - `Manufacturer Description (Device)`
    - `Model Description (Device)`
    - `Device Type Description (Device)`
  - Measure:
    - `Distinct Device ID`
- Component B, `Evented Devices by Model`
  - Island: `JoinTree_2`
  - Fields:
    - `Manufacturer Description`
    - `Model Description`
    - `Device Type Description`
  - Measures:
    - `Distinct Device ID`
    - `Distinct Device Event ID`
- Prompts:
  - Aligned manufacturer, model, device type, and date prompts
- Value:
  - Compares fleet size against event burden so weak models can be spotted without forcing a bad cross-island join

### 8. Data Quality / Orphan Device Exceptions

- Island: `JoinTree_1`
- Visuals: exception table, KPI tiles
- Columns:
  - `Device ID (Device)`
  - `Asset ID`
  - `Serial Number`
  - `Latest Device Status`
  - `Service Point ID (Install Event)`
  - `Account ID`
  - `Premise ID`
  - `Address`
  - `Installation Date/Time (Install Event)`
  - `Is Effective (Device Config)`
  - `Is Latest (Install Event)`
- Measures:
  - `Distinct Device ID`
- Filters:
  - Rows where `Asset ID` is blank, or `Account ID` is blank, or `Premise ID` is blank
- Sort/group:
  - Sort blanks first, then `Status Date/Time (Device)` descending
- Value:
  - Finds devices that exist in MDM/device inventory but are not cleanly linked for field, billing, or reporting use

## Best First Dashboard

Build one `Meter Operations` dashboard with:

- `Device Fleet Overview`
- `Latest Device Event Watchlist`
- `Device Event Volume Trend`
- `Bad ERT / High-Failure Type Analysis`

## Current Domain Gaps

You cannot do these well yet from the current XML:

- Event hot spots by `Address`, `City`, `Trend Area`, or `Premise`
- Event-to-account/customer drillthrough
- Event-to-work-order or field activity linkage
- True asset lifecycle cost or maintenance history

Reason:

- `JoinTree_2` has events plus device details, but not the premise/account/install context from `JoinTree_1`

## Guardrails

- For inventory-style reports on `JoinTree_1`, filter to `DVC_CFG_EFFECTIVE = 'Y'` and `IEVT_LATEST = 'Y'` when you want current-state reporting
- For event-style reports on `JoinTree_2`, use `DVC_EVT_LATEST = 'Y'` only for latest-event-per-device reports, not for trend reports
- Prefer `CountDistinct(Device ID)` and `CountDistinct(Device Event ID)` over raw row counts because install/event joins can multiply rows
- Keep `JoinTree_1` and `JoinTree_2` reports separate unless a report explicitly needs both current inventory and event history
- Use detailed tables for dispatch/investigation reports and charts for trend, hotspot, and fleet-mix reports
