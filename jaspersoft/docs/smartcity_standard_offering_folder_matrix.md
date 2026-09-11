# SmartCity Standard Offering Report List

Current official standard offering: `104` reports.

Source type key:
- `Snapshot` = governed Oracle snapshot-backed report
- `Live Domain` = governed live semantic-layer report

| Workstream | Source Type | Report Name | Description | What It Is Used For |
|---|---|---|---|---|
| Finance | Snapshot | General Ledger - Accounts Receivable | Current accounts receivable balances. | Receivables monitoring and balance review. |
| Finance | Snapshot | General Ledger - Adjustments Review | Write-off and adjustment reconciliation details. | Adjustment review and finance reconciliation. |
| Finance | Snapshot | General Ledger - GL Account and Distribution | GL accounts with associated distribution codes. | GL coding validation and distribution review. |
| Finance | Snapshot | General Ledger - Revenue Totals | Revenue totals by distribution code. | Revenue monitoring and distribution analysis. |
| Finance | Snapshot | General Ledger - Write Off Amounts | Write-off totals by distribution code. | Write-off monitoring and finance review. |
| Finance | Snapshot | General Ledger - By Batch Number | GL distributions sorted by batch number. | Batch review and posting reconciliation. |
| Finance | Snapshot | Financial Transaction - Bill Cycle Transactions | Transaction counts by type for each bill cycle. | Bill cycle activity monitoring. |
| Finance | Snapshot | Financial Transaction - Billed Revenue Trend | Billed revenue by month. | Monthly revenue trend analysis. |
| Finance | Snapshot | Financial Transaction - GL Distribution Status | GL distribution statuses for financial transactions. | Posting status and finance control review. |
| Finance | Snapshot | Financial Transaction - Revenue by Customer Class | Billed revenue by customer class. | Segment-based revenue analysis. |
| Finance | Snapshot | Financial Transaction - Total Transactions by Type | Transaction counts and amounts by type. | Financial transaction volume and amount monitoring. |
| Finance | Snapshot | Financial Transactions - Service Type FT Summary | Current FT amounts by service agreement type. | Service-type financial mix analysis. |
| Finance | Snapshot | Financial Transaction - Payment Account Detail | Payment-related financial transaction detail by account. | Detailed payment transaction review. |
| Billing and Rates | Snapshot | Billed Usage and Amount Charged | Billed usage and amount at segment level. | Billing summary review and billed usage analysis. |
| Billing and Rates | Snapshot | Billed Amount - by Customer Class | Total billed amount by customer class. | Billed amount segmentation by customer class. |
| Billing and Rates | Snapshot | Billed Amount - Amount Billed by Budget Plan | Billed amounts by budget plan. | Budget-plan billing analysis. |
| Billing and Rates | Snapshot | Billed Amount - By Utility Type | Total billed amount by utility type. | Utility-level billed amount comparison. |
| Billing and Rates | Snapshot | Billed Amount - Canceled Segments | Recently canceled bill segments and reasons. | Cancellation exception review. |
| Billing and Rates | Snapshot | Billed Amount - Estimated Segment | Billed amounts from estimated consumption. | Estimated billing review. |
| Billing and Rates | Snapshot | Billed Amount - Rebills | Recent rebills and billed amounts. | Rebill monitoring and billing exception review. |
| Billing and Rates | Snapshot | Billed Amount - Revenue by Rate Schedule | Billed revenue by rate schedule. | Rate-based revenue analysis. |
| Billing and Rates | Snapshot | Billed Usage - Account Level View | Billed usage at account and bill segment level. | Bill segment inquiry and account-level usage review. |
| Billing and Rates | Snapshot | Billed Usage - Across Customer Class & UOM | Billed usage by customer class and unit of measure. | Billed usage segmentation analysis. |
| Billing and Rates | Snapshot | Billed Usage - By SA Type & Class | Billed usage by service agreement type and class. | Service portfolio usage analysis. |
| Billing and Rates | Snapshot | Billed Usage - Segment Determinant | Determinant-level billed usage values such as UOM, SQI, and TOU. | Determinant review and bill-segment detail analysis. |
| Billing and Rates | Snapshot | Billed Usage - Tiered Billed Usage | Billed usage across tiers. | Tiered usage distribution review. |
| Meter Operations | Snapshot | Measurement - IMD Summary | Interval measurement detail and statuses. | IMD review and upstream measurement monitoring. |
| Meter Operations | Snapshot | Measurement - Measurement Conditions | Distribution of measurement conditions over time. | Measurement-condition trend monitoring. |
| Meter Operations | Snapshot | Measurement - Reads and Totals by Cycle | Read counts and totals by cycle. | Cycle-level measurement operations review. |
| Meter Operations | Snapshot | Measurement - SP Type | Measurement detail by service point type. | Service-point-type measurement analysis. |
| Meter Operations | Snapshot | Measurements - Estimated | Measurements flagged as estimated. | Estimated read exception review. |
| Meter Operations | Snapshot | Measurements - by Service Point ID | Measurement detail for specific service points. | Service-point measurement inquiry. |
| Meter Operations | Snapshot | Meter Reads - Counts by Component Type | Read counts and totals by measuring component type. | Read-volume monitoring by component. |
| Meter Operations | Snapshot | Usage - Account View | Usage start, end, and consumption by account. | Account-level usage inquiry. |
| Meter Operations | Snapshot | Usage - Customer Class and UOM | Usage by customer class and final unit of measure. | Usage segmentation by class and UOM. |
| Meter Operations | Snapshot | Usage - Highest Usage Customers | Highest-usage customers by UOM. | High-usage customer monitoring. |
| Meter Operations | Snapshot | Usage - Premise Consumption | Usage at the premise level. | Premise-level consumption research. |
| Meter Operations | Snapshot | Usage - by Measuring Component ID | Usage by measuring component ID. | Component-level usage analysis. |
| Meter Operations | Snapshot | Usage Transaction - By SA Type | Usage transactions by service agreement type. | Usage transaction mix analysis. |
| Meter Operations | Snapshot | Usage Transaction - by Subscription Type | Usage transactions by subscription type. | Usage transaction segmentation. |
| Meter Operations | Live Domain | Device - Daily Installations | Daily device installation activity. | Installation activity monitoring. |
| Meter Operations | Live Domain | Device - Disconnected Devices / Service Points | Disconnected devices and related service points. | Disconnect review and service-point exception analysis. |
| Meter Operations | Live Domain | Device - Meters Not Recently Read | Meters that have not been read recently. | Stale-read monitoring and meter operations follow-up. |
| Meter Operations | Live Domain | Asset - In Storage | Counts of assets by specification in storage. | Inventory totals and ordering review. |
| Meter Operations | Live Domain | Asset - Distribution of Installed Assets | Counts assets across asset type. | Asset inventory in the field. |
| Cashiering | Live Domain | Deposit Control - Ending Balances | Ending balances for deposit controls. | Deposit reconciliation and control balancing. |
| Cashiering | Live Domain | Deposit Control - Unbalanced Deposit Controls | Deposit controls that are out of balance. | Deposit exception follow-up. |
| Cashiering | Live Domain | Tender Control - Unbalanced | Tender controls out of balance. | Tender exception review. |
| Cashiering | Live Domain | Tender Control - Ending Balances | Ending balances for tender controls. | Tender reconciliation. |
| Cashiering | Live Domain | Pay Plan - Health Status | Payment plan health and status. | Payment plan monitoring and customer payment operations. |
| Cashiering | Live Domain | Pay Plan - Recently Canceled Pay Plans | Recently canceled payment plans. | Canceled payment plan monitoring and follow-up. |
| Cashiering | Live Domain | Pay Plan - Active Pay Plans | Active payment plans. | Active pay plan workload monitoring. |
| Cashiering | Live Domain | Pay Plan - Cancel Reason Distribution Trend | Pay plan cancellations by reason over time. | Cancellation trend and reason analysis. |
| Cashiering | Live Domain | Tender - Payment Tender Distribution by Status | Payment tenders distributed by status. | Tender status monitoring and payment control review. |
| Cashiering | Live Domain | Tender - Tender Type Distribution | Payment distribution by tender type. | Payment channel and tender mix analysis. |
| Cashiering | Live Domain | Payment - Cancel Reasons | Payment cancellations by reason. | Payment cancellation review. |
| Cashiering | Live Domain | Payment - Creation Trends | Payment creation trends over time. | Payment volume trend monitoring. |
| Cashiering | Live Domain | Payment - Lost Revenue Overview | Payment-related lost revenue detail. | Lost-revenue review in cashiering. |
| Cashiering | Live Domain | Payment - Unfrozen Payments | Payments that remain unfrozen. | Payment processing exception review. |
| Common | Live Domain | Batch Process - Incomplete Batch Runs | Incomplete batch runs. | Batch exception follow-up. |
| Common | Live Domain | Batch Process - Recent Batches | Batch runs over the last 24 hours. | Batch review. |
| Common | Live Domain | Bill Segment Exception - Open Bill Segments | Open bill segment exceptions. | Billing exception monitoring. |
| Common | Live Domain | To Do - Incomplete Entries | Incomplete to-do entries. | To-do backlog review. |
| Common | Live Domain | To Do - Unassigned Duration Trend | Average time to assign each to-do type. | Review assignment timing and backlog handling. |
| Common | Live Domain | Usage Transaction Exceptions - Incomplete | Usage transaction exceptions that impact billing. | Billing-impact exception review. |
| Common | Live Domain | VEE Exception - Exception Severity Distribution | VEE exceptions by severity distribution. | Severity-based exception prioritization. |
| Common | Live Domain | VEE Exception - Rules Generating the Most Exceptions | Rules producing the most VEE exceptions. | Rule tuning and exception reduction analysis. |
| Customer Operations | Live Domain | Account Alert - Collections Risk | Account alerts with active bankruptcy-related risk. | Alert handling and customer service follow-up. |
| Customer Operations | Live Domain | Customer Contact - Contact Breakdown | Customer contacts by type or category. | Contact mix analysis and workload segmentation. |
| Customer Operations | Live Domain | Customer Contact - Distribution of Letters Printed | Distribution of printed customer letters. | Correspondence volume monitoring. |
| Customer Operations | Live Domain | Customer Contact - Monthly Created Contacts | Customer contacts created by month. | Monthly contact trend analysis. |
| Customer Operations | Live Domain | Case - Open Cases by Account | Open cases by account. | Account-based case workload review. |
| Customer Operations | Live Domain | Case - Open Cases by Customer Class | Open cases by customer class. | Class-based case segmentation. |
| Customer Operations | Live Domain | Case - Time in Previous State | Time cases spent in their previous state. | Case aging and bottleneck review. |
| Customer Operations | Live Domain | Case - Closed Case Outcomes | Outcomes for closed cases. | Case outcome analysis and service quality review. |
| Customer Operations | Live Domain | Case - Average Case Duration | Average case duration. | Case throughput monitoring. |
| Customer Operations | Live Domain | Case - Cases Created by Month | Case creation volume by month. | Case trend and workload planning. |
| Customer Operations | Live Domain | Customer - Critical Care & Safety Report | Customers associated with critical care or safety conditions. | High-priority customer population review. |
| Customer Operations | Live Domain | Premise - Canceled SA by Type | Canceled service agreements by type at the premise level. | Premise-level canceled-service review. |
| Customer Operations | Live Domain | Premise - Not Linked to Service Agreements | Premises not linked to service agreements. | Premise linkage exception review. |
| Customer Operations | Live Domain | C-Side - Accounts on Life Support | Accounts flagged for life support. | Protected-customer population review. |
| New Services | Live Domain | New Services - Number of New Premises | Counts of new premises. | Growth and planning analysis. |
| New Services | Live Domain | New Services - New Service Counts | Counts of new service activity. | New service volume monitoring. |
| New Services | Live Domain | New Services - Premise Growth | Premise growth over time. | Growth trend analysis. |
| New Services | Live Domain | New Services - Pending Service Agreements | Pending service agreements with aging buckets. | Backlog review and pending SA follow-up. |
| Debt Management | Live Domain | Collection Process - Arrears by Customer Class | Arrears by customer class. | Debt segmentation by customer class. |
| Debt Management | Live Domain | Collection Process - Arrears by Debt Class | Arrears by debt class. | Debt portfolio analysis by debt class. |
| Debt Management | Live Domain | Write Offs - Debt Written Off Trend | Written-off debt trends over time. | Write-off trend analysis. |
| Debt Management | Live Domain | Write Offs - Average Process Duration | Time taken for write-off process completion. | Write-off process duration review. |
| Debt Management | Live Domain | Collection Process - Active Collections | Active collection processes. | Active collections workload monitoring. |
| Debt Management | Live Domain | Collection Process - Age of Unpaid Bills | Unpaid bill aging within collection process reporting. | Arrears aging review. |
| Debt Management | Live Domain | Collection Process - Upcoming Collection Events | Upcoming collection events. | Collections planning and review. |
| Debt Management | Live Domain | SA Snapshot - Aged Debt by Customer Class | Aged debt by customer class using SA snapshot reporting. | Aged debt segmentation. |
| Debt Management | Live Domain | SA Snapshot - Arrear Buckets (By Class) | Arrear buckets by class. | Arrear bucket analysis. |
| Debt Management | Live Domain | SA Snapshot - Total Amount of Aged Arrears | Total aged arrears amount. | Total arrears monitoring. |
| Debt Management | Live Domain | Severance Process - Active Processes by Class | Active severance processes. | Active severance workload monitoring. |
| Debt Management | Live Domain | Write Off Process - Active Write Off Processes | Active write-off processes. | Write-off workload monitoring. |
| Field Operations | Live Domain | Field Activity - Average Days per Field Task | Average days to complete field tasks. | Field work aging and operational KPI review. |
| Field Operations | Live Domain | Field Activity - Cancellations | Canceled field activities and reasons. | Field activity exception review. |
| Field Operations | Live Domain | Field Activity - Upcoming Field Work | Field activities scheduled for the next two weeks. | Short-term field work planning and readiness review. |
| Field Operations | Live Domain | Field Activity - Overdue Work Orders | Overdue field work orders. | Overdue work order monitoring. |
| Field Operations | Live Domain | Field Activity - Trends by Task Type | Field activity trends by activity type. | Activity-type trend analysis. |
| Field Operations | Live Domain | Crew - Incomplete Work Orders | Incomplete work in the field. | Work order aging and incomplete work follow-up. |
| Field Operations | Live Domain | Crew - Completed and Discarded | Completed and discarded field work. | Work order volume and completion control. |
