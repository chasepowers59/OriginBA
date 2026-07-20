CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_BATCH_THD_CAP_VW" ("BATCH_CD", "BATCH_NBR", "BATCH_RERUN_NBR", "BATCH_THREAD_NBR", "THREAD_START_DTTM", "THREAD_END_DTTM", "START_DT", "END_DT", "JOB_START_MINS", "JOB_END_MINS", "START_MINUTES", "END_MINUTES", "BATCH_BUS_DT", "BATCH_JOB_ID", "SUBMIT_METH_FLG", "SUBMIT_USER_ID", "THREADPOOL", "BATCH_THREAD_CAP_COUNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  WITH timeperiod AS (
    SELECT
        to_char(trunc(CURRENT_DATE) +((ROWNUM - 1) / 144), 'HH24":"MI')                                                                                                                                                                                                                                  AS
        start_time,
        to_char(trunc(CURRENT_DATE) + ROWNUM / 144, 'HH24":"MI')                                                                                                                                                                                                                                         AS
        end_time,
        to_number(to_char(trunc(CURRENT_DATE) +((ROWNUM - 1) / 144), 'HH24'), '99') * 60 + to_number(to_char(trunc(CURRENT_DATE) +((ROWNUM - 1) /
        144), 'MI'), '99')                                                                                                                                          AS
        start_minutes,
        decode(to_number(to_char(trunc(CURRENT_DATE) + ROWNUM / 144, 'HH24'), '99') * 60 + to_number(to_char(trunc(CURRENT_DATE) + ROWNUM / 144,
        'MI'), '99'), 0, 1440, to_number(to_char(trunc(CURRENT_DATE) + ROWNUM / 144, 'HH24'), '99') * 60 + to_number(to_char(trunc(CURRENT_DATE) +
        ROWNUM / 144, 'MI'), '99')) AS end_minutes
    FROM
        dual
    CONNECT BY
        ROWNUM <= 144
)
SELECT
    i.batch_cd,
    i.batch_nbr,
    i.batch_rerun_nbr,
    i.batch_thread_nbr,
    i.start_dttm                                                                                   AS thread_start_dttm,
    i.end_dttm                                                                                     AS thread_end_dttm,
    trunc(i.start_dttm)                                                                            AS start_dt,
    trunc(i.end_dttm)                                                                              AS end_dt,
    to_number(to_char(i.start_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.start_dttm, 'MI'), 99) AS job_start_mins,
    to_number(to_char(i.end_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.end_dttm, 'MI'), 99)     AS job_end_mins,
    t.start_minutes,
    t.end_minutes,
    r.batch_bus_dt,
    j.batch_job_id,
    j.submit_meth_flg,
    j.submit_user_id,
    decode(TRIM(p.batch_parm_val), '', 'DEFAULT', p.batch_parm_val)                                AS threadpool,
    1                                                                                           AS batch_thread_cap_count
FROM
      ci_batch_inst    i,
      ci_batch_run     r,
      ci_batch_job     j,
      ci_batch_job_prm p,
    timeperiod       t
WHERE
    i.start_dttm IS NOT NULL
    AND i.end_dttm IS NOT NULL
    AND r.batch_cd = i.batch_cd
    AND r.batch_nbr = i.batch_nbr
    AND r.batch_rerun_nbr = i.batch_rerun_nbr
    AND j.batch_cd = i.batch_cd
    AND j.batch_nbr = i.batch_nbr
    AND j.batch_rerun_nbr = i.batch_rerun_nbr
    AND p.batch_job_id = j.batch_job_id
    AND p.batch_parm_name = 'DIST-THD-POOL'
    AND ( ( t.start_minutes <= to_number(to_char(i.start_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.start_dttm, 'MI'), 99)
            AND t.end_minutes >= to_number(to_char(i.end_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.end_dttm, 'MI'), 99) )
          OR ( t.start_minutes <= to_number(to_char(i.start_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.end_dttm, 'MI'), 99)
               AND t.start_minutes >= to_number(to_char(i.start_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.start_dttm, 'MI'), 99) )
          OR ( t.end_minutes >= to_number(to_char(i.start_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.start_dttm, 'MI'), 99)
               AND t.end_minutes <= to_number(to_char(i.start_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.end_dttm, 'MI'), 99) ) );
