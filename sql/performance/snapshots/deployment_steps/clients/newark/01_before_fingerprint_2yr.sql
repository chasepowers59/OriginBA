-- Newark TEST: BEFORE fingerprint for 2-year retention cutover
-- Keep window: ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24)
-- Save output under deploy/snapshot_rollout_logs/newark/

DEFINE keep_months = 24

PROMPT === SNAPSHOT FINGERPRINTS (keep window + older-than-keep) ===
SELECT 'BSEG_BILLED' src,
       COUNT(*) total_rows,
       TO_CHAR(MIN(bill_dt),'YYYY-MM-DD') mn,
       TO_CHAR(MAX(bill_dt),'YYYY-MM-DD') mx,
       SUM(CASE WHEN bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END) keep_rows,
       SUM(CASE WHEN bill_dt <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END) purge_rows,
       SUM(CASE WHEN bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN NVL(total_bill_sq,0) ELSE 0 END) keep_bill_sq,
       SUM(CASE WHEN bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN NVL(total_calc_amt,0) ELSE 0 END) keep_calc_amt
FROM cisadm.bseg_billed_usage_rpt_curr
UNION ALL
SELECT 'BSEG_SQ', COUNT(*), TO_CHAR(MIN(bill_dt),'YYYY-MM-DD'), TO_CHAR(MAX(bill_dt),'YYYY-MM-DD'),
       SUM(CASE WHEN bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END),
       SUM(CASE WHEN bill_dt <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END),
       SUM(CASE WHEN bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN NVL(bill_sq,0) ELSE 0 END),
       NULL
FROM cisadm.bseg_sq_usage_rpt_curr
UNION ALL
SELECT 'FT_RPT', COUNT(*), TO_CHAR(MIN(accounting_dt),'YYYY-MM-DD'), TO_CHAR(MAX(accounting_dt),'YYYY-MM-DD'),
       SUM(CASE WHEN accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END),
       SUM(CASE WHEN accounting_dt <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END),
       SUM(CASE WHEN accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN NVL(cur_amt,0) ELSE 0 END),
       SUM(CASE WHEN accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN NVL(tot_amt,0) ELSE 0 END)
FROM cisadm.ft_rpt_curr
UNION ALL
SELECT 'FT_GL', COUNT(*), TO_CHAR(MIN(accounting_dt),'YYYY-MM-DD'), TO_CHAR(MAX(accounting_dt),'YYYY-MM-DD'),
       SUM(CASE WHEN accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END),
       SUM(CASE WHEN accounting_dt <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END),
       SUM(CASE WHEN accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN NVL(gl_amount,0) ELSE 0 END),
       SUM(CASE WHEN accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN NVL(debit_amt,0) ELSE 0 END)
FROM cisadm.ft_gl_distribution_rpt_curr
UNION ALL
SELECT 'D1_USAGE', COUNT(*), TO_CHAR(MIN(start_dttm),'YYYY-MM-DD'), TO_CHAR(MAX(end_dttm),'YYYY-MM-DD'),
       SUM(CASE WHEN NVL(end_dttm, start_dttm) >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END),
       SUM(CASE WHEN NVL(end_dttm, start_dttm) <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END),
       NULL, NULL
FROM cisadm.d1_usage_rpt_curr
UNION ALL
SELECT 'D1_USAGE_SCALAR', COUNT(*), TO_CHAR(MIN(start_dttm),'YYYY-MM-DD'), TO_CHAR(MAX(usage_end_dttm),'YYYY-MM-DD'),
       SUM(CASE WHEN NVL(usage_end_dttm, end_dttm) >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END),
       SUM(CASE WHEN NVL(usage_end_dttm, end_dttm) <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END),
       SUM(CASE WHEN NVL(usage_end_dttm, end_dttm) >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN NVL(usage,0) ELSE 0 END),
       NULL
FROM cisadm.d1_usage_scalar_dtl_rpt_curr
UNION ALL
SELECT 'D1_MSRMT', COUNT(*), TO_CHAR(MIN(msrmt_dttm),'YYYY-MM-DD'), TO_CHAR(MAX(msrmt_dttm),'YYYY-MM-DD'),
       SUM(CASE WHEN msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END),
       SUM(CASE WHEN msrmt_dttm <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN 1 ELSE 0 END),
       SUM(CASE WHEN msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) THEN NVL(msrmt_val,0) ELSE 0 END),
       NULL
