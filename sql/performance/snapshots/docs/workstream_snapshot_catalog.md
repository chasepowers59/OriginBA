# Workstream Snapshot Catalog

## Purpose
This document is the governed catalog for the snapshot-backed reporting assets in this repository.

It answers four practical questions:
- which workstreams currently have standardized snapshots
- what grain each snapshot uses
- which additive measures are trusted at that grain
- which workstreams still need a first governed snapshot

Use this as the top-level navigation document before opening the individual snapshot docs.

## Scope
This catalog covers the current snapshot workspaces under `sql/performance/snapshots/` and the business-facing docs that explain them.

It does not replace the deeper per-snapshot docs. Instead, it tells you which artifact to use first and where to go next.

For client-facing use cases, example Standard Offering reports, population/status scope, and workstream chooser guidance, see:
- `sql/performance/snapshots/docs/snapshot_client_reporting_guide.md`

For the repeatable process of converting an older manual Domain into one of these governed snapshots, see:
- `sql/performance/snapshots/docs/legacy_domain_to_snapshot_modernization_playbook.md`
- `sql/performance/snapshots/docs/snapshot_modernization_checklist.md`

For the importable Domain XML files behind these snapshots, see:
- `sql/performance/snapshots/docs/snapshot_xml_inventory.md`

## Snapshot Coverage Matrix

| Workstream | Snapshot | Grain | Trusted additive measure | Primary use |
| --- | --- | --- | --- | --- |
| `billing` | `BSEG_BILLED_USAGE_RPT_CURR` | one row per `BSEG_ID` | `TOTAL_BILL_SQ` | billed usage and billed amount at bill-segment grain |
| `billing` | `BSEG_SQ_USAGE_RPT_CURR` | one row per determinant key on a bill segment | `TOTAL_BILL_SQ` | billed quantity by `UOM / TOU / SQI` |
| `finance` | `FT_RPT_CURR` | one row per `FT_ID` | `CUR_AMT` | FT header reporting and trace analysis |
| `finance` | `FT_GL_DISTRIBUTION_RPT_CURR` | one row per `FT_ID`, `GL_SEQ_NBR` | `GL_AMOUNT` | GL account and distribution-code analysis |
| `debt_mgmt` | `ACCT_DEBT_RPT_CURR` | one row per `ACCT_ID` | `TOTAL_DEBT` | account-level debt exposure |
| `debt_mgmt` | `COLL_PROC_RPT_CURR` | one row per `COLL_PROC_ID` | context only, not debt truth | collection-process workflow monitoring |
| `meter_ops` | `D1_USAGE_RPT_CURR` | one row per `D1_USAGE_ID` | count of `D1_USAGE_ID` | usage-process monitoring |
| `meter_ops` | `D1_USAGE_SCALAR_DTL_RPT_CURR` | one row per `D1_USAGE_ID`, `SEQ_NUM` | `QUANTITY`, `FINAL_QUANTITY` | scalar quantity analysis |
| `meter_ops` | `D1_MSRMT_RPT_CURR` | one row per final processed measurement | measurement value fields | final measurement analysis |
| `payments_cashiering` | `PAY_TNDR_CASH_RPT_CURR` | one row per `PAY_TENDER_ID` | `TENDER_AMT` | payment intake and cashiering analysis |

## Current workstream status

| Workstream | Snapshot status | Notes |
| --- | --- | --- |
| `billing` | implemented | two production-style billed-usage snapshots exist |
| `finance` | implemented | FT header and FT GL line snapshots both exist |
| `debt_mgmt` | partially implemented | account debt and collection process are implemented; payment arrangement and write-off snapshots are still future-state |
| `meter_ops` | implemented | usage header, usage scalar detail, and final measurement snapshots exist |
| `payments_cashiering` | partially implemented | tender-centered snapshot exists; lower-grain payment application snapshots are still future-state |
| `cashiering` | represented through `payments_cashiering` | business-facing workstream name is cashiering; implementation folder is `payments_cashiering` |
| `common` | no governed snapshot yet | current coverage is mostly reference and enrichment oriented |
| `customer_ops` | no governed snapshot yet | current coverage is mostly report and domain oriented |
| `field_ops` | no governed snapshot yet | current coverage is report and operational SQL oriented |
| `field_tasks` | no governed snapshot yet | current coverage is workstream vocabulary and routing context, not a standardized snapshot |
| `new_services` | no governed snapshot yet | current coverage is planning and semantic-layer guidance rather than snapshot SQL |

