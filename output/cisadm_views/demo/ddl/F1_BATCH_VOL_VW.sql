CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_BATCH_VOL_VW" ("BATCH_CD", "BATCH_NBR", "BATCH_RERUN_NBR", "TOTAL_PROCESSED", "MAX_PROCESSED", "RECS_PER_MINUTE", "BATCH_THD_VOL_COUNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
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
    batch_rerun_nbr;
