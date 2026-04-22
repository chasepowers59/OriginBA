# Asset Vs Device Reporting Guide

## Purpose

This guide explains the operational difference between `assets` and `devices`, how the current `Asset Domain` should be used for utility reporting, and how to think about report design so the resulting reports answer the right business questions.

This is intended to be a working reference before building reports in Jaspersoft.

## Core Concept

A `device` is the operational meter or endpoint object that tells you what the meter is doing.

An `asset` is the owned maintainable object that tells you what the utility has, where it is, what condition it is in, and what it is worth.

In practical terms:

- `Device domain` answers:
  - What events happened?
  - Is the meter communicating?
  - What model is failing?
  - Which service point or premise is affected?
- `Asset domain` answers:
  - What do we own?
  - Where is it assigned?
  - What is its condition, age, and replacement value?
  - Which assets should be repaired, retired, or replaced?

That is why they should not be treated as the same reporting layer, even when many meters are also assets.

## How To Think About Them

Use this rule:

- If the business question starts with `what happened?`, start with the `device domain`
- If the business question starts with `what do we have, where is it, and what should we do with it?`, start with the `asset domain`

Examples:

- `How many bad ERT events did we have by model?`
  - Device domain
- `Which installed water meter assets are older than useful life and high replacement cost?`
  - Asset domain
- `Which devices are throwing repeated events?`
  - Device domain
- `Which assets in critical areas are poor condition and near predicted wear-out?`
  - Asset domain

## What This Asset Domain Is Good At

The current XML is clearly a `W1_ASSET`-centered lifecycle domain. It is strong for:

- asset inventory
- asset identification
- asset location and organization hierarchy
- asset condition and disposition
- asset ownership and service area
- financial lifecycle fields
- planning and replacement analysis

The highest-value groups in this domain are:

- `W1_ASSET`
  - core asset record
  - cost, condition, status, useful life, replacement value
- `CMS_W1_ASSET_IDENTIFIER_VW`
  - serial number, badge number, purchase order, firmware versions
- `W1_ASSET_NODE`
  - where the asset sits, attachment relationships, disposition, failure flag
- `W1_NODE`
  - location and organization context
- lookup tables
  - turn codes and flags into business labels

This domain is not mainly about real-time operational events. It is about `asset lifecycle, accountability, location, and economics`.

## Why Utilities Need This Domain

Utilities need asset reporting because they must decide:

- what assets are active, retired, missing, or disposed
- where assets are located
- which assets are aging out
- which asset classes cost too much to maintain
- which locations have high-risk assets
- which assets should be replaced first
- how to justify capital and maintenance spending

That creates four clear reporting value areas:

### 1. Inventory And Accountability

Utilities must know what physical infrastructure they own and where it is.

### 2. Risk And Reliability

Condition, failure, and lifecycle fields help prioritize maintenance and replacement.

### 3. Financial Planning

Book value, acquisition cost, replacement cost, disposal cost, and useful life support budgeting and capital planning.

### 4. Operational Support

Work, maintenance, and device issues make more sense when tied back to an asset population.

## How To Use This Domain For Reporting

Use this domain as the `authoritative asset base`, not as an event or work fact.

Best uses:

- `Asset Inventory Register`
  - one row per asset
  - status, type, serial, badge, location, owner, service area
- `Asset Condition and Risk`
  - asset condition, condition rating, confidence rating, failure flag, criticality
- `Replacement Planning`
  - acquisition date, in-service date, useful life, economic life, predicted wear-out, replacement cost, book value
- `Asset Location and Organization`
  - node, parent node, service area, planner, maintenance manager, owning organization
- `Asset Financial Exposure`
  - acquisition cost, replacement cost, salvage cost, disposal cost, average outage repair cost
- `Meter Asset Population`
  - use identifiers and specifications to isolate meter assets as a subset of all assets

This domain can support `meter asset` reporting, but only as a filtered subset of the broader asset population.

## How It Complements The Device Domain

This is the clean pattern:

- `Device domain` = what the meter or device did
- `Asset domain` = what the utility owns and how to manage it

