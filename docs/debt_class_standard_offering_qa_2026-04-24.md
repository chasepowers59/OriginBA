# Debt Class Standard Offering QA

Date: `2026-04-24`

## Purpose

This document records the current QA position for the active SmartCity debt
management report:

- `Arrears by Debt Class`

The goal is to determine whether the report should continue to rely on a live
Domain or whether the governed debt snapshot path is now the better standard
offering foundation.

This is not part of the current active 7-snapshot implementation scope. It is a
deferred standard-offering note for future debt-management work.

## Scope Clarification

This QA pass reflects the current business clarification that:

- `M-Side - Domain` is no longer part of the active standard offering
- `C-Side - Domain` is no longer part of the active standard offering
- debt class remains the active caution item that still needs evidence-backed
  positioning

## Approach

The repo points in two directions for debt-class reporting:

- older standard-offering documents still list `Arrears by Debt Class` as an
  `Existing Domain` / `Live Domain` report
- governed debt-management artifacts point to `ACCT_DEBT_RPT_CURR` as the
  intended account-debt truth layer for debt-class analysis

Because of that conflict, the QA approach was:

1. inspect the governed debt snapshot design and usage guidance
2. verify whether `ACCT_DEBT_RPT_CURR` is actually fresh and operational in the
   database
3. compare snapshot totals and debt-class distribution to the current governed
   source logic
4. decide whether the standard offering should keep the live-domain position,
   or move to the snapshot-backed position

## Evidence Gathered

### 1. Governed design intent

The repo consistently describes `ACCT_DEBT_RPT_CURR` as the account-debt truth
layer for debt segmentation:

- [docs/debt_mgmt_acct_debt_adhoc_recipes.md](/Users/chase/OriginBA-3/docs/debt_mgmt_acct_debt_adhoc_recipes.md)
- [sql/performance/snapshots/debt_mgmt/acct_debt/README.md](/Users/chase/OriginBA-3/sql/performance/snapshots/debt_mgmt/acct_debt/README.md)
- [sql/performance/snapshots/docs/debt_mgmt_acct_debt_snapshot.md](/Users/chase/OriginBA-3/sql/performance/snapshots/docs/debt_mgmt_acct_debt_snapshot.md)

That governed design has:

- grain: one row per `ACCT_ID`
- additive measure: `TOTAL_DEBT`
- debt-class profile fields:
  - `DEBT_CL_COUNT`
  - `SOLE_DEBT_CL_CD`
  - `SOLE_DEBT_CL_DESC`

This is a safer standard-offering shape than a bespoke live-domain aggregate,
because the grain and additive truth are explicit.

### 2. Current database state

Read-only checks against the current database returned:

- `ACCT_DEBT_RPT_CURR` live row count: `11,452`
- `MIN(LOAD_DTTM) = MAX(LOAD_DTTM) = 2026-04-08 12:50:12.670499`
- no rows returned from `ALL_SCHEDULER_JOBS` for
  `JOB_REFRESH_ACCT_DEBT_RPT_CURR`
- no recent rows returned from `ALL_SCHEDULER_JOB_RUN_DETAILS` for
  `JOB_REFRESH_ACCT_DEBT_RPT_CURR`

Interpretation:

- the snapshot exists
- the snapshot is not fresh relative to `2026-04-24`
- the snapshot does not appear to be an active scheduled asset in this
  environment

### 3. Snapshot-side QA

Read-only validation on `CISADM.ACCT_DEBT_RPT_CURR` returned:

- row count: `11,452`
- total debt: `185,657,295.62`
- duplicate `ACCT_ID` rows: `0`

Current snapshot debt-class profile:

| Debt Class Count | Sole Debt Class Code | Sole Debt Class Description | Account Count | Total Debt |
|---|---|---|---:|---:|
| `1` | `STD` | `Standard utility debt` | `5,825` | `110,599,603.51` |
| `2` | `NULL` | `NULL` | `4,397` | `72,358,077.58` |
| `3` | `NULL` | `NULL` | `1,175` | `2,634,976.38` |
| `1` | `N/A` | `No collection/severance` | `48` | `63,117.15` |
| `1` | `DEP` | `Deposit` | `7` | `1,521.00` |

