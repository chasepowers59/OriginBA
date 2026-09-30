-- SQL Developer performance checks for ACCT_DEBT_RPT_CURR
--
-- Run with F5 in SQL Developer so elapsed time is shown for each statement.
-- These checks mirror the two-phase refresh:
--   1) base debt fact build
--   2) optional enrichment passes

SET TIMING ON;

--------------------------------------------------------------------------------
-- 1) FT aggregation baseline
--------------------------------------------------------------------------------
WITH governed_ft AS (
    SELECT
        ft.sa_id,
        COUNT(*) AS governed_arrears_ft_count,
        SUM(ft.cur_amt) AS total_debt
    FROM cisadm.ci_ft ft
    WHERE ft.freeze_sw = 'Y'
      AND ft.not_in_ars_sw = 'N'
      AND ft.ft_type_flg NOT IN ('PS', 'PX')
      AND ft.ars_dt IS NOT NULL
    GROUP BY ft.sa_id
)
SELECT
    COUNT(*) AS debt_sa_count,
    SUM(governed_arrears_ft_count) AS governed_arrears_ft_count,
    SUM(total_debt) AS total_debt
FROM governed_ft;

--------------------------------------------------------------------------------
-- 2) FT aggregation + active SA join baseline
--------------------------------------------------------------------------------
WITH governed_ft AS (
    SELECT
        ft.sa_id,
        COUNT(*) AS governed_arrears_ft_count,
        SUM(ft.cur_amt) AS total_debt
    FROM cisadm.ci_ft ft
    WHERE ft.freeze_sw = 'Y'
      AND ft.not_in_ars_sw = 'N'
      AND ft.ft_type_flg NOT IN ('PS', 'PX')
      AND ft.ars_dt IS NOT NULL
    GROUP BY ft.sa_id
),
debt_sa AS (
    SELECT
        sa.sa_id,
        sa.acct_id,
        gf.governed_arrears_ft_count,
        gf.total_debt
    FROM governed_ft gf
    JOIN cisadm.ci_sa sa
      ON sa.sa_id = gf.sa_id
     AND sa.sa_status_flg = '20'
)
SELECT
    COUNT(*) AS debt_sa_count,
    COUNT(DISTINCT acct_id) AS debt_acct_count,
    SUM(total_debt) AS total_debt
FROM debt_sa;

--------------------------------------------------------------------------------
-- 3) Core positive-debt account rollup baseline
--------------------------------------------------------------------------------
WITH governed_ft AS (
    SELECT
        ft.sa_id,
        SUM(ft.cur_amt) AS total_debt
    FROM cisadm.ci_ft ft
    WHERE ft.freeze_sw = 'Y'
      AND ft.not_in_ars_sw = 'N'
      AND ft.ft_type_flg NOT IN ('PS', 'PX')
      AND ft.ars_dt IS NOT NULL
    GROUP BY ft.sa_id
),
debt_sa AS (
    SELECT
        sa.acct_id,
        gf.total_debt
    FROM governed_ft gf
    JOIN cisadm.ci_sa sa
      ON sa.sa_id = gf.sa_id
     AND sa.sa_status_flg = '20'
)
SELECT
    COUNT(*) AS acct_count,
    SUM(total_debt) AS total_debt
FROM (
    SELECT
        acct_id,
        SUM(total_debt) AS total_debt
    FROM debt_sa
    GROUP BY acct_id
    HAVING SUM(total_debt) > 0
);

--------------------------------------------------------------------------------
-- 4) Active-SA/debt-class profile baseline
--------------------------------------------------------------------------------
WITH governed_ft AS (
    SELECT
        ft.sa_id,
        SUM(ft.cur_amt) AS total_debt
    FROM cisadm.ci_ft ft
    WHERE ft.freeze_sw = 'Y'
      AND ft.not_in_ars_sw = 'N'
      AND ft.ft_type_flg NOT IN ('PS', 'PX')
      AND ft.ars_dt IS NOT NULL
    GROUP BY ft.sa_id
),
debt_accounts AS (
    SELECT acct_id
    FROM (
        SELECT
            sa.acct_id,
            SUM(gf.total_debt) AS total_debt
        FROM governed_ft gf
        JOIN cisadm.ci_sa sa
          ON sa.sa_id = gf.sa_id
         AND sa.sa_status_flg = '20'
        GROUP BY sa.acct_id
    )
    WHERE total_debt > 0
)
SELECT
    COUNT(*) AS sa_profile_rows
