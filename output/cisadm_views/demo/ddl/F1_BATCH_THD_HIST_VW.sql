CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_BATCH_THD_HIST_VW" ("BATCH_CD", "RUN_STATUS", "BATCH_BUS_DT", "BATCH_NBR", "BATCH_RERUN_NBR", "BATCH_THREAD_NBR", "THREAD_STATUS", "BATCH_JOB_ID", "RETRY_COUNT", "THREADPOOL", "TOTAL_PROCESSED", "TOTAL_ERROR", "PROCESS_DT", "THREAD_START_DTTM", "THREAD_END_DTTM", "ELAPSED_TIME", "RECS_PER_MINUTE", "BATCH_RUN_THD_COUNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    r.batch_cd,
    r.run_status,
    r.batch_bus_dt,
    r.batch_nbr,
    r.batch_rerun_nbr,
    t.batch_thread_nbr,
    t.thread_status,
    j.batch_job_id,
    nvl(t.thd_retry_cnt, 0)                                                  AS retry_count,
    decode(TRIM(p.batch_parm_val), '', 'DEFAULT', p.batch_parm_val)          AS threadpool,
    SUM(i.rec_proc_cnt)                                                      AS total_processed,
    SUM(i.rec_err_cnt)                                                       AS total_error,
    trunc(MIN(i.start_dttm))                                                 AS process_dt,
    MIN(i.start_dttm)                                                        AS thread_start_dttm,
    MAX(i.end_dttm)                                                          AS thread_end_dttm,
    ( MAX(i.end_dttm) - MIN(i.start_dttm) ) * 1440                           AS elapsed_time,
    SUM(i.rec_proc_cnt) / ( ( MAX(i.end_dttm) - MIN(i.start_dttm) ) * 1440 ) AS recs_per_minute,
    1                                                               AS batch_run_thd_count
FROM
      ci_batch_run     r,
      ci_batch_thd     t,
      ci_batch_job     j,
      ci_batch_inst    i,
      ci_batch_job_prm p
WHERE
     t.batch_cd = r.batch_cd
    AND t.batch_nbr = r.batch_nbr
    AND t.batch_rerun_nbr = r.batch_rerun_nbr
    AND i.batch_cd = t.batch_cd
    AND i.batch_nbr = t.batch_nbr
    AND i.batch_rerun_nbr = t.batch_rerun_nbr
    AND i.batch_thread_nbr = t.batch_thread_nbr
    AND j.batch_cd = t.batch_cd
    AND j.batch_nbr = t.batch_nbr
    AND j.batch_rerun_nbr = t.batch_rerun_nbr
    AND p.batch_job_id = j.batch_job_id
    AND p.batch_parm_name = 'DIST-THD-POOL'
    AND i.start_dttm IS NOT NULL
    AND i.end_dttm IS NOT NULL
    AND i.end_dttm != i.start_dttm
GROUP BY
    r.batch_cd,
    r.run_status,
    r.batch_bus_dt,
    r.batch_nbr,
    r.batch_rerun_nbr,
    t.batch_thread_nbr,
    t.thread_status,
    j.batch_job_id,
    j.submit_meth_flg,
    j.submit_user_id,
    j.user_id,
    nvl(t.thd_retry_cnt, 0),
    decode(TRIM(p.batch_parm_val), '', 'DEFAULT', p.batch_parm_val);