Together they answer better questions:

- Which meter assets are generating repeated device events?
- Which poor-condition assets are tied to bad ERT populations?
- Which asset types have the highest replacement cost and the worst device-event rate?

Do not make the asset domain the base for device-event trend reporting. That flips the grain and makes the model harder to trust.

## Reporting Thought Process

When deciding which domain to use, walk through these questions:

### 1. What Is The Grain?

- Asset domain: one asset
- Device domain: one device or one event

### 2. What Decision Is Being Made?

- Asset: replace, maintain, budget, inspect, locate
- Device: investigate, respond, monitor, analyze failures

### 3. What Is The Time Behavior?

- Asset domain is slower-moving lifecycle context
- Device domain is faster-moving operational activity

### 4. What Is The User Trying To Improve?

- Asset managers want prioritization and capital planning
- Meter operations wants event monitoring and failure response

That is why both provide value, but in different ways.

## Important Guardrails In This Asset Domain

This domain has a few technical implications:

- `W1_ASSET -> W1_ASSET_NODE` is an `inner` join
  - assets without location rows will disappear
- `W1_ASSET -> CMS_W1_ASSET_IDENTIFIER_VW` is also `inner`
  - assets without identifier rows will disappear
- `W1_ASSET_NODE` appears to carry location history
  - if current-state rows are not isolated, assets can duplicate

Because of that, every report should explicitly choose one of these two designs:

### Current-State Inventory Report

Use only the current asset-location row.

### History Or Movement Report

Use `W1_ASSET_NODE.EFF_DTTM` and treat the report as a timeline/history report.

If those are mixed together, counts and financial sums will drift.

## Best Utility Reporting Uses Right Now

This domain is best for:

- asset inventory and accountability
- meter asset register
- asset location hierarchy
- condition and risk scoring
- replacement candidate lists
- capital planning support
- asset data quality exceptions

This domain is not best for:

- device event monitoring
- communication failures
- bad ERT trends
- event aging
- event-to-customer operational response

That work belongs in the device domain.

## Recommended Asset Reports To Build First

### 1. Asset Inventory Register

Purpose:
- show the current asset population and where each asset sits

Key fields:
- `Asset`
- `Asset Type`
- `Asset Type Description`
- `Status (Asset)`
- `Status Description (Asset)`
- `Asset Condition`
- `Asset Condition Description`
- `Serial Number`
- `Badge Number`
- `External ID`
- `Location/Organization`
- `Description`
- `Service Area`
- `Owning Organization`

Best visual:
- detail table

Value:
- foundational lookup and accountability report

### 2. Asset Condition And Risk

Purpose:
- identify poor-condition and higher-risk asset populations

Key fields:
- `Asset`
- `Asset Type`
- `Asset Condition`
- `Condition Rating`
- `Confidence Rating`
- `Failure`
- `Criticality`
- `Run To Failure`
- `Service Condition`
- `Location/Organization`

Best visual:
- heatmap or grouped bar plus exception table

Value:
- supports prioritization of inspections, maintenance, and replacement

### 3. Replacement Planning

Purpose:
- identify assets near or beyond economic and useful life

Key fields:
- `Acquisition Date`
- `In Service Date`
- `Useful Life (Years)`
- `Economic Life (Years)`
- `Predicted Wear Out Date`
- `Book Value`
- `Replacement Cost`
- `Disposal Cost`
- `Salvage Cost`
- `Asset Type`
- `Location/Organization`

Best visual:
- aging buckets, replacement candidate table, yearly trend

Value:
- supports capital planning and replacement prioritization

### 4. Asset Financial Exposure

Purpose:
- understand lifecycle cost and financial footprint

Key fields:
- `Acquisition Cost`
- `Book Value`
- `Replacement Cost`
- `Average Outage Repair Cost`
- `Hourly Outage Cost`
- `Disposal Cost`
- `Core Charge`
- `Asset Type`
- `Owning Organization`
- `Vendor Location`

Best visual:
- KPI tiles, ranked bar chart, finance detail table

