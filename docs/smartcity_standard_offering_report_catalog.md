# SmartCity Standard Offering Report Catalog

## Purpose

This document defines the recommended **standard reporting offering** for SmartCity across the core municipal utility workstreams.

It combines:
- the **snapshot-backed reports** already designed on governed Oracle layers
- the **existing Domain / Ad Hoc / dashboard artifacts** exported from Jaspersoft for the remaining workstreams
- utility-focused judgment about which reports are broad enough to belong in the standard offering

This is intended to answer three questions:
1. Which reports belong in the standard offering?
2. Which reports are duplicates, overly narrow, or better treated as optional?
3. Which workstream business processes still have gaps?

## Standard Workstreams

The SmartCity standard offering should stay aligned to these 9 workstreams:
- `billing`
- `cashiering`
- `meter_ops`
- `customer_ops`
- `new_services`
- `finance`
- `common`
- `debt_mgmt`
- `field_ops`

## Design Rules For The Standard Offering

1. Each workstream should have:
   - at least one summary / KPI view
   - at least one exception or control report
   - at least one operational detail / drill report
2. Snapshot-backed governed reports should be preferred where the grain, performance, or row preservation matters.
3. Existing Domain / Ad Hoc reports can remain part of the standard offering when they already fit the business process cleanly and do not require a new snapshot.
4. The standard offering should avoid duplicates that answer the same question in slightly different formatting.
5. Niche or client-specific reports can still exist, but they should not be presented as part of the base standard offering unless they serve a broadly reusable utility process.

## Recommended Standard Offering

