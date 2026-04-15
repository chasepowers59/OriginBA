# FT_RPT_CURR Materialized View Cutover Runbook

## Goal
Convert `CISADM.FT_RPT_CURR` from a manually refreshed table into a materialized-view-backed reporting object without breaking:
- existing Jaspersoft Domains
- existing JRXML reports
- existing object name references
- existing scheduler job name
- existing refresh procedure name

## Current state
Today `FT_RPT_CURR` is:
- a physical table created by `01_create_snapshot_table.sql`
- refreshed by `REFRESH_FT_RPT_CURR`
- scheduled by `JOB_REFRESH_FT_RPT_CURR`

The current refresh pattern is:
- `TRUNCATE TABLE CISADM.FT_RPT_CURR`
- `INSERT INTO CISADM.FT_RPT_CURR ... SELECT ...`

## Recommended no-break pattern
Do not make the reporting object switch directly from table to materialized view under the same name on the first pass.

Use this safer compatibility pattern instead:

1. Persist the data in a new materialized view:
   - `CISADM.FT_RPT_CURR_MV`
2. Keep the consumer-facing object name stable as:
   - `CISADM.FT_RPT_CURR`
3. Recreate `CISADM.FT_RPT_CURR` as a plain view over `FT_RPT_CURR_MV`
4. Keep the procedure name:
   - `CISADM.REFRESH_FT_RPT_CURR`
5. Keep the scheduler job name:
   - `CISADM.JOB_REFRESH_FT_RPT_CURR`

That gives you:
- materialized-view storage under the hood
- stable object name for Domains and reports
- minimal scheduler/job disruption
- a cleaner rollback path

## Why this is the best first approach
If you replace the table directly with an MV of the same name:
- the cutover is more brittle
- grants may need to be recreated on the replacement object
- `LOAD_DTTM` becomes awkward because it is currently a physical column
- rollback is harder

If you use `FT_RPT_CURR_MV` plus a compatibility view:
- consumer SQL still references `CISADM.FT_RPT_CURR`
- the Domain XML does not need a resource rename
- `LOAD_DTTM` can be exposed from MV metadata
- rollback is simple: point the view back or restore the old table name

## Important compatibility note about `LOAD_DTTM`
The current Domain XML explicitly exposes `LOAD_DTTM`.

That means a direct MV rewrite must preserve a column called `LOAD_DTTM` or the Domain contract changes.

The safest approach is:
- keep `LOAD_DTTM` out of the MV storage definition
- expose it in the compatibility view from `USER_MVIEWS.LAST_REFRESH_DATE`

That turns `LOAD_DTTM` from "row insert timestamp" into "last materialized view refresh timestamp".

For this snapshot, that is usually the right meaning anyway.

## Target architecture

### Storage object
`CISADM.FT_RPT_CURR_MV`
- materialized view
- refreshed `COMPLETE ON DEMAND`
- stores the FT snapshot rows

### Consumer object
`CISADM.FT_RPT_CURR`
- standard view
- same column names used by Domains and reports
- selects from `FT_RPT_CURR_MV`
- derives `LOAD_DTTM` from MV metadata

### Refresh entry point
`CISADM.REFRESH_FT_RPT_CURR`
- thin wrapper procedure
- calls `DBMS_MVIEW.REFRESH('CISADM.FT_RPT_CURR_MV', 'C')`

### Scheduler entry point
`CISADM.JOB_REFRESH_FT_RPT_CURR`
- can keep the same job name
- can keep the same procedure target

## Cutover sequence

### Phase 0: Pre-cutover discovery
Run these first in SQL Developer.

Check whether users or reports actually reference `LOAD_DTTM`:
```sql
SELECT *
FROM cisadm.ft_rpt_curr
FETCH FIRST 5 ROWS ONLY;
```

Capture current grants:
```sql
SELECT grantee, privilege
FROM all_tab_privs
WHERE owner = 'CISADM'
  AND table_name = 'FT_RPT_CURR'
ORDER BY grantee, privilege;
```

