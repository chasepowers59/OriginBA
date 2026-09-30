# Payments Cashiering Tender Snapshot

## Purpose
`CISADM.PAY_TNDR_CASH_RPT_CURR` is the governed tender-centered snapshot for payment intake and cashiering analysis.

It is the right artifact when the business question is:
- which tender channels are driving payment intake
- how OriginPay compares to other intake sources
- what tender-control and deposit-control context exists
- how much tender volume is moving through cashiering

## Grain
One row per `PAY_TENDER_ID`.

Natural key:
- `PAY_TENDER_ID`

## Driving truth
The base population comes from `CISADM.CI_PAY_TNDR`, with event, tender-control, deposit-control, staged-source, and lightweight payment overlays added around that grain.

## What is included
- tender amount, type, and status
- payment event date and event-level payment overlay
- tender source and source-family classification
- tender-control context
- deposit-control context
- staged external tender context
- lightweight payor account and customer context

## What is intentionally excluded
- raw row-per-pay-segment detail
- debt exposure truth
- FT / GL payment accounting detail

Those belong in separate payment-application or finance artifacts.

## Key design rule
`TENDER_AMT` is the trusted additive measure.

Event and deposit totals are overlays and can repeat across multiple tender rows.

## XML artifact
Importable Domain XML:
- `domains/exports/manual_imports/PAY_TNDR_CASH_RPT_CURR_End_User_Friendly.xml`

Companion XML inventory:
- `sql/performance/snapshots/docs/snapshot_xml_inventory.md`

## SQL workspace
- `sql/performance/snapshots/payments_cashiering/pay_tndr_cashier/`

## Ad hoc guide
- `docs/payments_cashiering_pay_tndr_cash_adhoc_recipes.md`

## SQL Developer runbook
For exact SQL Developer steps to inspect the table, view the current procedure, and validate the scheduler job, use:
- `sql/performance/snapshots/docs/snapshot_sqldeveloper_runbook.md` under `PAY_TNDR_CASH_RPT_CURR`

## Business summary
This table answers the question:

"For each tender that came in, what source and control context did it have, how much money did it represent, and what payment-event context surrounds it?"
