-- College Station TEST: simplified post-cutover validation (24mo retain / 3mo rolling)
-- Lean checks: retention, exact 24mo counts, known-dup grain vs source, CMS SA LDAY, job health.
-- Designed to survive better than the full 31-statement validate pack.

PROMPT ============================================================
PROMPT CS cutover QA — retention (expect older_than_2yr = 0)
PROMPT ============================================================
SELECT 'BSEG_BILLED' src, COUNT(*) total_rows,
       TO_CHAR(MIN(bill_dt),'YYYY-MM-DD') mn, TO_CHAR(MAX(bill_dt),'YYYY-MM-DD') mx,
       SUM(CASE WHEN bill_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END) older_than_2yr
FROM cisadm.bseg_billed_usage_rpt_curr
UNION ALL
SELECT 'BSEG_SQ', COUNT(*), TO_CHAR(MIN(bill_dt),'YYYY-MM-DD'), TO_CHAR(MAX(bill_dt),'YYYY-MM-DD'),
       SUM(CASE WHEN bill_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END)
FROM cisadm.bseg_sq_usage_rpt_curr
UNION ALL
SELECT 'FT_RPT', COUNT(*), TO_CHAR(MIN(accounting_dt),'YYYY-MM-DD'), TO_CHAR(MAX(accounting_dt),'YYYY-MM-DD'),
       SUM(CASE WHEN accounting_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END)
FROM cisadm.ft_rpt_curr
UNION ALL
SELECT 'FT_GL', COUNT(*), TO_CHAR(MIN(accounting_dt),'YYYY-MM-DD'), TO_CHAR(MAX(accounting_dt),'YYYY-MM-DD'),
       SUM(CASE WHEN accounting_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END)
FROM cisadm.ft_gl_distribution_rpt_curr
UNION ALL
SELECT 'D1_MSRMT', COUNT(*), TO_CHAR(MIN(msrmt_dttm),'YYYY-MM-DD'), TO_CHAR(MAX(msrmt_dttm),'YYYY-MM-DD'),
       SUM(CASE WHEN msrmt_dttm < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END)
FROM cisadm.d1_msrmt_rpt_curr
UNION ALL
SELECT 'D1_USAGE', COUNT(*), TO_CHAR(MIN(NVL(end_dttm,start_dttm)),'YYYY-MM-DD'),
       TO_CHAR(MAX(NVL(end_dttm,start_dttm)),'YYYY-MM-DD'),
       SUM(CASE WHEN NVL(end_dttm,start_dttm) < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END)
FROM cisadm.d1_usage_rpt_curr
UNION ALL
SELECT 'D1_USAGE_SCALAR', COUNT(*), TO_CHAR(MIN(NVL(usage_end_dttm,end_dttm)),'YYYY-MM-DD'),
       TO_CHAR(MAX(NVL(usage_end_dttm,end_dttm)),'YYYY-MM-DD'),
       SUM(CASE WHEN NVL(usage_end_dttm,end_dttm) < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END)
FROM cisadm.d1_usage_scalar_dtl_rpt_curr;

PROMPT ============================================================
PROMPT CS cutover QA — 24mo source parity (exact counts)
PROMPT ============================================================
SELECT 'BSEG_BILLED' chk,
       (SELECT COUNT(*) FROM cisadm.ci_bseg bseg
        JOIN cisadm.ci_bill bill ON bill.bill_id = bseg.bill_id AND bill.bill_stat_flg = 'C '
        WHERE bill.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24)) raw_rows,
       (SELECT COUNT(*) FROM cisadm.bseg_billed_usage_rpt_curr
        WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24)) snap_rows
FROM dual
UNION ALL
SELECT 'BSEG_SQ',
       (SELECT COUNT(*) FROM cisadm.ci_bseg_sq sq
        JOIN cisadm.ci_bseg bseg ON bseg.bseg_id = sq.bseg_id
        JOIN cisadm.ci_bill bill ON bill.bill_id = bseg.bill_id AND bill.bill_stat_flg = 'C '
        WHERE bill.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24)),
       (SELECT COUNT(*) FROM cisadm.bseg_sq_usage_rpt_curr
        WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24))
FROM dual
UNION ALL
SELECT 'FT_RPT',
       (SELECT COUNT(*) FROM cisadm.ci_ft
        WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) AND redundant_sw = 'N'),
       (SELECT COUNT(*) FROM cisadm.ft_rpt_curr
        WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24))
FROM dual
UNION ALL
SELECT 'FT_GL',
       (SELECT COUNT(*) FROM cisadm.ci_ft_gl gl
        JOIN cisadm.ci_ft ft ON ft.ft_id = gl.ft_id
        WHERE ft.accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24)),
       (SELECT COUNT(*) FROM cisadm.ft_gl_distribution_rpt_curr
        WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24))
FROM dual
UNION ALL
SELECT 'D1_MSRMT',
       (SELECT COUNT(*) FROM cisadm.d1_msrmt
        WHERE msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24)),
       (SELECT COUNT(*) FROM cisadm.d1_msrmt_rpt_curr
        WHERE msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24))