Capture dependent objects:
```sql
SELECT owner, name, type
FROM all_dependencies
WHERE referenced_owner = 'CISADM'
  AND referenced_name = 'FT_RPT_CURR'
ORDER BY owner, name, type;
```

Capture current job definition:
```sql
SELECT owner, job_name, enabled, state, job_action, repeat_interval
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_FT_RPT_CURR';
```

Confirm current procedure text:
```sql
SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_FT_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;
```

### Phase 1: Prove the MV logic with a test name first
Before touching the live object, create a pilot MV with a temporary name in DEV.

Recommended temporary name:
- `CISADM.FT_RPT_CURR_MV_TEST`

Recommended refresh mode:
- `REFRESH COMPLETE ON DEMAND`

Do not start with fast refresh.

Use the same `SELECT` logic from the current procedure, except do not include `LOAD_DTTM` in the MV body.

The pilot goal is to prove:
- the MV compiles
- row count matches the current table
- one row per `FT_ID` is preserved
- Domains do not need any field changes once the compatibility view is added

### Phase 2: Create the real materialized view
After the pilot works, create:
- `CISADM.FT_RPT_CURR_MV`

Recommended shape:
```sql
CREATE MATERIALIZED VIEW cisadm.ft_rpt_curr_mv
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
AS
SELECT
    ft.ft_id,
    ft.ft_type_flg,
    CASE ft.ft_type_flg
        WHEN 'AD' THEN 'Adjustment'
        WHEN 'AX' THEN 'Adjustment Cancellation'
        WHEN 'BS' THEN 'Bill Segment'
        WHEN 'BX' THEN 'Bill Segment Cancellation'
        WHEN 'PS' THEN 'Pay Segment'
        WHEN 'PX' THEN 'Pay Segment Cancellation'
    END AS ft_type_flg_desc,
    ft.accounting_dt,
    ft.cre_dttm,
    ft.freeze_dttm,
    ft.freeze_user_id,
    COALESCE(NULLIF(TRIM(u.first_name || ' ' || u.last_name), ''), u.user_id) AS freeze_user_name,
    ft.cur_amt,
    ft.tot_amt,
    ft.currency_cd,
    ft.bill_id,
    ft.sa_id,
    ft.parent_id,
    ft.sibling_id,
    ft.gl_distrib_status,
    CASE ft.gl_distrib_status
        WHEN 'D' THEN 'Distributed'
        WHEN 'G' THEN 'Generated'
        WHEN 'M' THEN 'Modified'
        WHEN 'N' THEN 'Pending'
    END AS gl_distrib_status_desc,
    sa.acct_id,
    sa.sa_status_flg,
    sa_stat.descr  AS sa_status_desc,
    sa.sa_type_cd,
    sa_type.descr  AS sa_type_desc,
    acct.cust_cl_cd,
    acct.coll_cl_cd,
    acct.bill_cyc_cd,
    acct.acct_mgmt_grp_cd,
    bseg.bseg_id,
    bseg.bseg_stat_flg,
    bseg_stat.descr AS bseg_stat_desc,
    bseg.start_dt,
    bseg.end_dt,
    adj.adj_id,
    adj.adj_status_flg,
    adj_stat.descr AS adj_status_desc,
    adj.adj_type_cd,
    adj_type.descr AS adj_type_desc,
    adj.adj_amt,
    pay.pay_seg_id,
    pay.pay_id,
    pay.pay_seg_amt
FROM cisadm.ci_ft ft
LEFT JOIN cisadm.ci_sa sa
    ON sa.sa_id = ft.sa_id
LEFT JOIN cisadm.ci_acct acct
    ON acct.acct_id = sa.acct_id
LEFT JOIN cisadm.sc_user u
    ON u.user_id = ft.freeze_user_id
   AND u.language_cd = 'ENG'
LEFT JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = ft.sibling_id
   AND ft.ft_type_flg IN ('BS', 'BX')
LEFT JOIN cisadm.ci_adj adj
    ON adj.adj_id = ft.sibling_id
   AND ft.ft_type_flg IN ('AD', 'AX')
LEFT JOIN cisadm.ci_pay_seg pay
    ON pay.pay_seg_id = ft.sibling_id
   AND pay.pay_id = ft.parent_id
   AND ft.ft_type_flg IN ('PS', 'PX')
LEFT JOIN cisadm.ci_lookup_val_l sa_stat
    ON sa_stat.field_name = 'SA_STATUS_FLG'
   AND sa_stat.field_value = sa.sa_status_flg
   AND sa_stat.language_cd = 'ENG'
LEFT JOIN cisadm.ci_sa_type_l sa_type
    ON sa_type.sa_type_cd = sa.sa_type_cd
   AND sa_type.language_cd = 'ENG'
LEFT JOIN cisadm.ci_lookup_val_l bseg_stat
    ON bseg_stat.field_name = 'BSEG_STAT_FLG'
   AND bseg_stat.field_value = bseg.bseg_stat_flg
   AND bseg_stat.language_cd = 'ENG'
LEFT JOIN cisadm.ci_lookup_val_l adj_stat
    ON adj_stat.field_name = 'ADJ_STATUS_FLG'
   AND adj_stat.field_value = adj.adj_status_flg
   AND adj_stat.language_cd = 'ENG'
LEFT JOIN cisadm.ci_adj_type_l adj_type
    ON adj_type.adj_type_cd = adj.adj_type_cd
   AND adj_type.language_cd = 'ENG'
WHERE ft.redundant_sw = 'N';
```

