-- SCS-2322 read-only AR aging bake-off (CityCorp PROD).
-- Compare SA CUR_AMT vs FT_GL by Dist Code under three date bases.

SELECT SYSDATE AS db_now FROM dual;

-- LDAY snapshot if present
SELECT cm_snapshot_type_flg,
       COUNT(*) AS sa_cnt,
       ROUND(SUM(cur_bal), 2) AS sum_cur_bal,
       MAX(c1_snapshot_dt) AS max_snap_dt
FROM cisadm.cms_sa_snapshot
GROUP BY cm_snapshot_type_flg
ORDER BY 1;

-- Dist-code rollup (Jeremy Ad Hoc shape) as-of today, ARS due/past
WITH sa_dst AS (
    SELECT sa.sa_id, TRIM(st.dst_id) AS dst_id
    FROM cisadm.ci_sa sa
    JOIN cisadm.ci_sa_type st
      ON st.sa_type_cd = sa.sa_type_cd
     AND st.cis_division = sa.cis_division
)
SELECT d.dst_id,
       ROUND(SUM(ft.cur_amt), 2) AS current_bal
FROM cisadm.ci_ft ft
JOIN sa_dst d ON d.sa_id = ft.sa_id
WHERE ft.freeze_sw = 'Y'
  AND ft.not_in_ars_sw = 'N'
  AND ft.ars_dt IS NOT NULL
  AND ft.ars_dt <= TRUNC(SYSDATE)
GROUP BY d.dst_id
ORDER BY ABS(SUM(ft.cur_amt)) DESC;

-- Same rollup as-of fiscal EOY 2026-06-30
WITH sa_dst AS (
    SELECT sa.sa_id, TRIM(st.dst_id) AS dst_id
    FROM cisadm.ci_sa sa
    JOIN cisadm.ci_sa_type st
      ON st.sa_type_cd = sa.sa_type_cd
     AND st.cis_division = sa.cis_division
),
asof AS (SELECT DATE '2026-06-30' AS d FROM dual)
SELECT d.dst_id,
       ROUND(SUM(ft.cur_amt), 2) AS current_bal_eoy
FROM cisadm.ci_ft ft
JOIN sa_dst d ON d.sa_id = ft.sa_id
CROSS JOIN asof a
WHERE ft.freeze_sw = 'Y'
  AND ft.not_in_ars_sw = 'N'
  AND ft.ars_dt IS NOT NULL
  AND ft.ars_dt <= a.d
GROUP BY d.dst_id
ORDER BY ABS(SUM(ft.cur_amt)) DESC;

-- Internal balance: SA vs FT_GL same DST, three bases (today)
WITH sa_dst AS (
    SELECT sa.sa_id, TRIM(st.dst_id) AS dst_id
    FROM cisadm.ci_sa sa
    JOIN cisadm.ci_sa_type st
      ON st.sa_type_cd = sa.sa_type_cd
     AND st.cis_division = sa.cis_division
),
bases AS (
    SELECT 'ACCOUNTING_DT' AS basis FROM dual UNION ALL
    SELECT 'ARS_DT' FROM dual UNION ALL
    SELECT 'FREEZE_DT' FROM dual
),
sa AS (
    SELECT b.basis, d.dst_id, ROUND(SUM(ft.cur_amt), 2) AS sa_bal
    FROM bases b
    JOIN cisadm.ci_ft ft
      ON ft.freeze_sw = 'Y'
     AND ft.not_in_ars_sw = 'N'
     AND ft.ars_dt IS NOT NULL
    JOIN sa_dst d ON d.sa_id = ft.sa_id
    WHERE (b.basis = 'ARS_DT' AND ft.ars_dt <= TRUNC(SYSDATE))
       OR (b.basis = 'ACCOUNTING_DT'
           AND ft.accounting_dt <= TRUNC(SYSDATE)
           AND ft.ars_dt <= TRUNC(SYSDATE))
       OR (b.basis = 'FREEZE_DT'
           AND TRUNC(ft.freeze_dttm) <= TRUNC(SYSDATE)
           AND ft.ars_dt <= TRUNC(SYSDATE))
    GROUP BY b.basis, d.dst_id
),
gl AS (
    SELECT b.basis, TRIM(g.dst_id) AS dst_id, ROUND(SUM(g.amount), 2) AS gl_bal
    FROM bases b
    JOIN cisadm.ci_ft_gl g ON NVL(g.tot_amt_sw, 'Y') = 'Y'
    JOIN cisadm.ci_ft ft ON ft.ft_id = g.ft_id AND ft.freeze_sw = 'Y'
    WHERE (b.basis = 'ARS_DT'
           AND ft.ars_dt IS NOT NULL
           AND ft.ars_dt <= TRUNC(SYSDATE))
       OR (b.basis = 'ACCOUNTING_DT' AND ft.accounting_dt <= TRUNC(SYSDATE))
       OR (b.basis = 'FREEZE_DT' AND TRUNC(ft.freeze_dttm) <= TRUNC(SYSDATE))
    GROUP BY b.basis, TRIM(g.dst_id)
)
SELECT s.basis,
       s.dst_id,
       s.sa_bal,
       g.gl_bal,
       ROUND(s.sa_bal - g.gl_bal, 2) AS gap,
       CASE
           WHEN ABS(s.sa_bal - g.gl_bal) < 0.01 THEN 'BALANCES'
           ELSE 'GAP'
       END AS status
FROM sa s
JOIN gl g ON g.basis = s.basis AND g.dst_id = s.dst_id
WHERE s.dst_id IN (
    'A/R-WATER', 'A/R-SEWER', 'A/R-PA', 'A/P-OVPY', 'A/R-CARDS', 'A/R-SOLWST',
    'A/P-DEPOS', 'E-WO', 'E-WO-SAN', 'E-MISC'
)
ORDER BY s.dst_id,
         CASE s.basis WHEN 'ARS_DT' THEN 1 WHEN 'ACCOUNTING_DT' THEN 2 ELSE 3 END;

-- GL control totals by AR account (142000/050/060), as-of EOY, three bases
WITH asof AS (SELECT DATE '2026-06-30' AS d FROM dual),
gl AS (
    SELECT REGEXP_SUBSTR(g.gl_acct, '[0-9]+$') AS gl_num,
           g.amount,
           ft.accounting_dt,
           ft.ars_dt,
           TRUNC(ft.freeze_dttm) AS freeze_dt
    FROM cisadm.ci_ft_gl g
    JOIN cisadm.ci_ft ft ON ft.ft_id = g.ft_id
    WHERE ft.freeze_sw = 'Y'
      AND NVL(g.tot_amt_sw, 'Y') = 'Y'
      AND REGEXP_SUBSTR(g.gl_acct, '[0-9]+$') IN ('142000', '142050', '142060')
)
SELECT basis, gl_num, ROUND(SUM(amount), 2) AS cis_gl_bal, COUNT(*) AS gl_lines
FROM (
    SELECT 'ACCOUNTING_DT' AS basis, gl_num, amount
    FROM gl, asof WHERE accounting_dt <= asof.d
    UNION ALL
    SELECT 'ARS_DT', gl_num, amount
    FROM gl, asof WHERE ars_dt IS NOT NULL AND ars_dt <= asof.d
    UNION ALL
    SELECT 'FREEZE_DT', gl_num, amount
    FROM gl, asof WHERE freeze_dt <= asof.d
)
GROUP BY basis, gl_num
ORDER BY gl_num, basis;