FROM dual;

PROMPT ============================================================
PROMPT CS cutover QA — usage/scalar 3mo parity (usage-driver grain)
PROMPT ============================================================
SELECT 'D1_USAGE_3MO' chk,
       (SELECT COUNT(*) FROM cisadm.d1_usage u
        WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm))
              >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3)) raw_rows,
       (SELECT COUNT(*) FROM cisadm.d1_usage_rpt_curr
        WHERE NVL(start_dttm, NVL(usage_cre_dttm, status_upd_dttm))
              >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3)) snap_rows
FROM dual
UNION ALL
SELECT 'D1_SCALAR_BY_START_3MO',
       (SELECT COUNT(*) FROM cisadm.d1_usage_scalar_dtl d
        WHERE d.start_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3)),
       (SELECT COUNT(*) FROM cisadm.d1_usage_scalar_dtl_rpt_curr
        WHERE start_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3))
FROM dual
UNION ALL
SELECT 'D1_SCALAR_BY_USAGE_3MO',
       (SELECT COUNT(*) FROM cisadm.d1_usage_scalar_dtl d
        JOIN cisadm.d1_usage u ON u.d1_usage_id = d.d1_usage_id
        WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm))
              >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3)),
       (SELECT COUNT(*) FROM cisadm.d1_usage_scalar_dtl_rpt_curr s
        WHERE EXISTS (
          SELECT 1 FROM cisadm.d1_usage_rpt_curr u
          WHERE u.d1_usage_id = s.d1_usage_id
            AND NVL(u.start_dttm, NVL(u.usage_cre_dttm, u.status_upd_dttm))
                >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3)
        ))
FROM dual;

PROMPT ============================================================
PROMPT CS cutover QA — scalar dup grain vs source (expect equal)
PROMPT ============================================================
SELECT 'SCALAR_DUP_GROUPS' chk,
       (SELECT COUNT(*) FROM (
          SELECT d.d1_usage_id, d.seq_num
          FROM cisadm.d1_usage_scalar_dtl d
          JOIN cisadm.d1_usage u ON u.d1_usage_id = d.d1_usage_id
          WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm))
                >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24)
          GROUP BY d.d1_usage_id, d.seq_num
          HAVING COUNT(*) > 1
       )) raw_dup_groups,
       (SELECT COUNT(*) FROM (
          SELECT d1_usage_id, seq_num
          FROM cisadm.d1_usage_scalar_dtl_rpt_curr
          GROUP BY d1_usage_id, seq_num
          HAVING COUNT(*) > 1
       )) snap_dup_groups
FROM dual;

PROMPT ============================================================
PROMPT CS cutover QA — CMS SA LDAY + object health
PROMPT ============================================================
SELECT TRIM(cm_snapshot_type_flg) typ, COUNT(*) rows_n,
       COUNT(DISTINCT sa_id) sa_n, SUM(cur_bal) sum_cur
FROM cisadm.cms_sa_snapshot
GROUP BY TRIM(cm_snapshot_type_flg)
ORDER BY 1;

SELECT object_name, object_type, status
FROM all_objects
WHERE owner = 'CISADM'
  AND (
    object_name LIKE 'REFRESH_%RPT_CURR'
    OR object_name IN ('CMS_SA_SNAPSHOT', 'REFRESH_CMS_SA_SNAPSHOT')
  )
ORDER BY 1, 2;

PROMPT ============================================================
PROMPT CS cutover QA — scheduler health (rolling jobs)
PROMPT ============================================================
SELECT job_name, enabled, state,
       TO_CHAR(last_start_date,'YYYY-MM-DD HH24:MI') last_start,
       TO_CHAR(next_run_date,'YYYY-MM-DD HH24:MI') next_run
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND (
    job_name LIKE 'JOB_REFRESH_%RPT_CURR'
    OR job_name LIKE 'REFRESH_%RPT_CURR_JOB'
    OR job_name = 'JOB_REFRESH_CMS_SA_SNAPSHOT'
  )
ORDER BY 1;

