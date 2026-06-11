# Operations Exception Snapshot

This folder is for the Common workstream exception snapshot built from governed bill-segment, usage-transaction, and VEE exception sources.

## Purpose

`CISADM.OPS_EXCEPTION_RPT_CURR` is the standardized Common snapshot for operational exception monitoring across billing, usage, and VEE subjects.

It consolidates legacy live-domain subjects into one governed exception grain:
- `Bill Segment Exception - Domain`
- `Usage Transaction Exception - Domain`
- `VEE Exception - Domain`

## Grain

One row per source exception, unified with an `EXCP_SOURCE` discriminator.

Natural key:
- `EXCP_SOURCE` + `EXCP_NATURAL_KEY`

Source-specific keys preserved in typed columns:
- `BSEG`: `BSEG_ID` + `BSEG_EXCP_FLG` (`EXCP_NATURAL_KEY = BSEG_ID || '~' || BSEG_EXCP_FLG`)
- `USAGE`: `USAGE_EXCP_ID`
- `VEE`: `VEE_EXCP_ID`

## Why unified grain was chosen

Separate snapshot tables would preserve grain safely, but the Common workstream reports on exception workload across all three families. A unified table with `EXCP_SOURCE` is the safer cross-domain design because:

- each exception family has a different native primary key shape
- a single composite key (`EXCP_SOURCE`, `EXCP_NATURAL_KEY`) preserves uniqueness without forcing artificial key collisions
- typed nullable columns keep type-specific context without mixing incompatible measures
- one governed refresh and one Domain target simplify operational dashboards

The legacy exception domains inner-join `CI_TD_DRLKEY` / `CI_TD_ENTRY`, which can multiply exception rows when multiple to-do entries exist for the same driver key. This snapshot ranks to one primary linked to-do per driver key before join so exception population is preserved.

Usage and VEE service-point context is also ranked to one chosen service point per driver key to avoid MDM path fan-out.

## Driving truth

- Bill segment exceptions: `CISADM.CI_BSEG_EXCP`
- Usage transaction exceptions: `CISADM.D1_USAGE_EXCP`
- VEE exceptions: `CISADM.D1_VEE_EXCP`

Primary linked to-do context comes from `CISADM.CI_TD_DRLKEY`, `CISADM.CI_TD_DRLKEY_TY`, and `CISADM.CI_TD_ENTRY`, ranked to one open-or-latest entry per driver key.

## What is included

- exception header/status fields with resolved lookup and `_L` descriptions (`LANGUAGE_CD = 'ENG'`)
- type-specific exception attributes and account / SA / service-point context where applicable
- one ranked primary to-do overlay (`TD_*` columns)
- `LOAD_DTTM`

## What is intentionally excluded

- row-per-to-do detail when multiple to-do entries exist for the same exception driver key
- full bill-segment, usage-header, or initial-measurement detail beyond exception-safe context
- cross-source additive measures (counts are context only at this grain)

## Refresh strategy

| Script | Procedure | Use |
| --- | --- | --- |
| `02a_full_history_refresh_procedure.sql` | `REFRESH_OPS_EXCEPTION_RPT_CURR` | First-time baseline: `TRUNCATE` + full insert |
| `02_refresh_snapshot_procedure.sql` | `REFRESH_OPS_EXCEPTION_RPT_CURR` | Scheduled refresh: purge closed rows older than six months, then delete/reload the refresh scope |

Rolling scope includes:
- exceptions created in the last six months
- unreviewed bill segment exceptions
- open usage / VEE exceptions
- rows with open linked to-do entries retained outside the create-date window

Rolling window anchor:
- `EXCP_CRE_DTTM`

## Recommended use

- open exception workload by source (`BSEG`, `USAGE`, `VEE`)
- exception severity / status dashboards with primary to-do context
- account- or service-point-linked exception triage for billing and MDM teams

## Do not use for

- to-do queue analytics without exception context (use `WORKFLOW_QUEUE_RPT_CURR`)
- bill-segment billed usage or amount truth
- usage scalar detail or measurement history

## Workflow

1. Create the snapshot table with `01_create_snapshot_table.sql`.
2. Load full history once with `02a_full_history_refresh_procedure.sql`.
3. Deploy the rolling refresh procedure from `02_refresh_snapshot_procedure.sql`.
4. Validate row safety and source parity with `04_validation_queries.sql`.

## Related inventory inputs

- `output/standard_offering_domain_inventory/by_domain/Common_Exception_Bill_Segment_Exception.csv`
- `output/standard_offering_domain_inventory/by_domain/Common_Exception_Usage_Transaction_Exception.csv`
- `output/standard_offering_domain_inventory/by_domain/Common_Exception_VEE_Exception.csv`

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `02a_full_history_refresh_procedure.sql`
- `02_refresh_snapshot_procedure.sql`
- `04_validation_queries.sql`