Interpretation:

- the snapshot grain is intact
- debt-class fields are behaving as designed
- multi-class accounts intentionally leave `SOLE_DEBT_CL_*` blank

### 4. Current source parity

The current governed source logic was rebuilt read-only from:

- `CI_FT`
- active `CI_SA`
- `CI_SA_TYPE`
- `CI_DEBT_CL_L`

Current source parity result:

- account count: `11,450`
- total debt: `185,652,259.36`

Current source debt-class profile:

| Debt Class Count | Sole Debt Class Code | Sole Debt Class Description | Account Count | Total Debt |
|---|---|---|---:|---:|
| `1` | `STD` | `Standard utility debt` | `5,822` | `110,585,938.99` |
| `2` | `NULL` | `NULL` | `4,397` | `72,355,821.21` |
| `3` | `NULL` | `NULL` | `1,176` | `2,645,861.01` |
| `1` | `N/A` | `No collection/severance` | `48` | `63,117.15` |
| `1` | `DEP` | `Deposit` | `7` | `1,521.00` |

## Findings

### 1. No evidence of a structural debt-class logic defect

The snapshot shape and the current source shape are very close:

- snapshot account count delta vs source: `+2`
- snapshot total debt delta vs source: `+5,036.26`

That is very small relative to total debt of approximately `185.7M`.

This indicates:

- no obvious fan-out defect
- no duplicate-account defect
- no obvious debt-class derivation failure

### 2. The problem is freshness, not grain

The meaningful issue is operational:

- `ACCT_DEBT_RPT_CURR` is stale
- its scheduler metadata is not active in this environment

So the governed debt snapshot is conceptually the right standard-offering
artifact for debt-class reporting, but it is not currently fresh enough to be
presented as the active governed delivery path in this environment.

### 3. The live-domain listing is likely a current-state deployment label, not the best target-state design

Given the governed debt artifacts already in the repo, the most defensible
target-state position is:

- use `ACCT_DEBT_RPT_CURR` as the standard offering debt-class foundation

But the most honest current-state position is:

- the currently listed `Arrears by Debt Class` live-domain report may still be
  the deployed operational report today
- however, it should be treated as a transitional current-state artifact until
  the governed debt snapshot is refreshed and scheduled

## Recommendation

### Current-state recommendation

Keep `Arrears by Debt Class` in the standard offering, but document it as:

- currently delivered from an existing/live semantic-layer artifact
- pending migration to the governed `ACCT_DEBT_RPT_CURR` layer

### Target-state recommendation

Move debt-class reporting to `ACCT_DEBT_RPT_CURR` after:

1. the snapshot is manually refreshed
2. the validation pack in
   [04_validation_queries.sql](/Users/chase/OriginBA-3/sql/performance/snapshots/debt_mgmt/acct_debt/04_validation_queries.sql)
   passes again in the target environment
3. scheduler ownership for `JOB_REFRESH_ACCT_DEBT_RPT_CURR` is restored

## Why This Is The Right Approach

- It preserves the active standard offering without pretending the governed
  debt snapshot is already operational when it is not.
- It aligns the target-state design to the safer account-debt grain already
  built in the repo.
- It avoids over-investing in a bespoke live-domain aggregate when the governed
  replacement path already exists.

## Validation Checks Used

Read-only checks run for this QA:

1. snapshot row count and `LOAD_DTTM`
2. scheduler/job metadata check for `JOB_REFRESH_ACCT_DEBT_RPT_CURR`
3. duplicate `ACCT_ID` check in `ACCT_DEBT_RPT_CURR`
4. snapshot debt-class profile
5. source reconstructed debt-account and debt-class profile

## Next Actions

1. keep M-Side and C-Side out of active standard-offering QA scope
2. keep debt-management outside the current active 7-snapshot implementation
   track unless explicitly revived
3. when you are ready to resume debt-management work, manually refresh
   `ACCT_DEBT_RPT_CURR` and run its full
   QA pack before treating debt-class reporting as governed standard content
