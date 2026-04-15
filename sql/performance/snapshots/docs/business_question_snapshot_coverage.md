# Business Question Snapshot Coverage

## Purpose
This document maps the current business-question list to the governed snapshot family in the repository.

It uses three statuses:
- `Yes`: answerable now with the current governed snapshots
- `Partial`: partly answerable now, but only with caveats, a non-snapshot manual domain, or a snapshot that is close but not exact
- `No`: not answerable now with the current governed snapshot family

This is intentionally conservative. If a question needs a different grain, missing dimension, or missing process-history layer, it is not marked `Yes`.

## Current governed snapshot family
- `BSEG_BILLED_USAGE_RPT_CURR`
- `BSEG_SQ_USAGE_RPT_CURR`
- `FT_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`
- `ACCT_DEBT_RPT_CURR`
- `COLL_PROC_RPT_CURR`
- `D1_USAGE_RPT_CURR`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`
- `D1_MSRMT_RPT_CURR`
- `PAY_TNDR_CASH_RPT_CURR`

## Customer Ops and Case Management

| Business question | Status | Current artifact | Workstream / next step |
| --- | --- | --- | --- |
| Open cases across customer classes and case types | No | No governed case snapshot | `customer_ops`: build `CASE_RPT_CURR` at one row per case |
| Number of open cases and status by business user | No | No governed case snapshot | `customer_ops`: `CASE_RPT_CURR` with owner/user overlays |
| Persons / addresses that have had the greatest number of cases opened against them | No | No governed case snapshot | `customer_ops` plus premise/address overlay |
| Trend and case condition of created cases over the past 12 months | No | No governed case snapshot | `customer_ops`: case header snapshot with create date and current/final condition |
| Trend and case condition of created cases over the past 31 days | No | No governed case snapshot | `customer_ops`: same case header snapshot |
| For a specific case type, how long were cases in the previous state for? | No | No governed state-history snapshot | `customer_ops`: add `CASE_STATE_HIST_RPT` child snapshot |
| For a specific case type, what is the distribution across the final states the cases ended up in? | No | No governed case/state snapshot | `customer_ops`: case header plus final-state history |
| For a specific case type, what was the average case completion duration? | No | No governed case lifecycle snapshot | `customer_ops`: case header with start/end timestamps |
| How are customer contacts distributed across Customer Contact Classes and Customer Contact Types? | No | No governed customer-contact snapshot | `customer_ops`: build `CUSTOMER_CONTACT_RPT_CURR` |
| Daily trend for customer contacts | No | No governed customer-contact snapshot | `customer_ops`: `CUSTOMER_CONTACT_RPT_CURR` with create date |

## Meter Ops Consumption and Exception Analytics

| Business question | Status | Current artifact | Workstream / next step |
| --- | --- | --- | --- |
| Total consumption by region and customer type | Partial | `D1_USAGE_SCALAR_DTL_RPT_CURR` supports customer class and premise context, but not a governed region layer | `meter_ops` plus `common`: add geography / territory enrichment snapshot or domain |
| Total consumption for residential customers | Partial | `D1_USAGE_SCALAR_DTL_RPT_CURR` can support customer-class consumption; definition of "residential" must be validated | `meter_ops`: likely answerable once customer-class mapping is approved |
| How does usage break down by commodity and rate classification? | Partial | Usage snapshots support service type and customer class, but not a clean governed rate-classification layer | `meter_ops` plus `billing`: add rate / commodity classification artifact |
| Number of billing determinant exceptions per customer types | No | No governed determinant-exception snapshot | `meter_ops`: build usage / billing determinant exception snapshot |
| Usage exceptions that are holding up billing | Partial | `D1_USAGE_RPT_CURR` exposes usage process status, but not full exception detail | `meter_ops`: build `D1_USAGE_EXCP_RPT_CURR` |
| VEE rules generating the most exceptions | No | No governed VEE exception snapshot | `meter_ops`: build `D1_VEE_EXCP_RPT_CURR` |
| Service points / accounts have the most VEE errors | No | No governed VEE exception snapshot | `meter_ops`: `D1_VEE_EXCP_RPT_CURR` with SP/account overlays |

## Meter Inventory, Routes, and New Services

| Business question | Status | Current artifact | Workstream / next step |
| --- | --- | --- | --- |
| Number of non-meter assets at service points that were installed or removed within the last seven days | No | No governed install-event / asset snapshot | `meter_ops` or `common`: build service-point asset event snapshot |
| Number of meter devices installed during a period to support new meter rollouts | No | No governed device install snapshot | `meter_ops`: build device install-event snapshot |
| Number of disconnected devices, and where are they located | No | No governed current-state device snapshot | `meter_ops`: build current device-state snapshot with SP and geography |
| Number of connected or disconnected service points are, and where are they located | No | No governed service-point state snapshot | `common` or `meter_ops`: build service-point current-state snapshot |
| Number of meters are in each cycle / route | No | Current snapshots have route/cycle context but not reliable current meter inventory grain | `meter_ops`: build meter inventory snapshot at one row per current device or SP-device assignment |
| Meters that havent been read recently | Partial | `D1_MSRMT_RPT_CURR` gives measurement history, but not a current inventory-with-last-read snapshot | `meter_ops`: build meter-read-recency snapshot |
| Number of estimates that are created by route | Partial | `D1_USAGE_RPT_CURR` supports estimate and route analysis, but the exact "estimate created" definition needs a governed flag | `meter_ops`: likely a usage-estimate topic or route KPI report on top of `D1_USAGE_RPT_CURR` |
| Number of new services, by service type, that were created | No | No governed new-service snapshot | `new_services`: build service-start / SA creation snapshot |
| Service territories that are experiencing the most growth | No | No governed territory growth snapshot | `new_services` plus `common`: add geography / territory growth artifact |

## Field Operations and Work Orders

| Business question | Status | Current artifact | Workstream / next step |
| --- | --- | --- | --- |
| How many work orders, by type and area are created? | No | No governed field-work snapshot | `field_ops`: build work order / activity header snapshot |
| Overdue work orders | No | No governed field-work snapshot | `field_ops`: same work order snapshot with SLA / due-date metrics |
| Field worker performance metrics | No | No governed field-work snapshot | `field_ops`: work order snapshot plus assignee / crew performance overlays |

## Billing

| Business question | Status | Current artifact | Workstream / next step |
| --- | --- | --- | --- |
| Number of pending and completed bills within a period of time | No | `BSEG_BILLED_USAGE_RPT_CURR` is completed-bill-segment only | `billing`: build bill header / bill status snapshot |
| Trends in bill completions and bill amounts over a period of time | Partial | Completed billed amounts can come from `BSEG_BILLED_USAGE_RPT_CURR`, but completion workflow including pending bills is not fully covered | `billing`: add bill header/status snapshot |
| Number of pending bills without exceptions | No | No governed pending-bill snapshot | `billing`: bill header / exception snapshot |
| What are the billed amounts and billed quantities by Customer Class? | Yes | `BSEG_BILLED_USAGE_RPT_CURR` | `billing` |
| Month by month comparison of billed amounts and billed quantities over a period of time | Yes | `BSEG_BILLED_USAGE_RPT_CURR` | `billing` |
| Highest billed amounts and billed quantities by Rate | Partial | No governed rate-grain snapshot, but active manual domain `Billed_Usage_Consumption_Billed_Amount_Perf_6M.xml` covers rate questions | `billing`: build governed billed-usage-by-rate snapshot or topic |

## Payments and Cashiering

| Business question | Status | Current artifact | Workstream / next step |
| --- | --- | --- | --- |
| What is the extent of payments not yet finalized and therefore have not yet impacted a customers account balance? | No | Tender snapshot is not a payment-finalization snapshot | `payments_cashiering` plus `finance`: build payment header / payment status snapshot |
| Age distribution for payments that have not yet been finalized based on payment date | No | No governed payment-finalization snapshot | `payments_cashiering`: payment header snapshot |
| Trend and payment status of created payments over the past 12 months | Partial | `PAY_TNDR_CASH_RPT_CURR` has event-level pay overlays, but it is tender-grain, not payment-grain | `payments_cashiering`: build `PAY_RPT_CURR` |
| Trend and payment status of created payments over the past 31 days | Partial | Same limitation as above | `payments_cashiering`: `PAY_RPT_CURR` |
| What is the trend and tender status of created payment tenders over the past 12 months | Yes | `PAY_TNDR_CASH_RPT_CURR` | `payments_cashiering` |
| What is the trend and tender status of created payment tenders over the past 31 days | Yes | `PAY_TNDR_CASH_RPT_CURR` | `payments_cashiering` |
| Distribution of payments across how payments were made over the last 12 months | Partial | Tender method distribution is supported, but exact payment-grain distribution is not | `payments_cashiering`: payment header snapshot or governed tender-to-pay topic |
| Accounts having the greatest number of payment cancellations due to non-sufficient funds | No | No governed NSF / payment-cancel snapshot | `payments_cashiering`: payment status / cancellation-reason snapshot |
| Unbalanced tender controls | Yes | `PAY_TNDR_CASH_RPT_CURR` | `payments_cashiering` |
| Ending Balances for balanced tender controls | Yes | `PAY_TNDR_CASH_RPT_CURR` | `payments_cashiering` |
| Unbalanced deposit controls | Yes | `PAY_TNDR_CASH_RPT_CURR` | `payments_cashiering` |
| Ending Balances for balanced deposit controls | Yes | `PAY_TNDR_CASH_RPT_CURR` | `payments_cashiering` |

## Finance, Revenue, and GL

| Business question | Status | Current artifact | Workstream / next step |
| --- | --- | --- | --- |
| Billed revenue by Customer Class | Partial | No governed billed-revenue snapshot, but active manual revenue domains exist | `finance` plus `billing`: build billed-revenue snapshot |
| Billed revenue by Rate | Partial | No governed billed-revenue-by-rate snapshot, but active manual rate-component domains exist | `finance` plus `billing`: billed-revenue-by-rate snapshot |
| Yearly and monthly trend in billed revenue | Partial | Possible in current manual revenue domains, not in governed snapshot family | `finance`: billed-revenue trend snapshot |
| Billed revenue and tax amount | Partial | Active manual tax/revenue domains exist, but no governed snapshot | `finance`: billed-revenue-tax snapshot |
| General ledger accounts summary over a period of time | Yes | `FT_GL_DISTRIBUTION_RPT_CURR` | `finance` |
| Unbilled revenue? | Partial | No governed snapshot in `sql/performance/snapshots/`, but active manual domain `Unbilled_Revenue_Snapshot_Perf.xml` exists | `finance` or `billing`: promote governed unbilled revenue snapshot workspace |

## Debt Management

| Business question | Status | Current artifact | Workstream / next step |
| --- | --- | --- | --- |
| Number of accounts and the overall overdue debt under collectible and collection processing | Yes | `ACCT_DEBT_RPT_CURR` plus `COLL_PROC_RPT_CURR` | `debt_mgmt` |
| Trends in the creation of collectible processes | Yes | `COLL_PROC_RPT_CURR` | `debt_mgmt` |
| Most and least commonly used Collection Process Templates | Yes | `COLL_PROC_RPT_CURR` | `debt_mgmt` |
| Effectiveness of collectible processes in reducing a customers overdue debt | Partial | Active manual domain `Collections_Process_Effectiveness_Debt_Reduction_180D.xml` exists; current governed snapshots do not calculate debt-reduction effectiveness | `debt_mgmt`: promote a governed collections-effectiveness snapshot or topic |
| Customers that have the highest levels of debt under collectible processing | Yes | `ACCT_DEBT_RPT_CURR` plus `COLL_PROC_RPT_CURR` | `debt_mgmt` |
| Trends in the creation of severance processes | No | No governed severance snapshot | `debt_mgmt`: build severance-process snapshot |
| Most/Least popular Severance Process Templates | No | No governed severance snapshot | `debt_mgmt`: severance-process snapshot |
| Trend in service disconnections and reconnections | No | No governed severance / service-state snapshot | `debt_mgmt` plus `field_ops` / `meter_ops` |
| Effectiveness of severance processes in reducing a customers overdue debt | No | No governed severance-effectiveness snapshot | `debt_mgmt`: severance-effectiveness snapshot |
| Customers having the highest levels of debt under severance processing | No | No governed severance snapshot | `debt_mgmt`: severance-process snapshot with debt overlays |
| How many active write-off processes exist, and what amount of outstanding debt initiated these processes? | Partial | Active manual domain `Write_Off_Requirements_Final_DB_Validated.xml` exists; no governed write-off snapshot yet | `debt_mgmt`: build write-off snapshot |
| Trend in the effectiveness of write-off processes collecting outstanding debt over time | Partial | Active manual write-off domain exists; no governed write-off snapshot yet | `debt_mgmt`: write-off snapshot |
| Number of write-off processes are being created over time | Partial | Active manual write-off domain exists; no governed write-off snapshot yet | `debt_mgmt`: write-off snapshot |
| Trend in the amount of outstanding debt initiating write-off processes over time | Partial | Active manual write-off domain exists; no governed write-off snapshot yet | `debt_mgmt`: write-off snapshot |
| Has the amount of outstanding debt to be written off been increasing or decreasing over time? | Partial | Active manual write-off domain exists; no governed write-off snapshot yet | `debt_mgmt`: write-off snapshot |
| Has the time it takes to complete or cancel a write-off process been increasing or decreasing over time? | Partial | Active manual write-off domain exists; no governed write-off snapshot yet | `debt_mgmt`: write-off snapshot |
| Distribution of outstanding debt by age | Yes | `ACCT_DEBT_RPT_CURR` | `debt_mgmt` |
| Trend over the past 15 months of outstanding debt by age | Yes | `ACCT_DEBT_RPT_CURR` | `debt_mgmt` |
| Top 100 customers with the highest amount of outstanding debt older than 30 days | Yes | `ACCT_DEBT_RPT_CURR` | `debt_mgmt` |

## Deposits and To Do Workload

| Business question | Status | Current artifact | Workstream / next step |
| --- | --- | --- | --- |
| Compare deposits on hand to arrears | No | Tender/deposit-control snapshot is not customer-deposit-on-hand truth | `finance` plus `debt_mgmt` or `customer_ops`: build deposit-on-hand vs arrears artifact |
| Number of incomplete To Do Entries that are currently not being worked on / being worked on by users | Partial | Active manual domain `To_Do_Entry_Operations_Account_Resolved.xml` exists; no governed snapshot yet | `field_tasks`: build To Do entry snapshot |
| Trend of created To Do Entries over the past 24 months | Partial | Active manual To Do domain exists; no governed snapshot yet | `field_tasks`: To Do entry snapshot |
| Accounts / premises having the highest number of incomplete To Do Entries | Partial | Active manual To Do domain exists; no governed snapshot yet | `field_tasks`: To Do entry snapshot |
| Users with the highest number of incomplete To Do Entries | Partial | Active manual To Do domain exists; no governed snapshot yet | `field_tasks`: To Do entry snapshot |
| Average unassigned duration trend for open To Do Entries belonging to a specific To Do Type | Partial | Active manual To Do domain exists; no governed snapshot yet | `field_tasks`: To Do entry snapshot with queue-duration metrics |
| Average assigned duration trend for To Do Entries being worked on belonging to a specific To Do Type | Partial | Active manual To Do domain exists; no governed snapshot yet | `field_tasks`: To Do entry snapshot with assigned-duration metrics |

## Summary

### Strongly covered now with governed snapshots
- billing segment billed quantities and billed amounts by customer class and month
- FT header and GL-account finance reporting
- tender trends and tender/deposit-control monitoring
- account debt exposure and collection-process volume/template analysis
- debt aging and top-debtor questions

### Partly covered now
- usage consumption analysis where customer class or service type is enough, but geography / rate detail is missing
- payment questions that need exact payment-grain finalization rather than tender-grain overlays
- billed revenue, tax, unbilled revenue, write-off, and To Do analytics where current manual domains exist but governed snapshot promotion is still pending

### Not covered now by governed snapshots
- customer cases
- customer contacts
- meter and service-point current-state inventory
- VEE / usage exception analytics
- field work orders
- severance analytics
- new-services growth analytics
