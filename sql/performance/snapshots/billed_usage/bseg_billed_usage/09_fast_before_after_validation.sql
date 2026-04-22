WITH params AS (
    SELECT ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12) AS window_start FROM dual
)
SELECT
    COUNT(*) AS snapshot_rows,
    MIN(bill_dt) AS min_bill_dt,
    MAX(bill_dt) AS max_bill_dt,
    MIN(load_dttm) AS min_load_dttm,
    MAX(load_dttm) AS max_load_dttm,
    SUM(total_bill_sq) AS total_bill_sq,
    SUM(total_calc_amt) AS total_calc_amt
FROM cisadm.bseg_billed_usage_rpt_curr;

WITH params AS (
    SELECT ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12) AS window_start FROM dual
),
raw_months AS (
    SELECT
        TRUNC(bill.bill_dt, 'MM') AS bill_month,
        COUNT(*) AS raw_rows,
        SUM(NVL(sq_agg.total_bill_sq, 0)) AS raw_total_bill_sq,
        SUM(NVL(calc_agg.total_calc_amt, 0)) AS raw_total_calc_amt
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
       AND bill.bill_stat_flg = 'C '
    LEFT JOIN (
        SELECT bseg_id, SUM(NVL(bill_sq, 0)) AS total_bill_sq
        FROM cisadm.ci_bseg_sq
        GROUP BY bseg_id
    ) sq_agg
        ON sq_agg.bseg_id = bseg.bseg_id
    LEFT JOIN (
        SELECT bseg_id, SUM(NVL(calc_amt, 0)) AS total_calc_amt
        FROM cisadm.ci_bseg_calc
        GROUP BY bseg_id
    ) calc_agg
        ON calc_agg.bseg_id = bseg.bseg_id
    CROSS JOIN params p
    WHERE bill.bill_dt >= p.window_start
    GROUP BY TRUNC(bill.bill_dt, 'MM')
),
snap_months AS (
    SELECT
        TRUNC(s.bill_dt, 'MM') AS bill_month,
        COUNT(*) AS snapshot_rows,
        SUM(NVL(s.total_bill_sq, 0)) AS snapshot_total_bill_sq,
        SUM(NVL(s.total_calc_amt, 0)) AS snapshot_total_calc_amt
    FROM cisadm.bseg_billed_usage_rpt_curr s
    CROSS JOIN params p
    WHERE s.bill_dt >= p.window_start
    GROUP BY TRUNC(s.bill_dt, 'MM')
)
SELECT
    COALESCE(r.bill_month, s.bill_month) AS bill_month,
    NVL(r.raw_rows, 0) AS raw_rows,
    NVL(s.snapshot_rows, 0) AS snapshot_rows,
    NVL(s.snapshot_rows, 0) - NVL(r.raw_rows, 0) AS snapshot_minus_raw_rows,
    NVL(r.raw_total_bill_sq, 0) AS raw_total_bill_sq,
    NVL(s.snapshot_total_bill_sq, 0) AS snapshot_total_bill_sq,
    NVL(s.snapshot_total_bill_sq, 0) - NVL(r.raw_total_bill_sq, 0) AS snapshot_minus_raw_bill_sq,
    NVL(r.raw_total_calc_amt, 0) AS raw_total_calc_amt,
    NVL(s.snapshot_total_calc_amt, 0) AS snapshot_total_calc_amt,
    NVL(s.snapshot_total_calc_amt, 0) - NVL(r.raw_total_calc_amt, 0) AS snapshot_minus_raw_calc_amt
FROM raw_months r
FULL OUTER JOIN snap_months s
    ON s.bill_month = r.bill_month
ORDER BY bill_month;

SELECT
    bseg_id,
    COUNT(*) AS row_count
FROM cisadm.bseg_billed_usage_rpt_curr
GROUP BY bseg_id
HAVING COUNT(*) > 1;

SELECT
    (SELECT COUNT(*)
     FROM cisadm.ci_bseg bseg
     INNER JOIN cisadm.ci_bill bill
         ON bill.bill_id = bseg.bill_id
     WHERE bill.bill_stat_flg = 'C ') AS source_rows,
    (SELECT COUNT(*) FROM cisadm.bseg_billed_usage_rpt_curr) AS snapshot_rows,
    (SELECT SUM(NVL(sq_agg.total_bill_sq, 0))
     FROM cisadm.ci_bseg bseg
     INNER JOIN cisadm.ci_bill bill
         ON bill.bill_id = bseg.bill_id
        AND bill.bill_stat_flg = 'C '
     LEFT JOIN (
         SELECT bseg_id, SUM(NVL(bill_sq, 0)) AS total_bill_sq
         FROM cisadm.ci_bseg_sq
         GROUP BY bseg_id
     ) sq_agg
         ON sq_agg.bseg_id = bseg.bseg_id) AS source_total_bill_sq,
    (SELECT SUM(NVL(total_bill_sq, 0)) FROM cisadm.bseg_billed_usage_rpt_curr) AS snapshot_total_bill_sq,
    (SELECT SUM(NVL(calc_agg.total_calc_amt, 0))
     FROM cisadm.ci_bseg bseg
     INNER JOIN cisadm.ci_bill bill
         ON bill.bill_id = bseg.bill_id
        AND bill.bill_stat_flg = 'C '
     LEFT JOIN (
         SELECT bseg_id, SUM(NVL(calc_amt, 0)) AS total_calc_amt
         FROM cisadm.ci_bseg_calc
         GROUP BY bseg_id
     ) calc_agg
         ON calc_agg.bseg_id = bseg.bseg_id) AS source_total_calc_amt,
    (SELECT SUM(NVL(total_calc_amt, 0)) FROM cisadm.bseg_billed_usage_rpt_curr) AS snapshot_total_calc_amt
FROM dual;
