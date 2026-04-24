# OriginBA Reporting Standard Offering

## Executive Summary
The OriginBA SmartCity Standard Offering includes a library of `104` reports spanning `9` operational workstreams. These reports are designed to support day-to-day operations, exception management, financial reconciliation, customer service follow-up, and field activity analysis across municipal utility environments.

This library combines two report source types:
- `Snapshot` reports are built from scheduled Oracle snapshot tables and provide controlled, point-in-time reporting for financial, billing, and meter-operation subject areas where stable grain and governed logic matter most.
- `Live Domain` reports are drawn from the governed live semantic layer and are better suited for active monitoring, exception follow-up, and operational workflows.

## Overview
The SmartCity Standard Offering is intended to provide a reusable baseline report library for municipal utility clients. It is structured around the core business processes that most utilities need to monitor and manage, while still allowing additional client-specific extensions where required.

## Report Source Types
- `Snapshot`: scheduled, governed Oracle snapshot-backed reporting
- `Live Domain`: live semantic-layer reporting from the governed Jaspersoft Domain model

## Workstream Coverage

| # | Workstream | Total Reports | Snapshot | Live Domain |
|---|---|---:|---:|---:|
| 1 | Finance | 13 | 13 | 0 |
| 2 | Billing and Rates | 13 | 13 | 0 |
| 3 | Meter Operations | 19 | 14 | 5 |
| 4 | Cashiering | 14 | 0 | 14 |
| 5 | Common | 8 | 0 | 8 |
| 6 | Customer Operations | 14 | 0 | 14 |
| 7 | New Services | 4 | 0 | 4 |
| 8 | Debt Management | 12 | 0 | 12 |
| 9 | Field Operations | 7 | 0 | 7 |
|  | **Total** | **104** | **40** | **64** |

## Report Library by Workstream

### Finance
Governed financial reporting across general ledger activity, revenue monitoring, transaction analysis, receivables review, and distribution validation. The Finance workstream contains `13` reports, and all use snapshot tables.

| Report Name | Source | Description | Primary Use |
|---|---|---|---|
| General Ledger - Accounts Receivable | Snapshot | Current accounts receivable balances. | Receivables monitoring and balance review. |
| General Ledger - Adjustments Review | Snapshot | Write-off and adjustment reconciliation details. | Adjustment review and finance reconciliation. |
| General Ledger - GL Account and Distribution | Snapshot | GL accounts with associated distribution codes. | GL coding validation and distribution review. |
| General Ledger - Revenue Totals | Snapshot | Revenue totals by distribution code. | Revenue monitoring and distribution analysis. |
| General Ledger - Write Off Amounts | Snapshot | Write-off totals by distribution code. | Write-off monitoring and finance review. |
| General Ledger - By Batch Number | Snapshot | GL distributions sorted by batch number. | Batch review and posting reconciliation. |
| Financial Transaction - Bill Cycle Transactions | Snapshot | Transaction counts by type for each bill cycle. | Bill cycle activity monitoring. |
| Financial Transaction - Billed Revenue Trend | Snapshot | Billed revenue by month. | Monthly revenue trend analysis. |
| Financial Transaction - GL Distribution Status | Snapshot | GL distribution statuses for financial transactions. | Posting status and finance control review. |
| Financial Transaction - Revenue by Customer Class | Snapshot | Billed revenue by customer class. | Segment-based revenue analysis. |
| Financial Transaction - Total Transactions by Type | Snapshot | Transaction counts and amounts by type. | Financial transaction volume and amount monitoring. |
| Financial Transactions - Service Type FT Summary | Snapshot | Current FT amounts by service agreement type. | Service-type financial mix analysis. |
| Financial Transaction - Payment Account Detail | Snapshot | Payment-related financial transaction detail by account. | Detailed payment transaction review. |

### Billing and Rates
Billed usage and amount reporting at multiple levels of segmentation, including customer class, utility type, rate schedule, and billing exception categories. The workstream contains `13` reports, and all use snapshot tables.

