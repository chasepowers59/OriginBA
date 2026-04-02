# CISADM Relationship Map

## Purpose
This guide maps the main reporting chains for billing, usage, and finance so you can see:
- what table usually drives the query
- what child tables add detail
- where row multiplication risk appears
- what the chain includes and excludes

## 1. Billing Chain

### Core relationship
```text
CI_ACCT
  -> CI_SA
    -> CI_BSEG
      -> CI_BILL
```

### Meaning
- `CI_ACCT`: customer/account umbrella
- `CI_SA`: service-level contract under the account
- `CI_BSEG`: billed service period/fact
- `CI_BILL`: final bill header

### Typical join keys
```text
CI_ACCT.ACCT_ID = CI_SA.ACCT_ID
CI_SA.SA_ID = CI_BSEG.SA_ID
CI_BSEG.BILL_ID = CI_BILL.BILL_ID
CI_BILL.ACCT_ID = CI_ACCT.ACCT_ID
```

### What this chain is good for
- billed population
- bill-cycle reporting
- bill status and completion
- billing gap analysis when paired with expected population logic

### What it does not automatically include
- payment activity
- GL distribution detail
- unbilled but active SAs
- detailed usage determinants unless joined separately

### Main row-grain options
- one row per account
- one row per service agreement
- one row per bill segment
- one row per bill

### Main risk
If you add multiple child billing detail tables at once, bill-segment counts and billed amounts can multiply.

### Support/detail tables often added
- `CI_BSEG_SQ`
- `CI_BSEG_READ`
- `CI_BSEG_CALC`
- `CI_BSEG_CALC_LN`
- `CI_BSEG_ITEM`
- `CI_BSEG_EXCP`

### Rule
If the question is about billing-period facts, `CI_BSEG` is often the safest driver.

## 2. Expected Billing Population Chain

### Core relationship
```text
CI_ACCT
  -> CI_SA
```

### Meaning
This is the expected service population before proving that billing actually occurred.

### What this chain is good for
- active service population
- expected-to-bill baseline
- start-service backlog or missing-bill analysis

### What it does not automatically include
- actual billed records
- actual financial postings

### Rule
Never treat active-SA population as the same thing as billed population without saying so explicitly.

## 3. Finance Chain

### Core relationship
```text
CI_ACCT
  -> CI_SA
    -> CI_FT
      -> CI_FT_GL
```

### Meaning
- `CI_FT` is the accounting-impact fact
- `CI_FT_GL` extends the transaction into GL-facing detail

### Typical join keys
```text
CI_ACCT.ACCT_ID = CI_SA.ACCT_ID
CI_SA.SA_ID = CI_FT.SA_ID
CI_FT.<transaction key> = CI_FT_GL.<transaction key>
```

### What this chain is good for
- arrears exposure
- posted transaction analysis
- GL distribution checks
- adjustment and balance reporting

### What it does not automatically include
- bill-header presentation logic
- usage quantities
- device or service-point context

### Main row-grain options
- one row per FT
- one row per account after aggregation
- one row per GL posting after GL join

### Main risk
Joining `CI_FT` to GL/detail rows and then summarizing at account level without pre-aggregation can overstate totals.

### Rule
If the business question is financial impact, start from `CI_FT`, not `CI_BILL`.

## 4. Billing-to-Finance Bridge

### Core relationship
```text
CI_SA
  -> CI_BSEG
  -> CI_FT
```

### Meaning
This bridge is used when you need to compare billing outcomes to financial posting outcomes.

### What this chain is good for
- billed amount versus posted amount reconciliation
- bill segment to transaction impact analysis
- revenue assurance investigations

### Main risk
There is not always a simple one-to-one relationship between bill segments and financial transactions.

### Rule
Aggregate both sides to a common business grain before comparing them.

## 5. Usage Chain

### Core relationship
```text
CI_ACCT
  -> CI_SA
    -> C1_USAGE
      -> D1_USAGE
        -> D1_USAGE_PERIOD_SQ
```

### Meaning
- `C1_USAGE` bridges service agreement context to usage processing
- `D1_USAGE` is the usage transaction fact
- `D1_USAGE_PERIOD_SQ` holds quantity detail at usage-period level

### Typical join keys
```text
CI_SA.SA_ID = C1_USAGE.SA_ID
C1_USAGE.USAGE_ID = D1_USAGE.USG_EXT_ID
D1_USAGE.D1_USAGE_ID = D1_USAGE_PERIOD_SQ.D1_USAGE_ID
```