### Phase 3: Preserve the public object name
Once the MV exists and validates, rename the current table out of the way.

Example:
```sql
ALTER TABLE cisadm.ft_rpt_curr RENAME TO ft_rpt_curr_tbl_bak_20260409;
```

Then create the compatibility view with the original name:
```sql
CREATE OR REPLACE VIEW cisadm.ft_rpt_curr AS
SELECT
    mv.ft_id,
    mv.ft_type_flg,
    mv.ft_type_flg_desc,
    mv.accounting_dt,
    mv.cre_dttm,
    mv.freeze_dttm,
    mv.freeze_user_id,
    mv.freeze_user_name,
    mv.cur_amt,
    mv.tot_amt,
    mv.currency_cd,
    mv.bill_id,
    mv.sa_id,
    mv.parent_id,
    mv.sibling_id,
    mv.gl_distrib_status,
    mv.gl_distrib_status_desc,
    mv.acct_id,
    CAST(meta.last_refresh_date AS TIMESTAMP) AS load_dttm,
    mv.sa_status_flg,
    mv.sa_status_desc,
    mv.sa_type_cd,
    mv.sa_type_desc,
    mv.cust_cl_cd,
    mv.coll_cl_cd,
    mv.bill_cyc_cd,
    mv.acct_mgmt_grp_cd,
    mv.bseg_id,
    mv.bseg_stat_flg,
    mv.bseg_stat_desc,
    mv.start_dt,
    mv.end_dt,
    mv.adj_id,
    mv.adj_status_flg,
    mv.adj_status_desc,
    mv.adj_type_cd,
    mv.adj_type_desc,
    mv.adj_amt,
    mv.pay_seg_id,
    mv.pay_id,
    mv.pay_seg_amt
FROM cisadm.ft_rpt_curr_mv mv
CROSS JOIN (
    SELECT last_refresh_date
    FROM user_mviews
    WHERE mview_name = 'FT_RPT_CURR_MV'
) meta;
```

That keeps the consumer-facing object name and field list stable.

## Refresh procedure rewrite
Keep the same procedure name, but change the internals.

New procedure pattern:
```sql
CREATE OR REPLACE PROCEDURE cisadm.refresh_ft_rpt_curr AS
BEGIN
    DBMS_MVIEW.REFRESH(
        list            => 'CISADM.FT_RPT_CURR_MV',
        method          => 'C',
        atomic_refresh  => TRUE
    );
END;
/
```

