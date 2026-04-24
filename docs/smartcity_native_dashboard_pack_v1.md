# SmartCity Native Dashboard Pack V1

## Decision

The next highest-value dashboard work should focus on **actual Jaspersoft dashboards** (`dashboardModelResource`), not JRXML reports that are merely styled like dashboards.

This is the correct priority because:

- the source export already contains real dashboard objects
- clients expect importable dashboard pages, not only summary reports
- native dashboards let you compose existing governed Ad Hoc views and Domains without rebuilding all visual logic as JRXML

## What Was Confirmed

The exported Workstreams package already includes real native dashboards such as:

- `Financial Transaction Dashboard`
- `General Ledger Dashboard`
- `Billing Dashboard`
- `Usage Dashboard`
- `Batch Process Dashboard`
- `Exception and To Do Dashboard`
- `Field Operations Dashboard`
- `Debt Management Dashboard`
- `New Premises Dashboard`
- `New Service Agreements Dashboard`

Snapshot-side native dashboards specifically confirmed in the export:

- `Billed Usage and Amount Charged`
- `Usage Dashboard`
- `Financial Transaction Dashboard`
- `General Ledger Dashboard`

## Highest-Value Next Dashboard Build

The best next deliverable is a curated **Native Snapshot Dashboard Pack V1** using the already governed snapshot-backed subject areas.

Recommended V1 scope:

1. `Billing Dashboard`
2. `Usage Dashboard`
3. `Financial Transaction Dashboard`
4. `General Ledger Dashboard`

These are the best first native dashboards because they align to the strongest governed snapshot estate:

- `BSEG_BILLED_USAGE_RPT_CURR`
- `BSEG_SQ_USAGE_RPT_CURR`
- `D1_USAGE_RPT_CURR`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`
- `D1_MSRMT_RPT_CURR`
- `FT_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`

## Why These Four First

### Billing Dashboard

Highest business value:

- revenue visibility
- exception review
- billed amount and usage trends
- customer class and bill cycle segmentation

### Usage Dashboard

Highest operational value:

- early warning for billing-impacting usage defects
- usage population monitoring
- high-usage and exception visibility

### Financial Transaction Dashboard

Highest reconciliation value:

- transaction health
- bill cycle transaction monitoring
- distribution status visibility
- payment detail drill

### General Ledger Dashboard

Highest finance-control value:

- AR visibility
- GL distribution tracing
- batch-level review
- write-off monitoring

## Build Approach

Do not create these from scratch first.

Instead:

1. start from the existing exported native dashboard objects
2. inventory the dashlets, filters, and nested dependencies
3. rewrite them to a governed `Standard_Offering` or `Dashboard_Pack_V1` folder structure
4. remove unnecessary temporary or stale dependencies
5. verify that each dashlet points only to approved snapshot-side assets

This is a modernization and packaging effort first, not a blank-sheet design effort.

## Packaging Goal

Target native dashboard folder:

- `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Standard_Offering`

Recommended business subfolders:

- `/Standard_Offering/Billing_and_Rates`
- `/Standard_Offering/Meter_Operations`
- `/Standard_Offering/Finance`

Recommended packaged dashboard objects:

- `Billing_Dashboard`
- `Usage_Dashboard`
- `Financial_Transaction_Dashboard`
- `General_Ledger_Dashboard`

## Required Dependency Rules

Before a native dashboard is packaged, validate:

- every dashlet points to a governed report, Ad Hoc view, or Domain
- no dashlet depends on `/public/templates/...` unless intentionally accepted
- no temporary `/temp/...` component references remain unresolved
- no stale `Workstreams/Development/Snapshots/...` references remain if the target package is meant to be curated
- datasource and Domain references are package-safe

## What To Avoid

Do not prioritize:

- live-domain dashboards first
- rebuilding the same dashboard concept as JRXML before using the native dashboard export you already have
- broad dashboard packs with mixed governance quality

Do not assume:

- every native dashboard in the export is already client-ready
- every nested Ad Hoc dashlet is safe to move unchanged

## Most Valuable Immediate Automation

The highest-value automation after the `Standard_Offering` package pipeline is:

- a **native dashboard inventory and dependency auditor**

That tool should:

- find every `dashboardModelResource`
- list dashlets and nested resources
- list Domains and Ad Hoc views used by each dashboard
- flag `/public/templates/...` dependencies
- flag `/temp/...` references
- flag datasource mismatches
- output a package-safety report

This is more valuable than generic dashboard ideas because it gives a direct path from exported dashboards to safe importable client packages.

That audit tool now exists:

- [audit_native_dashboards.py](/Users/chase/OriginBA-3/scripts/jaspersoft/audit_native_dashboards.py)
- [native_dashboard_inventory_audit.md](/Users/chase/OriginBA-3/docs/native_dashboard_inventory_audit.md)
- [native_dashboard_inventory_audit.json](/Users/chase/OriginBA-3/deploy/native_dashboard_pack_v1/native_dashboard_inventory_audit.json)

## Recommended Next Implementation

The next concrete build should be:

1. package-safe rewrite `Financial Transaction Dashboard`
2. package-safe rewrite `General Ledger Dashboard`

Why those two first:

- strongest current governed snapshot backing
- highest client-facing reconciliation value
- lowest ambiguity compared with live-domain dashboards

After that:

4. `Billing Dashboard`
5. `Usage Dashboard`

## Bottom Line

If the goal is something clients can simply import and use, the best next move is:

- build a **native dashboard pack modernization workflow**
- start with the existing snapshot-backed native dashboards already in the export
- make those dashboards safe, governed, and portable

That is the highest-value path.
