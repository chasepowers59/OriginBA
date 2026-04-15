# Snapshot SQL Developer Runbook

## Purpose
This runbook gives exact SQL Developer steps for every current governed snapshot.

Use it when you need to:
- inspect the current snapshot table
- confirm the latest load timestamp and row count
- view the current refresh procedure text in the database
- inspect and validate the scheduler job
- review recent scheduler run history

## General notes
- These checks are read-only.
- Run them in SQL Developer with the `CISADM`-capable reporting account.
- Replace nothing in the SQL blocks below unless you are adapting the pattern for a new snapshot.

## Common validation pattern

### 1. Check the snapshot table
```sql
SELECT COUNT(*) AS row_count,
       MIN(load_dttm) AS min_load_dttm,
       MAX(load_dttm) AS max_load_dttm
FROM cisadm.<snapshot_table>;

SELECT *
FROM cisadm.<snapshot_table>
FETCH FIRST 50 ROWS ONLY;
```

### 2. View the current procedure text
```sql
SELECT line,
       text
FROM all_source
WHERE owner = 'CISADM'
  AND name = '<procedure_name>'
  AND type = 'PROCEDURE'
ORDER BY line;
```

### 3. Check the scheduler job definition
```sql
SELECT owner,
       job_name,
       enabled,
       state,
       job_action,
       repeat_interval,
       last_start_date,
       next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = '<job_name>';
```

### 4. Check recent scheduler run history
```sql
SELECT log_id,
       status,
       actual_start_date,
       run_duration,
       additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name = '<job_name>'
ORDER BY log_id DESC
FETCH FIRST 20 ROWS ONLY;
```

## Billing

## `BSEG_BILLED_USAGE_RPT_CURR`
- Table: `CISADM.BSEG_BILLED_USAGE_RPT_CURR`
- Procedure: `REFRESH_BSEG_BILLED_USAGE_RPT_CURR`
- Job: `JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR`

```sql
SELECT COUNT(*) AS row_count, MIN(load_dttm) AS min_load_dttm, MAX(load_dttm) AS max_load_dttm
FROM cisadm.bseg_billed_usage_rpt_curr;

SELECT *
FROM cisadm.bseg_billed_usage_rpt_curr
FETCH FIRST 50 ROWS ONLY;

SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_BSEG_BILLED_USAGE_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;

SELECT owner, job_name, enabled, state, job_action, repeat_interval, last_start_date, next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR';

SELECT log_id, status, actual_start_date, run_duration, additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR'
ORDER BY log_id DESC
FETCH FIRST 20 ROWS ONLY;
```

## `BSEG_SQ_USAGE_RPT_CURR`
- Table: `CISADM.BSEG_SQ_USAGE_RPT_CURR`
- Procedure: `REFRESH_BSEG_SQ_USAGE_RPT_CURR`
- Job: `REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB`

```sql
SELECT COUNT(*) AS row_count, MIN(load_dttm) AS min_load_dttm, MAX(load_dttm) AS max_load_dttm
FROM cisadm.bseg_sq_usage_rpt_curr;

SELECT *
FROM cisadm.bseg_sq_usage_rpt_curr
FETCH FIRST 50 ROWS ONLY;

SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_BSEG_SQ_USAGE_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;

SELECT owner, job_name, enabled, state, job_action, repeat_interval, last_start_date, next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = 'REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB';

SELECT log_id, status, actual_start_date, run_duration, additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name = 'REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB'
ORDER BY log_id DESC
FETCH FIRST 20 ROWS ONLY;
```

## Finance

## `FT_RPT_CURR`
- Table: `CISADM.FT_RPT_CURR`
- Procedure: `REFRESH_FT_RPT_CURR`
- Job: `JOB_REFRESH_FT_RPT_CURR`

```sql
SELECT COUNT(*) AS row_count, MIN(load_dttm) AS min_load_dttm, MAX(load_dttm) AS max_load_dttm
FROM cisadm.ft_rpt_curr;

SELECT *
FROM cisadm.ft_rpt_curr
FETCH FIRST 50 ROWS ONLY;

SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_FT_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;

SELECT owner, job_name, enabled, state, job_action, repeat_interval, last_start_date, next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_FT_RPT_CURR';

SELECT log_id, status, actual_start_date, run_duration, additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_FT_RPT_CURR'
ORDER BY log_id DESC
FETCH FIRST 20 ROWS ONLY;
```

## `FT_GL_DISTRIBUTION_RPT_CURR`
- Table: `CISADM.FT_GL_DISTRIBUTION_RPT_CURR`
- Procedure: `REFRESH_FT_GL_DISTRIBUTION_RPT_CURR`
- Job: `JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR`

```sql
SELECT COUNT(*) AS row_count, MIN(load_dttm) AS min_load_dttm, MAX(load_dttm) AS max_load_dttm
FROM cisadm.ft_gl_distribution_rpt_curr;

SELECT *
FROM cisadm.ft_gl_distribution_rpt_curr
FETCH FIRST 50 ROWS ONLY;

SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_FT_GL_DISTRIBUTION_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;

SELECT owner, job_name, enabled, state, job_action, repeat_interval, last_start_date, next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR';

SELECT log_id, status, actual_start_date, run_duration, additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR'
ORDER BY log_id DESC
FETCH FIRST 20 ROWS ONLY;
```

## Debt Management

## `ACCT_DEBT_RPT_CURR`
- Table: `CISADM.ACCT_DEBT_RPT_CURR`
- Procedure: `REFRESH_ACCT_DEBT_RPT_CURR`
- Job: `JOB_REFRESH_ACCT_DEBT_RPT_CURR`

