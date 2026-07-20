CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_BATCH_RUN_HIST_VW" ("BATCH_CD", "BATCH_JOB_ID", "BATCH_NBR", "BATCH_RERUN_NBR", "BATCH_BUS_DT", "RUN_STATUS", "PROCESS_DT", "START_DTTM", "END_DTTM", "ELAPSED_TIME", "THREADPOOL", "TOTAL_PROCESSED", "TOTAL_ERROR", "BATCH_RUN_COUNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    r.batch_cd,
    j.batch_job_id,
    r.batch_nbr,
    r.batch_rerun_nbr,
    r.batch_bus_dt,
    r.run_status,
    trunc(r.start_dttm)                                             AS process_dt,
    r.start_dttm,
    r.end_dttm,
    ( r.end_dttm - r.start_dttm ) * 1440                            AS elapsed_time,
    decode(TRIM(p.batch_parm_val), '', 'DEFAULT', p.batch_parm_val) AS threadpool,
    SUM(i.rec_proc_cnt)                                           AS total_processed,
    SUM(i.rec_err_cnt)                                              AS total_error,
    1                                                               AS batch_run_count
FROM
    ci_batch_job     j,
    ci_batch_run     r,
    ci_batch_job_prm p,
    ci_batch_inst    i
WHERE
     j.batch_cd = r.batch_cd
    AND j.batch_nbr = r.batch_nbr
    AND j.batch_rerun_nbr = r.batch_rerun_nbr
    AND p.batch_job_id = j.batch_job_id
    AND p.batch_parm_name = 'DIST-THD-POOL'
    AND r.start_dttm IS NOT NULL
    AND i.batch_cd = r.batch_cd
    AND i.batch_nbr = r.batch_nbr
    AND i.batch_rerun_nbr = r.batch_rerun_nbr
GROUP BY
    r.batch_cd,
    j.batch_job_id,
    j.submit_meth_flg,
    j.submit_user_id,
    j.user_id,
    j.batch_job_stat_flg,
    r.batch_nbr,
    r.batch_rerun_nbr,
    r.batch_bus_dt,
    r.run_status,
    trunc(r.start_dttm),
    r.start_dttm,
    r.end_dttm,
    ( r.end_dttm - r.start_dttm ) * 1440,
    decode(TRIM(p.batch_parm_val), '', 'DEFAULT', p.batch_parm_val);