| Report Name | Source | Description | Primary Use |
|---|---|---|---|
| Billed Usage and Amount Charged | Snapshot | Billed usage and amount at segment level. | Billing summary review and billed usage analysis. |
| Billed Amount - by Customer Class | Snapshot | Total billed amount by customer class. | Billed amount segmentation by customer class. |
| Billed Amount - Amount Billed by Budget Plan | Snapshot | Billed amounts by budget plan. | Budget-plan billing analysis. |
| Billed Amount - By Utility Type | Snapshot | Total billed amount by utility type. | Utility-level billed amount comparison. |
| Billed Amount - Canceled Segments | Snapshot | Recently canceled bill segments and reasons. | Cancellation exception review. |
| Billed Amount - Estimated Segment | Snapshot | Billed amounts from estimated consumption. | Estimated billing review. |
| Billed Amount - Rebills | Snapshot | Recent rebills and billed amounts. | Rebill monitoring and billing exception review. |
| Billed Amount - Revenue by Rate Schedule | Snapshot | Billed revenue by rate schedule. | Rate-based revenue analysis. |
| Billed Usage - Account Level View | Snapshot | Billed usage at account and bill segment level. | Bill segment inquiry and account-level usage review. |
| Billed Usage - Across Customer Class & UOM | Snapshot | Billed usage by customer class and unit of measure. | Billed usage segmentation analysis. |
| Billed Usage - By SA Type & Class | Snapshot | Billed usage by service agreement type and class. | Service portfolio usage analysis. |
| Billed Usage - Segment Determinant | Snapshot | Determinant-level billed usage values such as UOM, SQI, and TOU. | Determinant review and bill-segment detail analysis. |
| Billed Usage - Tiered Billed Usage | Snapshot | Billed usage across tiers. | Tiered usage distribution review. |

### Meter Operations
Measurement monitoring, read validation, usage analysis, and device and asset operational reporting across service points and measuring components. The workstream contains `19` reports: `14` snapshot-backed and `5` live-domain reports.

| Report Name | Source | Description | Primary Use |
|---|---|---|---|
| Measurement - IMD Summary | Snapshot | Interval measurement detail and statuses. | IMD review and upstream measurement monitoring. |
| Measurement - Measurement Conditions | Snapshot | Distribution of measurement conditions over time. | Measurement-condition trend monitoring. |
| Measurement - Reads and Totals by Cycle | Snapshot | Read counts and totals by cycle. | Cycle-level measurement operations review. |
| Measurement - SP Type | Snapshot | Measurement detail by service point type. | Service-point-type measurement analysis. |
| Measurements - Estimated | Snapshot | Measurements flagged as estimated. | Estimated read exception review. |
| Measurements - by Service Point ID | Snapshot | Measurement detail for specific service points. | Service-point measurement inquiry. |
| Meter Reads - Counts by Component Type | Snapshot | Read counts and totals by measuring component type. | Read-volume monitoring by component. |
| Usage - Account View | Snapshot | Usage start, end, and consumption by account. | Account-level usage inquiry. |
| Usage - Customer Class and UOM | Snapshot | Usage by customer class and final unit of measure. | Usage segmentation by class and UOM. |
| Usage - Highest Usage Customers | Snapshot | Highest-usage customers by UOM. | High-usage customer monitoring. |
| Usage - Premise Consumption | Snapshot | Usage at the premise level. | Premise-level consumption research. |
| Usage - by Measuring Component ID | Snapshot | Usage by measuring component ID. | Component-level usage analysis. |
| Usage Transaction - By SA Type | Snapshot | Usage transactions by service agreement type. | Usage transaction mix analysis. |
| Usage Transaction - by Subscription Type | Snapshot | Usage transactions by subscription type. | Usage transaction segmentation. |
| Device - Daily Installations | Live Domain | Daily device installation activity. | Installation activity monitoring. |
| Device - Disconnected Devices / Service Points | Live Domain | Disconnected devices and related service points. | Disconnect review and service-point exception analysis. |
| Device - Meters Not Recently Read | Live Domain | Meters that have not been read recently. | Stale-read monitoring and meter operations follow-up. |
| Asset - In Storage | Live Domain | Counts of assets by specification in storage. | Inventory totals and ordering review. |
| Asset - Distribution of Installed Assets | Live Domain | Counts assets across asset type. | Asset inventory in the field. |

### Cashiering
Payment activity, tender management, payment plan monitoring, and deposit and tender control reporting. The workstream contains `14` reports, and all use live Domains.

