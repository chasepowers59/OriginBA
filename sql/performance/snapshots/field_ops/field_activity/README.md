# Field Activity Snapshot

This folder is for the field-operations activity snapshot built from `CISADM.D1_ACTIVITY` with BODA, MDM service-point, and CIS premise/account context consolidated at activity grain.

## Purpose

`CISADM.FIELD_ACTIVITY_RPT_CURR` is the standardized field-operations snapshot for field-activity workload, appointment context, and service-location overlays.

It is designed for ad hoc reporting where users need one safe row per field activity with:
- activity status, type, lifecycle timestamps, and aging metrics
- BODA appointment and contact details
- MobileLite / representative characteristics when present
- MDM service-point descriptors from `D1_SP`
- CIS service point, premise, and account context via `CI_SP` / `CI_PREM` / `CI_ACCT`

## Grain

One row per `D1_ACTIVITY_ID` for field-activity category rows (`D1FA`).

Natural key:
- `D1_ACTIVITY_ID`

## Source domain consolidated

Field coverage is aligned to Standard Offering domain inventory:
- `Field_Operations_Field_Activity_Field_Activity.csv`

## Driving truth

Activity truth comes from `CISADM.D1_ACTIVITY` joined to:
- `D1_ACTIVITY_TYPE` with `ACTIVITY_TYPE_CAT_FLG = 'D1FA'`
- `CMS_D1_ACTIVITY_D1FA_BODA_VW` (inner join to match governed domain population)

This keeps the snapshot focused on field activities rather than all activity categories.

## Join rules that preserve grain

- `D1_ACTIVITY_REL_OBJ` is pre-aggregated to one `D1-SP` link per activity before joining `D1_SP`.
- `CI_SP` is joined on `SP_ID = D1_SP_ID`.
- `CI_SA` is ranked to one account per service point (active SA preferred) to avoid fan-out.
- `D1_ACTIVITY_REL` parent link (`D1PR`) is optional and does not multiply rows.
- `CMS_ACTIVITY_ML` and `CMS_D1_ACTIVITY_CHAR_VW` are left joins for representative / priority overlays.

## What is included

- core activity header and status descriptions from framework lookup tables
- cancel, field-task-type, and reschedule reason descriptions
- BODA appointment, contact, and instruction fields
- representative / intermediate-status overlays from MobileLite sources
- MDM service-point address, market, route, and status descriptors
- CIS premise and account customer-class context when SP linkage exists
- computed aging fields: `DAYS_OLD`, `DAYS_COMPLETED`, `DAYS_STARTED_SINCE_CREATE`

## What is intentionally excluded

- row-per-activity-relationship detail
- row-per-characteristic detail
- multi-SP fan-out when an activity touches multiple related objects

Those belong in separate lower-grain snapshots if needed.

## Refresh strategy

| Script | Procedure | Use |
| --- | --- | --- |
| `02a_full_history_refresh_procedure.sql` | `REFRESH_FIELD_ACTIVITY_RPT_CURR` | First-time baseline: `TRUNCATE` + full insert |
| `02_refresh_snapshot_procedure.sql` | `REFRESH_FIELD_ACTIVITY_RPT_CURR` | Scheduled refresh: delete/reload activities with any activity date in the rolling 6-month window |

Rolling window anchors (any one qualifies the row):
- `ACT_CRE_DTTM`
- `START_DTTM`
- `STATUS_UPD_DTTM`
- `END_DTTM`

Deploy `02a` for initial population, then replace the procedure with `02` for ongoing operations (same procedure name, rolling implementation).

## End-user guidance

Use this snapshot for:
- open and completed field-activity workload by type, status, and division
- appointment-required populations and aging dashboards
- service-point and premise overlays on field work
- customer/account context on field activities with CIS SP linkage

Do not use it to answer:
- crew productivity at representative grain (use `CREW_OPS_RPT_CURR`)
- activity relationship graphs or child-object detail
- task-log workflow history

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `02a_full_history_refresh_procedure.sql`
- `02_refresh_snapshot_procedure.sql`
- `04_validation_queries.sql`

## Related inventory input

- `output/standard_offering_domain_inventory/by_domain/Field_Operations_Field_Activity_Field_Activity.csv`