## How to choose the right snapshot

### Start with grain
- If the question is about a finished bill segment, start in billing.
- If the question is about a financial transaction header, start in `FT_RPT_CURR`.
- If the question is about GL distribution detail, start in `FT_GL_DISTRIBUTION_RPT_CURR`.
- If the question is about current debt by account, start in `ACCT_DEBT_RPT_CURR`.
- If the question is about process workflow in collections, start in `COLL_PROC_RPT_CURR`.
- If the question is about usage processing, start in `D1_USAGE_RPT_CURR`.
- If the question is about scalar quantities, start in `D1_USAGE_SCALAR_DTL_RPT_CURR`.
- If the question is about final processed measurements, start in `D1_MSRMT_RPT_CURR`.
- If the question is about payment intake channel or tender operations, start in `PAY_TNDR_CASH_RPT_CURR`.

### Then confirm the additive measure
- Segment usage totals belong to the billed-usage snapshots.
- FT header dollars belong to `CUR_AMT` in `FT_RPT_CURR`.
- GL totals belong to `GL_AMOUNT` in `FT_GL_DISTRIBUTION_RPT_CURR`.
- Debt totals belong to `TOTAL_DEBT` in `ACCT_DEBT_RPT_CURR`.
- Tender totals belong to `TENDER_AMT` in `PAY_TNDR_CASH_RPT_CURR`.

### Then confirm what the snapshot is not
- Do not use FT header rows for GL line totals.
- Do not use collection-process rows for account debt truth.
- Do not use usage-header rows for scalar quantity totals.
- Do not use tender rows for exact payment-application detail.

## Workstream-by-workstream reference

## `billing`
### Business meaning
Billing is the workstream for completed bill segments, billed quantities, billed amount context, and billing-cycle performance.

### Implemented snapshots
`BSEG_BILLED_USAGE_RPT_CURR`
- Grain: one row per completed `BSEG_ID`
- Best for: billed usage and billed amount at segment grain
- Trusted measure: `TOTAL_BILL_SQ`
- Detailed doc: `sql/performance/snapshots/docs/billing_bseg_billed_usage_snapshot.md`
- XML artifact: `domains/exports/manual_imports/BSEG_BILLED_USAGE_RPT_CURR_End_User_Friendly.xml`
- SQL workspace: `sql/performance/snapshots/billed_usage/bseg_billed_usage/`

`BSEG_SQ_USAGE_RPT_CURR`
- Grain: one row per determinant key on a completed bill segment
- Best for: quantity analysis by `UOM / TOU / SQI`
- Trusted measure: `TOTAL_BILL_SQ`
- Detailed doc: `sql/performance/snapshots/docs/billing_bseg_sq_usage_snapshot.md`
- XML artifact: `domains/exports/manual_imports/BSEG_SQ_USAGE_RPT_CURR_End_User_Friendly.xml`
- SQL workspace: `sql/performance/snapshots/billed_usage/bseg_sq_usage/`

### Key artifact choice
- Use the segment snapshot when the business question is bill-segment-level.
- Use the determinant snapshot when the business question is unit-family or determinant-level quantity.

### Current gaps
- No dedicated governed calc-line billed-revenue snapshot exists yet in the snapshot workspace.
- Billing verification and cycle reconciliation remain report and SQL assets rather than standardized snapshot tables.

## `finance`
### Business meaning
Finance is the workstream for financial transaction truth, GL distribution detail, and accounting-facing reporting.

### Implemented snapshots
`FT_RPT_CURR`
- Grain: one row per `FT_ID`
- Best for: FT counts, amounts, status monitoring, adjustment trace, payment-linked FT analysis
- Trusted measure: `CUR_AMT`
- Detailed doc: `sql/performance/snapshots/docs/finance_ft_rpt_curr_snapshot.md`
- XML artifact: `domains/exports/manual_imports/FT_RPT_CURR_End_User_Friendly.xml`
- SQL workspace: `sql/performance/snapshots/finance/ft_rpt_curr/`