| Workstream | Business Process | Recommended Report | Source Layer | Recommendation | Notes |
|---|---|---|---|---|---|
| `finance` | GL batch review | `General Ledger - By Batch Number` | Snapshot | Core | Strong operational finance review report |
| `finance` | GL coding and posting review | `General Ledger - GL Account and Distribution` | Snapshot | Core | Good crosswalk between account and distribution |
| `finance` | revenue monitoring | `General Ledger - Revenue Totals` | Snapshot | Core | Keep as a finance summary |
| `finance` | write-off monitoring | `General Ledger - Write Off Amounts` | Snapshot | Core | Broad utility value |
| `finance` | adjustment / reconciliation review | `General Ledger - Adjustments Review` | Snapshot | Core | Useful control report |
| `finance` | receivables balance monitoring | `General Ledger - Accounts Receivable` | Snapshot | Core | Broad finance use case |
| `finance` | FT operational volume | `Financial Transaction - Total Transactions by Type` | Snapshot | Core | Strong FT summary |
| `finance` | bill-cycle FT monitoring | `Financial Transaction - Bill Cycle Transactions` | Snapshot | Core | Good finance/billing crossover |
| `finance` | FT posting health | `Financial Transaction - GL Distribution Status` | Snapshot | Core | Good operational control |
| `finance` | revenue trend | `Financial Transaction - Billed Revenue Trend` | Snapshot | Core | Good time-series management view |
| `finance` | class-based revenue analysis | `Financial Transaction - Revenue by Customer Class` | Snapshot | Core | Useful for executive / rate review |
| `finance` | SA-type financial mix | `Financial Transactions - Service Type FT Summary` | Snapshot | Core | Good portfolio segmentation |
| `billing` | billed amount summary | `Billed Usage and Amount Charged` | Snapshot Dashboard | Core | Keep as the main billing dashboard |
| `billing` | billed amount by customer segment | `Billed Amount - by Customer Class` | Snapshot | Core | Good standard chart |
| `billing` | billed amount by budget plan | `Billed Amount - Amount Billed by Budget Plan` | Snapshot | Core | Good operational/billing finance crossover |
| `billing` | billed amount by utility | `Billed Amount - By Utility Type` | Snapshot | Core | Broad utility value |
| `billing` | canceled bill segment review | `Billed Amount - Canceled Segments` | Snapshot | Core | Strong operational exception report |
| `billing` | estimated billing review | `Billed Amount - Estimated Segment` | Snapshot | Core | Important for customer-impact monitoring |
| `billing` | rebill review | `Billed Amount - Rebills` | Snapshot | Core | High-value billing exception process |
| `billing` | billed revenue by rate | `Billed Amount - Revenue by Rate Schedule` | Snapshot | Core | Good rates / finance crossover |
| `billing` | detailed billed segment inquiry | `Billed Usage - Account Level View` | Snapshot | Core | Good detailed drill report |
| `billing` | usage by determinant class | `Billed Usage - Across Customer Class & UOM` | Snapshot | Core | Good self-service summary |
| `billing` | service-type billed usage | `Billed Usage - By SA type & Class` | Snapshot | Core | Good service portfolio view |
| `billing` | determinant detail | `Billed Usage - Segment Determinant` | Snapshot | Core | Essential determinant truth layer |
| `billing` | tiered billed usage | `Billed Usage - Tiered Billed Usage` | Snapshot | Core | Useful if tier logic is business-relevant in this client |
| `cashiering` | deposit control balancing | `Deposit Control - Ending Balances` | Existing Domain | Core | Broad cashiering control report |
| `cashiering` | payment application/account review | `Payment Segments - Account View` | Existing Domain | Core | Good operational detail layer |
| `cashiering` | online payment trend | `OriginPay - Payment Count and Amount Trends` | Existing Domain | Core | Valuable digital-channel KPI |
| `cashiering` | payment plan health | `Pay Plan - Health Status` | Existing Domain | Core | Important customer/payment operations process |
| `cashiering` | autopay operations | `AutoPay Drafts By Scheduled Date` | Existing Domain | Core | Broad operational value |
| `cashiering` | autopay exception / population review | `Autopay Accounts With Active Deposits` | Existing Domain | Secondary | Keep as optional unless used broadly |
| `common` | batch operations health | `Batch Process Dashboard` | Existing Domain Dashboard | Core | Strong common-workstream monitor |
| `common` | batch status monitoring | `Batch Run by Status` | Existing Domain | Core | Broad technical operations view |
| `common` | incomplete batch review | `Incomplete Batch Runs` | Existing Domain | Core | Important support control |
| `common` | period-based batch exception monitoring | `Incomplete Batch Runs by Period` | Existing Domain | Core | Good trend/exceptions view |
| `common` | bill-segment exceptions | `Bill Segment Exception` | Existing Domain | Core | Broad billing support value |
| `common` | usage transaction exceptions | `Usage Transaction Exception` | Existing Domain | Core | Strong operational monitoring value |
| `common` | VEE exception monitoring | `Most VEE Exceptions` | Existing Domain | Core | Strong utility operations use case |
| `common` | VEE exception categorization | `VEE Exception Types by Person` | Existing Domain | Secondary | Keep if business users actively use it |
| `common` | task and exception control | `Exception and To Do Dashboard` | Existing Domain Dashboard | Core | Good common support dashboard |
| `customer_ops` | customer service dashboard | `Customer Operations Dashboard` | Existing Domain Dashboard | Core | Main entry point for customer-facing operations |
| `customer_ops` | account exception handling | `Account Alert` | Existing Domain | Core | High-value service-rep use case |
| `customer_ops` | customer contact workload / trend | `Customer Contact - Daily Contact Trends` | Existing Domain | Core | Useful management and staffing view |
| `customer_ops` | customer contact detail | `Customer Contact Detail` | Existing Domain | Core | Good drill report |
| `customer_ops` | case operations | `Case Detail / Work Queue` | Existing Domain | Core | Important business process |
| `customer_ops` | customer inquiry | `Customer Detail` | Existing Domain | Core | Good inquiry/reporting layer |
| `customer_ops` | premise inquiry | `Premise Detail` | Existing Domain | Core | Good service-address support report |
| `customer_ops` | landlord portfolio management | `Landlord Agreement Detail` | Existing Domain | Secondary | Keep as optional unless landlord processes are a standard sell |
| `new_services` | new service KPI view | `New Services Dashboard` | Existing Domain Dashboard | Core | Main summary for onboarding |
| `new_services` | new premises KPI view | `New Premises Dashboard` | Existing Domain Dashboard | Core | Good planning / growth view |
| `new_services` | onboarding detail | `New Services - Accounts Detailed` | Existing Domain | Core | Operational drill layer |
| `new_services` | new premise counts / trend | `New Services - Number of New Premises` | Existing Domain | Core | Good planning and growth summary |
| `new_services` | pending SA backlog aging | `Pending Service Agreement Aging` | Existing Domain | Core | Gap-fill report now completed using existing resources |
| `debt_mgmt` | collections dashboard | `Collections Performance Dashboard` | Existing Domain Dashboard | Core | Main debt-management summary |
| `debt_mgmt` | aging portfolio | `Age of Unpaid Bills` | Existing Domain | Core | Essential debt process report |
| `debt_mgmt` | arrears by segment | `Arrears by Customer Class` | Existing Domain | Core | Good portfolio segmentation |
| `debt_mgmt` | arrears by debt class | `Arrears by Debt Class` | Existing Domain | Core | Good operational and executive use case |
| `debt_mgmt` | collections account drill | `Collection Process - Account Details` | Existing Domain | Core | Strong operational detail |
| `debt_mgmt` | collections effectiveness | `Collection Process - Effectiveness` | Existing Domain | Core | High-value management metric |
| `debt_mgmt` | severance operations | `Severance Process - Account Details` | Existing Domain | Core | Important utility process |
| `debt_mgmt` | write-off trend | `Write Offs - Debt Written Off Trend` | Existing Domain | Core | Broad finance/debt value |
| `debt_mgmt` | active write-off workload | `Write Offs - Active Write Off Processes / Initiated Debt` | Existing Domain | Core | Good operational control |
| `debt_mgmt` | collection agency referrals | `Collection Agency Referral Detail` | Existing Domain | Secondary | Keep if outside-agency handoff is part of the standard sell |
| `field_ops` | field operations dashboard | `Field Operations Dashboard` | Existing Domain Dashboard | Core | Main field process summary |
| `field_ops` | field work aging | `Field Activity - Average Days per Field Task` | Existing Domain | Core | Good operational KPI |
| `field_ops` | field activity exceptions | `Field Activity - Cancellations` | Existing Domain | Core | High-value operational exception view |
| `field_ops` | field activity detail | `Field Activity Detail` | Existing Domain | Core | Good drill / research layer |
| `field_ops` | crew management | `Crew Detail` | Existing Domain | Secondary | Keep if crew assignment is an active client process |
| `field_ops` | location / organization detail | `Location Organization Detail` | Existing Domain | Secondary | Useful but less central than activity views |
| `meter_ops` | measurement staging / IMD review | `Measurement - IMD Summary` | Snapshot | Core | Important upstream quality report |
| `meter_ops` | measurement condition trend | `Measurement - Measurement Conditions` | Snapshot | Core | Keep as the chart / trend version |
| `meter_ops` | measurement condition detail | `Measurement - Measuring Conditions` | Snapshot | Secondary | Similar to the trend report; keep only if users need table detail |
| `meter_ops` | measurement cycle totals | `Measurement - Reads and Totals by Cycle` | Snapshot | Core | Good operational summary |
| `meter_ops` | measurement by service point type | `Measurement - SP Type` | Snapshot | Core | Good portfolio segmentation |
| `meter_ops` | estimated measurement review | `Measurements - Estimated` | Snapshot | Core | High-value quality exception report |
| `meter_ops` | service-point measurement detail | `Measurements - by Service Point ID` | Snapshot | Core | Strong drill layer |
| `meter_ops` | meter read component monitoring | `Meter Reads - Counts by Component Type` | Snapshot | Core | Good summary |
| `meter_ops` | usage by account | `Usage - Account View` | Snapshot | Core | High-value operational detail |
| `meter_ops` | usage by customer class and UOM | `Usage - Customer Class and UOM` | Snapshot | Core | Good summary |
| `meter_ops` | high-usage customer review | `Usage - Highest Usage Customers` | Snapshot | Core | Good business-facing insight |
| `meter_ops` | premise consumption research | `Usage - Premise Consumption` | Snapshot | Core | Good premise-level analysis |
| `meter_ops` | usage by component | `Usage - by Measuring Component ID` | Snapshot | Core | Good operational drill |
| `meter_ops` | usage transaction by SA type | `Usage Transaction - By SA Type` | Snapshot | Core | Good usage-header process view |
| `meter_ops` | usage transaction by subscription type | `Usage Transaction - by Subscription Type` | Snapshot | Core | Good complementary segmentation |