Why keep the same name:
- existing scheduler jobs can stay pointed at `REFRESH_FT_RPT_CURR`
- operational runbooks remain mostly valid
- support staff do not need a new procedure name

## Scheduler job handling
Best case:
- keep `JOB_REFRESH_FT_RPT_CURR` unchanged
- it still calls `CISADM.REFRESH_FT_RPT_CURR`

That means you may only need to replace the procedure body, not the job itself.

Validate with:
```sql
SELECT owner, job_name, enabled, state, job_action, repeat_interval
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_FT_RPT_CURR';
```

## Post-cutover validation

### 1. Consumer object still works
```sql
SELECT COUNT(*) AS row_count
FROM cisadm.ft_rpt_curr;

SELECT *
FROM cisadm.ft_rpt_curr
FETCH FIRST 20 ROWS ONLY;
```

### 2. MV metadata looks healthy
```sql
SELECT mview_name,
       staleness,
       last_refresh_type,
       last_refresh_date,
       compile_state
FROM all_mviews
WHERE owner = 'CISADM'
  AND mview_name = 'FT_RPT_CURR_MV';
```

### 3. Natural key is still unique
```sql
SELECT ft_id, COUNT(*) AS row_count
FROM cisadm.ft_rpt_curr
GROUP BY ft_id
HAVING COUNT(*) > 1;
```

### 4. Row parity between compatibility view and MV
```sql
SELECT COUNT(*) AS mv_count
FROM cisadm.ft_rpt_curr_mv;

SELECT COUNT(*) AS view_count
FROM cisadm.ft_rpt_curr;
```

### 5. Amount parity against the current backup table
Run this only while the old table backup still exists:
```sql
SELECT SUM(cur_amt) AS old_sum_cur_amt
FROM cisadm.ft_rpt_curr_tbl_bak_20260409;

SELECT SUM(cur_amt) AS new_sum_cur_amt
FROM cisadm.ft_rpt_curr;
```

### 6. Refresh procedure still works
```sql
BEGIN
    cisadm.refresh_ft_rpt_curr;
END;
/
```

### 7. `LOAD_DTTM` has the new meaning you expect
```sql
SELECT MIN(load_dttm) AS min_load_dttm,
       MAX(load_dttm) AS max_load_dttm
FROM cisadm.ft_rpt_curr;
```

Expected result:
- both values should usually be the same refresh timestamp
- that timestamp should align with `ALL_MVIEWS.LAST_REFRESH_DATE`

## Rollback plan
If the cutover fails:

1. Drop the compatibility view:
```sql
DROP VIEW cisadm.ft_rpt_curr;
```

2. Rename the backup table back:
```sql
ALTER TABLE cisadm.ft_rpt_curr_tbl_bak_20260409 RENAME TO ft_rpt_curr;
```

3. Restore the old procedure text.

4. Re-run a validation sample against the restored table.

This is why the compatibility-view pattern is preferred for the pilot.

## What changes and what does not

### What should not change
- Domain object name reference: `FT_RPT_CURR`
- column names
- report field IDs
- scheduler job name
- refresh procedure name

### What does change
- the persisted storage object becomes `FT_RPT_CURR_MV`
- the public `FT_RPT_CURR` object becomes a view instead of a table
- `LOAD_DTTM` becomes refresh metadata rather than row insert time
- validation and runbooks should start checking `ALL_MVIEWS`

## Recommendation for the pilot
Use this exact order:
1. Build `FT_RPT_CURR_MV_TEST`
2. Validate counts and amounts against current `FT_RPT_CURR`
3. Prove the compatibility view works
4. Rewrite `REFRESH_FT_RPT_CURR` to call `DBMS_MVIEW.REFRESH`
5. Cut over in DEV only
6. Validate one Domain query and one report
7. Reuse this pattern for the remaining snapshots

## Decision points before broader rollout
After the FT pilot, decide:
- whether the compatibility view pattern is acceptable for all snapshots
- whether `LOAD_DTTM` should remain exposed everywhere
- whether any snapshots need MV-specific indexes
- whether any snapshot should remain a table because the MV tradeoff is not worth it
