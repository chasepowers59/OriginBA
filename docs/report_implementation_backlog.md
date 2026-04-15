# Report Implementation Backlog

## Purpose

Convert the SQL query-library review into a concrete implementation backlog based on:
- the SQL reviewed under `Oracle SQL Developer Queries`
- the governed snapshots already completed in this repo
- the remaining governed snapshot work still needed

This is the execution-oriented follow-up to:
- [oracle_sql_query_library_workstream_catalog.md](C:/Users/cvpow/OneDrive/Desktop/OriginBA/docs/oracle_sql_query_library_workstream_catalog.md)
- [governed_snapshot_delivery_status.md](C:/Users/cvpow/OneDrive/Desktop/OriginBA/sql/performance/snapshots/docs/governed_snapshot_delivery_status.md)

## Important Note

Yes, the report recommendations are based on the SQL library that was reviewed.

But they are not treated as raw one-to-one SQL-to-report conversions.
They are filtered through:
- current governed snapshot availability
- data grain safety
- repeat business value
- whether the use case should be `Ad Hoc` or fixed `JRXML`

## Build Rules

- Use `Ad Hoc` when the need is self-service slicing/filtering on a governed semantic layer.
- Use `JRXML` when the layout needs to be standardized, branded, subtotaled, or operationally repeatable.
- Do not build new reports directly on raw legacy SQL when a governed snapshot exists or should exist.
- If a use case depends on unfinished governed snapshots, finish the snapshot package first.
- Do not list a field in a build plan unless it exists in the current governed snapshot contract or is explicitly marked as derived in the report layer.
- When a current snapshot lacks important business detail, note the gap explicitly instead of implying the report can already provide it.

## Current Snapshot Reality Check

This backlog has been reviewed against the current governed snapshot contracts.