### What this chain is good for
- processed usage reporting
- usage outlier analysis
- usage status monitoring
- quantity trending

### What it does not automatically include
- customer bill amounts
- device installation history
- raw inbound read lifecycle

### Main row-grain options
- one row per usage transaction
- one row per usage transaction plus quantity rollup
- one row per account after usage aggregation

### Main risk
`D1_USAGE_PERIOD_SQ` and other detail tables can create row multiplication if joined before aggregation.

### Rule
When the question is usage volume, aggregate detail to `D1_USAGE_ID` before joining wide dimensions.

## 6. Meter and Device Chain

### Core relationship
```text
CI_SP
  -> D1_INSTALL_EVT
    -> D1_DVC_CFG
      -> D1_DVC
      -> D1_MEASR_COMP
```

### Meaning
- `CI_SP` is the service location
- `D1_INSTALL_EVT` shows when device configuration was installed or removed
- `D1_DVC_CFG` is the effective-dated configuration state
- `D1_DVC` is the physical device
- `D1_MEASR_COMP` is the measurement channel/component

### What this chain is good for
- which device was installed where and when
- service-point to meter mapping
- configuration-aware device analytics

### What it does not automatically include
- customer balances
- billed dollars
- completed usage transactions

### Main row-grain options
- one row per install event
- one row per service point
- one row per device configuration

### Main risk
Time validity matters. A device can have multiple configurations or install events over time.

### Rule
For historical meter questions, always define the time window explicitly.

## 7. Measurement and Read Processing Chain

### Core relationship
```text
D1_DVC / D1_MEASR_COMP
  -> D1_INIT_MSRMT_DATA
  -> D1_MSRMT
  -> D1_MSRMT_LOG
```

### Meaning
- IMD is raw inbound measurement data
- measurement is processed/accepted measurement
- measurement log records processing events

### What this chain is good for
- read ingestion monitoring
- VEE/process troubleshooting
- measurement lifecycle analysis

### Main risk
Raw and processed measurement objects represent different lifecycle stages. They should not be treated as identical facts.

### Rule
Decide whether the question is about inbound reads, accepted measurements, or usage transactions. Those are different chains.

## 8. Field Operations Chain

### Core relationship
```text
CI_SP
  -> D1_ACTIVITY
    -> D1_ACTIVITY_REL
    -> D1_ACTIVITY_REL_OBJ
```

### Meaning
- service-point-centered operational work
- relationship tables add hierarchy and context

### What this chain is good for
- open/completed field work
- appointment and operational SLA analysis
- cancellation/reschedule pattern analysis

### Main risk
Related-object tables can create multiple rows per activity.

### Rule
If the output is one row per activity, aggregate relationship tables first or treat them as optional detail.

## 9. Collections Chain

### Core relationship
```text
CI_ACCT
  -> CI_SA
    -> CI_FT
  -> CI_COLL_PROC
  -> C1_PA_RQST
```

### Meaning
- debt comes from financial transactions
- collection process adds workflow context
- payment arrangement adds negotiated repayment context

### What this chain is good for
- debt aging
- collections effectiveness
- arrangement participation

### Main risk
Collections workflow rows are not the same thing as debt rows.

### Rule
Calculate debt from `CI_FT`; use collections tables to explain treatment and process.

## Inclusion / Exclusion Shortcuts

### Start from `CI_BSEG`
Includes:
- actual billed population

Excludes:
- expected but unbilled population

### Start from `CI_FT`
Includes:
- financial-impact population

Excludes:
- pure bill-presentation context

### Start from `D1_USAGE`
Includes:
- processed usage population

Excludes:
- raw read-only populations unless joined separately

### Start from `D1_INSTALL_EVT`
Includes:
- install-history population

Excludes:
- finance and debt context

## Default Reporting Rules
1. Decide the grain first.
2. Choose the driver table that matches the business question.
3. Add only the joins needed for that question.
4. Keep optional enrichments as `LEFT JOIN`s.
5. Aggregate detail before joining across workstreams.
6. Validate row counts after every major join.

## Companion Docs
- `docs/cisadm_workstream_vocabulary_guide.md`
- `docs/cisadm_sql_cheat_sheet.md`
- `docs/cisadm_workstream_study_deck.md`
