# CISADM Workstream Vocabulary Guide

## Purpose
This document is a business-facing orientation guide for the curated CISADM workstreams already represented in this repository.

It is meant to help you:
- build vocabulary faster
- understand what each workstream is trying to measure
- recognize the most important CISADM tables in that workstream
- connect table names to real business use cases

## Scope and Limits
- This guide is based on the curated repository source of truth, not the full physical CISADM schema.
- Primary source: `output/workstream_reporting_dictionary.json`
- Supporting context:
  - `knowledge_base/c2m_cisadm/cisadm_core_model.md`
  - `output/domain_designs_metadata.json`
  - `domains/working/manual_designs/DOMAIN_BUSINESS_CATALOG.md`
  - `sql/performance/snapshots/docs/workstream_snapshot_catalog.md`
  - `docs/smartcity_9_workstream_product_plan.md`
- Current curated coverage: 10 workstreams and 73 aligned tables.

## How To Read CISADM Quickly

### Core business objects
- `CI_ACCT`: customer account; the financial relationship.
- `CI_SA`: service agreement; the service-level contract under an account.
- `CI_SP`: service point; the physical point where service is delivered.
- `CI_BILL`: bill header; the finished customer bill.
- `CI_BSEG`: bill segment; a bill component tied to a service agreement and bill period.
- `CI_FT`: financial transaction; accounting-impact rows such as charges, adjustments, and payments.
- `C1_USAGE`: usage transaction envelope in C2M usage processing.
- `D1_USAGE`: detailed usage transaction record.
- `D1_INSTALL_EVT`: install/removal event for meter or device configuration at a service point.
- `D1_ACTIVITY`: field activity or operational work event.

### Common join path
For many reporting questions, the business chain is:

`CI_ACCT -> CI_SA -> CI_BSEG/CI_FT` for billing and finance questions

`CI_ACCT -> CI_SA -> C1_USAGE -> D1_USAGE` for usage questions

`CI_SP -> D1_INSTALL_EVT -> D1_DVC/D1_DVC_CFG` for meter and device questions

### Useful mental model
- `CI_*` tables usually represent customer information, billing, finance, and core CIS objects.
- `D1_*` tables usually represent device, measurement, usage, and field operations.
- `F1_*` tables usually represent framework-level controls, bundles, tasks, or migration/runtime support.
- `C1_*` tables often extend base CIS behavior for C2M-specific business processes.

## Workstream Overview

| Workstream | What it covers | Primary business question |
| --- | --- | --- |
| `billing` | bills, bill segments, billed quantities, bill messaging | Did we bill the right customers correctly and on time? |
| `cashiering` | payment events, tenders, deposit controls | Did cash receipts post and reconcile correctly? |
| `common` | reference data, premises, geo, bundles, migration state | Are shared setup and reference objects healthy and usable? |
| `customer_ops` | customer identity, alerts, approvals, contacts | Can service reps act on complete and accurate customer context? |
| `debt_mgmt` | overdue balances, collections, payment arrangements | Which debt needs action, and is collections working? |
| `field_ops` | field activities tied to service points | Are field jobs created, tracked, and completed correctly? |
| `field_tasks` | framework tasks and task logs | What task workload exists behind operational processing? |
| `finance` | transaction accounting, GL distribution, adjustments | Did transactions distribute and post correctly to finance? |
| `meter_ops` | devices, install events, measurements, usage | Are meters, reads, and usage flows behaving correctly? |
| `new_services` | new service agreements and service point attributes | Is the start-service pipeline moving cleanly into production billing? |

## Workstream Guides

## `billing`
### Simple definition
Billing is the workstream that turns service activity and usage into customer-facing bills and bill segments.

### Common use cases
- monitor bill completion backlog
- identify missing or canceled bill segments
- reconcile billed quantities to billed dollars
- explain why a customer bill looks wrong

### Key tables
| Table | Simple definition | Business application |
| --- | --- | --- |
| `CI_BILL` | Bill header. One record per customer bill. | Use for bill date, due date, bill status, account, and cycle reporting. |
| `CI_BSEG` | Bill segment. A service-period component of a bill. | Use for bill-period detail, segment status, service agreement alignment, and expected-vs-actual billing checks. |
| `CI_FT` | Financial transaction. | Use to connect billed amounts, postings, arrears exposure, and accounting impact back to billing activity. |
| `CI_BSEG_READ` | Reads attached to a bill segment. | Use when validating which reads contributed to billing. |
| `CI_BSEG_SQ` | Service quantities on a bill segment. | Use for billed usage quantity and determinant analysis. |
| `CI_BSEG_CALC` | Bill segment calculation summary. | Use to inspect how a segment was calculated. |
| `CI_BSEG_CALC_LN` | Calculation line detail for a bill segment. | Use for rate-component or line-level billing explanation. |
| `CI_BSEG_ITEM` | Itemized segment details or charges. | Use for item-level breakdowns on a bill segment. |
| `CI_BSEG_EXCP` | Bill segment exceptions. | Use to find bill failures or rule exceptions. |
| `CI_BSEG_MSG` | Messages attached to a segment. | Use for bill narrative, warnings, or explanatory text. |
| `CI_BILL_MSGS` | Messages attached to a bill. | Use for bill-level communication or notice reporting. |
| `CI_BILL_MSG_PRM` | Parameters for bill messages. | Use to decode message context or personalized bill text. |
| `CI_BILL_ROUTING` | Bill routing or delivery path details. | Use for print, delivery, or routing investigations. |
| `CI_RS_L` | Rate schedule lookup/label table. | Use to present readable rate schedule names in bill analytics. |