Current build-ready governed snapshots for reporting:
- `PAY_TNDR_CASH_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`
- `FT_RPT_CURR`
- `BSEG_BILLED_USAGE_RPT_CURR`
- `BSEG_SQ_USAGE_RPT_CURR`
- `D1_USAGE_RPT_CURR`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`
- `D1_MSRMT_RPT_CURR`

Important current gaps and caveats:
- `PAY_TNDR_CASH_RPT_CURR` is tender-grain only. It does not currently publish `PAY_ID`, `SA_ID`, or true payment-application detail.
- `PAY_TNDR_CASH_RPT_CURR.DEP_CTL_START_BALANCE` exists in the snapshot contract but is currently loaded as null in the released procedure, so do not rely on it in production-facing reconciliation logic.
- `FT_GL_DISTRIBUTION_RPT_CURR.IS_LATEST_BATCH_NBR` exists but is intentionally not populated in the current release; do not use it in report filters or KPIs.
- `ACCT_DEBT_RPT_CURR` and `COLL_PROC_RPT_CURR` are not yet complete, so debt and collections report plans remain future-state only.
- Any debit, credit, net, exception, or variance columns called for below are report-layer derivations unless the snapshot explicitly stores them as separate fields.

## Phase 1: Build Now From Current Snapshots

### 1. Tender Control Balancing

- Artifact Type:
  `Ad Hoc`
- Source Snapshot:
  `PAY_TNDR_CASH_RPT_CURR`
- SQL Basis:
  `C2M.Payments.TenderControl.sql`
  `C2M.Payments.PaymentTenders.sql`
  `C2M.Payments.sql`
- Users:
  cashiering operations, finance operations
- Purpose:
  summarize tenders by tender control for balancing and intake review
- Row / Group Grain:
  grouped by `TNDR_CTL_ID`
- Core Fields:
  `TNDR_CTL_ID`
  `TNDR_SOURCE_DESC`
  `TNDR_SRCE_TYPE_FLG`
  `PAY_DT`
  optional `SOURCE_FAMILY_DESC`
- Measures:
  tender count
  `SUM(TENDER_AMT)`
  staged tender count if available
- Filters:
  date range
  source family
  tender source
  tender status
- Why Ad Hoc:
  users will want to slice and sort interactively
- Next Deliverable:
  build saved Ad Hoc view from the payments Domain

### 2. Deposit Control Reconciliation

- Artifact Type:
  `JRXML`
- Source Snapshot:
  `PAY_TNDR_CASH_RPT_CURR`
- SQL Basis:
  `C2M.Payments.DepositControl.sql`
  `C2M.Payments.PaymentTenders.sql`
  `C2M.Payments.DepositLabels.sql`
- Users:
  finance ops, cashiering supervisors
- Purpose:
  reconcile tender totals to deposit control totals
- Row / Group Grain:
  one row per `DEP_CTL_ID`
- Core Fields:
  `DEP_CTL_ID`
  `DEP_CTL_CRE_DTTM`
  `DEP_CTL_STATUS_FLG`
  `DEP_CTL_SRCE_TYPE_FLG`
  `DEP_CTL_END_BALANCE`
  `DEP_CTL_TNDR_DEP_COUNT`
  `DEP_CTL_TNDR_DEP_AMT`
- Measures:
  tender count
  `SUM(TENDER_AMT)`
  variance
- Filters:
  date range
  source type
  status
  optionally non-zero variance only
- Why JRXML:
  this is a recurring operational reconciliation packet
- Next Deliverable:
  refine the existing deposit-control report package into final production layout
- Current Snapshot Note:
  `DEP_CTL_START_BALANCE` should be treated as unavailable for now because the released snapshot procedure leaves it null. Build the report around `TENDER_AMT`, `DEP_CTL_TNDR_DEP_AMT`, `DEP_CTL_TNDR_DEP_COUNT`, `DEP_CTL_END_BALANCE`, and derived variance instead.

### 3. Payment Tender Detail

- Artifact Type:
  `Ad Hoc`
- Source Snapshot:
  `PAY_TNDR_CASH_RPT_CURR`
- SQL Basis:
  `C2M.Payments.PaymentTenders.sql`
  `C2M.Payments.sql`
- Users:
  payment support, finance ops, customer operations
- Purpose:
  inspect payment tenders with channel/source context
- Row / Group Grain:
  one row per `PAY_TENDER_ID`
- Core Fields:
  `PAY_TENDER_ID`
  `PAY_DT`
  `TENDER_AMT`
  `TENDER_TYPE_DESC`
  `TNDR_SOURCE_DESC`
  `TNDR_SRCE_TYPE_FLG`
  `SOURCE_FAMILY_DESC`
  `CUSTOMER_NAME`
  `PAYOR_ACCT_ID`
- Measures:
  tender count
  `SUM(TENDER_AMT)`
- Filters:
  pay date
  tender type
  source family
  staged tender switch
- Why Ad Hoc:
  investigation and self-service use case
- Next Deliverable:
  build saved Ad Hoc and decide whether one fixed JRXML export is also needed

### 4. Payment Application Detail

- Artifact Type:
  `Ad Hoc`
- Source Snapshot:
  none currently sufficient
- SQL Basis:
  `C2M.Payments.PaymentDetails.sql`
  `C2M.Payments.PaymentEvent.sql`
- Users:
  finance ops, customer care
- Purpose:
  show how payment events were applied to accounts and service agreements
- Row / Group Grain:
  payment application detail
- Core Fields:
  `PAY_EVENT_ID`
  `PAYOR_ACCT_ID`
  `CUSTOMER_NAME`
  `EVENT_PAY_STATUS_FLG`
  `EVENT_PAY_STATUS_DESC`
  `EVENT_PAY_AMT`
  `EVENT_PAY_SEG_COUNT`
  `EVENT_PAY_SEG_AMT`
  `EVENT_MATCH_EVT_COUNT`
  tender context
- Measures:
  event amount
  event count
- Filters:
  payment date
  account
  payment status
- Why Ad Hoc:
  users will navigate and filter heavily
- Next Deliverable:
  do not build this as a full payment-application report from the current tender snapshot. The current snapshot does not expose `PAY_ID`, `SA_ID`, or payment-application grain. If business needs true payment-to-SA application reporting, package a follow-on governed payment-application snapshot first.

### 5. GL Distribution Code Summary

- Artifact Type:
  `Ad Hoc`
- Source Snapshot:
  `FT_GL_DISTRIBUTION_RPT_CURR`
- SQL Basis:
  `C2M.GLDL Summary.sql`
  `_AdHoc Reports\\GL Reports\\GLDL Distribution Codes.sql`
- Users:
  finance analysts
- Purpose:
  summarize GL activity by batch, distribution code, and GL account
- Row / Group Grain:
  grouped by `BATCH_NBR`, `DST_ID`, `DST_DESC`, optionally `GL_ACCT`
- Core Fields:
  `BATCH_NBR`
  `BATCH_CD`
  `DST_ID`
  `DST_DESC`
  `GL_ACCT`
  `FT_TYPE_FLG_DESC`
  `GL_DISTRIB_STATUS_DESC`
- Measures:
  `SUM(GL_AMOUNT)`
  row count
  distinct FT count
- Filters:
  batch number
  batch code
  FT type
  GL status
- Why Ad Hoc:
  finance users need exploratory slicing
- Next Deliverable:
  build saved Ad Hoc view off the GL snapshot Domain

### 6. GL Batch Business Review

- Artifact Type:
  `JRXML`
- Source Snapshot:
  `FT_GL_DISTRIBUTION_RPT_CURR`
- SQL Basis:
  `C2M.GLDL Detail Query.sql`
  `_AdHoc Reports\\GL Reports\\GLDL Detail Query.sql`
- Users:
  finance operations, controllers
- Purpose:
  review one GL batch with business groupings and exceptions
- Row / Group Grain:
  detailed GL lines within one selected batch
- Core Fields:
  batch metadata
  accounting date
  GL status
  distribution
  debit
  credit
  net amount
  account
  customer
  FT identifiers
- Measures:
  total debits
  total credits
  net amount
  row counts by severity
- Filters:
  batch number
  batch code
  GL status
  GL account
  exceptions only
- Why JRXML:
  standardized finance review packet
- Next Deliverable:
  continue refining the working JRXML package already built
- Current Snapshot Note:
  debit and credit should be derived from the sign of `GL_AMOUNT` at report time; the snapshot stores `GL_AMOUNT` and `STATISTIC_AMOUNT`, not separate native debit and credit columns.

### 7. GL Exception Monitor

- Artifact Type:
  `JRXML`
- Source Snapshot:
  `FT_GL_DISTRIBUTION_RPT_CURR`
- SQL Basis:
  same GLDL detail family, focused on exceptions
- Users:
  finance controls, reconciliation users
- Purpose:
  isolate rows with missing GL account, zero amount, or unusual GL distribution status
- Row / Group Grain:
  detailed GL lines, default exceptions only
- Core Fields:
  accounting date
  GL status
  GL account
  distribution
  amount
  account/customer
  FT identifiers
- Measures:
  error count
  warning count
- Filters:
  batch number
  status
  amount threshold
- Why JRXML:
  best as a fixed control-review report
- Next Deliverable:
  derive from the current GL batch report package as a tighter exceptions-only sibling
- Current Snapshot Note:
  do not use `IS_LATEST_BATCH_NBR` in this report because it is intentionally not populated in the current release.

## Phase 2: Finish Snapshots, Then Build

These items are intentionally future-state. Field-level designs for them must be validated against the final governed snapshot contracts once `ACCT_DEBT_RPT_CURR` and `COLL_PROC_RPT_CURR` are completed.

### 8. Arrears Band Dashboard

- Artifact Type:
  `Ad Hoc` or Dashboard
- Required Snapshot:
  `ACCT_DEBT_RPT_CURR`
- SQL Basis:
  `C2M.Account.00to20Arrears.sql`
  `C2M.Account.21to30Arrears.sql`
  `C2M.Account.31to60Arrears.sql`
  `C2M.Account.Over60Arrears.sql`
  `C2M.Account.TotalArrears.sql`
- Users:
  collections and finance leadership
- Purpose:
  consolidated view of arrears bands by account/customer attributes
- Row / Group Grain:
  grouped by aging bucket, customer class, bill cycle, optional debt class
- Measures:
  account count
  total arrears
  over-60 total
- Why after snapshot:
  the root SQL variants should be consolidated into one governed debt model first
- Next Deliverable:
  finish `ACCT_DEBT_RPT_CURR` QA and guide, then build the Domain and Ad Hoc

### 9. Overpayment Exceptions

- Artifact Type:
  `Ad Hoc`
- Required Snapshot:
  `ACCT_DEBT_RPT_CURR`
- SQL Basis:
  `C2M.Account.OverPayments.sql`
- Users:
  customer ops, finance ops
- Purpose:
  identify accounts with credit/overpayment conditions
- Row / Group Grain:
  one row per account
- Core Fields:
  account
  customer
  setup date
  autopay flag
  credit/current/payoff values
- Measures:
  count of accounts
  overpayment amount
- Next Deliverable:
  model overpayment fields inside the debt snapshot or a companion account-risk layer

### 10. Debt Aging Master Summary

- Artifact Type:
  `JRXML`
- Required Snapshot:
  `ACCT_DEBT_RPT_CURR`
- SQL Basis:
  `Master Report.sql`
  `Master Report - Debt Classes.sql`
  `C@M Current & Payoff Totals by SA.sql`
  `C@M Current & Payoff Totals by Debt Class.sql`
- Users:
  collections leadership, finance leadership
- Purpose:
  primary aging and debt portfolio report
- Row / Group Grain:
  summary by account and debt class with aging bands
- Measures:
  total current amount
  total payoff
  bucket totals
  account counts
- Why JRXML:
  leadership packet, recurring and standardized
- Next Deliverable:
  design the governed aging grain in Oracle first

### 11. Bill/Adjustment Aging Drilldown

- Artifact Type:
  `Ad Hoc`
- Required Snapshot:
  likely `ACCT_DEBT_RPT_CURR` plus detailed FT aging logic
- SQL Basis:
  `Age of All Bills & Adjustments.sql`
  `Age of all Bills & Adjustment FTs w ARREAR BALANCE.sql`
  variants with SA and debt class
- Users:
  collections analysts
- Purpose:
  inspect bill and adjustment FTs that make up aged balances
- Row / Group Grain:
  bill/adjustment FT detail
- Measures:
  current amount
  payoff amount
  running arrear balance
- Why after snapshot:
  the running-balance logic needs to be stabilized in governed Oracle SQL
- Next Deliverable:
  decide whether this belongs inside the debt snapshot package or a separate detailed aging snapshot

### 12. Collections Portfolio Summary

- Artifact Type:
  `JRXML`
- Required Snapshot:
  `COLL_PROC_RPT_CURR`
- SQL Basis:
  debt/aging family plus collections process reporting need
- Users:
  collections supervisors and management
- Purpose:
  summarize collections workload and progression
- Row / Group Grain:
  summary by collections status / process stage / age
- Measures:
  account count
  amount at risk
  counts by stage
- Next Deliverable:
  finish `COLL_PROC_RPT_CURR` package before report design

## Phase 3: Targeted Business/Niche Reporting

### 13. Account 360

- Artifact Type:
  `Ad Hoc`
- Source Candidate:
  future governed account-centered model
- SQL Basis:
  `C2M.Account.Main.sql`
  `C2M.Person.Main.sql`
  `C2M.AllFTsbyPerson.sql`
  `C2M.Account.Alert.sql`
  `C2M.Account.Characteristic.sql`
- Users:
  customer care, collections, analytics
- Purpose:
  customer/account inquiry with financial and service context
- Why later:
  high value, but requires careful grain control and a reusable account semantic layer
- Next Deliverable:
  define whether to build a new account snapshot or a curated Domain from existing governed assets

### 14. Landlord Portfolio Summary

- Artifact Type:
  `Ad Hoc` first
- Source Candidate:
  likely new landlord/property governed model
- SQL Basis:
  `C2M.Landlord.sql`
  `C2M.Premise.Landlord.sql`
  `S_KeyCity Properties Accounts & Balance.sql`
- Users:
  utility business users dealing with landlord/property portfolios
- Purpose:
  summarize balances and locations for landlord/property-owner entities
- Why later:
  strong niche value, but not as universal as payments/GL/debt
- Next Deliverable:
  validate repeated client demand before building governed model

### 15. Budget Billing Change Audit

- Artifact Type:
  `Ad Hoc`
- Source Candidate:
  likely direct governed model later if demand persists
- SQL Basis:
  `C2M.BudgetBilling.EffDate1YearorMore.sql`
  `C2M_BudBillChanges.sql`
- Users:
  billing operations
- Purpose:
  review long-running budget billing setups and changes
- Why later:
  targeted value, but narrower audience
- Next Deliverable:
  start with ad hoc unless repeated operational use justifies a governed layer

### 16. Outside Agency Contact Export

- Artifact Type:
  `Ad Hoc` export only
- Source Candidate:
  direct controlled Domain or utility dataset
- SQL Basis:
  `C2M.OutsideAgency.ContactLookup.sql`
- Users:
  collections / external agency workflows
- Purpose:
  export contact and identity information for approved agency use cases
- Why Ad Hoc only:
  sensitive and export-oriented rather than dashboard/report oriented
- Next Deliverable:
  keep controlled and permission-aware

## Leave As Ad Hoc Utilities

Do not prioritize governed report builds yet for:

- `S_123 Conversion Street_Accounts.sql`
- `S_ACCT_to_PREMISE_mapping_testing.sql`
- `S_CMMA_Map_Draft.sql`
- `S_CustomerCount_ITS-11177.sql`
- `S_Bad_Manufacturer_and_Model_Conversion.sql`
- `S_NonMetered_FinalBill_Severance_ITS-10149_SQL.sql`
- `S_NonMetered_FinalBill_Severance_ITS-10149_ORACLE.sql`
- ticket-specific and conversion-specific working files

Reason:
- one-off
- migration-focused
- issue-driven
- not broad standing analytics products

## Recommended Build Order

1. Tender Control Balancing
2. Deposit Control Reconciliation
3. Payment Tender Detail
4. GL Distribution Code Summary
5. GL Batch Business Review refinements
6. GL Exception Monitor
7. Decide whether a new payment-application snapshot is needed
8. Finish `ACCT_DEBT_RPT_CURR`
9. Finish `COLL_PROC_RPT_CURR`
10. Arrears Band Dashboard
11. Overpayment Exceptions
12. Debt Aging Master Summary
13. Bill/Adjustment Aging Drilldown
14. Collections Portfolio Summary
15. Account 360
16. Landlord Portfolio Summary
17. Budget Billing Change Audit

## Missing But Potentially Valuable Data

These are the most important gaps exposed by this review. They are not defects in the current snapshots, but they do limit which reports can be built cleanly today.

### Payments / Cashiering

- Missing for true payment-application reporting:
  `PAY_ID`, `PAY_SEG_ID`, `SA_ID`, and a stable payment-application grain
- Missing for stronger deposit-control balancing:
  a populated `DEP_CTL_START_BALANCE`
- Optional future additions worth considering:
  `DISTINCT_SA_COUNT` per payment event or per tender
  `SOLE_SA_ID` only when exactly one service agreement exists for the payment event

### Finance / GL

- Missing for latest-batch-style report logic:
  a populated `IS_LATEST_BATCH_NBR`
- Not currently needed, but potentially useful later:
  explicit derived debit and credit snapshot columns if finance wants consistent reuse across many reports instead of deriving them in each JRXML

### Debt / Collections

- The major gap is not individual fields; it is that `ACCT_DEBT_RPT_CURR` and `COLL_PROC_RPT_CURR` are still unfinished.
- Once those are complete, revisit all debt and collections build plans against the actual final snapshot contracts before implementing reports.
