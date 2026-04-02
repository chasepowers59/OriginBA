# C2M CISADM Analyst Handbook

## Purpose
This handbook is a practical learning guide for understanding CISADM reporting data in Oracle C2M.

It combines:
- vocabulary
- workstream context
- dataflow patterns
- inclusion and exclusion logic
- starter SQL patterns

Use it as the main study document. The companion docs go deeper on specific topics.

## Companion Docs
- `docs/cisadm_workstream_vocabulary_guide.md`
- `docs/cisadm_sql_cheat_sheet.md`
- `docs/cisadm_workstream_study_deck.md`
- `docs/cisadm_relationship_map.md`
- `docs/cisadm_starter_sql_patterns.md`

## 1. Core CISADM Mental Model

### The 3 most important anchors
- `CI_ACCT`: the customer financial umbrella
- `CI_SA`: the service-level contract under the account
- `CI_SP`: the physical place where service is delivered

### The 3 most important reporting facts
- `CI_BSEG`: billed service-period fact
- `CI_FT`: financial-impact fact
- `D1_USAGE`: usage transaction fact

### The 3 most important operational bridges
- `CI_BILL`: finished bill header
- `C1_USAGE`: bridge from service agreement into usage processing
- `D1_INSTALL_EVT`: bridge from service point to device configuration over time

## 2. Main Business Chains

### Billing
```text
CI_ACCT -> CI_SA -> CI_BSEG -> CI_BILL
```
Use when the question is about actual billed population, bill segments, cycles, or bill status.

### Finance
```text
CI_ACCT -> CI_SA -> CI_FT -> CI_FT_GL
```
Use when the question is about balances, postings, arrears, or GL distribution.

### Usage
```text
CI_ACCT -> CI_SA -> C1_USAGE -> D1_USAGE -> D1_USAGE_PERIOD_SQ
```
Use when the question is about processed usage, usage volume, or usage lifecycle.

### Meter
```text
CI_SP -> D1_INSTALL_EVT -> D1_DVC_CFG -> D1_DVC
```
Use when the question is about which device was installed where and when.

### Field Ops
```text
CI_SP -> D1_ACTIVITY
```
Use when the question is about appointments, field work, status, or aging.

## 3. Inclusion and Exclusion Logic

### If you start from `CI_BSEG`
Includes:
- actual billed rows
- bill-period facts

Excludes:
- expected but unbilled service agreements
- payments unless you bridge to finance

### If you start from `CI_FT`
Includes:
- transaction-level financial impact
- debt and posting context

Excludes:
- bill presentation logic
- usage quantities unless bridged carefully

### If you start from `D1_USAGE`
Includes:
- processed usage rows
- usage status and timing

Excludes:
- raw inbound measurements unless joined explicitly
- finished billing outcomes unless bridged explicitly

### If you start from `CI_ACCT`
Includes:
- the account population

Excludes:
- service-level, billed, or usage detail unless you add those joins

## 4. Row Grain Rules

### Rule 1
Always state the intended grain in one sentence before you write SQL.

Examples:
- one row per account
- one row per active service agreement
- one row per bill segment
- one row per financial transaction
- one row per usage transaction

### Rule 2
Do not mix detailed children from multiple chains without aggregation.

Common failure:
- joining `CI_BSEG`, `CI_BSEG_SQ`, `CI_BSEG_CALC_LN`, and `CI_FT` directly, then summing amounts

### Rule 3
Optional enrichment should usually be `LEFT JOIN`, not `INNER JOIN`.

### Rule 4
High-volume fact tables should be filtered early.

## 5. Common Status Logic

### Active SA
```sql
NULLIF(TRIM(SA.SA_STATUS_FLG), '') = '20'
```

### Processed usage
```sql
C1_USAGE.BO_STATUS_CD = 'BD-PROC'
AND D1_USAGE.BO_STATUS_CD = 'SENT'
```

### Frozen financial transactions
```sql
FT.FREEZE_SW = 'Y'
```

### Arrears-eligible transactions
```sql
FT.NOT_IN_ARS_SW = 'N'
AND FT.ARS_DT IS NOT NULL
```

## 6. Workstream Quick Study Notes

### Billing
- first learn `CI_BILL`, `CI_BSEG`, `CI_FT`
- ask: who billed, what billed, what failed, what is missing

### Cashiering
- first learn `CI_PAY_EVENT`, `CI_PAY_TNDR`, `CI_DEP_CTL`
- ask: did money come in, and is it controlled/reconciled

### Customer Ops
- first learn `CI_ACCT`, `CI_PER`, `CI_PER_NAME`, `CI_ACCT_ALERT`
- ask: who is the customer, and what should a rep know before acting

### Debt Management
- first learn `CI_FT`, `CI_COLL_PROC`, `C1_PA_RQST`
- ask: what debt exists, how old is it, and what process is treating it

### Finance
- first learn `CI_FT`, `CI_FT_GL`, `CI_ADJ`
- ask: what posted, what distributed, and what is missing

### Meter Ops
- first learn `D1_DVC`, `D1_INSTALL_EVT`, `C1_USAGE`, `D1_USAGE`
- ask: which device is where, what reads/usage processed, what failed

### Field Ops
- first learn `D1_ACTIVITY`, `CI_SP`
- ask: what work is open, aging, canceled, or completed

## 7. Safe SQL Habits
1. Pick the fact table that matches the business question.
2. Filter early on date and status.
3. Keep lookups and optional enrichments outer-joined.
4. Aggregate detail before crossing workstreams.
5. Validate row counts after every major join.
6. Use read-only patterns only in this repo's reporting workflow.

## 8. Recommended Learning Order
1. `CI_ACCT`, `CI_SA`, `CI_SP`
2. `CI_BSEG`, `CI_BILL`, `CI_FT`
3. `C1_USAGE`, `D1_USAGE`, `D1_USAGE_PERIOD_SQ`
4. `D1_INSTALL_EVT`, `D1_DVC_CFG`, `D1_DVC`
5. `CI_LOOKUP_VAL`, `CI_PREM`
6. `CI_COLL_PROC`, `C1_PA_RQST`, `D1_ACTIVITY`

## 9. Short Self-Test
You should be able to answer these without notes:
1. What is the difference between account, service agreement, and service point?
2. Why is `CI_BSEG` often a better billing fact than `CI_BILL`?
3. Why is `CI_FT` often the right finance fact?
4. What does starting from `D1_USAGE` exclude?
5. Why can optional joins break a report if they use `INNER JOIN`?
6. What does one row represent in your current query?

## 10. Source Alignment
- `output/workstream_reporting_dictionary.json`
- `knowledge_base/c2m_cisadm/cisadm_core_model.md`
- `knowledge_base/oracle_c2m_query_patterns.md`
- `knowledge_base/c2m_cisadm/performance_playbook.md`
- `docs/sql_quality_workflow.md`
