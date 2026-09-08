# Tender Cashiering Snapshot

This folder is for the first governed payments and cashiering snapshot built for this tenant.

## Purpose

`CISADM.PAY_TNDR_CASH_RPT_CURR` is the standardized tender-centered snapshot for current and historical payment intake analysis.

It is designed for ad hoc reporting where users need one row per tender with:
- payment-event business date
- tender amount, type, and status
- derived tender source family
- tender source and tender-control context
- deposit-control context
- staged external-source context when present
- lightweight payment, account, customer, and pay-segment overlays

## Grain

One row per `PAY_TENDER_ID`.

Natural key:
- `PAY_TENDER_ID`

## Why tender grain

Discovery in this tenant showed:
- `PAY_EVENT -> PAY_TNDR` is close to one-to-one
- `PAY -> PAY_SEG` is strongly one-to-many
- tender control and deposit control are materially populated and join cleanly from `CI_PAY_TNDR`
- legacy auto-pay configuration exists, but current activity is dominated by OriginPay plus standard cashier/mail/drop-off sources

That makes tender the safest first combined cashiering grain.

## Driving truth

The base population comes from `CISADM.CI_PAY_TNDR` joined to:
- `CISADM.CI_PAY_EVENT` for business date
- `CISADM.CI_TNDR_CTL` for tender control
- `CISADM.CI_DEP_CTL` for deposit control
- delivered lookup/description tables for tender type, tender source, and payment status

## What is included

- one row per tender
- additive `TENDER_AMT`
- derived `SOURCE_FAMILY_CD` / `SOURCE_FAMILY_DESC` for governed channel grouping
- event-level payment summary:
  - pay count
  - sole pay id when the event has exactly one pay row
  - event pay status when all pay rows share one status
  - event pay amount
- event-level tender count and amount
- tender type description
- tender source description and source-type flag
- deposit-control status and balances
- staged tender linkage through `CI_PAY_TNDR_ST` and `CI_APAY_SRC`
- primary customer row for `PAYOR_ACCT_ID` when available
- event-level pay-segment counts and amounts
- deposit totals summarized from `CI_TNDR_DEP`
- populated deposit-control start and end balances from `CI_DEP_CTL`

## Additive vs overlay fields

`TENDER_AMT` is the trusted additive measure at snapshot grain.

The following are contextual overlays and should not be summed across tender rows without understanding the grouping:
- `EVENT_PAY_AMT`
- `EVENT_TENDER_AMT`
- `EVENT_PAY_SEG_AMT`
- `DEP_CTL_START_BALANCE`
- `DEP_CTL_END_BALANCE`
- `DEP_CTL_TNDR_DEP_AMT`

Those values are repeated across multiple tender rows whenever multiple tenders share the same event or deposit control.

## What is intentionally excluded

- raw row-per-pay-segment detail
- detailed tender-control balancing workflow
- debt-class deposit obligation logic
- raw FT / GL payment accounting detail

Those belong in separate lower-grain or finance-focused snapshots if needed later.

## Key design rules

No business decoding is hardcoded where a governed lookup exists.

Descriptions are sourced from delivered lookup/translation tables, and the refresh is split into:
- base tender-grain load
- post-load enrichment merges for customer, staged external-source, deposit summary, and pay-segment overlay

`SOURCE_FAMILY_*` is a governed reporting classification derived in the snapshot with this priority:
- staged external tender
- OriginPay
- legacy auto-pay
- other cashiering source

This avoids introducing `PAY -> PAY_SEG` fanout into the base insert.

## Recommended use

- payment channel mix and trend analysis
- OriginPay versus non-OriginPay intake analysis
- cashier/mail/drop-off source analysis
- staged external tender monitoring
- tender-control and deposit-control operational reporting

## Do not use for

- exact additive payment-event totals across multi-tender events
- raw payment application detail by pay segment
- debt exposure reporting
- FT / GL reconciliation

Use dedicated payment-application or finance snapshots for those subjects.

## Domain XML
- Workspace copy: `PAY_TNDR_CASH_RPT_CURR_End_User_Friendly.xml`
- Import bundle: `domains/exports/manual_imports/PAY_TNDR_CASH_RPT_CURR_End_User_Friendly.xml`
- Keep both copies synchronized when the Domain changes.

## Master Guide
- Full technical guide: `06_master_technical_guide.md`
- Use it for final design, source-family logic, QA evidence, and deployment/debugging guidance.

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `01b_alter_existing_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`
- `05_qa_results_template.md`
- `07_intensive_qa_queries.sql`
- `06_master_technical_guide.md`
- `PAY_TNDR_CASH_RPT_CURR_End_User_Friendly.xml`