```sql
SELECT COUNT(*) AS row_count, MIN(load_dttm) AS min_load_dttm, MAX(load_dttm) AS max_load_dttm
FROM cisadm.acct_debt_rpt_curr;

SELECT *
FROM cisadm.acct_debt_rpt_curr
FETCH FIRST 50 ROWS ONLY;

SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_ACCT_DEBT_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;

SELECT owner, job_name, enabled, state, job_action, repeat_interval, last_start_date, next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_ACCT_DEBT_RPT_CURR';

SELECT log_id, status, actual_start_date, run_duration, additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_ACCT_DEBT_RPT_CURR'
ORDER BY log_id DESC
FETCH FIRST 20 ROWS ONLY;
```

## `COLL_PROC_RPT_CURR`
- Table: `CISADM.COLL_PROC_RPT_CURR`
- Procedure: `REFRESH_COLL_PROC_RPT_CURR`
- Job: `JOB_REFRESH_COLL_PROC_RPT_CURR`

```sql
SELECT COUNT(*) AS row_count, MIN(load_dttm) AS min_load_dttm, MAX(load_dttm) AS max_load_dttm
FROM cisadm.coll_proc_rpt_curr;

SELECT *
FROM cisadm.coll_proc_rpt_curr
FETCH FIRST 50 ROWS ONLY;

SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_COLL_PROC_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;

SELECT owner, job_name, enabled, state, job_action, repeat_interval, last_start_date, next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_COLL_PROC_RPT_CURR';

SELECT log_id, status, actual_start_date, run_duration, additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_COLL_PROC_RPT_CURR'
ORDER BY log_id DESC
FETCH FIRST 20 ROWS ONLY;
```

## Meter Operations

## `D1_USAGE_RPT_CURR`
- Table: `CISADM.D1_USAGE_RPT_CURR`
- Procedure: `REFRESH_D1_USAGE_RPT_CURR`
- Job: `JOB_REFRESH_D1_USAGE_RPT_CURR`

```sql
SELECT COUNT(*) AS row_count, MIN(load_dttm) AS min_load_dttm, MAX(load_dttm) AS max_load_dttm
FROM cisadm.d1_usage_rpt_curr;

SELECT *
FROM cisadm.d1_usage_rpt_curr
FETCH FIRST 50 ROWS ONLY;

SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_D1_USAGE_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;

SELECT owner, job_name, enabled, state, job_action, repeat_interval, last_start_date, next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_D1_USAGE_RPT_CURR';

SELECT log_id, status, actual_start_date, run_duration, additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_D1_USAGE_RPT_CURR'
ORDER BY log_id DESC
FETCH FIRST 20 ROWS ONLY;
```

## `D1_USAGE_SCALAR_DTL_RPT_CURR`
- Table: `CISADM.D1_USAGE_SCALAR_DTL_RPT_CURR`
- Procedure: `REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR`
- Job: `JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR`

```sql
SELECT COUNT(*) AS row_count, MIN(load_dttm) AS min_load_dttm, MAX(load_dttm) AS max_load_dttm
FROM cisadm.d1_usage_scalar_dtl_rpt_curr;

SELECT *
FROM cisadm.d1_usage_scalar_dtl_rpt_curr
FETCH FIRST 50 ROWS ONLY;

SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;

SELECT owner, job_name, enabled, state, job_action, repeat_interval, last_start_date, next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR';

SELECT log_id, status, actual_start_date, run_duration, additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR'
ORDER BY log_id DESC
FETCH FIRST 20 ROWS ONLY;
```

## `D1_MSRMT_RPT_CURR`
- Table: `CISADM.D1_MSRMT_RPT_CURR`
- Procedure: `REFRESH_D1_MSRMT_RPT_CURR`
- Job: `JOB_REFRESH_D1_MSRMT_RPT_CURR`

```sql
SELECT COUNT(*) AS row_count, MIN(load_dttm) AS min_load_dttm, MAX(load_dttm) AS max_load_dttm
FROM cisadm.d1_msrmt_rpt_curr;

SELECT *
FROM cisadm.d1_msrmt_rpt_curr
FETCH FIRST 50 ROWS ONLY;

SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_D1_MSRMT_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;

SELECT owner, job_name, enabled, state, job_action, repeat_interval, last_start_date, next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_D1_MSRMT_RPT_CURR';

SELECT log_id, status, actual_start_date, run_duration, additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_D1_MSRMT_RPT_CURR'
ORDER BY log_id DESC
FETCH FIRST 20 ROWS ONLY;
```

## Payments and Cashiering

## `PAY_TNDR_CASH_RPT_CURR`
- Table: `CISADM.PAY_TNDR_CASH_RPT_CURR`
- Procedure: `REFRESH_PAY_TNDR_CASH_RPT_CURR`
- Job: `REFRESH_PAY_TNDR_CASH_RPT_CURR_JB`

```sql
SELECT COUNT(*) AS row_count, MIN(load_dttm) AS min_load_dttm, MAX(load_dttm) AS max_load_dttm
FROM cisadm.pay_tndr_cash_rpt_curr;

SELECT *
FROM cisadm.pay_tndr_cash_rpt_curr
FETCH FIRST 50 ROWS ONLY;

SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_PAY_TNDR_CASH_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;

SELECT owner, job_name, enabled, state, job_action, repeat_interval, last_start_date, next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = 'REFRESH_PAY_TNDR_CASH_RPT_CURR_JB';

SELECT log_id, status, actual_start_date, run_duration, additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name = 'REFRESH_PAY_TNDR_CASH_RPT_CURR_JB'
ORDER BY log_id DESC
FETCH FIRST 20 ROWS ONLY;
```
