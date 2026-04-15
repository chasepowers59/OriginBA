# Oracle SQL Query Library Workstream Catalog

## Purpose

Catalog the SQL library under:
- `C:\Users\cvpow\OneDrive\Desktop\Oracle SQL Developer Queries\Oracle SQL Developer Queries`
- `C:\Users\cvpow\OneDrive\Desktop\Oracle SQL Developer Queries\Oracle SQL Developer Queries\_AdHoc Reports`

This document maps the query library into OriginBA workstreams, identifies what each query is for, and recommends which items should become governed reports or stay as ad hoc operational utilities.

## What Was Reviewed

- `60` SQL files total
- `27` SQL files in the root library
- `18` SQL files in `_AdHoc Reports`
- `12` SQL files in `_AdHoc Reports\Aging Report`
- `3` SQL files in `_AdHoc Reports\GL Reports`

## Recommended Workstream Buckets

Use these buckets for backlog, governed snapshot planning, and report design:

1. `Payments & Cashiering`
2. `Finance & General Ledger`
3. `Debt Management & Aging`
4. `Customer, Account & Service 360`
5. `Property, Landlord & External Agency`
6. `Budget Billing`
7. `Conversion, Migration & Data Quality`
8. `Reference Datasets & Utility Models`

## Executive Read

Highest-value governed reporting opportunities from this library:

1. `Debt aging master package`
   Notes:
   The Aging Report folder is the richest undeveloped reporting set in the library. It should become a governed debt-aging package with account, SA, and debt-class views.

2. `Payments operational suite`
   Notes:
   The payments queries already point to a strong report family:
   payment event detail, payment tender detail, tender control balancing, deposit control balancing, autopay monitoring, and bankruptcy payment review.

3. `Finance GL batch and distribution suite`
   Notes:
   The GLDL queries align well to the snapshot work already underway and justify both batch-level and distribution-code-level finance reporting.

4. `Customer/account risk and exception monitoring`
   Notes:
   The arrears, overpayment, alerts, and non-metered queries support a practical account-risk workstream.

5. `Landlord/property portfolio reporting`
   Notes:
   The landlord and KeyCity-style property balance queries are strong portfolio-level business reports.

## Existing Snapshot Alignment

Queries that already align closely to governed snapshot work in this repo:

- `C2M.Payments.sql`
- `C2M.Payments.PaymentDetails.sql`
- `C2M.Payments.PaymentEvent.sql`
- `C2M.Payments.PaymentTenders.sql`
- `C2M.Payments.TenderControl.sql`
- `C2M.Payments.DepositControl.sql`
  Notes:
  These align to `PAY_TNDR_CASH_RPT_CURR`.

- `C2M.GLDL Summary.sql`
- `C2M.GLDL Detail Query.sql`
- `_AdHoc Reports\GL Reports\GLDL Detail Query.sql`
- `_AdHoc Reports\GL Reports\GLDL Distinct Query.sql`
- `_AdHoc Reports\GL Reports\GLDL Distribution Codes.sql`
  Notes:
  These align to `FT_GL_DISTRIBUTION_RPT_CURR`.

- Root and Ad Hoc arrears/aging queries
  Notes:
  These align conceptually to `ACCT_DEBT_RPT_CURR` and future debt-aging governed reporting.

## Bucket 1: Payments & Cashiering

### Core payment models

- `C2M.Payments.sql`
  Use case:
  broad payment event reporting model with both application-side and tender-side context.
  Best report:
  governed payment 360 detail dataset or semantic model.
  Recommendation:
  use as a source concept, not as a final report query.

- `C2M.Payments.PaymentDetails.sql`
  Use case:
  detailed payment allocation reporting by account and SA.
  Best report:
  payment application detail report.
  Recommendation:
  governed report candidate.

- `C2M.Payments.PaymentEvent.sql`
  Use case:
  payment event header-level reporting.
  Best report:
  payment event operational summary.
  Recommendation:
  governed report candidate if business users need event grain.