Value:
- supports budgeting and business case development

### 5. Asset Location And Hierarchy

Purpose:
- understand where assets are placed and how locations roll up

Key fields:
- `Location/Organization`
- `Parent Location/Organization`
- `Location/Organization Type`
- `Service Area`
- `Planner`
- `Maintenance Manager`
- `Address`
- `City`
- `State`
- `Latitude`
- `Longitude`
- `Asset`
- `Asset Type`

Best visual:
- hierarchy table or map if mapping is available

Value:
- supports operational ownership and geographic planning

### 6. Meter Asset Register

Purpose:
- isolate the meter-like subset of the asset population

Key fields:
- `Asset`
- `Asset Type`
- `Specification`
- `Serial Number`
- `Badge Number`
- `Metrology Firmware Version`
- `NIC Firmware Version`
- `Purchase Order`
- `Vendor Location`
- `Location/Organization`

Best visual:
- detail table with filters

Value:
- creates the bridge between broad asset management and meter-specific operations

### 7. Asset Data Quality Exceptions

Purpose:
- find assets missing key reporting attributes

Key exception checks:
- missing `Serial Number`
- missing `Asset Type`
- missing `Location/Organization`
- missing `Owning Organization`
- missing current identifier row
- missing current location row

Best visual:
- exception table

Value:
- improves trust in all downstream reporting

## Simple Summary

Use the `asset domain` when the utility wants to manage the asset as a thing it owns.

Use the `device domain` when the utility wants to manage the meter as something that is behaving, failing, or producing events.

The value of the asset domain is that it turns raw infrastructure into management decisions:

- keep it
- repair it
- replace it
- move it
- retire it
- budget for it

## Build Checklist Before Publishing A Report

- Confirm the report grain is `one row per asset` unless it is intentionally historical
- Decide whether the report is `current-state` or `history`
- Validate that inner joins are not silently dropping assets you expected to see
- Prefer descriptive lookup fields over raw codes
- Check for duplicated assets caused by multiple `W1_ASSET_NODE` rows
- Use exception reports to identify missing identifiers or missing locations
- Keep asset reports separate from event reports unless the asset-event bridge has been proven safe

## Asset Domain Report Build Sheet

### Build Rules

This Domain is centered on `W1_ASSET`, but the current join design has two important implications:

- `W1_ASSET -> W1_ASSET_NODE` is an `inner` join
- `W1_ASSET -> CMS_W1_ASSET_IDENTIFIER_VW` is an `inner` join

That means assets without a node row or identifier row will not appear in the Domain result set.

For every report, explicitly choose one of these approaches:

- `Current-state asset reporting`
  - one row per asset
  - use the current node/location relationship only
- `Asset movement/history reporting`
  - one row per asset-location-effective-date combination
  - use `W1_ASSET_NODE.EFF_DTTM` intentionally

Use distinct measures where possible:

- `Distinct Asset ID`
- `Distinct Location/Organization`

### 1. Asset Inventory Register

- Purpose:
  - show the current known asset population with identifier, type, status, and location
- Best visual:
  - detail table
- Core fields:
  - `Asset`
  - `Asset Type`
  - `Asset Type Description`
  - `Status (Asset)`
  - `Status Description (Asset)`
  - `Status Reason Description (Asset)`
  - `Serial Number`
  - `Badge Number`
  - `External ID`
  - `Description`
  - `Location/Organization`
  - `Location/Organization Type`
  - `Service Area`
  - `Owning Organization Description (Asset)`
- Measures:
  - `Distinct Asset ID`
- Prompts:
  - `Asset Type`
  - `Status (Asset)`
  - `Location/Organization Type`
  - `Service Area`
  - `Owning Organization`
- Sort/group:
  - sort by asset type, then location, then asset id
- Value:
  - foundational lookup report for what exists, where it is, and how it is classified

### 2. Meter Asset Register

- Purpose:
  - isolate the meter-like subset of the asset population for meter operations and metrology users
- Best visual:
  - detail table with export