FROM cisadm.d1_msrmt_rpt_curr;

PROMPT === MONTHLY KEEP-WINDOW SNAPSHOT BUCKETS (recent 6 months detail) ===
SELECT 'BSEG_BILLED' src, TO_CHAR(TRUNC(bill_dt,'MM'),'YYYY-MM') ym,
       COUNT(*) rows_n, SUM(NVL(total_bill_sq,0)) bill_sq, SUM(NVL(total_calc_amt,0)) calc_amt
FROM cisadm.bseg_billed_usage_rpt_curr
WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -6)
GROUP BY TRUNC(bill_dt,'MM')
ORDER BY 1,2;

PROMPT === SOURCE vs SNAP (BSEG billed, keep window totals) ===
WITH p AS (SELECT ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) keep_start FROM dual),
raw AS (
  SELECT COUNT(*) raw_rows
  FROM cisadm.ci_bseg bseg
  JOIN cisadm.ci_bill bill ON bill.bill_id = bseg.bill_id AND bill.bill_stat_flg = 'C '
  CROSS JOIN p
  WHERE bill.bill_dt >= p.keep_start
),
snap AS (
  SELECT COUNT(*) snap_rows
  FROM cisadm.bseg_billed_usage_rpt_curr CROSS JOIN p
  WHERE bill_dt >= p.keep_start
)
SELECT r.raw_rows, s.snap_rows, s.snap_rows - r.raw_rows AS snap_minus_raw
FROM raw r CROSS JOIN snap s;

PROMPT === SOURCE vs SNAP (FT_RPT keep window totals) ===
WITH p AS (SELECT ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) keep_start FROM dual),
raw AS (
  SELECT COUNT(*) raw_rows, SUM(NVL(cur_amt,0)) raw_cur
  FROM cisadm.ci_ft CROSS JOIN p
  WHERE accounting_dt >= p.keep_start
),
snap AS (
  SELECT COUNT(*) snap_rows, SUM(NVL(cur_amt,0)) snap_cur
  FROM cisadm.ft_rpt_curr CROSS JOIN p
  WHERE accounting_dt >= p.keep_start
)
SELECT r.raw_rows, s.snap_rows, s.snap_rows - r.raw_rows AS row_diff,
       r.raw_cur, s.snap_cur, s.snap_cur - r.raw_cur AS cur_diff
FROM raw r CROSS JOIN snap s;

PROMPT === SOURCE vs SNAP (D1_MSRMT keep window totals) ===
WITH p AS (SELECT CAST(ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) AS TIMESTAMP) keep_start FROM dual),
raw AS (
  SELECT COUNT(*) raw_rows
  FROM cisadm.d1_msrmt CROSS JOIN p
  WHERE msrmt_dttm >= p.keep_start
),
snap AS (
  SELECT COUNT(*) snap_rows
  FROM cisadm.d1_msrmt_rpt_curr CROSS JOIN p
  WHERE msrmt_dttm >= p.keep_start
)
SELECT r.raw_rows, s.snap_rows, s.snap_rows - r.raw_rows AS snap_minus_raw
FROM raw r CROSS JOIN snap s;

PROMPT === SOURCE vs SNAP (D1_USAGE keep window totals) ===
WITH p AS (SELECT CAST(ADD_MONTHS(TRUNC(SYSDATE,'MM'), -&keep_months) AS TIMESTAMP) keep_start FROM dual),
raw AS (
  SELECT COUNT(*) raw_rows
  FROM cisadm.d1_usage u CROSS JOIN p
  WHERE NVL(u.end_dttm, NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm))) >= p.keep_start
),
snap AS (
  SELECT COUNT(*) snap_rows
  FROM cisadm.d1_usage_rpt_curr CROSS JOIN p
  WHERE NVL(end_dttm, start_dttm) >= p.keep_start
)
SELECT r.raw_rows, s.snap_rows, s.snap_rows - r.raw_rows AS snap_minus_raw
FROM raw r CROSS JOIN snap s;
