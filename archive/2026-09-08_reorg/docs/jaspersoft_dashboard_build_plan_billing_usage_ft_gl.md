# Jaspersoft Dashboard Build Plan: Billing, Usage, FT, and GL

## Purpose

This document is the starter dashboard plan for Jaspersoft using the governed snapshot tables already completed in this repo.

It is focused on four high-value subject areas:
- billing totals
- usage
- financial transactions
- general ledger

The goal is to build dashboards that are:
- useful to business users
- simple enough to maintain
- grounded in current governed snapshots
- capable of supporting both executive review and operational drilldown

## Build Principles

- Use dashboards for summary, trend, and exception navigation.
- Use Ad Hoc views or reports underneath each dashboard panel so users can drill from summary into detail.
- Keep each dashboard to one primary subject.
- Favor 5 to 7 tiles or panels, not a crowded wall of visuals.
- Lead with KPIs, then trends, then distribution charts, then exception/detail tables.
- Default to recent periods like last 30, 60, or 90 days unless the subject is batch-specific.

## Primary Source Selection Rules

When multiple governed snapshots exist in the same subject area, do not mix them casually on the main dashboard canvas.

Use these rules:

- billing totals dashboard:
  use `BSEG_BILLED_USAGE_RPT_CURR` for all top-line totals, billed amount KPIs, billed usage KPIs, bill-segment counts, and executive trends
- billing determinant drill:
  use `BSEG_SQ_USAGE_RPT_CURR` only when the question is determinant detail such as `UOM`, `TOU`, `SQI`, or billed-consumption composition
- usage dashboard:
  use `D1_USAGE_RPT_CURR` for all dashboard KPIs and trends because it is the governed usage-header layer
- usage scalar drill:
  use `D1_USAGE_SCALAR_DTL_RPT_CURR` only for line-level scalar quantity drilldown and troubleshooting
- measurement monitoring:
  use `D1_MSRMT_RPT_CURR` only for upstream measurement health, not as the main usage totals source
- FT dashboard:
  use `FT_RPT_CURR` for transaction-level KPIs, counts, and amount trends
- GL dashboard:
  use `FT_GL_DISTRIBUTION_RPT_CURR` for ledger-line metrics, debit, credit, distribution, and batch review

Simple rule:

- if the dashboard is about the business event itself, use the higher-grain summary snapshot
- if the dashboard is about the composition under that event, use the lower-grain drill snapshot
- do not use the lower-grain drill snapshot for executive totals unless that lower grain is the actual business question

## 1. Billing Totals Dashboard

### Purpose

Give billing and revenue users a governed summary of billed usage, billed amount, determinant volume, and bill-segment activity.

### Why It Is Useful For Utilities

Billing totals are where operational usage becomes customer-facing revenue. Utilities need a fast view of billed volume, billed amount, bill cycle behavior, and service mix so they can monitor revenue and spot anomalies before they become large customer-impact issues.

### Source Snapshots

- summary layer:
  `BSEG_BILLED_USAGE_RPT_CURR`
- determinant drill layer:
  `BSEG_SQ_USAGE_RPT_CURR`

### Use This Vs Not That

Use `BSEG_BILLED_USAGE_RPT_CURR` for:
- total billed amount
- total billed usage at bill-segment reporting level
- bill segment counts
- billed revenue trends
- executive billing totals

Use `BSEG_SQ_USAGE_RPT_CURR` for:
- `UOM` / `TOU` / `SQI` determinant analysis
- billed-consumption composition
- determinant-level troubleshooting
- drill tables under billed totals

Do not use `BSEG_SQ_USAGE_RPT_CURR` as the main source for top-line billed totals unless the business question is explicitly determinant-grain. It is lower grain and can have multiple rows per bill segment.

### Recommended Dashboard Layout

#### Top KPI strip

- Total Billed Amount
  Source: `SUM(TOTAL_CALC_AMT)`
- Total Billed Usage
  Source: `SUM(TOTAL_BILL_SQ)`
- Bill Segment Count
  Source: `COUNT(BSEG_ID)`