### Business application
Billing data is what operations, revenue assurance, and customer service use to prove that service agreements actually became accurate customer charges.

## `cashiering`
### Simple definition
Cashiering covers the intake of money, the tender used, and the control structures that support deposit and reconciliation.

### Common use cases
- find payment events missing valid deposit control
- audit tender status by payment event
- support daily close and cashier reconciliation

### Key tables
| Table | Simple definition | Business application |
| --- | --- | --- |
| `CI_PAY_EVENT` | Payment event header. | Use to count and time-stamp payment activity. |
| `CI_PAY_TNDR` | Tender rows under a payment event. | Use for payment method, tender status, and tender control tracking. |
| `CI_DEP_CTL` | Deposit control. | Use for reconciliation status and close-control checks. |
| `CI_PAY_SEG` | Payment segment allocation. | Use to understand how a payment was distributed across debt or obligations. |

### Business application
Cashiering reporting helps finance and customer service answer whether money was received, controlled, and applied correctly.

## `common`
### Simple definition
Common contains shared reference and platform-level objects used across multiple business processes.

### Common use cases
- validate lookup/reference quality
- enrich operational reports with premise or geo context
- inspect migration or bundle deployment state

### Key tables
| Table | Simple definition | Business application |
| --- | --- | --- |
| `CI_PREM` | Premise; the serviced location. | Use for address-level service reporting and customer location context. |
| `CI_PREM_CHAR` | Premise characteristics. | Use for premise attributes such as class, flags, or local business tags. |
| `CI_PREM_GEO` | Premise geography detail. | Use for mapping, territory, route, and geo segmentation. |
| `CI_LOOKUP_VAL` | Shared lookup values. | Use to translate coded values into readable business labels. |
| `F1_BNDL` | Bundle or packaged release artifact. | Use for release-management visibility into what was installed. |
| `F1_BNDL_ENTTY` | Objects included in a bundle. | Use to inspect the contents of a release bundle. |
| `F1_MIGR_DATA_ST` | Migration data set or migration status object. | Use to understand migration readiness or migration execution state. |
| `F1_MIGR_TRANS` | Migration transaction detail. | Use for migration troubleshooting and audit trails. |

### Business application
This workstream matters because almost every report eventually depends on clean reference data, valid addresses, and stable deployment metadata.

## `customer_ops`
### Simple definition
Customer operations focuses on the customer record, service-facing context, alerts, approvals, and contact information.

### Common use cases
- prepare customer service views
- check whether outbound contact letters are printable
- surface alerts or approval history before a rep takes action

### Key tables
| Table | Simple definition | Business application |
| --- | --- | --- |
| `CI_ACCT` | Customer account. | Use as the anchor for most customer-service reporting. |
| `CI_PER` | Person or customer identity record. | Use for who the customer/contact is. |
| `CI_PER_NAME` | Person names. | Use for display names, primary name selection, and contact print logic. |
| `CI_ACCT_ALERT` | Alerts on an account. | Use to surface service warnings, collections flags, or handling instructions. |
| `CI_APPR_REQ` | Approval request/history. | Use for operational approval tracking such as adjustments pending/frozen. |
| `C1_REPRESENTATIVE` | Representative or crew/person relationship object. | Use when work needs to be attributed to a rep or crew. |
| `D1_US_CONTACT` | Usage-service contact linkage. | Use for customer/contact relationships in usage-related workflows. |
| `D1_CONTACT_IDENTIFIER` | Contact identifiers. | Use when matching contacts to external IDs or operational identifiers. |
| `CI_LANDLORD` | Landlord relationship information. | Use for property-owner and tenant-oriented customer processes. |

### Business application
Customer ops reporting reduces avoidable service friction by making sure agents can see who the customer is, what warnings apply, and whether outbound communication can actually be sent.

## `debt_mgmt`
### Simple definition
Debt management tracks overdue balances, collections processes, and payment arrangements.

### Common use cases
- rank accounts by arrears risk
- monitor collection process effectiveness
- review payment arrangement terms and linked objects

