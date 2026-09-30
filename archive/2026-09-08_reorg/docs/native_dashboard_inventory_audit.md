# Native Dashboard Inventory Audit

## Purpose

This document describes the native dashboard audit tool used to inspect exported Jaspersoft `dashboardModelResource` objects before trying to package or promote them.

Script:

- [audit_native_dashboards.py](/Users/chase/OriginBA-3/scripts/jaspersoft/audit_native_dashboards.py)

Current audit output:

- [native_dashboard_inventory_audit.json](/Users/chase/OriginBA-3/deploy/native_dashboard_pack_v1/native_dashboard_inventory_audit.json)

## Why This Tool Exists

Native dashboards are more complex than standalone reports or saved Ad Hoc views. They often contain:

- nested temporary Ad Hoc dashlets
- local input controls
- file resources such as wiring, layout, and dashboard components
- hidden public-template dependencies
- environment-specific repository paths

That means a dashboard can look fine in the source environment but still be unsafe to package for another folder or environment.

## What The Tool Checks

For each `dashboardModelResource`, the audit extracts:

- dashboard label and repository folder
- source ZIP member path
- `resourceDescriptor` counts by type
- temp dashlet ids
- public template dependencies
- development snapshot path references
- datasource URIs
- nested Ad Hoc resource counts
- nested report-unit counts
- local resource type counts

It also gives a simple package-safety outcome:

- `package_safe = true`
  - no hard blockers detected
- `package_safe = false`
  - one or more blocking dependencies detected

## Current High-Value Findings

The initial audit of the four priority snapshot/finance dashboard families showed:

- all currently audited dashboards are **not yet package-safe**
- every audited dashboard still references a shared public template
- all audited dashboards contain temp dashlet ids
- the snapshot-development dashboards also retain `Development/Snapshots` path references

Current audited dashboards:

- `Billing Dashboard`
  - legacy billing-side version under `Billing_and_Rates/Bill_Segment`
  - snapshot-development version under `Development/Snapshots/Billed_Usage/Amount_Billed`
- `Usage Dashboard`
  - snapshot-development version under `Development/Snapshots/Meter_Operations/Scalar_Usage`
  - legacy meter-ops version under `Meter_Operations/Unbilled_Usage`
- `Financial Transaction Dashboard`
- `General Ledger Dashboard`

## Example Command

Audit the priority dashboards:

```bash
python3 /Users/chase/OriginBA-3/scripts/jaspersoft/audit_native_dashboards.py \
  --source-zip "/Users/chase/Downloads/Workstream folder.zip" \
  --dashboard-label "Financial Transaction Dashboard" \
  --dashboard-label "General Ledger Dashboard" \
  --dashboard-label "Billing Dashboard" \
  --dashboard-label "Usage Dashboard" \
  --output-json /Users/chase/OriginBA-3/deploy/native_dashboard_pack_v1/native_dashboard_inventory_audit.json
```

## How To Read The Output

### `public_template_refs`

If non-empty, the dashboard still depends on shared template resources such as:

- `/public/templates/actual_size.820.jrxml`

That is a packaging blocker unless the target server is guaranteed to have the same shared template path.

### `temp_ids`

If non-empty, the dashboard still contains temp-style dashlet IDs such as:

- `/temp/tmpAdv_...`

Those are expected in exported dashboards, but they are a signal that the dashboard needs careful rewrite and verification before promotion.

### `development_snapshot_refs`

If non-empty, the dashboard still references:

- `/Workstreams/Development/Snapshots/...`

Those references must be rewritten if the dashboard is being promoted into a curated client package.

### `nested_adhoc_resources`

These are the embedded dashlets that usually matter most. For each one, the audit records:

- embedded datasource or Domain URIs
- input control count
- public template references

## What To Do Next

The audit tool is the discovery step, not the packaging step.

The next tool to build should be:

- a **native dashboard packager / rewriter**

That next tool should:

- choose the correct source dashboard when labels are duplicated
- rewrite folder URIs
- rewrite Domain and datasource references
- remove or replace public-template dependencies where appropriate
- normalize temp dashlet references
- emit an import-safe dashboard package

## Recommended Next Packaging Order

1. `Financial Transaction Dashboard`
2. `General Ledger Dashboard`
3. `Billing Dashboard` from the snapshot-development branch, not the legacy live-domain branch
4. `Usage Dashboard` from the snapshot-development branch, not the older unbilled-usage branch

That order gives the strongest governed story first.