| Report Name | Source | Description | Primary Use |
|---|---|---|---|
| Deposit Control - Ending Balances | Live Domain | Ending balances for deposit controls. | Deposit reconciliation and control balancing. |
| Deposit Control - Unbalanced Deposit Controls | Live Domain | Deposit controls that are out of balance. | Deposit exception follow-up. |
| Tender Control - Unbalanced | Live Domain | Tender controls out of balance. | Tender exception review. |
| Tender Control - Ending Balances | Live Domain | Ending balances for tender controls. | Tender reconciliation. |
| Pay Plan - Health Status | Live Domain | Payment plan health and status. | Payment plan monitoring and customer payment operations. |
| Pay Plan - Recently Canceled Pay Plans | Live Domain | Recently canceled payment plans. | Canceled payment plan monitoring and follow-up. |
| Pay Plan - Active Pay Plans | Live Domain | Active payment plans. | Active pay plan workload monitoring. |
| Pay Plan - Cancel Reason Distribution Trend | Live Domain | Pay plan cancellations by reason over time. | Cancellation trend and reason analysis. |
| Tender - Payment Tender Distribution by Status | Live Domain | Payment tenders distributed by status. | Tender status monitoring and payment control review. |
| Tender - Tender Type Distribution | Live Domain | Payment distribution by tender type. | Payment channel and tender mix analysis. |
| Payment - Cancel Reasons | Live Domain | Payment cancellations by reason. | Payment cancellation review. |
| Payment - Creation Trends | Live Domain | Payment creation trends over time. | Payment volume trend monitoring. |
| Payment - Lost Revenue Overview | Live Domain | Payment-related lost revenue detail. | Lost-revenue review in cashiering. |
| Payment - Unfrozen Payments | Live Domain | Payments that remain unfrozen. | Payment processing exception review. |

### Common
Cross-functional exception monitoring for batch processing, billing, usage transactions, to-do work, and validation exceptions. The workstream contains `8` reports, all of which use live Domains.

| Report Name | Source | Description | Primary Use |
|---|---|---|---|
| Batch Process - Incomplete Batch Runs | Live Domain | Incomplete batch runs. | Batch exception follow-up. |
| Batch Process - Recent Batches | Live Domain | Batch runs over the last 24 hours. | Batch review. |
| Bill Segment Exception - Open Bill Segments | Live Domain | Open bill segment exceptions. | Billing exception monitoring. |
| To Do - Incomplete Entries | Live Domain | Incomplete to-do entries. | To-do backlog review. |
| To Do - Unassigned Duration Trend | Live Domain | Average time to assign each to-do type. | Review assignment timing and backlog handling. |
| Usage Transaction Exceptions - Incomplete | Live Domain | Usage transaction exceptions that impact billing. | Billing-impact exception review. |
| VEE Exception - Exception Severity Distribution | Live Domain | VEE exceptions by severity distribution. | Severity-based exception prioritization. |
| VEE Exception - Rules Generating the Most Exceptions | Live Domain | Rules producing the most VEE exceptions. | Rule tuning and exception reduction analysis. |

### Customer Operations
Case management, customer contact analysis, critical care identification, and premise-level service reviews. The workstream contains `14` reports, and all use live Domains.

| Report Name | Source | Description | Primary Use |
|---|---|---|---|
| Account Alert - Collections Risk | Live Domain | Account alerts with active bankruptcy-related risk. | Alert handling and customer service follow-up. |
| Customer Contact - Contact Breakdown | Live Domain | Customer contacts by type or category. | Contact mix analysis and workload segmentation. |
| Customer Contact - Distribution of Letters Printed | Live Domain | Distribution of printed customer letters. | Correspondence volume monitoring. |
| Customer Contact - Monthly Created Contacts | Live Domain | Customer contacts created by month. | Monthly contact trend analysis. |
| Case - Open Cases by Account | Live Domain | Open cases by account. | Account-based case workload review. |
| Case - Open Cases by Customer Class | Live Domain | Open cases by customer class. | Class-based case segmentation. |
| Case - Time in Previous State | Live Domain | Time cases spent in their previous state. | Case aging and bottleneck review. |
| Case - Closed Case Outcomes | Live Domain | Outcomes for closed cases. | Case outcome analysis and service quality review. |
| Case - Average Case Duration | Live Domain | Average case duration. | Case throughput monitoring. |
| Case - Cases Created by Month | Live Domain | Case creation volume by month. | Case trend and workload planning. |
| Customer - Critical Care & Safety Report | Live Domain | Customers associated with critical care or safety conditions. | High-priority customer population review. |
| Premise - Canceled SA by Type | Live Domain | Canceled service agreements by type at the premise level. | Premise-level canceled-service review. |
| Premise - Not Linked to Service Agreements | Live Domain | Premises not linked to service agreements. | Premise linkage exception review. |
| C-Side - Accounts on Life Support | Live Domain | Accounts flagged for life support. | Protected-customer population review. |

