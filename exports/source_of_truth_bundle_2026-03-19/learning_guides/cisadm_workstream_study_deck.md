# CISADM Workstream Study Deck

## Purpose
This is a study-deck style guide for learning the major CISADM workstreams through simple prompts:
- what it is
- why the business cares
- what tables matter first
- what questions you should be able to answer

## How To Use This Deck
For each workstream:
1. learn the business story
2. memorize the first 2-5 anchor tables
3. practice the example questions
4. sketch the likely join path before opening SQL

## `billing`
### Business story
Billing turns service activity and usage into customer-facing charges.

### Learn these first
- `CI_BILL`
- `CI_BSEG`
- `CI_FT`
- `CI_BSEG_SQ`

### You should understand
- bill header vs bill segment
- billed population vs expected population
- why bill segment is often the better analysis grain than bill header

### Example questions
- Which active services should have billed but did not?
- Which bill segments are in error or canceled status?
- How much billed quantity rolled into this bill cycle?
- Which accounts have bills created but not completed?

### Likely join path
`CI_ACCT -> CI_SA -> CI_BSEG -> CI_BILL`

### Business warning
If you only query `CI_BSEG`, you are looking at actual billed segments, not every account expected to bill.

## `cashiering`
### Business story
Cashiering answers whether money came in correctly and whether controls/reconciliation are intact.

### Learn these first
- `CI_PAY_EVENT`
- `CI_PAY_TNDR`
- `CI_DEP_CTL`
- `CI_PAY_SEG`

### You should understand
- payment event vs tender row
- why deposit control matters for reconciliation
- how one payment can be split across obligations

### Example questions
- Which payment events are missing valid deposit control?
- Which tenders are unresolved?
- How much payment activity happened in a given time window?

### Likely join path
`CI_PAY_EVENT -> CI_PAY_TNDR -> CI_DEP_CTL`

### Business warning
Cash receipt data and debt allocation data are related but not identical.

## `common`
### Business story
Common provides shared setup and reference context used by many other reports.

### Learn these first
- `CI_LOOKUP_VAL`
- `CI_PREM`
- `CI_PREM_CHAR`
- `CI_PREM_GEO`

### You should understand
- coded values versus business-readable labels
- premise as a location object, not an account
- why bad reference data can break many reports at once

### Example questions
- Which lookup values are inactive but still referenced?
- Which premises are missing expected geo or characteristic values?
- Which release bundles were installed in a period?

### Likely join path
Usually enrichment-only from a main fact table into `CI_LOOKUP_VAL` or premise tables.

### Business warning
These tables usually explain facts; they usually should not become the fact grain.

## `customer_ops`
### Business story
Customer operations gives service reps the context needed to talk to customers and act correctly.

### Learn these first
- `CI_ACCT`
- `CI_PER`
- `CI_PER_NAME`
- `CI_ACCT_ALERT`

### You should understand
- account vs person
- primary name selection
- alert-driven handling
- why print/contact readiness depends on multiple optional objects

### Example questions
- Which accounts have active alerts?
- Which contact letters are not printable and why?
- Which people are tied to an account and what is the primary name?

### Likely join path
`CI_ACCT -> CI_PER / CI_PER_NAME`, with optional joins to alerts and contact objects

### Business warning
Optional person/contact joins should usually stay outer joins.

## `debt_mgmt`
### Business story
Debt management tracks overdue balances and the processes used to recover them.

### Learn these first
- `CI_ACCT`
- `CI_FT`
- `CI_COLL_PROC`
- `C1_PA_RQST`

### You should understand
- overdue debt comes from transaction rows, not just bill headers
- collection process is workflow context, not the balance itself
- payment arrangement is a negotiated debt treatment, not a payment event

### Example questions
- Which accounts have debt over 60 days?
- Which collection processes reduce arrears the most?
- Which accounts are on payment arrangements and what are the terms?

### Likely join path
`CI_ACCT -> CI_SA -> CI_FT`, then optional joins to collections and arrangement tables

### Business warning
Do not confuse all balance rows with arrears-eligible rows.

