# Current Snapshot Report Backlog For Utilities

## Purpose

This document turns the completed governed snapshot estate into a practical report backlog focused on utility business value.

It only includes report ideas that can be built now from snapshots already completed and QA-passed in this repo.

Current snapshots in scope:
- `PAY_TNDR_CASH_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`
- `FT_RPT_CURR`
- `D1_USAGE_RPT_CURR`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`
- `D1_MSRMT_RPT_CURR`
- `BSEG_BILLED_USAGE_RPT_CURR`
- `BSEG_SQ_USAGE_RPT_CURR`

## Why These Reports Matter For Utilities

Utility organizations are operationally dense. Reporting is not just for historical analytics. It is used to:
- verify revenue capture and accounting movement
- monitor payment intake and cashiering controls
- validate usage and measurement populations before billing defects grow
- explain billed quantities and billed revenue to business users
- surface exceptions quickly enough for operations to act before customer impact expands

The best utility reports usually do one of three things:
- help control money
- help validate billing and usage truth
- help operations identify exceptions early

## Priority Backlog

### Priority 1. Deposit Control Reconciliation

- Source Snapshot:
  `PAY_TNDR_CASH_RPT_CURR`
- Artifact Type:
  `JRXML`
- Primary Users:
  cashiering supervisors, finance operations
- Why It Is Important For Utilities:
  utility payment operations run through multiple intake channels and control layers. Deposit-control reconciliation helps confirm that tenders, deposit amounts, and balances align before issues affect cash reporting or downstream finance processes.
- Business Questions Answered:
  which deposit controls are balanced
  which deposit controls have unusual variances
  what source types are driving deposit activity
- Recommended Grain:
  one row per `DEP_CTL_ID`
- Core Fields:
  `DEP_CTL_ID`
  `DEP_CTL_CRE_DTTM`
  `DEP_CTL_STATUS_FLG`
  `DEP_CTL_SRCE_TYPE_FLG`
  `DEP_CTL_START_BALANCE`
  `DEP_CTL_END_BALANCE`
  `DEP_CTL_TNDR_DEP_COUNT`
  `DEP_CTL_TNDR_DEP_AMT`
- Core Measures:
  tender count
  `SUM(TENDER_AMT)`
  variance
- Best Filters:
  date range
  deposit source type
  deposit status
  non-zero variance only

### Priority 2. Payment Channel Summary

- Source Snapshot:
  `PAY_TNDR_CASH_RPT_CURR`
- Artifact Type:
  `Ad Hoc`
- Primary Users:
  finance ops, cashiering leadership, customer operations
- Why It Is Important For Utilities:
  utilities take payments from walk-in, mail, drop box, bank, OriginPay, and auto-pay channels. Business users need to know which channels are being used, how much money is flowing through them, and where operational attention is needed.
- Business Questions Answered:
  where payments are coming from
  whether OriginPay or legacy auto-pay usage is changing
  which tender types and sources are driving payment volume
- Recommended Grain:
  summary by day, source family, tender type, or tender source
- Core Fields:
  `PAY_DT`
  `SOURCE_FAMILY_DESC`
  `TENDER_TYPE_DESC`
  `TNDR_SOURCE_DESC`
  `TNDR_SRCE_TYPE_FLG`
  `STAGED_TENDER_SW`
- Core Measures:
  tender count
  `SUM(TENDER_AMT)`
- Best Filters:
  pay date
  source family
  tender type
  staged tender switch

### Priority 3. GL Distribution Code Summary

- Source Snapshot:
  `FT_GL_DISTRIBUTION_RPT_CURR`
- Artifact Type:
  `Ad Hoc`
- Primary Users:
  finance analysts, controllers
- Why It Is Important For Utilities:
  utilities post high volumes of financial activity across many GL accounts and distribution codes. Users need a governed way to see how activity is distributed by batch, account, and transaction family without reading raw GL lines.
- Business Questions Answered:
  which GL accounts and distribution codes are active
  what a given batch posted to each account
  whether debit and credit activity looks reasonable by account and distribution
- Recommended Grain:
  grouped by `BATCH_NBR`, `DST_ID`, `DST_DESC`, `GL_ACCT`
- Core Fields:
  `BATCH_CD`
  `BATCH_NBR`
  `GL_ACCT`
  `DST_ID`
  `DST_DESC`
  `FT_TYPE_FLG_DESC`
  `GL_DISTRIB_STATUS_DESC`
- Core Measures:
  `SUM(GL_AMOUNT)`
  `SUM(DEBIT_AMT)`
  `SUM(CREDIT_AMT)`
  row count
  distinct FT count
- Best Filters:
  batch number
  batch code
  FT type
  GL status

### Priority 4. Usage Operations Summary

- Source Snapshot:
  `D1_USAGE_RPT_CURR`
- Artifact Type:
  `Ad Hoc`
- Primary Users:
  meter operations, billing support, usage analysts
- Why It Is Important For Utilities:
  usage is the bridge between field measurement and billing. If usage populations drift, billing defects, customer disputes, and revenue impacts follow. Users need a safe operational summary of usage counts and quantities.
- Business Questions Answered:
  how much usage is being produced by period
  which usage statuses are present
  whether usage counts are stable over time
- Recommended Grain:
  one row per usage in the snapshot, summarized by month, status, SA, or service dimensions
- Core Fields:
  `D1_USAGE_ID`
  usage dates and timing fields
  `SA_ID`
  `ACCT_ID`
  status fields exposed in the snapshot
- Core Measures:
  usage count
  quantity totals
  final quantity totals
- Best Filters:
  date range
  service agreement
  account
  usage status

### Priority 5. Billed Usage Summary

- Source Snapshot:
  `BSEG_BILLED_USAGE_RPT_CURR`
- Artifact Type:
  `Ad Hoc`
- Primary Users:
  billing analysts, revenue analysts
- Why It Is Important For Utilities:
  billed usage is where operational usage becomes customer-facing and revenue-facing billing truth. Business users need to analyze billed quantities and billed amounts without relying on raw bill segment joins.
- Business Questions Answered:
  what usage and billed amounts were billed by service agreement
  which bill cycles or service types drove billed revenue
  where high-usage or high-bill amounts are occurring
- Recommended Grain:
  one row per `BSEG_ID`, summarized by SA, bill cycle, customer, or period
- Core Fields:
  `BSEG_ID`
  `SA_ID`
  `ACCT_ID`
  bill-cycle and service-type fields
  billed usage and billed amount fields
- Core Measures:
  billed usage total
  billed amount total
  bill segment count
- Best Filters:
  billing period
  bill cycle
  service type
  account

### Priority 6. Measurement Quality Monitor

- Source Snapshot:
  `D1_MSRMT_RPT_CURR`
- Artifact Type:
  `Ad Hoc`
- Primary Users:
  meter data management, meter operations
- Why It Is Important For Utilities:
  measurements are the upstream feed for usage and billing. If measurement populations are thin, duplicated, delayed, or missing in certain components or service points, billing and operations will feel it later.
- Business Questions Answered:
  how many measurements are arriving by day or month
  which measuring components and service points are active
  whether measurement populations look stable across install events
- Recommended Grain:
  one row per measurement, summarized by time, measuring component, service point, install event
- Core Fields:
  `MEASR_COMP_ID`
  `MSRMT_DTTM`
  service point and install-event fields
  quality/status fields exposed in the snapshot
- Core Measures:
  measurement count
  measurement quantity totals where applicable
- Best Filters:
  measurement date
  measuring component
  service point
  install event

### Priority 7. GL Exception Monitor

- Source Snapshot:
  `FT_GL_DISTRIBUTION_RPT_CURR`
- Artifact Type:
  `JRXML`
- Primary Users:
  finance controls, reconciliation users
- Why It Is Important For Utilities:
  utility finance teams often need a control packet, not just a detail listing. This report gives them a fast way to isolate unusual GL rows and focus on what may need action.
- Business Questions Answered:
  which GL lines have unusual status or missing context
  which rows have zero amount or suspicious patterns
  what exceptions are present inside a batch or date range
- Recommended Grain:
  detailed GL lines, filtered to exception criteria
- Core Fields:
  `BATCH_CD`
  `BATCH_NBR`
  `ACCOUNTING_DT`
  `GL_ACCT`
  `DST_DESC`
  `FT_TYPE_FLG_DESC`
  `GL_DISTRIB_STATUS_DESC`
  `GL_AMOUNT`
  `DEBIT_AMT`
  `CREDIT_AMT`
  `CUSTOMER_NAME_UPR`
  `ACCT_ID`
  `FT_ID`
- Core Measures:
  error count
  warning count
  debit total
  credit total
- Best Filters:
  batch number
  GL status
  amount threshold
  exception category

### Priority 8. Tender Control Balancing

- Source Snapshot:
  `PAY_TNDR_CASH_RPT_CURR`
- Artifact Type:
  `Ad Hoc`
- Primary Users:
  cashiering operations
- Why It Is Important For Utilities:
  utility cashiering is operational and repetitive. Users need to review intake control buckets by source, date, and amount to support balancing and close workflows.
- Business Questions Answered:
  what tenders were captured under each tender control
  which sources and channels are associated to a control
  what amount moved through each control
- Recommended Grain:
  grouped by `TNDR_CTL_ID`
- Core Fields:
  `TNDR_CTL_ID`
  `TNDR_CTL_CRE_DTTM`
  `TNDR_SOURCE_DESC`
  `TNDR_SRCE_TYPE_FLG`
  `SOURCE_FAMILY_DESC`
- Core Measures:
  tender count
  `SUM(TENDER_AMT)`
- Best Filters:
  date range
  tender source
  source family
  tender status

### Priority 9. Billed Determinant Analysis

- Source Snapshot:
  `BSEG_SQ_USAGE_RPT_CURR`
- Artifact Type:
  `Ad Hoc`
- Primary Users:
  billing analysts, rates analysts
- Why It Is Important For Utilities:
  utilities often need to explain billed determinants, not just total billed usage. UOM, TOU, and SQI-level reporting helps validate determinant construction and rate-component behavior.
- Business Questions Answered:
  what determinants were billed
  which UOM/TOU/SQI combinations are most active
  how billed quantities vary by bill segment and service context
- Recommended Grain:
  one row per determinant key in the snapshot
- Core Fields:
  `BSEG_ID`
  `UOM_CD`
  `TOU_CD`
  `SQI_CD`
  `SA_ID`
  bill-segment context
- Core Measures:
  determinant quantity totals
  determinant row count
- Best Filters:
  billing period
  UOM
  TOU
  SQI
  service agreement

### Priority 10. Financial Transaction Operations Report

- Source Snapshot:
  `FT_RPT_CURR`
- Artifact Type:
  `Ad Hoc`
- Primary Users:
  finance ops, auditors, support analysts
- Why It Is Important For Utilities:
  this gives a cleaner FT-header operational view than the GL-line snapshot when users care about the transaction itself rather than each GL distribution row.
- Business Questions Answered:
  what FT types are being created
  what freeze and distribution states exist
  which accounts and service agreements are associated with transactions
- Recommended Grain:
  one row per `FT_ID`
- Core Fields:
  `FT_ID`
  `FT_TYPE_FLG_DESC`
  `ACCOUNTING_DT`
  `FREEZE_SW`
  `GL_DISTRIB_STATUS_DESC`
  `SA_ID`
  `ACCT_ID`
  `CUSTOMER_NAME`
- Core Measures:
  FT count
  amount totals available at FT grain
- Best Filters:
  accounting date
  FT type
  freeze status
  GL distribution status
  account

## Recommended Delivery Sequence

1. Deposit Control Reconciliation
2. Payment Channel Summary
3. GL Distribution Code Summary
4. Usage Operations Summary
5. Billed Usage Summary
6. Measurement Quality Monitor
7. GL Exception Monitor
8. Tender Control Balancing
9. Billed Determinant Analysis
10. Financial Transaction Operations Report

## Practical Delivery Guidance

- Start with `Ad Hoc` for summary and exploratory reports where users need slicing and filtering.
- Use `JRXML` where the utility business process expects a controlled packet, especially reconciliation and exception reporting.
- Keep using the governed snapshots instead of rebuilding raw SQL join logic in Jaspersoft.
- If a business request needs data that the snapshot does not currently publish, document the gap and extend Oracle first rather than forcing a risky Domain join.

## Next Best Build Set

If only a few reports are going to be built next, the highest-value starter set is:
- `Deposit Control Reconciliation`
- `Payment Channel Summary`
- `GL Distribution Code Summary`
- `Usage Operations Summary`
- `Billed Usage Summary`

That set gives immediate coverage across payments, finance, meter operations, and billing using governed data already available now.