- Distinct Account Count
  Source: `COUNT_DISTINCT(ACCT_ID)`
- Distinct Service Agreement Count
  Source: `COUNT_DISTINCT(SA_ID)`

#### Main visual row

- Trend chart:
  billed amount by `BILL_DT` month
- Companion trend chart:
  billed usage by `BILL_DT` month
- Distribution chart:
  billed amount by `SA_TYPE_DESC` or `UTILITY_TYPE_CD`

#### Secondary visual row

- bar chart:
  billed amount by `BSEG_BILL_CYC_DESC`
- bar chart:
  billed amount by `CUST_CL_DESC`
- table:
  top 20 accounts or service agreements by billed amount

#### Drill panel

- determinant drill table from `BSEG_SQ_USAGE_RPT_CURR`
  grouped by `UOM_CD`, `TOU_CD`, `SQI_CD`

### Recommended Filters

- bill date range
- bill cycle
- service type
- customer class
- utility type
- account id
- service agreement id

### Best Supporting Detail Reports

- `Billed Usage Summary`
- `Billed Determinant Analysis`

### First Build Order

1. KPI strip from `BSEG_BILLED_USAGE_RPT_CURR`
2. billed amount trend by month
3. billed amount by service type
4. billed amount by bill cycle
5. top-account detail table
6. add determinant drill using `BSEG_SQ_USAGE_RPT_CURR`

## 2. Usage Dashboard

### Purpose

Give meter operations and billing support a governed view of usage population health, usage timing, and usage business context.

### Why It Is Useful For Utilities

Usage defects usually show up before billing defects do. A governed usage dashboard helps users see whether usage populations, usage timing, and usage context are stable, which reduces the chance of silent billing failures or late-cycle operational surprises.

### Source Snapshots

- header layer:
  `D1_USAGE_RPT_CURR`
- scalar drill layer:
  `D1_USAGE_SCALAR_DTL_RPT_CURR`
- optional upstream population check:
  `D1_MSRMT_RPT_CURR`

### Use This Vs Not That

Use `D1_USAGE_RPT_CURR` for:
- usage count KPIs
- usage trends
- operational usage status monitoring
- account / SA / bill-cycle usage summaries
- the main usage dashboard tiles

Use `D1_USAGE_SCALAR_DTL_RPT_CURR` for:
- scalar-line detail
- quantity and final-quantity troubleshooting
- one-usage-to-many-scalar drilldown

Use `D1_MSRMT_RPT_CURR` for:
- upstream measurement population health
- measuring-component and install-event stability checks
- validating whether measurement supply looks healthy before usage issues surface

Do not use `D1_USAGE_SCALAR_DTL_RPT_CURR` as the main usage totals source. It is a lower-grain drill layer. Do not use `D1_MSRMT_RPT_CURR` as a substitute for governed usage totals; it is upstream measurement truth, not usage-header truth.

### Recommended Dashboard Layout

#### Top KPI strip

- Usage Count
  Source: `COUNT(D1_USAGE_ID)`
- Distinct Account Count
  Source: `COUNT_DISTINCT(ACCT_ID)`
- Distinct Service Agreement Count
  Source: `COUNT_DISTINCT(SA_ID)`
- Most Recent Usage Date
  Source: `MAX(start/end/create/status date field used in snapshot context)`
- Bridge Match Count or Bridge Success indicator
  Source: bridge trace fields such as `BRIDGE_METHOD` / `C1_MATCH_COUNT` where useful

#### Main visual row

- trend chart:
  usage count by month
- trend chart:
  usage count by status over time
- distribution chart:
  usage count by service type or customer class

#### Secondary visual row

- bar chart:
  usage count by bill cycle
- bar chart:
  usage count by premise or division grouping if exposed
- exception table:
  recent usage records with suspicious bridge/context combinations

#### Drill panel

- scalar detail table from `D1_USAGE_SCALAR_DTL_RPT_CURR`
  show `QUANTITY` and `FINAL_QUANTITY` by usage id and scalar line

### Recommended Filters

- usage date range
- account id
- service agreement id
- bill cycle
- customer class
- service type
- usage status