- `C2M.Payments.PaymentTenders.sql`
  Use case:
  tender-side detail including tender control and deposit control.
  Best report:
  payment tender detail report.
  Recommendation:
  already largely covered by `PAY_TNDR_CASH_RPT_CURR`.

- `C2M.Payments.TenderControl.sql`
  Use case:
  tender control balancing.
  Best report:
  tender control summary and cashier balancing report.
  Recommendation:
  strong governed report candidate.

- `C2M.Payments.DepositControl.sql`
  Use case:
  deposit control end-balance review.
  Best report:
  deposit control summary / reconciliation report.
  Recommendation:
  already in active report design work.

- `C2M.Payments.DepositLabels.sql`
  Use case:
  reference mapping of tender source and tender type to deposit method logic.
  Best report:
  reference lookup table or documentation artifact, not a user-facing report by itself.
  Recommendation:
  fold into documentation or enrichment logic.

### Payment exceptions and operations

- `S_Auto Pay Accounts w Active Deposit.sql`
  Use case:
  autopay accounts with active deposit service agreements.
  Best report:
  autopay + deposit exception report.
  Recommendation:
  useful operational ad hoc and candidate for exception dashboard.

- `S_Autopay_Drafts_by_Date.sql`
  Use case:
  autopay draft activity by date and account context.
  Best report:
  autopay draft calendar / volume report.
  Recommendation:
  governed candidate if autopay operations are high-volume.

- `S_C2M_TwoPayments_Same_Amount_2days_apart.sql`
  Use case:
  suspicious duplicate-payment pattern detection.
  Best report:
  duplicate payment exception report.
  Recommendation:
  keep as targeted operational exception report.

- `S_BKRPTCY_payments.sql`
  Use case:
  payment review for accounts with bankruptcy alerts.
  Best report:
  bankruptcy payment monitoring report.
  Recommendation:
  ad hoc exception report with compliance value.

### Recommended report family for this bucket

- Payment Event Summary
- Payment Application Detail
- Payment Tender Detail
- Tender Control Balancing
- Deposit Control Reconciliation
- Autopay Draft Monitoring
- Duplicate Payment Exceptions
- Bankruptcy Payment Review

## Bucket 2: Finance & General Ledger

### GL detail and summary

- `C2M.GLDL Summary.sql`
  Use case:
  summarized GL distribution by batch, destination, GL account, SA type, and service type.
  Best report:
  GL batch summary and finance reconciliation report.
  Recommendation:
  governed report candidate.

- `C2M.GLDL Detail Query.sql`
  Use case:
  detailed FT-to-GL distribution reporting.
  Best report:
  GL batch detail investigation report.
  Recommendation:
  governed report candidate and already aligned to current GL batch report work.

- `_AdHoc Reports\GL Reports\GLDL Detail Query.sql`
  Use case:
  ad hoc variant of GL detail.
  Recommendation:
  merge conceptually into governed GL detail package.

- `_AdHoc Reports\GL Reports\GLDL Distinct Query.sql`
  Use case:
  distinct SA / service / GL combinations for GLDL analysis.
  Best report:
  GL coverage / mapping audit report.
  Recommendation:
  useful secondary finance QA report.

- `_AdHoc Reports\GL Reports\GLDL Distribution Codes.sql`
  Use case:
  distribution code and batch-level GL amounts.
  Best report:
  distribution code finance summary.
  Recommendation:
  strong governed report candidate.

### Refunds

- `C2M.SystemGeneratedRefundssql.sql`
  Use case:
  system-generated refund review using FT parent/sibling structure.
  Best report:
  refund audit report.
  Recommendation:
  valuable finance exception report.

### Recommended report family for this bucket

- GL Batch Business Review
- GL Batch Executive Summary
- Distribution Code Summary
- Refund Audit
- GL Mapping / Coverage QA

## Bucket 3: Debt Management & Aging

This is the densest report backlog area in the library.

### Root arrears slices

