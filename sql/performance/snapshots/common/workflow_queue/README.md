# Workflow Queue Snapshot

This folder is for the Common workstream workflow snapshot built from governed to-do entry and batch process sources.

## Purpose

`CISADM.WORKFLOW_QUEUE_RPT_CURR` is the standardized Common snapshot for operational queue monitoring across manual to-do work and batch thread execution.

It consolidates legacy live-domain subjects into one governed queue grain:
- `To Do - Domain`
- `Batch Process - Domain`

## Grain

One row per queue item, unified with a `QUEUE_SOURCE` discriminator.

Natural key:
- `QUEUE_SOURCE` + `QUEUE_NATURAL_KEY`

Source-specific keys preserved in typed columns:
- `TODO`: `TD_ENTRY_ID`
- `BATCH`: `SCHEDULER_ID` on `CI_BATCH_INST` (batch thread instance)

## Why this grain was chosen

To Do and Batch Process are different operational subjects with different native keys, but both answer "what work is in the queue?" for Common operations reporting.

A unified table with `QUEUE_SOURCE` is the safer cross-domain design because:
- to-do truth is one row per `CI_TD_ENTRY.TD_ENTRY_ID`
- batch truth is one row per `CI_BATCH_INST` thread instance (`SCHEDULER_ID`), not the batch run header alone
- a single composite key (`QUEUE_SOURCE`, `QUEUE_NATURAL_KEY`) preserves uniqueness without mixing incompatible row shapes
- typed nullable columns expose the right context for each queue family

The legacy To Do domain inner-joins `CMS_TD_ENTRY_FKREF`, which can drop to-do entries without FK reference rows. This snapshot keeps the full to-do population and left-joins FK, premise, and timing overlays.

The legacy Batch Process domain drives from `CI_BATCH_INST` and joins run and thread context at thread-instance grain, which this snapshot preserves directly.

## Driving truth

- To Do entries: `CISADM.CI_TD_ENTRY`
- Batch thread instances: `CISADM.CI_BATCH_INST`
- Batch run header context: `CISADM.CI_BATCH_RUN`
- Batch thread status context: `CISADM.CI_BATCH_THD`

Optional to-do overlays:
- `CISADM.CMS_TD_ENTRY_FKREF` and `CISADM.CMS_TD_ENTRY_TIMES` when present (SmartCity client views)
- Portable fallback: `CI_TD_DRLKEY` / `CI_TD_DRLKEY_TY` pivot plus inline timing formulas from `CI_TD_ENTRY`
- Optional FK enrichment: `CISADM.X1_BI_TD_ENTRY_VW` (comment out join in refresh procedures when unavailable)
- `CISADM.CI_PREM`
- `CISADM.CI_PER_NAME`
- `CISADM.CI_MSG_L`

## What is included

- to-do status, assignment, message, timing, FK reference, and premise context
- batch run / thread status, record counts, duration, and control descriptions
- `LOAD_DTTM`

## What is intentionally excluded

- exception detail from bill segment / usage / VEE domains (use `OPS_EXCEPTION_RPT_CURR`)
- row-per-FK-reference expansion when multiple FK rows exist for one to-do
- batch control master setup detail beyond run/thread context

## Refresh strategy

| Script | Procedure | Use |
| --- | --- | --- |
| `02a_full_history_refresh_procedure.sql` | `REFRESH_WORKFLOW_QUEUE_RPT_CURR` | First-time baseline: `TRUNCATE` + full insert |
| `02_refresh_snapshot_procedure.sql` | `REFRESH_WORKFLOW_QUEUE_RPT_CURR` | Scheduled refresh: purge stale completed rows, then delete/reload the refresh scope |

Rolling scope includes:
- to-do entries created in the last six months or still open
- batch thread instances started in the last six months or tied to runs without an end timestamp

Rolling window anchors:
- `TODO`: `CI_TD_ENTRY.CRE_DTTM`
- `BATCH`: `CI_BATCH_INST.START_DTTM`

## Recommended use

- open to-do workload by type, role, owner, and age
- batch thread monitoring by control, run status, and error counts
- cross-queue operational dashboards in the Common workstream

## Do not use for

- exception root-cause analysis (use `OPS_EXCEPTION_RPT_CURR`)
- batch control configuration analytics
- premise or account master reporting without queue context

## Workflow

1. Create the snapshot table with `01_create_snapshot_table.sql`.
2. Load full history once with `02a_full_history_refresh_procedure.sql`.
3. Deploy the rolling refresh procedure from `02_refresh_snapshot_procedure.sql`.
4. Validate row safety and source parity with `04_validation_queries.sql`.

## Related inventory inputs

- `output/standard_offering_domain_inventory/by_domain/Common_To_Do_To_Do.csv`
- `output/standard_offering_domain_inventory/by_domain/Common_Batch_Batch_Process.csv`

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `02a_full_history_refresh_procedure.sql`
- `02_refresh_snapshot_procedure.sql`
- `04_validation_queries.sql`