FROM (
    SELECT
        sa.acct_id
    FROM cisadm.ci_sa sa
    JOIN debt_accounts da
      ON da.acct_id = sa.acct_id
    LEFT JOIN cisadm.ci_sa_type st
      ON st.sa_type_cd = sa.sa_type_cd
     AND st.cis_division = sa.cis_division
    WHERE sa.sa_status_flg = '20'
    GROUP BY sa.acct_id
);

--------------------------------------------------------------------------------
-- 5) Customer-name enrichment baseline for positive-debt accounts
--------------------------------------------------------------------------------
WITH governed_ft AS (
    SELECT
        ft.sa_id,
        SUM(ft.cur_amt) AS total_debt
    FROM cisadm.ci_ft ft
    WHERE ft.freeze_sw = 'Y'
      AND ft.not_in_ars_sw = 'N'
      AND ft.ft_type_flg NOT IN ('PS', 'PX')
      AND ft.ars_dt IS NOT NULL
    GROUP BY ft.sa_id
),
debt_accounts AS (
    SELECT acct_id
    FROM (
        SELECT
            sa.acct_id,
            SUM(gf.total_debt) AS total_debt
        FROM governed_ft gf
        JOIN cisadm.ci_sa sa
          ON sa.sa_id = gf.sa_id
         AND sa.sa_status_flg = '20'
        GROUP BY sa.acct_id
    )
    WHERE total_debt > 0
)
SELECT
    COUNT(*) AS customer_enrichment_rows
FROM (
    SELECT
        ap.acct_id
    FROM cisadm.ci_acct_per ap
    JOIN cisadm.ci_per_name pn
      ON pn.per_id = ap.per_id
    JOIN debt_accounts da
      ON da.acct_id = ap.acct_id
    WHERE ap.main_cust_sw = 'Y'
      AND (pn.prim_name_sw = 'Y' OR pn.name_type_flg = 'PRIM')
    GROUP BY ap.acct_id
)
;

--------------------------------------------------------------------------------
-- 6) Latest collection process enrichment baseline
--------------------------------------------------------------------------------
WITH governed_ft AS (
    SELECT
        ft.sa_id,
        SUM(ft.cur_amt) AS total_debt
    FROM cisadm.ci_ft ft
    WHERE ft.freeze_sw = 'Y'
      AND ft.not_in_ars_sw = 'N'
      AND ft.ft_type_flg NOT IN ('PS', 'PX')
      AND ft.ars_dt IS NOT NULL
    GROUP BY ft.sa_id
),
debt_accounts AS (
    SELECT acct_id
    FROM (
        SELECT
            sa.acct_id,
            SUM(gf.total_debt) AS total_debt
        FROM governed_ft gf
        JOIN cisadm.ci_sa sa
          ON sa.sa_id = gf.sa_id
         AND sa.sa_status_flg = '20'
        GROUP BY sa.acct_id
    )
    WHERE total_debt > 0
)
SELECT
    COUNT(*) AS latest_coll_proc_rows
FROM (
    SELECT
        cp.acct_id,
        ROW_NUMBER() OVER (
            PARTITION BY cp.acct_id
            ORDER BY cp.cre_dttm DESC, cp.coll_proc_id DESC
        ) AS rn
    FROM cisadm.ci_coll_proc cp
    JOIN debt_accounts da
      ON da.acct_id = cp.acct_id
)
WHERE rn = 1;

--------------------------------------------------------------------------------
-- 7) Latest write-off process enrichment baseline
--------------------------------------------------------------------------------
WITH governed_ft AS (
    SELECT
        ft.sa_id,
        SUM(ft.cur_amt) AS total_debt
    FROM cisadm.ci_ft ft
    WHERE ft.freeze_sw = 'Y'
      AND ft.not_in_ars_sw = 'N'
      AND ft.ft_type_flg NOT IN ('PS', 'PX')
      AND ft.ars_dt IS NOT NULL
    GROUP BY ft.sa_id
),
debt_accounts AS (
    SELECT acct_id
    FROM (
        SELECT
            sa.acct_id,
            SUM(gf.total_debt) AS total_debt
        FROM governed_ft gf
        JOIN cisadm.ci_sa sa
          ON sa.sa_id = gf.sa_id
         AND sa.sa_status_flg = '20'
        GROUP BY sa.acct_id
    )
    WHERE total_debt > 0
)
SELECT
    COUNT(*) AS latest_wo_proc_rows
FROM (
    SELECT
        vw.acct_id,
        ROW_NUMBER() OVER (
            PARTITION BY vw.acct_id
            ORDER BY vw.cre_dttm DESC, vw.uncoll_proc_id DESC
        ) AS rn
    FROM cisadm.c1_bi_woproc_vw vw
    JOIN debt_accounts da
      ON da.acct_id = vw.acct_id
)
WHERE rn = 1;

SET TIMING OFF;