### Best Supporting Detail Reports

- `Usage Operations Summary`
- `Usage Scalar Detail Exceptions`
- `Measurement Quality Monitor`

### First Build Order

1. usage count KPI strip
2. monthly usage count trend
3. usage status distribution
4. usage by service type / bill cycle
5. scalar-detail drill table

## 3. Financial Transaction Dashboard

### Purpose

Give finance operations and support users a governed FT-header view of transaction volume, amount, status, and business context without the noise of GL-line detail.

### Why It Is Useful For Utilities

Utilities generate large numbers of financial transactions from billing, adjustments, and payments. Users need to monitor transaction populations and statuses at FT-header grain so they can understand operational finance movement before dropping into GL detail.

### Source Snapshot

- `FT_RPT_CURR`

### Use This Vs Not That

Use `FT_RPT_CURR` for:
- FT counts
- FT amount trends
- FT status distributions
- FT type mix
- transaction-level finance operations monitoring

Do not use `FT_GL_DISTRIBUTION_RPT_CURR` for the main FT dashboard KPIs. That snapshot is GL-line grain and will multiply header-level FT questions into ledger-line activity.

### Recommended Dashboard Layout

#### Top KPI strip

- FT Count
  Source: `COUNT(FT_ID)`
- Total Current Amount
  Source: `SUM(CUR_AMT)`
- Total Payoff Amount
  Source: `SUM(TOT_AMT)`
- Distinct Account Count
  Source: `COUNT_DISTINCT(ACCT_ID)`
- Distinct Service Agreement Count
  Source: `COUNT_DISTINCT(SA_ID)`

#### Main visual row

- trend chart:
  FT count by `ACCOUNTING_DT` month
- trend chart:
  `SUM(CUR_AMT)` by `ACCOUNTING_DT` month
- distribution chart:
  FT count by `FT_TYPE_FLG_DESC`

#### Secondary visual row

- bar chart:
  FT count by `GL_DISTRIB_STATUS_DESC`
- bar chart:
  FT amount by `SA_TYPE_DESC`
- table:
  recent high-amount or operationally notable transactions

#### Drill panel

- detail table:
  `FT_ID`, `ACCOUNTING_DT`, `FT_TYPE_FLG_DESC`, `CUR_AMT`, `TOT_AMT`, `GL_DISTRIB_STATUS_DESC`, `ACCT_ID`, `SA_ID`, `CUSTOMER_NAME`

### Recommended Filters

- accounting date range
- FT type
- GL distribution status
- service type
- customer class
- account id
- service agreement id

### Best Supporting Detail Reports

- `Financial Transaction Operations Report`
- GL dashboard drillthrough to `FT_GL_DISTRIBUTION_RPT_CURR`

### First Build Order

1. FT KPI strip
2. FT count and amount trend by month
3. FT type distribution
4. GL distribution status distribution
5. recent high-amount FT table

## 4. GL Dashboard

### Purpose

Give finance analysts and controllers a governed dashboard for batch-aware GL activity, debit/credit movement, distribution-code behavior, and exception review.

### Why It Is Useful For Utilities

Utilities need to trace operational billing, payment, and adjustment activity into finance. A governed GL dashboard helps users monitor how transactions distribute into the ledger, which accounts are active, and where batch-level review or reconciliation attention is needed.

### Source Snapshot

- `FT_GL_DISTRIBUTION_RPT_CURR`

### Use This Vs Not That

Use `FT_GL_DISTRIBUTION_RPT_CURR` for:
- debit and credit totals
- GL account activity
- distribution-code activity
- batch analysis
- GL exception monitoring

Do not use `FT_RPT_CURR` for ledger-line KPIs like debit, credit, distribution code, or GL account movement. `FT_RPT_CURR` is FT-header grain, not GL-line grain.

### Recommended Dashboard Layout

#### Top KPI strip

- GL Line Count
  Source: `COUNT(*)`
- Total Net GL Amount
  Source: `SUM(GL_AMOUNT)`
- Total Debits
  Source: `SUM(DEBIT_AMT)`
