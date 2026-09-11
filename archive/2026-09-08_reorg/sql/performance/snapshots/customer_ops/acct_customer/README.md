# Account Customer Snapshot

This folder is for the customer-operations account snapshot built from governed CISADM account, person, alert, service-agreement, and landlord sources.

## Purpose

`CISADM.ACCT_CUSTOMER_RPT_CURR` is the standardized customer-operations snapshot for current account-level customer context.

It consolidates legacy live-domain subjects into one governed account grain:
- `Customer - Domain` (main customer person at account)
- `Account Alert - Domain` (alert counts aggregated at account; no bill-segment fan-out)
- `C-Side - Domain` (account + SA summary aggregates)
- `Landlord Agreement - Domain` (landlord agreement counts and primary agreement)

## Grain

One row per `ACCT_ID`.

Natural key:
- `ACCT_ID`

## Driving truth

Account truth comes from `CISADM.CI_ACCT`.

Main customer context comes from:
- `CISADM.CI_ACCT_PER` with `MAIN_CUST_SW = 'Y'`
- `CISADM.CI_PER`
- `CISADM.CI_PER_NAME` with `NAME_TYPE_FLG = 'PRIM'`

Alert truth is pre-aggregated from `CISADM.CI_ACCT_ALERT` before join so the snapshot never inherits the `CI_BSEG` fan-out present in the legacy Account Alert domain.

Service-agreement truth is pre-aggregated from `CISADM.CI_SA` and `CISADM.CI_SA_TYPE`.

Landlord truth is pre-aggregated from `CISADM.CI_LANDLORD`.

Contact overlays come from `CISADM.C1_PER_CONTDET` joined to `CISADM.C1_COMM_RTE_TYPE` for active routes only (`CND_ACTINACT_FLG = 'C1AC'`).

## What is included

- account setup and classification fields with resolved `_L` descriptions (`LANGUAGE_CD = 'ENG'`)
- main customer name, address, person/business, life-support, and bill-route context
- active contact pivots for primary email and ranked phone routes
- `alert_count`, `open_alert_count`, and latest open-alert reference fields
- `active_sa_count`, `total_sa_count`, and lightweight SA-type profile fields
- landlord agreement count plus primary landlord agreement reference
- `LOAD_DTTM`

## What is intentionally excluded

- row-per-alert detail
- row-per-SA detail
- row-per-landlord-premise detail
- bill-segment or GL reconciliation fields from the legacy Account Alert domain

Those belong in lower-grain or finance-specific snapshots.

## Key design rules

- `ACCT_ID` is the only additive population key; alert and SA measures are account-level aggregates, not row-multipliers.
- Legacy Account Alert joins to `CI_SA` / `CI_BSEG` are deliberately not used.
- `SOLE_ACTIVE_SA_TYPE_CD` / `SOLE_ACTIVE_SA_TYPE_DESC` populate only when the account has exactly one active SA type.
- Phone pivots rank active `PHONE` routes by primary flag and contact id; they are convenience overlays, not a full contact-detail replacement.
- Full-history deployment uses `02a_full_history_refresh_procedure.sql` (`TRUNCATE` + `INSERT`).
- Scheduled maintenance uses `02_refresh_snapshot_procedure.sql`, which:
  1. deletes dormant accounts with `SETUP_DT` older than six months and no SA/alert activity in the retention window
  2. deletes and re-inserts the refresh scope (recent setup, active SAs, recent SA changes, recent alerts, and currently open alerts)

## Recommended use

- account outreach and customer-class segmentation
- open-alert operational dashboards without alert-row fan-out
- account + active-SA population summaries
- landlord account identification at account grain

## Do not use for

- alert workflow detail at alert grain
- SA lifecycle or balance detail
- landlord premise/coverage detail
- customer-contact event history

Use separate lower-grain snapshots or live domains for those subjects.

## Workflow

1. Create the snapshot table with `01_create_snapshot_table.sql`.
2. Load full history once with `02a_full_history_refresh_procedure.sql`.
3. Deploy the rolling refresh procedure from `02_refresh_snapshot_procedure.sql`.
4. Validate row safety and aggregate parity with `04_validation_queries.sql`.

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `02a_full_history_refresh_procedure.sql`
- `02_refresh_snapshot_procedure.sql`
- `04_validation_queries.sql`
