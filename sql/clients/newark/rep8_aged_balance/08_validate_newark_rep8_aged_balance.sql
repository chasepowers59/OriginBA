-- Validate JRS2C2M.NEWARK_REP8_AGED_BALANCE after refresh.
-- Compares account current balance to CISADM.CMS_SA_SNAPSHOT (LDAY) rollup where available.

PROMPT --- Object status ---
SELECT owner, object_name, object_type, status
FROM all_objects
WHERE (owner = 'CISADM' AND object_name IN ('NEWARK_REP8_AGED_BALANCE', 'REFRESH_NEWARK_REP8_AGED_BALANCE'))
   OR (owner = 'JRS2C2M' AND object_name IN ('NEWARK_REP8_AGED_BALANCE', 'NEWARK_REP8_AGED_BALANCE_CURR'))
ORDER BY owner, object_type, object_name;

PROMPT --- Staging slice summary ---
SELECT
    rpt_dt,
    COUNT(*) AS row_count,
    ROUND(SUM(current_bal), 2) AS sum_current_bal,
    ROUND(SUM(arrears_total), 2) AS sum_arrears_total,
    MIN(refreshed_at) AS refreshed_at
FROM jrs2c2m.newark_rep8_aged_balance
GROUP BY rpt_dt
ORDER BY rpt_dt DESC;

PROMPT --- Population parity vs CM_AGED_BALANCE (latest rpt_dt) ---
WITH latest AS (
    SELECT MAX(rpt_dt) AS rpt_dt
    FROM jrs2c2m.newark_rep8_aged_balance
),
stg AS (
    SELECT COUNT(*) AS stg_cnt
    FROM jrs2c2m.newark_rep8_aged_balance s
    CROSS JOIN latest l
    WHERE s.rpt_dt = l.rpt_dt
),
dem AS (
    SELECT COUNT(*) AS dem_cnt
    FROM jrs2c2m.cm_aged_balance
)
SELECT stg.stg_cnt,
       dem.dem_cnt,
       stg.stg_cnt - dem.dem_cnt AS row_delta
FROM stg
CROSS JOIN dem;

PROMPT --- Current balance parity vs CMS_SA_SNAPSHOT LDAY total (latest rpt_dt) ---
WITH latest AS (
    SELECT MAX(rpt_dt) AS rpt_dt
    FROM jrs2c2m.newark_rep8_aged_balance
),
stg AS (
    SELECT ROUND(SUM(s.current_bal), 2) AS stg_current_bal
    FROM jrs2c2m.newark_rep8_aged_balance s
    CROSS JOIN latest l
    WHERE s.rpt_dt = l.rpt_dt
),
sa AS (
    SELECT ROUND(SUM(s.cur_bal), 2) AS sa_current_bal
    FROM cisadm.cms_sa_snapshot s
    CROSS JOIN latest l
    WHERE s.cm_snapshot_type_flg = 'LDAY'
      AND s.c1_snapshot_dt = l.rpt_dt
)
SELECT stg.stg_current_bal,
       sa.sa_current_bal,
       stg.stg_current_bal - sa.sa_current_bal AS current_bal_delta
FROM stg
CROSS JOIN sa;

PROMPT --- Account-level current balance vs CMS_SA_SNAPSHOT LDAY (latest rpt_dt) ---
WITH latest AS (
    SELECT MAX(rpt_dt) AS rpt_dt
    FROM jrs2c2m.newark_rep8_aged_balance
),
sa_acct AS (
    SELECT
        s.acct_id,
        ROUND(SUM(s.cur_bal), 2) AS sa_cur_bal
    FROM cisadm.cms_sa_snapshot s
    CROSS JOIN latest l
    WHERE s.cm_snapshot_type_flg = 'LDAY'
      AND s.c1_snapshot_dt = l.rpt_dt
    GROUP BY s.acct_id
),
rep8 AS (
    SELECT
        r.account,
        ROUND(r.current_bal, 2) AS rep8_current_bal
    FROM jrs2c2m.newark_rep8_aged_balance r
    CROSS JOIN latest l
    WHERE r.rpt_dt = l.rpt_dt
),
cmp AS (
    SELECT
        COALESCE(sa.acct_id, rep8.account) AS acct_id,
        NVL(sa.sa_cur_bal, 0) AS sa_cur_bal,
        NVL(rep8.rep8_current_bal, 0) AS rep8_current_bal
    FROM sa_acct sa
    FULL OUTER JOIN rep8
      ON rep8.account = sa.acct_id
)
SELECT
    COUNT(*) AS compared_accounts,
    SUM(CASE WHEN ABS(sa_cur_bal - rep8_current_bal) > 0.01 THEN 1 ELSE 0 END) AS mismatch_accounts,
    ROUND(SUM(sa_cur_bal), 2) AS sum_sa_cur_bal,
    ROUND(SUM(rep8_current_bal), 2) AS sum_rep8_current_bal,
    ROUND(SUM(rep8_current_bal) - SUM(sa_cur_bal), 2) AS sum_delta
FROM cmp;