## `field_ops`
### Business story
Field ops tracks real-world service work like appointments, investigations, installations, and service actions.

### Learn these first
- `D1_ACTIVITY`
- `CI_SP`
- `D1_ACTIVITY_REL_OBJ`

### You should understand
- field activity is the work event
- service point is the place of work
- related objects often tell you what business entities the work touched

### Example questions
- How many field activities are open, working, canceled, or completed?
- Which service points have aged field activities?
- What cancellation or reschedule reasons appear most often?

### Likely join path
`CI_SP -> D1_ACTIVITY`, with optional relationship joins

### Business warning
Relationship tables can multiply rows if you do not keep the intended grain.

## `field_tasks`
### Business story
Field tasks represent framework-managed operational workload when the process is task-driven.

### Learn these first
- `F1_TSK`
- `F1_TSK_LOG`
- `CI_SP`

### You should understand
- task record vs task log
- how task-driven work differs from activity-driven work

### Example questions
- Which tasks are open or aged?
- Which tasks generate the most rework/log activity?

### Likely join path
`F1_TSK -> F1_TSK_LOG`, with optional service-point enrichment

### Business warning
Task log is event history, not one-row-per-task.

## `finance`
### Business story
Finance verifies that transaction activity distributed correctly into accounting structures.

### Learn these first
- `CI_FT`
- `CI_FT_GL`
- `CI_FT_PROC`
- `CI_ADJ`

### You should understand
- financial transaction as the accounting-impact fact
- GL detail as enrichment or downstream distribution detail
- adjustment as one subtype/business process within transaction flows

### Example questions
- Which transactions are missing GL distribution status?
- Which adjustments were created in the period?
- How much financial activity hit a given division or GL structure?

### Likely join path
`CI_FT -> CI_FT_GL`, with optional joins to processing or adjustment context

### Business warning
One `CI_FT` can have multiple related GL/detail rows; aggregate before higher-level reporting.

## `meter_ops`
### Business story
Meter ops is where device inventory, read processing, measurement lifecycle, and usage transactions meet.

### Learn these first
- `D1_DVC`
- `D1_DVC_CFG`
- `D1_INSTALL_EVT`
- `D1_USAGE`
- `C1_USAGE`

### You should understand
- device vs device configuration
- install event as the time-based link to service point
- measurement vs usage
- usage exception vs VEE exception

### Example questions
- Which service points are missing install-event linkage?
- Which devices generated exception-heavy usage?
- Which usage rows processed successfully in the period?
- Which devices are tied to which service points and customers?

### Likely join path
`CI_SP -> D1_INSTALL_EVT -> D1_DVC_CFG -> D1_DVC`

and

`CI_ACCT -> CI_SA -> C1_USAGE -> D1_USAGE`

### Business warning
Usage detail tables can fan out quickly; aggregate before broad enrichment.

## `new_services`
### Business story
New services tracks onboarding from service request/setup into active service agreements.

### Learn these first
- `CI_SA`
- `CI_SP_CHAR`

### You should understand
- pending vs active service agreement status
- why onboarding delays show up before billing problems do

### Example questions
- Which pending SAs have aged past expected start timing?
- Which service-point characteristics affect service setup routing?

### Likely join path
`CI_SA` with optional service-point/service-point-characteristic context

### Business warning
If you only look at active SAs, you lose visibility into start-service backlog.

## Suggested Memorization Order
1. `CI_ACCT`, `CI_SA`, `CI_SP`
2. `CI_BILL`, `CI_BSEG`, `CI_FT`
3. `D1_DVC`, `D1_INSTALL_EVT`, `C1_USAGE`, `D1_USAGE`
4. `CI_LOOKUP_VAL`, `CI_PREM`
5. `CI_COLL_PROC`, `C1_PA_RQST`, `D1_ACTIVITY`

## Companion Docs
- `docs/cisadm_workstream_vocabulary_guide.md`
- `docs/cisadm_sql_cheat_sheet.md`
- `docs/cisadm_relationship_map.md`
