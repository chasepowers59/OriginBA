# Meter Ops Usage Header Snapshot

## Purpose
`CISADM.D1_USAGE_RPT_CURR` is the standardized lean usage-header snapshot for meter-side usage transactions.

It is designed for Jasper domains, ad hoc reporting, and analyst self-service where runtime joins across `D1_USAGE`, subscription context, billing bridge tables, service agreement, account, and customer dimensions would otherwise be expensive and structurally fragile.

## Recommended workflow
1. Run the preflight validation in `sql/performance/snapshots/meter_ops/d1_usage/00a_preflight_validation.sql`.
2. Confirm `D1_USAGE` is cleanly one row per `D1_USAGE_ID`.
3. Build the snapshot from the usage-header grain, not from a mixed-grain legacy domain export.
4. Run the validation suite after the table and procedure are created.
5. Run the refresh off-hours because the procedure commits monthly batches and the table can be partially refreshed while the load is in progress.

## Grain
One row per usage transaction in `CISADM.D1_USAGE`.

Natural key:
- `D1_USAGE_ID`

## Driving table
`CISADM.D1_USAGE`

This keeps the snapshot focused on usage-transaction truth rather than customer-first or child-detail-first reporting shapes.

## What is included
- usage status, reason, timing, calculation group, calculation type, source, route, cycle, and service-provider context
- usage-subscription context from `D1_US`
- optional billing bridge fields from `C1_USAGE`
- bill-segment, service-agreement, account, customer, customer class, and premise context when the billing bridge resolves

## What was intentionally removed
- aggregated usage-period quantity context from `D1_USAGE_PERIOD_SQ`
- aggregated scalar-detail context from `D1_USAGE_SCALAR_DTL`
- mutually exclusive resolved quantity fields
- raw child detail grain

Why:
- quantity and determinant analysis is a different fact than a usage header
- keeping quantity logic in the header snapshot made refreshes much heavier and blurred the intended grain
- XML-dependent BODA parsing introduced runtime failures that are not acceptable for a core operational snapshot
- quantity reporting is now better handled by a dedicated scalar-detail snapshot

## Key design rule
Billing linkage is treated as optional enrichment, not as the driving truth.

That means the snapshot keeps all usage headers, then adds billing context only through the canonical path `D1_USAGE.USG_EXT_ID -> C1_USAGE.USAGE_ID` for `C1_USAGE.BO_STATUS_CD = 'BD-PROC'`. If no bridge resolves, the usage header still remains in the snapshot.

The refresh procedure loads the snapshot in monthly batches based on the best available usage timestamp (`START_DTTM`, then `CRE_DTTM`, then `STATUS_UPD_DTTM`). This keeps the final logic the same while reducing Oracle TEMP usage during large rebuilds.

The refresh clears the table with `DELETE` rather than `TRUNCATE`. That is slower than DDL truncate, but it is less likely to fail with `ORA-00054` when users or tools still have the snapshot open.

## Best use cases
- usage transaction monitoring by status, reason, cycle, route, or service provider
- estimate and skip-pattern analysis
- comparing usage created vs. used-on-bill / linked-to-frozen-bseg behavior
- subscription-centric usage reporting
- customer-class, service-type, or premise segmentation of usage transaction volume
- a governed header layer for scalar-detail usage reporting

## Business summary
This table answers a simple question:

"What usage transaction did the system create, what process and subscription context did it have, and how did it bridge into billing when that bridge exists?"

It gives end users a stable usage-header dataset without forcing them to understand the full C2M usage-processing and billing chain.

## XML artifact
Importable Domain XML:
- `domains/exports/manual_imports/D1_USAGE_RPT_CURR_End_User_Friendly.xml`

Companion XML inventory:
- `sql/performance/snapshots/docs/snapshot_xml_inventory.md`

## SQL Developer runbook
For exact SQL Developer steps to inspect the table, view the current procedure, and validate the scheduler job, use:
- `sql/performance/snapshots/docs/snapshot_sqldeveloper_runbook.md` under `D1_USAGE_RPT_CURR`