## Reports To Merge, Rename, Or Reposition

These reports are useful, but the standard offering should present them more cleanly.

| Current Report | Action | Reason |
|---|---|---|
| `Dashboard | Billed Usage and Amount by segment` | Merge into `Billed Usage and Amount Charged` | Same business purpose; keep one standardized name |
| `Measurement - Measurement Conditions` and `Measurement - Measuring Conditions` | Keep one as chart and one as detail, or merge | They appear too close in purpose to present as separate flagship offerings without clearer naming |
| `General Ledger - Aged Debt by SA` | Reposition under `debt_mgmt` or make secondary | This reads more like a debt aging report than a pure GL report |
| `Financial Transaction - Payment Account Detail` | Reposition under `cashiering` or make secondary | Likely closer to payment operations than FT standard finance reporting |
| `Autopay Accounts With Active Deposits` | Secondary only | Useful, but narrower than the other cashiering standards |
| `Landlord Agreement Detail` | Secondary only | Valuable in some utilities, but not universal enough to lead the standard set |
| `Crew Detail` | Secondary only | Useful if a client actively manages crews in C2M/JRS; not always standard |
| `Location Organization Detail` | Secondary only | More administrative than core field operations reporting |

## Biggest Current Gaps In The Standard Offering

Even with the exported reports and snapshot-backed suite, the standard offering still has some gaps.

