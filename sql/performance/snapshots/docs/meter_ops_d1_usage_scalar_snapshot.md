# Meter Ops Usage Scalar Detail Snapshot

## Purpose
`CISADM.D1_USAGE_SCALAR_DTL_RPT_CURR` is the standardized scalar-detail usage snapshot for meter-side quantity analysis.

It is designed for Jasper domains, ad hoc reporting, and analyst self-service where users need additive consumption by final unit of measure, customer class, premise, service type, or measuring component.

## Grain
One row per scalar detail line in `CISADM.D1_USAGE_SCALAR_DTL`.

Natural key:
- `D1_USAGE_ID`
- `SEQ_NUM`

## Driving table
`CISADM.D1_USAGE_SCALAR_DTL`

The snapshot brings `D1_USAGE` header context onto each scalar line rather than trying to summarize scalar quantities into a usage-header fact.

Billing context is added only through the canonical path `D1_USAGE.USG_EXT_ID -> C1_USAGE.USAGE_ID` for `C1_USAGE.BO_STATUS_CD = 'BD-PROC'`.

## What is included
- raw and final quantity fields from `D1_USAGE_SCALAR_DTL`
- raw and final `UOM / TOU / SQI` codes and descriptions
- usage, measuring-component-use, peak-quantity, and measurement-condition flags with descriptions
- usage-header context from `D1_USAGE`
- subscription context from `D1_US`
- optional billing bridge fields from `C1_USAGE`
- service-agreement, account, customer class, service type, and premise context

## Best use cases
- customer-class consumption by final unit of measure
- premise and service-point consumption trace
- service-type quantity trends
- measuring-component usage analysis
- raw vs. final quantity comparison
- billing-linked scalar usage research

## Business summary
This table answers a different question than the usage header snapshot:

"What scalar usage quantities were produced for each usage transaction, and how do those quantities break down by unit family and customer context?"

## XML artifact
Importable Domain XML:
- `domains/exports/manual_imports/D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml`

Companion XML inventory:
- `sql/performance/snapshots/docs/snapshot_xml_inventory.md`

## SQL Developer runbook
For exact SQL Developer steps to inspect the table, view the current procedure, and validate the scheduler job, use:
- `sql/performance/snapshots/docs/snapshot_sqldeveloper_runbook.md` under `D1_USAGE_SCALAR_DTL_RPT_CURR`