- Total Credits
  Source: `SUM(CREDIT_AMT)`
- Distinct FT Count
  Source: `COUNT_DISTINCT(FT_ID)`

#### Main visual row

- trend chart:
  debit and credit by `ACCOUNTING_DT` month
- distribution chart:
  GL line count by `FT_TYPE_FLG_DESC`
- bar chart:
  net amount by `GL_ACCT`

#### Secondary visual row

- bar chart:
  net amount by `DST_DESC`
- bar chart:
  GL line count by `GL_DISTRIB_STATUS_DESC`
- table:
  top 20 GL accounts by debit or credit

#### Exception / batch panel

- detail table:
  batch, FT type, GL account, distribution, amount, debit, credit, status, customer
- optional second table:
  exception-only rows based on zero amounts, unusual statuses, or missing context

### Recommended Filters

- accounting date range
- batch number
- batch code
- FT type
- GL account
- distribution code
- GL distribution status
- account id

### Best Supporting Detail Reports

- `GL Distribution Code Summary`
- `GL Batch Business Review`
- `GL Exception Monitor`

### First Build Order

1. GL KPI strip
2. debit and credit trend by month
3. GL account ranking chart
4. distribution code summary chart
5. batch-aware detail table

## Dashboard Navigation Strategy

Use the dashboards as the front door and pair them with reports underneath:

- Billing dashboard:
  drill to billed usage summary and determinant analysis
- Usage dashboard:
  drill to usage detail and scalar detail
- FT dashboard:
  drill to FT detail and then GL detail when needed
- GL dashboard:
  drill to batch detail report and exception report

This keeps the dashboards clean while still giving power users a path to deeper analysis.

## Recommended Start Sequence

Build in this order:

1. GL dashboard
  reason:
  the business is already working actively in GL batch review
2. Billing totals dashboard
  reason:
  high business value and strong executive usefulness
3. Usage dashboard
  reason:
  good operational value and supports billing integrity
4. FT dashboard
  reason:
  useful but best as a finance operations companion after GL

## Effective Visual Rules For These Dashboards

- Use blue as the primary theme, but keep the background light and clean.
- Avoid more than two chart colors per panel unless comparing a small number of categories.
- Use title-case labels, not all caps.
- Put currency KPIs in accounting format with parentheses for negatives.
- Keep filters visible but compact at the top or left.
- Limit “top N” charts to 10 or 15 rows.
- Use exception tables instead of giant detail tables on the dashboard canvas.
- Push full detail into linked Ad Hoc views or reports.

## What Not To Do

- Do not mix FT-header and GL-line metrics in the same main dashboard tile.
- Do not use determinant-grain quantity as if it were bill-segment billed amount.
- Do not overload the usage dashboard with raw scalar-detail rows on the first screen.
- Do not rely on raw-code-only fields as the main user-facing dimensions when a readable description already exists.

## Fast Source Decision Guide

Use this when choosing the dataset for a dashboard tile:

- `BSEG_BILLED_USAGE_RPT_CURR`
  use for billed totals, billed amount, billed usage, segment-level revenue views
- `BSEG_SQ_USAGE_RPT_CURR`
  use for determinant composition, `UOM` / `TOU` / `SQI`, billed-consumption drilldown
- `D1_USAGE_RPT_CURR`
  use for usage totals, usage timing, usage status, usage operational summaries
- `D1_USAGE_SCALAR_DTL_RPT_CURR`
  use for scalar detail only
- `D1_MSRMT_RPT_CURR`
  use for upstream measurement health and measurement operations monitoring
- `FT_RPT_CURR`
  use for FT-header operations and finance transaction monitoring
- `FT_GL_DISTRIBUTION_RPT_CURR`
  use for GL-line, debit/credit, distribution, and batch-oriented finance analysis

## Best Starter Deliverables

If you want the highest-value first version, build these four dashboards:

- `Billing Totals Dashboard`
- `Usage Operations Dashboard`
- `Financial Transaction Dashboard`
- `GL Activity Dashboard`

That gives you one strong dashboard per major utility reporting subject using governed data you already trust.
