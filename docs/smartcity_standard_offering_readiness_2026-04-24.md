# SmartCity Standard Offering Readiness

Date: `2026-04-24`

## Purpose

This document consolidates the current operational evidence for the SmartCity
 standard offering:

- active snapshot runtime and freshness status
- live-domain structural readiness
- current report-library strengths and gaps
- prioritized next actions for QA and offering buildout

It is intended to support both delivery planning and client-facing packaging of
the standard offering.

Current scope clarification:

- the active implementation and runtime optimization program is the current
  7-snapshot family only
- debt-management snapshots are not part of the active implementation scope
- cashiering is not part of the active snapshot implementation scope

## Snapshot Runtime Status

Current active 7-snapshot scheduler evidence was refreshed from the live
 database on `2026-04-24`.

### Latest observed active runtimes

| Workstream | Snapshot | Latest Start | Run Duration | Run Minutes | Current position |
|---|---|---|---:|---:|---|
| finance | `FT_RPT_CURR` | `2026-04-24 13:00:00` | `0:03:13` | `3.22` | healthy |
| billing | `BSEG_BILLED_USAGE_RPT_CURR` | `2026-04-24 07:30:00` | `0:05:01` | `5.02` | healthy; rolling window promoted |
| billing | `BSEG_SQ_USAGE_RPT_CURR` | `2026-04-24 08:00:00` | `0:05:37` | `5.62` | healthy; rolling window promoted |
| meter_ops | `D1_MSRMT_RPT_CURR` | `2026-04-24 08:30:00` | `0:04:06` | `4.10` | healthy |
| finance | `FT_GL_DISTRIBUTION_RPT_CURR` | `2026-04-24 09:00:00` | `0:11:38` | `11.63` | still the heaviest current scheduled refresh |
| meter_ops | `D1_USAGE_RPT_CURR` | `2026-04-24 09:30:00` | `0:09:31` | `9.52` | healthy |
| meter_ops | `D1_USAGE_SCALAR_DTL_RPT_CURR` | `2026-04-24 10:00:00` | `0:07:31` | `7.52` | healthy |

### Runtime interpretation

- All 7 active scheduler jobs are enabled, scheduled, and succeeded on the
  latest observed cycle.
- The current stagger remains operationally safe.
- `FT_GL_DISTRIBUTION_RPT_CURR` is still the longest active scheduled refresh
  and should remain a watch item.
- The two BSEG snapshots are now part of the active rolling-window family and
  no longer need to be treated as full-refresh-only exceptions.

### Freshness interpretation

Latest row-count and `LOAD_DTTM` evidence shows:

- billing snapshots are fresh after `2026-04-24` cutover validation
- finance and meter snapshots are refreshing on current cadence
- debt-management and payments snapshots remain stale relative to the active 7
  snapshot family because they are not currently part of the active stagger
- those debt-management and payments snapshots should be treated as inactive
  relative to the current implementation track, not as active optimization
  targets

## Live Domain Readiness

The current structural assessment in:

- `docs/live_domain_fit_assessment.md`
- `docs/cashiering_live_domain_assessment.md`

supports this position.

### Safe to keep live now

- Cashiering core:
  - `Payment - Domain`
  - `Tender - Domain`
  - `Pay Plan - Domain`
  - `Deposit Control - Domain`
- Common:
  - `Batch Process - Domain`
  - `Bill Segment Exception - Domain`
  - `Usage Transaction Exception - Domain`
  - `VEE Exception - Domain`
  - `To Do - Domain`
- Customer operations:
  - `Account Alert - Domain`
  - `Case - Domain`
  - `Customer - Domain`
  - `Customer Contact - Domain`
  - `Premise - Domain`
- New services:
  - `New Services - Domain`
- Debt management:
  - `Collection Process - Domain`
  - `SA Snapshot - Domain`
  - `Severance Process - Domain`
  - `Write Off Process - Domain`
  - `Write Offs - Domain`
- Field operations:
  - `Field Activity - Domain`

### Keep only with explicit caution

- `To Do w/ Account Info - Domain`
- `Collection Process Amounts - Domain`
- `Debt Class - Domain`
- `Crew - Domain`
- `Location/Organization - Domain`

### Exclude or rebuild

- `AutoPay/Balances - Domain`
- `Payment Segments - Account View`

## Live Domain QA Priorities

These are the highest-priority live-domain QA tasks before broader standard
offering rollout.

They are not part of the current active 7-snapshot optimization track.

### Priority 1

- `Debt Class - Domain`
  - applies to active standard-offering report:
    - `Arrears by Debt Class`
  - business clarification confirmed this is the only active caution live-
    domain family still in scope
  - direct QA shows the governed replacement path should be
    `ACCT_DEBT_RPT_CURR`, but that snapshot is currently stale and not actively
    scheduled in this environment
  - keep the current report in the standard offering, but treat it as a
    transitional live-domain artifact pending governed cutover

### Priority 2

- `Field Activity - Domain`
  - run recent-slice parity on the operational KPI views used in the standard
    offering

## Standard Offering Status

The current official standard offering still documents `104` reports across
 `9` workstreams.

### Strongest workstreams now

- finance
- billing and rates
- meter operations
- cashiering
- debt management

These workstreams either have:

- governed snapshot backing
- structurally strong live domains
- or both

### Adequate but should mature

- customer operations
- common
- field operations

These have usable report families, but they still need more direct parity QA on
selected live views before being treated as fully hardened standard content.

### Biggest current offering gaps

- reference-data health / lookup governance in `common`
- customer communication readiness in `customer_ops`
- payment arrangement visibility in `debt_mgmt`
- install-event / service-point linkage exceptions in `field_ops`
- truly governed asset reporting in `meter_ops`

## Catalog Reconciliation Notes

The repo still had one older catalog that did not match the more recent live-
domain assessments and official report-library view.

The following items were inconsistent and should not be treated as active core
 standard-offering content:

- `Payment Segments - Account View`
- `AutoPay Drafts By Scheduled Date`
- `Autopay Accounts With Active Deposits`

Those were structurally rejected by the cashiering live-domain assessment and
 should remain excluded until rebuilt on a governed cashiering grain.

## Immediate Next Actions

1. Update any remaining standard-offering docs that still describe billing
   snapshots as full-refresh-only.
2. Keep `M-Side` and `C-Side` out of the active standard-offering QA path.
3. Keep debt-management and cashiering outside the current active snapshot
   implementation scope unless explicitly revived.
4. Build a narrowed client-facing `Core` versus `Secondary` standard-offering
   view from the current `104` reports.
5. Continue runtime tracking and QA hardening for the active 7 snapshots only.

## Recommended Delivery Position

For SmartCity clients today:

- present the snapshot-backed finance, billing, and meter reporting as the
  strongest governed layer
- present live-domain families selectively, based on the structural-fit
  assessments already completed
- explicitly exclude or caveat the known misleading live assets
- keep documenting direct SQL parity evidence as each live family is hardened
- treat `Arrears by Debt Class` as a transitional live-domain report until
  `ACCT_DEBT_RPT_CURR` is refreshed and operationalized
