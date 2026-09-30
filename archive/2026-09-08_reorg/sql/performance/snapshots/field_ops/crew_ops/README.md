# Crew Operations Snapshot

This folder is for the field-operations crew snapshot built from `CISADM.C1_REPRESENTATIVE` with field-activity rollups linked through `D1_ACTIVITY_CHAR` (`CMFAREP`).

## Purpose

`CISADM.CREW_OPS_RPT_CURR` is the standardized field-operations snapshot for crew/representative workload, capability context, and linked field-activity performance metrics.

It is designed for ad hoc reporting where users need one safe row per crew with:
- representative status, type, and user linkage
- MobileLite service-area and worker-capability profile
- distinct field-activity counts (total, completed, open)
- latest linked field-activity context without duplicating the crew row

## Grain

One row per `CREW_ID` (`C1_REPRESENTATIVE_CD`).

Natural key:
- `CREW_ID`

## Source domain consolidated

Field coverage is aligned to Standard Offering domain inventory:
- `Field_Operations_Crew_Crew.csv`

## Driving truth

Crew truth comes from `CISADM.C1_REPRESENTATIVE` joined to:
- `CMS_C1_REPRESENTATIVE_BODA_VW` (inner join to match governed domain population)

Field-activity linkage comes from `D1_ACTIVITY_CHAR` where:
- `CHAR_TYPE_CD = 'CMFAREP'`
- `SRCH_CHAR_VAL = C1_REPRESENTATIVE_CD`

Activities are restricted to field-activity category rows via `D1_ACTIVITY_TYPE.ACTIVITY_TYPE_CAT_FLG = 'D1FA'`.

Completed activities follow the Standard Offering domain rule:
- `BO_STATUS_CD IN ('COMPLETED', 'DISCARDED')`

## Why this grain was chosen

The legacy Crew domain mixes:
- `C1_REPRESENTATIVE` as the driving crew entity
- optional `D1_ACTIVITY_CHAR` / `D1_ACTIVITY` joins that would fan out at activity grain
- BODA crew profile and activity detail tables

Joining activities directly at crew grain would repeat crew rows unless activity facts are rolled up first.

## What is included

- crew header fields from `C1_REPRESENTATIVE`
- crew name, status, type, and external-system descriptions
- linked application user name from `SC_USER`
- service area and worker capability from `CMS_C1_REPRESENTATIVE_BODA_VW`
- field-activity count rollups and latest-activity overlay per crew
- open-work aging (`OLDEST_OPEN_FA_DAYS`) and average completion duration

## What is intentionally excluded

- one row per field activity (use `FIELD_ACTIVITY_RPT_CURR`)
- row-per-activity-characteristic detail
- requester-user or appointment detail beyond latest-activity overlay

Those belong in the activity-grain snapshot.

## Refresh strategy

| Script | Procedure | Use |
| --- | --- | --- |
| `02a_full_history_refresh_procedure.sql` | `REFRESH_CREW_OPS_RPT_CURR` | First-time baseline: `TRUNCATE` + full insert for all BODA-profiled crews |
| `02_refresh_snapshot_procedure.sql` | `REFRESH_CREW_OPS_RPT_CURR` | Scheduled refresh: delete/reload crews with linked field activities in the rolling 6-month activity-date window |

Rolling window anchors on linked `D1_ACTIVITY` rows (any one qualifies the crew for refresh):
- `CRE_DTTM`
- `START_DTTM`
- `STATUS_UPD_DTTM`
- `END_DTTM`

In rolling mode, activity rollups count only field activities inside the same 6-month window.

Deploy `02a` for initial population, then replace the procedure with `02` for ongoing operations (same procedure name, rolling implementation).

## End-user guidance

Use this snapshot for:
- crew workload and open-activity backlog by service area or capability
- completed vs. open field-activity mix by crew
- identifying crews with aged open work
- latest-activity status/type overlays at crew grain

Do not use it to answer:
- row-level field-activity appointment or contact detail
- activity-to-premise/account tracing (use `FIELD_ACTIVITY_RPT_CURR`)
- activity relationship or cancellation reason distributions at activity grain

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `02a_full_history_refresh_procedure.sql`
- `02_refresh_snapshot_procedure.sql`
- `04_validation_queries.sql`

## Related inventory input

- `output/standard_offering_domain_inventory/by_domain/Field_Operations_Crew_Crew.csv`