PROMPT --- Top 10 account deltas (CMS_SA vs REP8 current_bal) ---
WITH latest AS (
    SELECT MAX(rpt_dt) AS rpt_dt
    FROM jrs2c2m.newark_rep8_aged_balance
),
sa_acct AS (
    SELECT
        s.acct_id,
        ROUND(SUM(s.cur_bal), 2) AS sa_cur_bal
    FROM cisadm.cms_sa_snapshot s
    CROSS JOIN latest l
    WHERE s.cm_snapshot_type_flg = 'LDAY'
      AND s.c1_snapshot_dt = l.rpt_dt
    GROUP BY s.acct_id
),
rep8 AS (
    SELECT
        r.account,
        ROUND(r.current_bal, 2) AS rep8_current_bal
    FROM jrs2c2m.newark_rep8_aged_balance r
    CROSS JOIN latest l
    WHERE r.rpt_dt = l.rpt_dt
)
SELECT *
FROM (
    SELECT
        COALESCE(sa.acct_id, rep8.account) AS acct_id,
        NVL(sa.sa_cur_bal, 0) AS sa_cur_bal,
        NVL(rep8.rep8_current_bal, 0) AS rep8_current_bal,
        NVL(rep8.rep8_current_bal, 0) - NVL(sa.sa_cur_bal, 0) AS delta
    FROM sa_acct sa
    FULL OUTER JOIN rep8
      ON rep8.account = sa.acct_id
    WHERE ABS(NVL(rep8.rep8_current_bal, 0) - NVL(sa.sa_cur_bal, 0)) > 0.01
    ORDER BY ABS(NVL(rep8.rep8_current_bal, 0) - NVL(sa.sa_cur_bal, 0)) DESC
)
WHERE ROWNUM <= 10;

PROMPT --- Arrears total parity vs CMS_SA_SNAPSHOT LDAY (latest rpt_dt) ---
WITH latest AS (
    SELECT MAX(rpt_dt) AS rpt_dt
    FROM jrs2c2m.newark_rep8_aged_balance
),
sa_acct AS (
    SELECT
        s.acct_id,
        ROUND(SUM(s.ars_amt2 + s.ars_amt3 + s.ars_amt4 + s.ars_amt5), 2) AS sa_arrears_total
    FROM cisadm.cms_sa_snapshot s
    CROSS JOIN latest l
    WHERE s.cm_snapshot_type_flg = 'LDAY'
      AND s.c1_snapshot_dt = l.rpt_dt
    GROUP BY s.acct_id
),
rep8 AS (
    SELECT
        r.account,
        ROUND(r.arrears_total, 2) AS rep8_arrears_total
    FROM jrs2c2m.newark_rep8_aged_balance r
    CROSS JOIN latest l
    WHERE r.rpt_dt = l.rpt_dt
),
cmp AS (
    SELECT
        COALESCE(sa.acct_id, rep8.account) AS acct_id,
        NVL(sa.sa_arrears_total, 0) AS sa_arrears_total,
        NVL(rep8.rep8_arrears_total, 0) AS rep8_arrears_total
    FROM sa_acct sa
    FULL OUTER JOIN rep8
      ON rep8.account = sa.acct_id
)
SELECT
    COUNT(*) AS compared_accounts,
    SUM(CASE WHEN ABS(sa_arrears_total - rep8_arrears_total) > 0.01 THEN 1 ELSE 0 END) AS mismatch_accounts,
    ROUND(SUM(sa_arrears_total), 2) AS sum_sa_arrears_total,
    ROUND(SUM(rep8_arrears_total), 2) AS sum_rep8_arrears_total,
    ROUND(SUM(rep8_arrears_total) - SUM(sa_arrears_total), 2) AS sum_delta
FROM cmp;

PROMPT --- Top 10 arrears_total deltas (CMS_SA vs REP8) ---
WITH latest AS (
    SELECT MAX(rpt_dt) AS rpt_dt
    FROM jrs2c2m.newark_rep8_aged_balance
),
sa_acct AS (
    SELECT
        s.acct_id,
        ROUND(SUM(s.ars_amt2 + s.ars_amt3 + s.ars_amt4 + s.ars_amt5), 2) AS sa_arrears_total
    FROM cisadm.cms_sa_snapshot s
    CROSS JOIN latest l
    WHERE s.cm_snapshot_type_flg = 'LDAY'
      AND s.c1_snapshot_dt = l.rpt_dt
    GROUP BY s.acct_id
),
rep8 AS (
    SELECT
        r.account,
        ROUND(r.arrears_total, 2) AS rep8_arrears_total
    FROM jrs2c2m.newark_rep8_aged_balance r
    CROSS JOIN latest l
    WHERE r.rpt_dt = l.rpt_dt
)
SELECT *
FROM (
    SELECT
        COALESCE(sa.acct_id, rep8.account) AS acct_id,
        NVL(sa.sa_arrears_total, 0) AS sa_arrears_total,
        NVL(rep8.rep8_arrears_total, 0) AS rep8_arrears_total,
        NVL(rep8.rep8_arrears_total, 0) - NVL(sa.sa_arrears_total, 0) AS delta
    FROM sa_acct sa
    FULL OUTER JOIN rep8
      ON rep8.account = sa.acct_id
    WHERE ABS(NVL(rep8.rep8_arrears_total, 0) - NVL(sa.sa_arrears_total, 0)) > 0.01
    ORDER BY ABS(NVL(rep8.rep8_arrears_total, 0) - NVL(sa.sa_arrears_total, 0)) DESC
)
WHERE ROWNUM <= 10;

PROMPT --- Interactive read timing (should be seconds, not minutes) ---
SELECT COUNT(*) AS curr_view_rows
FROM jrs2c2m.newark_rep8_aged_balance_curr;