- `C2M.Account.00to20Arrears.sql`
- `C2M.Account.21to30Arrears.sql`
- `C2M.Account.31to60Arrears.sql`
- `C2M.Account.Over60Arrears.sql`
- `C2M.Account.TotalArrears.sql`
  Use case:
  account arrears segmentation and aging bands.
  Best report:
  account aging dashboard or arrears band monitor.
  Recommendation:
  these should not remain separate reports long term; fold them into one governed aging model.

- `C2M.Account.OverPayments.sql`
  Use case:
  accounts with credit/overpayment conditions.
  Best report:
  overpayment exception report.
  Recommendation:
  useful adjunct to aging and collections reporting.

### Aging Report folder

- `Master Report.sql`
- `Master Report - Debt Classes.sql`
  Use case:
  master aging report by account with debt-class-aware variant.
  Best report:
  primary governed debt aging package.
  Recommendation:
  highest-priority future governed report set in this library.

- `Aging Report.sql`
- `Aging Report (teryn).sql`
  Use case:
  broad aging extracts via linked-server/openquery patterns.
  Recommendation:
  source concepts only; govern in Oracle directly instead of linked-server patterns.

- `Age of All Bills & Adjustments.sql`
- `Age of all Bills & Adjustment FTs w ARREAR BALANCE.sql`
- `Age of all Bills & Adjustment FTs w ARREAR BALANCE and SA Table.sql`
- `Age of all Bills & Adjustment FTs w ARREAR BALANCE and SA Debt Class.sql`
  Use case:
  bill and adjustment FT aging with running arrear-balance logic.
  Best report:
  bill/adjustment aging drilldown and debt-class aging drilldown.
  Recommendation:
  strong governed drilldown candidate once the running balance logic is stabilized in Oracle.

- `C@M Current & Payoff Totals by SA.sql`
- `C@M Current & Payoff Totals by Debt Class.sql`
  Use case:
  current and payoff totals by SA and debt class.
  Best report:
  debt portfolio summary.
  Recommendation:
  governed KPI summary candidate.

- `quick ref.sql`
- `Working file.sql`
  Use case:
  development scaffolding for aging logic.
  Recommendation:
  not direct report candidates; use for design notes only.

### Recommended report family for this bucket

- Debt Aging Master Summary
- Debt Aging by Debt Class
- Bill/Adjustment Aging Drilldown
- Arrears Band Dashboard
- Overpayment Exceptions
- Collections Portfolio Summary

## Bucket 4: Customer, Account & Service 360

### Account and customer core

- `C2M.Account.Main.sql`
  Use case:
  broad account 360 base dataset.
  Best report:
  account overview semantic model.
  Recommendation:
  foundational dataset candidate.

- `C2M.Person.Main.sql`
  Use case:
  person-centered account/customer view.
  Best report:
  customer 360 detail report.
  Recommendation:
  governed candidate if customer service users need person-first inquiry.

- `C2M.AllFTsbyPerson.sql`
  Use case:
  all financial transactions by person/account relationship.
  Best report:
  customer financial activity history.
  Recommendation:
  valuable inquiry report, but watch row volume.

- `C2M.SvcPoint.Main.sql`
  Use case:
  service point master view.
  Best report:
  service point inventory / operations report.
  Recommendation:
  governed candidate.

### Account enrichment

- `C2M.Account.Alert.sql`
  Use case:
  account alert reporting.
  Best report:
  account alert monitoring report.
  Recommendation:
  strong supplement to account 360.

- `C2M.Account.Characteristic.sql`
  Use case:
  account characteristics and effective-dated values.
  Best report:
  account attribute export or detail drilldown.
  Recommendation:
  useful enrichment layer rather than standalone headline report.

### Dataset-style utilities

- `z_C2M Accounts Dataset.sql`
- `z_C2M Balance Dataset.sql`
- `z_C2M SA Dataset.sql`
- `z_C2M SP Dataset.sql`
  Use case:
  reusable dataset-building queries for accounts, balances, service agreements, and service points.
  Best report:
  semantic staging inputs, not direct polished reports.
  Recommendation:
  mine for governed snapshot design; do not expose raw as-is.

