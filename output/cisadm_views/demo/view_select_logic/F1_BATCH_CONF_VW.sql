-- SELECT logic for CISADM.F1_BATCH_CONF_VW
SELECT
    batch_cd,
    AVG(end_dttm - start_dttm) * 1440 + 3 * ( STDDEV(end_dttm - start_dttm) * 1440 )        AS confidence,
    AVG(end_dttm - start_dttm) * 1440                                                       AS avg_elapsed,
    MEDIAN(end_dttm - start_dttm) * 1440                                                    AS med_elapsed,
    STDDEV(end_dttm - start_dttm) * 1440                                                    AS std_deviation,
    MIN(end_dttm - start_dttm) * 1440                                                       AS best_elapsed,
    MAX(end_dttm - start_dttm) * 1440                                                       AS worst_elapsed,
    COUNT(*)                                                                                AS sample_size,
 1                                                                                      AS batch_perf_count
FROM
    ci_batch_run
WHERE
    start_dttm IS NOT NULL
    AND end_dttm IS NOT NULL
GROUP BY
    batch_cd