`FT_GL_DISTRIBUTION_RPT_CURR`
- Grain: one row per `FT_ID`, `GL_SEQ_NBR`
- Best for: GL account analysis, distribution-code analysis, FT-to-GL trace
- Trusted measures: `GL_AMOUNT`, `STATISTIC_AMOUNT`
- Detailed doc: `sql/performance/snapshots/docs/finance_ft_gl_distribution_snapshot.md`
- XML artifact: `domains/exports/manual_imports/FT_GL_DISTRIBUTION_RPT_CURR_End_User_Friendly.xml`
- SQL workspace: `sql/performance/snapshots/finance/ft_gl_distribution/`

### Key artifact choice
- If you need unduplicated FT header totals, use `FT_RPT_CURR`.
- If you need chart-of-accounts detail, use `FT_GL_DISTRIBUTION_RPT_CURR`.

### Current gaps
- No separate standardized fund-balance snapshot exists in `sql/performance/snapshots/`; current fund-balance assets are still broader SQL/domain designs.

## `debt_mgmt`
### Business meaning
Debt management is the workstream for overdue debt truth, collections process monitoring, and recovery-oriented segmentation.

### Implemented snapshots
`ACCT_DEBT_RPT_CURR`
- Grain: one row per `ACCT_ID`
- Best for: total debt exposure, aging buckets, collections segmentation
- Trusted measure: `TOTAL_DEBT`
- Detailed doc: `sql/performance/snapshots/docs/debt_mgmt_acct_debt_snapshot.md`
- XML artifact: `domains/exports/manual_imports/ACCT_DEBT_RPT_CURR_End_User_Friendly.xml`
- SQL workspace: `sql/performance/snapshots/debt_mgmt/acct_debt/`

`COLL_PROC_RPT_CURR`
- Grain: one row per `COLL_PROC_ID`
- Best for: collections workload, next event monitoring, process status views
- Trusted debt note: `ARS_AMT` is process context, not replacement debt truth
- Detailed doc: `sql/performance/snapshots/docs/debt_mgmt_coll_proc_snapshot.md`
- XML artifact: `domains/exports/manual_imports/COLL_PROC_RPT_CURR_End_User_Friendly.xml`
- SQL workspace: `sql/performance/snapshots/debt_mgmt/coll_proc/`

### Key artifact choice
- Use `ACCT_DEBT_RPT_CURR` for "how much debt exists".
- Use `COLL_PROC_RPT_CURR` for "what collections process activity is happening".

### Current gaps
- Payment arrangement snapshot is still recommended but not implemented.
- Write-off snapshot is still recommended but not implemented.
- Severance and agency-child snapshots are still recommended but not implemented.

## `meter_ops`
### Business meaning
Meter operations is the workstream for processed measurements, usage transactions, scalar quantities, devices, and billing bridge behavior.

### Implemented snapshots
`D1_USAGE_RPT_CURR`
- Grain: one row per `D1_USAGE_ID`
- Best for: usage-process monitoring and subscription/billing bridge context
- Trusted KPI: count of usage transactions
- Detailed doc: `sql/performance/snapshots/docs/meter_ops_d1_usage_snapshot.md`
- XML artifact: `domains/exports/manual_imports/D1_USAGE_RPT_CURR_End_User_Friendly.xml`
- SQL workspace: `sql/performance/snapshots/meter_ops/d1_usage/`

`D1_USAGE_SCALAR_DTL_RPT_CURR`
- Grain: one row per `D1_USAGE_ID`, `SEQ_NUM`
- Best for: determinant and quantity analysis
- Trusted measures: `QUANTITY`, `FINAL_QUANTITY`
- Detailed doc: `sql/performance/snapshots/docs/meter_ops_d1_usage_scalar_snapshot.md`
- XML artifact: `domains/exports/manual_imports/D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml`
- SQL workspace: `sql/performance/snapshots/meter_ops/d1_usage_scalar_dtl/`

`D1_MSRMT_RPT_CURR`
- Grain: one row per final processed measurement
- Best for: final accepted measurement history and service-point/device measurement context
- Detailed doc: `sql/performance/snapshots/docs/meter_ops_final_measurement_snapshot.md`
- XML artifact: `domains/exports/manual_imports/D1_MSRMT_RPT_CURR_End_User_Friendly.xml`
- SQL workspace: `sql/performance/snapshots/meter_ops/d1_msrmt/`