### Key tables
| Table | Simple definition | Business application |
| --- | --- | --- |
| `CI_ACCT` | Customer account. | Use as the debtor/account anchor. |
| `CI_FT` | Financial transactions affecting balance. | Use to calculate overdue debt, arrears age, and collectible exposure. |
| `CI_COLL_PROC` | Collection process record. | Use to track collection stage, status, and next action. |
| `C1_PA_RQST` | Payment arrangement request. | Use for down payment, installment count, installment amount, and arrangement monitoring. |
| `C1_PA_RQST_REL_OBJ` | Objects related to a payment arrangement request. | Use to tie arrangements back to accounts, obligations, or other affected objects. |

### Business application
This is the workstream for collections teams, revenue recovery analysts, and executives who need to know which debt is aging, which strategies work, and where intervention should happen next.

## `field_ops`
### Simple definition
Field operations centers on operational activities performed at service points, often involving appointments, installs, inspections, or status-changing work.

### Common use cases
- monitor open and completed field activities
- analyze activity aging and cancellation reasons
- connect field work to service points and related objects

### Key tables
| Table | Simple definition | Business application |
| --- | --- | --- |
| `D1_ACTIVITY` | Field activity record. | Use for work status, type, timing, appointment windows, and operational SLA reporting. |
| `CI_SP` | Service point. | Use to place field work at the actual location receiving service. |
| `D1_ACTIVITY_CHAR` | Activity characteristics. | Use for configurable activity attributes without changing base table structure. |
| `D1_ACTIVITY_REL` | Relationships between activities. | Use for parent-child or linked activity analysis. |
| `D1_ACTIVITY_REL_OBJ` | Related business objects tied to an activity. | Use to connect field work to accounts, devices, or other entities. |

### Business application
Field ops reporting tells supervisors whether work orders are aging, where crews are spending time, and how field actions are affecting service delivery.

## `field_tasks`
### Simple definition
Field tasks is a lightweight task-management view built on framework task objects rather than full field activity objects.

### Common use cases
- inspect background or assigned task workload
- review task logs for troubleshooting
- connect tasks to service-point context

### Key tables
| Table | Simple definition | Business application |
| --- | --- | --- |
| `F1_TSK` | Framework task. | Use for task queue, assignment, and task status reporting. |
| `F1_TSK_LOG` | Task log or event history. | Use for troubleshooting, audit trail, and elapsed-time analysis. |
| `CI_SP` | Service point. | Use when the task needs location or service context. |

### Business application
This workstream is useful when operational work is represented as tasks and logs rather than as full field-activity transactions.

## `finance`
### Simple definition
Finance focuses on how transactional activity is processed, adjusted, and distributed to the general ledger.

### Common use cases
- detect financial transactions missing GL distribution status
- review adjustment activity
- reconcile financial transactions to GL-facing detail

### Key tables
| Table | Simple definition | Business application |
| --- | --- | --- |
| `CI_FT` | Financial transaction. | Use as the base accounting-impact fact. |
| `CI_FT_GL` | GL-related detail for a financial transaction. | Use to analyze chart-of-accounts or fund distribution outcomes. |
| `CI_FT_PROC` | Financial transaction processing details. | Use to inspect processing status, lifecycle, or engine behavior. |
| `CI_ADJ` | Adjustment transaction header/detail. | Use to report manual or system adjustments and supporting approval paths. |

### Business application
Finance reporting is where utility operations meets accounting: it confirms that charges, corrections, and other transaction events are not only present but properly distributed and controllable.

## `meter_ops`
### Simple definition
Meter operations is the operational meter-to-usage workstream: devices, configurations, install events, measurements, usage transactions, and exceptions.

### Common use cases
- find service points without install-event linkage
- monitor raw reads and processed measurements
- analyze usage exceptions, VEE exceptions, or usage outliers
- connect devices to accounts, service points, and billed usage