- Core fields:
  - `Asset`
  - `Asset Type`
  - `Asset Type Description`
  - `Specification`
  - `Specification Description`
  - `Serial Number`
  - `Badge Number`
  - `Purchase Order`
  - `Metrology Firmware Version`
  - `NIC Firmware Version`
  - `Vendor Location`
  - `Location/Organization`
  - `Service Area`
- Measures:
  - `Distinct Asset ID`
- Prompts:
  - `Asset Type`
  - `Specification`
  - `Vendor Location`
  - `Service Area`
- Sort/group:
  - sort by specification, serial number, asset id
- Value:
  - gives meter operations a controlled inventory of meter assets without mixing in all non-meter asset populations

### 3. Asset Condition And Risk

- Purpose:
  - identify poor-condition or risky asset populations that should be inspected, repaired, or replaced
- Best visual:
  - grouped bar + heatmap + exception table
- Core fields:
  - `Asset`
  - `Asset Type`
  - `Asset Condition`
  - `Asset Condition Description`
  - `Condition Rating`
  - `Confidence Rating`
  - `Failure`
  - `Failure Description`
  - `Criticality`
  - `Criticality Description`
  - `Run To Failure`
  - `Run to Failure Description`
  - `Service Condition`
  - `Service Condition Description`
  - `Location/Organization`
  - `Service Area`
- Measures:
  - `Distinct Asset ID`
- Prompts:
  - `Asset Type`
  - `Asset Condition`
  - `Criticality`
  - `Failure`
  - `Service Area`
  - `Location/Organization`
- Sort/group:
  - group by asset type and condition
  - sort by worst condition and highest criticality first
- Value:
  - helps asset managers prioritize attention on the most exposed parts of the fleet

### 4. Replacement Planning

- Purpose:
  - identify assets nearing end of life or with poor economic case for continued use
- Best visual:
  - aging buckets + ranked replacement table
- Core fields:
  - `Asset`
  - `Asset Type`
  - `Acquisition Date`
  - `In Service Date`
  - `Useful Life (Years)`
  - `Economic Life (Years)`
  - `Predicted Wear Out Date`
  - `Book Value`
  - `Replacement Cost`
  - `Disposal Cost`
  - `Salvage Cost`
  - `Acquisition Cost`
  - `Location/Organization`
  - `Service Area`
- Measures:
  - `Distinct Asset ID`
  - sum of `Book Value`
  - sum of `Replacement Cost`
- Prompts:
  - asset type
  - in-service date range
  - wear-out date range
  - service area
- Sort/group:
  - sort by predicted wear-out date ascending, then replacement cost descending
- Value:
  - supports capital planning and defensible replacement decisions

### 5. Asset Financial Exposure

- Purpose:
  - understand the financial footprint of asset populations and locations
- Best visual:
  - KPI tiles + ranked bar + finance table
- Core fields:
  - `Asset`
  - `Asset Type`
  - `Acquisition Cost`
  - `Book Value`
  - `Replacement Cost`
  - `Average Outage Repair Cost`
  - `Hourly Outage Cost`
  - `Disposal Cost`
  - `Core Charge`
  - `Vendor Location`
  - `Owning Organization`
  - `Service Area`
- Measures:
  - `Distinct Asset ID`
  - sum of `Acquisition Cost`
  - sum of `Book Value`
  - sum of `Replacement Cost`
- Prompts:
  - asset type
  - vendor location
  - owning organization
  - service area
- Sort/group:
  - sort by replacement cost descending
- Value:
  - helps finance and asset management identify high-cost asset populations and budget exposure

### 6. Asset Location And Hierarchy

- Purpose:
  - understand where assets sit and how they roll up through the location hierarchy
- Best visual:
  - hierarchy table or map
- Core fields:
  - `Asset`
  - `Location/Organization`
  - `Description`
  - `Parent Location/Organization`
  - `Address`
  - `City`
  - `State`
  - `Postal`
  - `Latitude`
  - `Longitude`
  - `Location/Organization Type`
  - `Service Area`
  - `Planner`
  - `Maintenance Manager`
