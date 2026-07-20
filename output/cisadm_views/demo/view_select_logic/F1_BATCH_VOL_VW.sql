-- SELECT logic for CISADM.F1_BATCH_VOL_VW
SELECT
    batch_cd,
    batch_nbr,
    batch_rerun_nbr,
    SUM(total_processed)                                         AS total_processed,
    MAX(total_processed)                                         AS max_processed,
    MIN(recs_per_minute)                                         AS recs_per_minute,
    1                                                            AS batch_thd_vol_count
FROM
      f1_batch_thd_hist_vw
GROUP BY
    batch_cd,
    batch_nbr,
    batch_rerun_nbr