PROMPT ============================================================
PROMPT CS cutover QA — FAIL rows (expect 0)
PROMPT ============================================================
SELECT chk, raw_rows, snap_rows, snap_rows - raw_rows AS diff, 'COUNT_MISMATCH' AS failure_code
FROM (
    SELECT 'BSEG_BILLED' chk,
           (SELECT COUNT(*) FROM cisadm.ci_bseg bseg
            JOIN cisadm.ci_bill bill ON bill.bill_id = bseg.bill_id AND bill.bill_stat_flg = 'C '
            WHERE bill.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24)) raw_rows,
           (SELECT COUNT(*) FROM cisadm.bseg_billed_usage_rpt_curr
            WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24)) snap_rows
    FROM dual
    UNION ALL
    SELECT 'BSEG_SQ',
           (SELECT COUNT(*) FROM cisadm.ci_bseg_sq sq
            JOIN cisadm.ci_bseg bseg ON bseg.bseg_id = sq.bseg_id
            JOIN cisadm.ci_bill bill ON bill.bill_id = bseg.bill_id AND bill.bill_stat_flg = 'C '
            WHERE bill.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24)),
           (SELECT COUNT(*) FROM cisadm.bseg_sq_usage_rpt_curr
            WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24))
    FROM dual
    UNION ALL
    SELECT 'FT_RPT',
           (SELECT COUNT(*) FROM cisadm.ci_ft
            WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) AND redundant_sw = 'N'),
           (SELECT COUNT(*) FROM cisadm.ft_rpt_curr
            WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24))
    FROM dual
    UNION ALL
    SELECT 'FT_GL',
           (SELECT COUNT(*) FROM cisadm.ci_ft_gl gl
            JOIN cisadm.ci_ft ft ON ft.ft_id = gl.ft_id
            WHERE ft.accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24)),
           (SELECT COUNT(*) FROM cisadm.ft_gl_distribution_rpt_curr
            WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24))
    FROM dual
    UNION ALL
    SELECT 'D1_MSRMT',
           (SELECT COUNT(*) FROM cisadm.d1_msrmt
            WHERE msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24)),
           (SELECT COUNT(*) FROM cisadm.d1_msrmt_rpt_curr
            WHERE msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24))
    FROM dual
    UNION ALL
    SELECT 'D1_USAGE_3MO',
           (SELECT COUNT(*) FROM cisadm.d1_usage u
            WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm))
                  >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3)),
           (SELECT COUNT(*) FROM cisadm.d1_usage_rpt_curr
            WHERE NVL(start_dttm, NVL(usage_cre_dttm, status_upd_dttm))
                  >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3))
    FROM dual
    UNION ALL
    SELECT 'D1_SCALAR_BY_START_3MO',
           (SELECT COUNT(*) FROM cisadm.d1_usage_scalar_dtl d
            WHERE d.start_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3)),
           (SELECT COUNT(*) FROM cisadm.d1_usage_scalar_dtl_rpt_curr
            WHERE start_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3))
    FROM dual
    UNION ALL
    SELECT 'D1_SCALAR_BY_USAGE_3MO',
           (SELECT COUNT(*) FROM cisadm.d1_usage_scalar_dtl d
            JOIN cisadm.d1_usage u ON u.d1_usage_id = d.d1_usage_id
            WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm))
                  >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3)),
           (SELECT COUNT(*) FROM cisadm.d1_usage_scalar_dtl_rpt_curr s
            WHERE EXISTS (
              SELECT 1 FROM cisadm.d1_usage_rpt_curr u
              WHERE u.d1_usage_id = s.d1_usage_id
                AND NVL(u.start_dttm, NVL(u.usage_cre_dttm, u.status_upd_dttm))
                    >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3)
            ))
    FROM dual
    UNION ALL
    SELECT 'SCALAR_DUP_GROUPS',
           (SELECT COUNT(*) FROM (
              SELECT d.d1_usage_id, d.seq_num
              FROM cisadm.d1_usage_scalar_dtl d
              JOIN cisadm.d1_usage u ON u.d1_usage_id = d.d1_usage_id
              WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm))
                    >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24)
              GROUP BY d.d1_usage_id, d.seq_num
              HAVING COUNT(*) > 1
           )),
           (SELECT COUNT(*) FROM (
              SELECT d1_usage_id, seq_num
              FROM cisadm.d1_usage_scalar_dtl_rpt_curr
              GROUP BY d1_usage_id, seq_num
              HAVING COUNT(*) > 1
           ))
    FROM dual
)
WHERE snap_rows <> raw_rows

UNION ALL

SELECT src, older_than_2yr, 0, older_than_2yr, 'RETENTION_BREACH'
FROM (
    SELECT 'BSEG_BILLED' src,
           SUM(CASE WHEN bill_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END) older_than_2yr
    FROM cisadm.bseg_billed_usage_rpt_curr
    UNION ALL
    SELECT 'BSEG_SQ',
           SUM(CASE WHEN bill_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END)
    FROM cisadm.bseg_sq_usage_rpt_curr
    UNION ALL
    SELECT 'FT_RPT',
           SUM(CASE WHEN accounting_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END)
    FROM cisadm.ft_rpt_curr
    UNION ALL
    SELECT 'FT_GL',
           SUM(CASE WHEN accounting_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END)
    FROM cisadm.ft_gl_distribution_rpt_curr
    UNION ALL
    SELECT 'D1_MSRMT',
           SUM(CASE WHEN msrmt_dttm < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END)
    FROM cisadm.d1_msrmt_rpt_curr
    UNION ALL
    SELECT 'D1_USAGE',
           SUM(CASE WHEN NVL(end_dttm,start_dttm) < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END)
    FROM cisadm.d1_usage_rpt_curr
    UNION ALL
    SELECT 'D1_USAGE_SCALAR',
           SUM(CASE WHEN NVL(usage_end_dttm,end_dttm) < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -24) THEN 1 ELSE 0 END)
    FROM cisadm.d1_usage_scalar_dtl_rpt_curr
)
WHERE older_than_2yr > 0;
