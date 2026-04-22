WITH source_base AS (
    SELECT
        bseg.bseg_id,
        bill.bill_dt,
        bill.cre_dttm,
        bseg.start_dt,
        bseg.end_dt
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
      AND bill.bill_dt IS NOT NULL
)
SELECT
    COUNT(*) AS total_bseg_rows,
    MIN(bill_dt) AS min_bill_dt,
    MAX(bill_dt) AS max_bill_dt,
    MIN(cre_dttm) AS min_bill_cre_dttm,
    MAX(cre_dttm) AS max_bill_cre_dttm,
    SUM(CASE WHEN bill_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6) THEN 1 ELSE 0 END) AS rows_last_6_months,
    SUM(CASE WHEN bill_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12) THEN 1 ELSE 0 END) AS rows_last_12_months,
    SUM(CASE WHEN bill_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -24) THEN 1 ELSE 0 END) AS rows_last_24_months
FROM source_base;

WITH source_base AS (
    SELECT
        bill.bill_dt
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
      AND bill.bill_dt IS NOT NULL
)
SELECT
    TRUNC(bill_dt, 'MM') AS bill_month,
    COUNT(*) AS bseg_rows
FROM source_base
GROUP BY TRUNC(bill_dt, 'MM')
ORDER BY bill_month;

WITH source_base AS (
    SELECT
        bill.bill_dt,
        bill.cre_dttm
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
      AND bill.bill_dt IS NOT NULL
      AND bill.cre_dttm IS NOT NULL
),
windows AS (
    SELECT 30 AS window_days FROM dual UNION ALL
    SELECT 90 AS window_days FROM dual UNION ALL
    SELECT 180 AS window_days FROM dual
)
SELECT
    w.window_days,
    COUNT(*) AS created_rows,
    SUM(CASE WHEN s.bill_dt < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6) THEN 1 ELSE 0 END) AS bill_dt_older_than_6_months,
    SUM(CASE WHEN s.bill_dt < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12) THEN 1 ELSE 0 END) AS bill_dt_older_than_12_months,
    SUM(CASE WHEN s.bill_dt < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -24) THEN 1 ELSE 0 END) AS bill_dt_older_than_24_months
FROM windows w
JOIN source_base s
    ON s.cre_dttm >= SYSDATE - w.window_days
GROUP BY w.window_days
ORDER BY w.window_days;

WITH source_base AS (
    SELECT
        bill.bill_dt,
        bill.cre_dttm,
        TRUNC(bill.cre_dttm) - TRUNC(bill.bill_dt) AS lag_days
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
      AND bill.bill_dt IS NOT NULL
      AND bill.cre_dttm IS NOT NULL
)
SELECT
    CASE
        WHEN lag_days <= 7 THEN '0_TO_7_DAYS'
        WHEN lag_days <= 30 THEN '8_TO_30_DAYS'
        WHEN lag_days <= 90 THEN '31_TO_90_DAYS'
        WHEN lag_days <= 180 THEN '91_TO_180_DAYS'
        WHEN lag_days <= 365 THEN '181_TO_365_DAYS'
        ELSE 'OVER_365_DAYS'
    END AS lag_bucket,
    COUNT(*) AS row_count
FROM source_base
GROUP BY
    CASE
        WHEN lag_days <= 7 THEN '0_TO_7_DAYS'
        WHEN lag_days <= 30 THEN '8_TO_30_DAYS'
        WHEN lag_days <= 90 THEN '31_TO_90_DAYS'
        WHEN lag_days <= 180 THEN '91_TO_180_DAYS'
        WHEN lag_days <= 365 THEN '181_TO_365_DAYS'
        ELSE 'OVER_365_DAYS'
    END
ORDER BY lag_bucket;
