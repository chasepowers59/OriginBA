# Debt Management Snapshot Workspace

This folder is for standardizing debt-management reporting into snapshot-backed, grain-safe artifacts instead of one large mixed-grain domain.

Each active debt snapshot subfolder also carries its matching end-user Domain XML copy so SQL, QA, and Domain artifacts stay together.

## Recommended snapshot family

### 1. Account debt snapshot
- Proposed table: `CISADM.ACCT_DEBT_RPT_CURR`
- Grain: one row per `ACCT_ID`
- Purpose:
  - current aged debt exposure by account
  - collection class / credit review prioritization
  - account-level outreach queueing

Primary financial truth should come from `CI_FT` arrears logic:
- `FREEZE_SW = 'Y'`
- `NOT_IN_ARS_SW = 'N'`
- `FT_TYPE_FLG NOT IN ('PS', 'PX')`
- `ARS_DT IS NOT NULL`

This is the best high-level debt fact because debt aging is financial truth, while process tables are operational overlays.

### 2. Collection process snapshot
- Proposed table: `CISADM.COLL_PROC_RPT_CURR`
- Grain: one row per `COLL_PROC_ID`
- Purpose:
  - operational status of collections workflows
  - process start / status / arrears-at-trigger reporting
  - account and SA linkage through `CI_COLL_PROC_SA`

### 3. Payment arrangement snapshot
- Proposed table: `CISADM.PA_RQST_RPT_CURR`
- Grain: one row per `PA_RQST_ID`
- Purpose:
  - payment arrangement request volume, amount, status, and outcome
  - arrangement pipeline and eligibility/result monitoring

### 4. Write-off snapshot
- Proposed table: `CISADM.WO_PROC_RPT_CURR`
- Grain: one row per `WO_PROC_ID`
- Purpose:
  - write-off process status, timing, exposure, and recovery tracking

Prefer `C1_BI_WOPROC_VW` when it is populated and tenant-valid because it is already a write-off-focused BI shape.

### 5. Severance / agency child snapshots
- Build only if the tenant actually uses them and the tables are populated.
- These are not the best first debt-management snapshot because they are usually process-specific, optional, and often client-configured differently.

## Why this structure is safer

Debt management mixes at least three different business grains:
- account debt exposure
- process objects such as collection / write-off / severance
- child links such as SA, agency reference, or related-object tables

Trying to force those into one rowset creates the same fan-out and misuse risks seen in older billing and meter domains.

## First step

Run `00a_config_discovery_validation.sql` to determine:
- which process tables are populated in this tenant
- whether `C1_BI_WOPROC_VW` is usable
- whether collection agency and severance objects are active enough to model now
- whether account-level debt should be the first snapshot to build

## Recommended first implementation

Build `ACCT_DEBT_RPT_CURR` first.

Reason:
- it gives the highest-level debt view the business expects
- it uses the most trustworthy arrears truth from `CI_FT`
- it can later be joined conceptually to collections, payment arrangements, and write-off process snapshots without forcing them into one grain

## Implemented account snapshot

- `acct_debt/01_create_snapshot_table.sql`
- `acct_debt/02_refresh_snapshot_procedure.sql`
- `acct_debt/03_schedule_snapshot_job.sql`
- `acct_debt/04_validation_queries.sql`
- `acct_debt/ACCT_DEBT_RPT_CURR_End_User_Friendly.xml`

## Implemented collection-process snapshot

- `coll_proc/01_create_snapshot_table.sql`
- `coll_proc/02_refresh_snapshot_procedure.sql`
- `coll_proc/03_schedule_snapshot_job.sql`
- `coll_proc/04_validation_queries.sql`
- `coll_proc/COLL_PROC_RPT_CURR_End_User_Friendly.xml`