### Key tables
| Table | Simple definition | Business application |
| --- | --- | --- |
| `D1_DVC` | Device or meter. | Use for meter inventory and device-level reporting. |
| `D1_DVC_CFG` | Effective-dated device configuration. | Use to know how a device was configured at a point in time. |
| `D1_INSTALL_EVT` | Install/removal event. | Use to tie a device configuration to a service point over time. |
| `D1_MEASR_COMP` | Measuring component. | Use to identify the specific channel or point where measurement is recorded. |
| `D1_INIT_MSRMT_DATA` | Initial measurement data (raw inbound reads). | Use for read-ingestion monitoring and pre-VEE exception analysis. |
| `D1_MSRMT` | Processed measurement. | Use for accepted measurement history and analytics. |
| `C1_USAGE` | Usage transaction envelope. | Use as the bridge from service agreement to detailed usage processing. |
| `D1_USAGE` | Usage transaction detail. | Use for usage status, usage period, and usage-based operations reporting. |
| `D1_USAGE_PERIOD_SQ` | Usage-period service quantities. | Use for quantity aggregation at the usage period level. |
| `D1_USAGE_EXCP` | Usage exceptions. | Use to find failed or problematic usage transactions. |
| `D1_VEE_EXCP` | VEE exceptions. | Use to track validation, estimation, and editing issues. |
| `D1_DVC_EVT` | Device event. | Use for outage, tamper, remote command, or operational device-event tracking. |
| `D1_SP` | D1-side service point entity. | Use when meter/usage modeling requires the device-management SP object. |
| `CI_SP` | CIS service point. | Use when cross-walking meter/device operations to customer-service context. |
| `D1_US` | Usage subscription. | Use to group usage behavior at the usage-subscription level. |
| `D1_US_SP` | Usage subscription to service point relation. | Use to connect usage subscriptions to actual service points. |
| `D1_SP_EQPMNT` | Equipment associated with a service point. | Use for equipment inventory and service-point equipment mapping. |
| `D1_SP_MSRMT_CYC_SCHED_RTE` | SP measurement cycle/schedule/route detail. | Use for read routing, scheduling, and meter-cycle analytics. |
| `D1_DVC_CFG_CHAR` | Device-configuration characteristics. | Use for configurable attributes on the device configuration. |
| `D1_DVC_IDENTIFIER` | Device identifiers. | Use for serial numbers, badges, external IDs, and meter matching. |
| `D1_SP_IDENTIFIER` | Service-point identifiers. | Use for alternate identifiers or external keys. |
| `D1_US_IDENTIFIER` | Usage-subscription identifiers. | Use for external subscription references. |
| `D1_MSRMT_LOG` | Measurement processing log. | Use for troubleshooting read and measurement lifecycle events. |
| `D1_USAGE_BO_DATA_AREA` | Usage business-object data area. | Use when operational logic depends on BO-specific usage metadata. |

### Business application
Meter ops is the most operationally dense workstream in this guide. It answers whether the utility knows which device is installed where, whether reads were received and processed, and whether usage made it cleanly into downstream billing and analytics.

## `new_services`
### Simple definition
New services tracks the pipeline from requested or pending service into active service agreements and service-point attributes.

### Common use cases
- identify stale pending service agreements
- monitor start-service backlog
- inspect service-point characteristics used during service setup

### Key tables
| Table | Simple definition | Business application |
| --- | --- | --- |
| `CI_SA` | Service agreement. | Use to track pending, active, and newly created service relationships. |
| `CI_SP_CHAR` | Service point characteristics. | Use for service-point attributes that affect onboarding, routing, or classification. |

### Business application
This workstream is used to detect onboarding delays before they create missed usage, missed billing, or poor customer start-service experiences.

## Quick Vocabulary Cheatsheet
| Term | Plain-English meaning |
| --- | --- |
| Account | The customer's financial umbrella. |
| Service Agreement | The specific service relationship under an account. |
| Service Point | The place where service is delivered. |
| Bill | The final customer-facing bill. |
| Bill Segment | A bill component for one service period or SA context. |
| Financial Transaction | A charge, adjustment, payment effect, or other balance-impact row. |
| Device | The meter or asset recording service activity. |
| Install Event | The event that places or removes a device at a service point. |
| Measurement | Meter/read data after processing. |
| Usage | Consumption or determinant data prepared for billing or analytics. |
| Collection Process | The workflow used to pursue overdue debt. |
| Payment Arrangement | A structured plan to pay debt over time. |

## Recommended Study Order
1. Start with `CI_ACCT`, `CI_SA`, `CI_SP`, `CI_BILL`, `CI_BSEG`, and `CI_FT`.
2. Learn `meter_ops` next if your reporting work touches usage, reads, or devices.
3. Learn `debt_mgmt` and `finance` next if your work touches arrears, GL, or revenue.
4. Use `common` tables as lookup and enrichment context, not as the main fact grain.

## Notes For Reporting Work
- Preserve grain before adding lookup enrichment.
- For billing and finance, `CI_FT` is often the accounting fact table.
- For usage analysis, filter `D1_USAGE` early and aggregate detail before joining broad dimensions.
- Use lookup label tables carefully and language-safe where available.
- The workstream dictionary includes some "auto-added coverage tables"; those are still useful, but they are often support/enrichment tables rather than the primary business grain.

## Source Alignment
This guide is intentionally aligned to:
- `output/workstream_reporting_dictionary.json`
- `knowledge_base/c2m_cisadm/cisadm_core_model.md`
- `output/domain_designs_metadata.json`
- `domains/working/manual_designs/DOMAIN_BUSINESS_CATALOG.md`
- `docs/smartcity_9_workstream_product_plan.md`