### 1. `common` workstream reference-data health
The current common set is strong on exceptions and batch processing, but weak on:
- inactive lookup values still referenced
- reference-data completeness
- release / bundle governance beyond raw bundle views

Recommended future addition:
- `Reference Data Health Monitor`

### 2. `customer_ops` customer communication readiness
The current customer operations set is good on contacts, cases, and alerts, but still thin on:
- correspondence readiness
- unprintable / undeliverable communications
- address/contact quality defects

Recommended future addition if richer existing resources become available:
- `Customer Communication Readiness`

### 3. `debt_mgmt` payment arrangement visibility
The debt set is strong on collections, arrears, severance, and write-offs, but it is still thin on:
- payment arrangement workload and performance

Recommended future addition if richer existing resources become available:
- `Payment Arrangement Summary`

### 4. `field_ops` install-event / service-point linkage
The field operations export is field-activity-centric, which is good, but it does not obviously cover:
- service points without install-event linkage
- activity-to-asset/device linkage quality

Recommended future addition if richer existing resources become available:
- `Service Point / Install Linkage Exceptions`

## Coverage Summary

### Strong coverage now
- `finance`
- `billing`
- `meter_ops`
- `cashiering`
- `debt_mgmt`

### Adequate but should mature
- `customer_ops`
- `common`
- `field_ops`

### Strengthened by recent completion
- `new_services`

## Recommendation

The standard offering should be presented in two layers:

### 1. Core standard offering
The reports marked `Core` in this document.

### 2. Secondary / optional add-ons
The reports marked `Secondary`, which are still valuable but may not belong in every base client package.

This gives SmartCity:
- broad workstream coverage
- a clearer utility business-process story
- less duplication
- a cleaner path for future snapshot and Domain investments