### Recommended report family for this bucket

- Account 360
- Customer Financial Activity
- Service Point Master Listing
- Account Alerts Monitor
- Account Attributes Export

## Bucket 5: Property, Landlord & External Agency

- `C2M.Landlord.sql`
- `C2M.Premise.Landlord.sql`
  Use case:
  landlord-to-premise and landlord-to-account mapping.
  Best report:
  landlord portfolio report.
  Recommendation:
  governed candidate for municipal rental/property use cases.

- `S_KeyCity Properties Accounts & Balance.sql`
  Use case:
  portfolio balance reporting for property-owner-style customers.
  Best report:
  landlord/property account balance summary.
  Recommendation:
  high-value business report candidate.

- `C2M.OutsideAgency.ContactLookup.sql`
  Use case:
  identity/contact lookup for external agency workflows.
  Best report:
  agency referral / collections contact export.
  Recommendation:
  sensitive operational utility; strong ad hoc export candidate.

### Recommended report family for this bucket

- Landlord Portfolio Summary
- Property Account Balance Rollup
- Outside Agency Contact Export

## Bucket 6: Budget Billing

- `C2M.BudgetBilling.EffDate1YearorMore.sql`
  Use case:
  budget billing accounts with long-standing effective dates.
  Best report:
  budget billing review / stale enrollment report.
  Recommendation:
  exception report candidate.

- `C2M_BudBillChanges.sql`
  Use case:
  budget billing change history investigation.
  Best report:
  budget billing change audit.
  Recommendation:
  good operational drilldown report.

### Recommended report family for this bucket

- Budget Billing Enrollment Review
- Budget Billing Change Audit

## Bucket 7: Conversion, Migration & Data Quality

- `S_Bad_Manufacturer_and_Model_Conversion.sql`
  Use case:
  conversion mismatch between legacy and C2M manufacturer/model attributes.
  Best report:
  conversion QA exception report.
  Recommendation:
  keep as migration/data-quality utility.

- `S_ACCT_to_PREMISE_mapping_testing.sql`
  Use case:
  account-to-premise mapping validation.
  Best report:
  conversion QA mapping report.
  Recommendation:
  keep as project/implementation utility.

- `S_123 Conversion Street_Accounts.sql`
  Use case:
  account/person/address mapping for a specific conversion street or pattern.
  Recommendation:
  one-off ad hoc utility.

- `S_CMMA_Map_Draft.sql`
  Use case:
  customer/account/premise mapping extract.
  Recommendation:
  implementation utility, possibly GIS or third-party mapping support.

- `S_CustomerCount_ITS-11177.sql`
  Use case:
  customer count / service agreement status analysis tied to issue tracking.
  Recommendation:
  issue-resolution ad hoc query.

### Recommended report family for this bucket

- Conversion QA Exception Pack
- Account-to-Premise Mapping Audit
- Meter Attribute Conversion QA

## Bucket 8: Specialized Operations & Exceptions

- `S_NonMetered_Accounts.sql`
  Use case:
  non-metered account identification.
  Best report:
  non-metered account inventory.
  Recommendation:
  operational niche report.

- `S_NonMetered_FinalBill_Severance_ITS-10149_ORACLE.sql`
- `S_NonMetered_FinalBill_Severance_ITS-10149_SQL.sql`
  Use case:
  final bill / severance exception analysis for non-metered accounts.
  Best report:
  non-metered severance exception monitor.
  Recommendation:
  high-value operational exception report if this process is business-critical.

- `S_Adj_to_FTUSER.sql`
  Use case:
  adjustment creation/freeze user audit.
  Best report:
  adjustment user activity audit.
  Recommendation:
  useful finance or controls audit utility.

## What Should Become Governed First

Priority 1:
- Aging / debt master reporting package
- GL distribution / batch reporting package
- payments operational suite

Priority 2:
- account 360 and customer financial activity
- landlord/property portfolio reporting
- budget billing audit reports

Priority 3:
- conversion QA and issue-specific utilities
- one-off operational investigations