### Key artifact choice
- Use the usage-header snapshot for process monitoring.
- Use the scalar-detail snapshot for quantity analysis.
- Use the measurement snapshot for final accepted measurement history.

### Current gaps
- No separate governed device-install-event snapshot exists yet.
- D1 activity and field-operations coverage is still outside the snapshot family.

## `payments_cashiering`
### Business meaning
This is the tender and payment-intake workstream. In business-facing language it overlaps the `cashiering` workstream in the vocabulary guide.

### Implemented snapshot
`PAY_TNDR_CASH_RPT_CURR`
- Grain: one row per `PAY_TENDER_ID`
- Best for: payment channel mix, tender source reporting, OriginPay analysis, deposit-control context
- Trusted measure: `TENDER_AMT`
- Detailed doc: `sql/performance/snapshots/docs/payments_cashiering_pay_tndr_cash_snapshot.md`
- XML artifact: `domains/exports/manual_imports/PAY_TNDR_CASH_RPT_CURR_End_User_Friendly.xml`
- SQL workspace: `sql/performance/snapshots/payments_cashiering/pay_tndr_cashier/`

### Key artifact choice
- Use this snapshot for tender-centered intake analysis.
- Do not use it as row-per-payment-application detail.

### Current gaps
- No dedicated pay-segment application snapshot exists yet.
- No finance-style FT/GL payment reconciliation snapshot exists yet inside this workstream.

## `common`
### Business meaning
Common covers shared reference and platform-level objects used across multiple workstreams.

### Snapshot status
No governed snapshot workspace currently exists.

### Existing documentation anchors
- `docs/cisadm_workstream_vocabulary_guide.md`
- `docs/semantic-layer.md`
- `docs/report-lookup-coverage-matrix.md`

### Likely future snapshot candidates
- reference-data quality snapshot
- premise and geography readiness snapshot
- migration or deployment-control status snapshot

## `customer_ops`
### Business meaning
Customer operations covers account, person, contact, alert, approval, and outbound communication context.

### Snapshot status
No governed snapshot workspace currently exists.

### Existing documentation anchors
- `docs/cisadm_workstream_vocabulary_guide.md`
- `reports/customer_contact_print_check.jrxml`
- `docs/bill_templating_playbook.md`

### Likely future snapshot candidates
- account-contact readiness snapshot
- approval and alert queue snapshot
- outbound correspondence readiness snapshot

## `field_ops`
### Business meaning
Field operations covers field activities tied to service points and operational work execution.

### Snapshot status
No governed snapshot workspace currently exists.

### Existing documentation anchors
- `docs/cisadm_workstream_vocabulary_guide.md`
- `reports/field_activity_operational_intelligence.jrxml`
- `reports/field_ops_action_queue.jrxml`

### Likely future snapshot candidates
- field activity header snapshot
- field activity aging and SLA snapshot

## `field_tasks`
### Business meaning
Field tasks is the lighter task-log and task-workload layer behind operations.

### Snapshot status
No governed snapshot workspace currently exists.

### Existing documentation anchors
- `docs/cisadm_workstream_vocabulary_guide.md`
- `docs/semantic-layer.md`

### Likely future snapshot candidates
- task workload snapshot
- task aging and assignment snapshot

## `new_services`
### Business meaning
New services covers onboarding, start-service movement, and early lifecycle readiness before usage and billing stabilize.

### Snapshot status
No governed snapshot workspace currently exists.

### Existing documentation anchors
- `docs/cisadm_workstream_vocabulary_guide.md`
- `docs/semantic-layer.md`
- `docs/smartcity_9_workstream_product_plan.md`

### Likely future snapshot candidates
- start-service pipeline snapshot
- onboarding-to-first-bill readiness snapshot

## Related documentation
- `docs/cisadm_workstream_vocabulary_guide.md`
- `docs/smartcity_9_workstream_product_plan.md`
- `sql/performance/README.md`
- `sql/performance/snapshots/README.md`

## Maintenance rule
Whenever a new governed snapshot is added:
1. Add the SQL workspace under `sql/performance/snapshots/<workstream>/<subset>/`.
2. Add or update the business-facing doc in `docs/`.
3. Update this catalog so workstream coverage stays explicit.
