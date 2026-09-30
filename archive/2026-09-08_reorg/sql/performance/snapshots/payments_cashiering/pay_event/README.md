# Payment Event Snapshot

This folder is for the governed payments and cashiering snapshot built from `CISADM.CI_PAY` with payment-event, tender, deposit-control, and pay-plan context.

## Purpose

`CISADM.PAY_EVENT_RPT_CURR` is the standardized payment snapshot for cashiering analysis where users need one row per payment with safe event-level overlays.

It consolidates legacy live-domain subjects into one governed payment grain:
- `Payment Header - Domain` (payment header and payment event context)
- `Payment Tender - Domain` (tender counts and amounts aggregated to payment event)
- `Deposit Control - Domain` (tender-control and deposit-control context aggregated to payment event)
- `Pay Plan - Domain` (account pay-plan summary overlay)

## Grain

One row per `PAY_ID` from `CISADM.CI_PAY`.

Natural key:
- `PAY_ID`

The snapshot name reflects the payment-event business context carried on each payment row (`PAY_EVENT_ID`, `PAY_DT`, tender/deposit overlays). It is not a payment-event-only population.

## Driving truth

Payment truth comes from `CISADM.CI_PAY` joined to `CISADM.CI_PAY_EVENT`.

Tender, tender-control, and deposit-control truth is pre-aggregated from:
- `CISADM.CI_PAY_TNDR`
- `CISADM.CI_TNDR_CTL`
- `CISADM.CI_DEP_CTL`
- `CISADM.CI_TNDR_DEP`

before join so the snapshot never inherits tender-row fan-out onto the payment grain.

Pay-plan truth is pre-aggregated from `CISADM.CI_PP` at account grain and joined back to the payment account.

Main customer context comes from `CISADM.CI_ACCT_PER` with `MAIN_CUST_SW = 'Y'` and `CISADM.CI_PER_NAME`.

## What is included

- payment header fields with resolved lookup descriptions (`LANGUAGE_CD = 'ENG'`)
- payment event date, create date/time, and document number
- primary customer name for the payment account
- `DAYS_OLD` based on `PAY_DT`
- event-level tender summary:
  - `EVENT_TENDER_COUNT`
  - `EVENT_TENDER_AMT`
  - `DISTINCT_TENDER_TYPE_COUNT`
  - sole tender type when the event has exactly one tender type
- event-level tender-control and deposit-control references
- `EVENT_DEP_AMT` summarized from `CI_TNDR_DEP`
- account pay-plan count, active pay-plan count, and primary pay-plan reference
- `LOAD_DTTM`

## Additive vs overlay fields

`PAY_AMT` is the trusted additive measure at snapshot grain.

The following are contextual overlays and should not be summed across payment rows without understanding the grouping:
- `EVENT_TENDER_AMT`
- `EVENT_DEP_AMT`
- `PRIMARY_DEP_CTL_END_BALANCE`
- `ACCT_PP_COUNT`
- `ACTIVE_PP_COUNT`

Those values repeat across multiple payment rows whenever multiple payments share the same event or account overlay scope.

## What is intentionally excluded

- row-per-tender detail
- row-per-pay-segment detail
- row-per-pay-plan-schedule detail
- raw FT / GL payment accounting detail

Those belong in separate lower-grain cashiering or finance snapshots such as `PAY_TNDR_CASH_RPT_CURR`.

## Key design rules

- `PAY_ID` is the only additive population key.
- Tender and deposit context is aggregated to `PAY_EVENT_ID` before join.
- Pay-plan context is aggregated to `ACCT_ID` before join.
- Full-history deployment uses `02a_full_history_refresh_procedure.sql` (`TRUNCATE` + `INSERT`).
- Scheduled maintenance uses `02_refresh_snapshot_procedure.sql`, which:
  1. deletes payments with `PAY_DT` older than six months
  2. deletes and re-inserts the six-month refresh scope by payment business date

## Recommended use

- payment header reporting with event business date
- payment status and cancel-reason analysis
- payment rows enriched with event tender mix and deposit-control context
- account pay-plan presence on payment activity

## Do not use for

- tender-level cashiering detail
- exact additive payment-event totals when multiple payments exist on one event
- pay-plan schedule detail
- FT / GL reconciliation

Use `PAY_TNDR_CASH_RPT_CURR` or dedicated finance snapshots for those subjects.

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