- Measures:
  - `Distinct Asset ID`
  - `Distinct Location/Organization`
- Prompts:
  - location type
  - service area
  - planner
  - maintenance manager
- Sort/group:
  - group by service area and node type
  - sort by location then asset
- Value:
  - supports ownership, geographic planning, and operational accountability

### 7. Asset Movement And Disposition History

- Purpose:
  - show where assets have moved over time and their disposition changes
- Best visual:
  - chronological detail table
- Core fields:
  - `Asset`
  - `Effective Date/Time`
  - `Asset Disposition`
  - `Asset Disposition Description`
  - `Location/Organization`
  - `Current Location/Organization ID`
  - `Attached to Asset ID`
  - `Current Attached to Asset ID`
  - `Failure`
  - `Failure Description`
- Measures:
  - `Distinct Asset ID`
- Prompts:
  - effective date range
  - asset disposition
  - failure flag
  - location
- Sort/group:
  - sort by asset, then effective date/time descending
- Value:
  - supports lifecycle audit, movement tracing, and current-vs-historical location analysis

### 8. Asset Ownership And Organization Accountability

- Purpose:
  - show who owns assets operationally and financially
- Best visual:
  - grouped bar + table
- Core fields:
  - `Asset`
  - `Owning Organization (Asset)`
  - `Owning Organization Description (Asset)`
  - `Owning Organization (Location)`
  - `Owning Organization Description (Location)`
  - `Planner`
  - `Maintenance Manager`
  - `Buyer`
  - `Work Request Approval Profile`
- Measures:
  - `Distinct Asset ID`
- Prompts:
  - owning organization
  - planner
  - maintenance manager
  - buyer
- Sort/group:
  - group by owning organization and planner
- Value:
  - makes it clear who is accountable for asset populations and decision flow

### 9. Asset Procurement And Vendor View

- Purpose:
  - understand where assets came from and which vendors are associated with them
- Best visual:
  - vendor summary bar + detail table
- Core fields:
  - `Asset`
  - `Vendor Location`
  - `Location Name`
  - `Purchase Order`
  - `Acquisition Date`
  - `Acquisition Cost`
  - `Serial Number`
  - `Asset Type`
  - `Specification`
- Measures:
  - `Distinct Asset ID`
  - sum of `Acquisition Cost`
- Prompts:
  - vendor location
  - acquisition date range
  - asset type
- Sort/group:
  - group by vendor location
  - sort by acquisition cost descending
- Value:
  - supports procurement review and supplier-linked asset inventory analysis

### 10. Asset Data Quality Exceptions

- Purpose:
  - find assets that are missing key identifiers or management attributes
- Best visual:
  - exception table
- Core checks:
  - missing `Serial Number`
  - missing `Asset Type`
  - missing `Location/Organization`
  - missing `Owning Organization`
  - missing `Specification`
  - missing `Vendor Location` where expected
- Measures:
  - `Distinct Asset ID`
- Prompts:
  - asset type
  - status
  - location
- Sort/group:
  - sort by missing-field pattern, then asset id
- Value:
  - improves trust in all downstream lifecycle and financial reports

## Recommended First Build Order

If the goal is to build practical utility reports quickly, start in this order:

1. `Asset Inventory Register`
2. `Meter Asset Register`
3. `Asset Condition And Risk`
4. `Replacement Planning`
5. `Asset Location And Hierarchy`
6. `Asset Data Quality Exceptions`

This order works because it gives:

- a trusted inventory baseline first
- a meter-specific operational slice second
- prioritization and planning views after the baseline is understood

## Practical Domain Use Summary

Use this Asset Domain when the report needs to answer:

- What assets do we own?
- Where are they?
- What state are they in?
- What are they worth?
- Which ones should we repair, retire, or replace?

Do not use this Asset Domain as the primary source when the report needs to answer:

- What device events are occurring right now?
- Which models are producing bad ERT events?
- What event types are trending up?
- Which service points have repeated device failures?

Those are device-domain questions.