## What Should Stay Ad Hoc

Keep these as ad hoc or issue-driven utilities unless repeated demand appears:

- street-specific conversion queries
- ITS-ticket-specific scripts
- draft/working aging calculations
- migration QA one-offs
- one-off property name searches

## Similarity Notes

Queries that are clearly variants of the same business need and should be consolidated:

- root arrears band queries
  Notes:
  replace with one governed aging model with configurable buckets.

- GLDL root and `_AdHoc Reports\GL Reports` queries
  Notes:
  consolidate into one governed GL semantic layer and report family.

- payments root queries
  Notes:
  keep one governed payment snapshot/domain and multiple report layouts, not many separate source queries.

- Aging Report folder variants
  Notes:
  they represent design exploration around one core aging problem, not separate long-term products.

## Recommended Next Steps

1. Treat this library as a backlog source, not as direct production SQL.
2. Fold recurring business needs into governed Oracle snapshots first.
3. Build report families, not one-off reports:
   - one data model
   - several consumption layouts
4. Prioritize debt aging, payments, and GL because the library density and business value are highest there.
5. Archive issue-specific and conversion-specific queries separately from governed reporting assets.

## Prioritization Matrix

Scoring scale:
- `Business Value`
  - `High`, `Medium`, `Low`
- `Effort`
  - `Low`, `Medium`, `High`
- `Data Readiness`
  - `High` means the query intent is clear and source patterns are already established
- `Snapshot Readiness`
  - `Ready` means a governed snapshot already exists or the source model is effectively in place
  - `Partial` means the logic is clear but the governed layer is incomplete
  - `Low` means substantial Oracle design work is still needed

| Workstream Product | Business Value | Effort | Data Readiness | Snapshot Readiness | Recommended Next Action |
|---|---|---|---|---|---|
| Payments operational suite | High | Low-Medium | High | Ready | expand governed report family off `PAY_TNDR_CASH_RPT_CURR` |
| GL batch and distribution suite | High | Low-Medium | High | Ready | continue report packaging and finance layouts off `FT_GL_DISTRIBUTION_RPT_CURR` |
| Debt aging master package | High | High | Medium | Partial | design governed aging snapshot/model before building final reports |
| Account risk and arrears exceptions | High | Medium | High | Partial | build focused exception reports first while aging master is being designed |
| Account / customer 360 | High | Medium-High | Medium-High | Partial | define safe grain and create reusable account-centered governed layer |
| Budget billing audit reports | Medium | Low | High | Low-Partial | build as targeted operational reports after top three workstreams |
| Landlord / property reporting | Medium | Low-Medium | Medium-High | Low-Partial | package as portfolio-style niche report set for clients that need it |
| Outside agency contact export | Medium | Low | Medium | Low | keep as controlled export utility unless repeated business demand emerges |
| Conversion QA exception pack | Medium-Low | Low-Medium | High | Low | keep ad hoc unless active implementation work justifies governed QA assets |
| Ticket-specific one-off operational SQL | Low | Low | High | Low | leave ad hoc and archive by issue/use case |

## Recommended Delivery Queue

1. Payments operational suite
   Reason:
   highest ratio of business value to effort, and the governed snapshot already exists.

2. GL batch and distribution suite
   Reason:
   finance value is high and the governed snapshot already exists.

3. Account risk and arrears exceptions
   Reason:
   strong business need, faster to deliver than the full debt-aging master package.

4. Debt aging master package
   Reason:
   highest strategic value, but should be done as a designed governed model rather than stitched together from ad hoc SQL variants.

5. Account / customer 360
   Reason:
   broad cross-functional value, but requires careful modeling to avoid grain and fan-out issues.

6. Budget billing audit reports
   Reason:
   targeted operational value with relatively contained logic.

7. Landlord / property reporting
   Reason:
   strong niche value for certain clients and municipalities.

8. Conversion QA and one-off utilities
   Reason:
   useful, but not the best standing product investment unless active implementation work is ongoing.