### New Services
Tracking of new premise and service activity, growth trends, and pending service agreement backlogs. The workstream contains `4` reports, all of which use live Domains.

| Report Name | Source | Description | Primary Use |
|---|---|---|---|
| New Services - Number of New Premises | Live Domain | Counts of new premises. | Growth and planning analysis. |
| New Services - New Service Counts | Live Domain | Counts of new service activity. | New service volume monitoring. |
| New Services - Premise Growth | Live Domain | Premise growth over time. | Growth trend analysis. |
| New Services - Pending Service Agreements | Live Domain | Pending service agreements with aging buckets. | Backlog review and pending SA follow-up. |

### Debt Management
Arrears monitoring, write-off tracking, collections and severance process management, and aged debt analysis. The workstream contains `12` reports, and all use live Domains.

| Report Name | Source | Description | Primary Use |
|---|---|---|---|
| Collection Process - Arrears by Customer Class | Live Domain | Arrears by customer class. | Debt segmentation by customer class. |
| Collection Process - Arrears by Debt Class | Live Domain | Arrears by debt class. | Debt portfolio analysis by debt class. |
| Write Offs - Debt Written Off Trend | Live Domain | Written-off debt trends over time. | Write-off trend analysis. |
| Write Offs - Average Process Duration | Live Domain | Time taken for write-off process completion. | Write-off process duration review. |
| Collection Process - Active Collections | Live Domain | Active collection processes. | Active collections workload monitoring. |
| Collection Process - Age of Unpaid Bills | Live Domain | Unpaid bill aging within collection process reporting. | Arrears aging review. |
| Collection Process - Upcoming Collection Events | Live Domain | Upcoming collection events. | Collections planning and review. |
| SA Snapshot - Aged Debt by Customer Class | Live Domain | Aged debt by customer class using SA snapshot reporting. | Aged debt segmentation. |
| SA Snapshot - Arrear Buckets (By Class) | Live Domain | Arrear buckets by class. | Arrear bucket analysis. |
| SA Snapshot - Total Amount of Aged Arrears | Live Domain | Total aged arrears amount. | Total arrears monitoring. |
| Severance Process - Active Processes by Class | Live Domain | Active severance processes. | Active severance workload monitoring. |
| Write Off Process - Active Write Off Processes | Live Domain | Active write-off processes. | Write-off workload monitoring. |

### Field Operations
Scheduling, performance, and exception management for field work orders and activities. The workstream contains `7` reports, and all use live Domains.

| Report Name | Source | Description | Primary Use |
|---|---|---|---|
| Field Activity - Average Days per Field Task | Live Domain | Average days to complete field tasks. | Field work aging and operational KPI review. |
| Field Activity - Cancellations | Live Domain | Canceled field activities and reasons. | Field activity exception review. |
| Field Activity - Upcoming Field Work | Live Domain | Field activities scheduled for the next two weeks. | Short-term field work planning and readiness review. |
| Field Activity - Overdue Work Orders | Live Domain | Overdue field work orders. | Overdue work order monitoring. |
| Field Activity - Trends by Task Type | Live Domain | Field activity trends by activity type. | Activity-type trend analysis. |
| Crew - Incomplete Work Orders | Live Domain | Incomplete work in the field. | Work order aging and incomplete work follow-up. |
| Crew - Completed and Discarded | Live Domain | Completed and discarded field work. | Work order volume and completion control. |

## Implementation Notes
- This report library is aligned to the current official standard offering list.
- The detailed report lists are treated as authoritative for report totals and source-type counts.
- Snapshot reports refresh on scheduled cadence; live-domain reports depend on current transactional availability and deployed semantic-layer resources.
