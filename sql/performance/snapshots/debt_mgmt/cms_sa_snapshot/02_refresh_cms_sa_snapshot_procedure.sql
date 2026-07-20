-- Refresh procedure for CISADM.CMS_SA_SNAPSHOT.
-- Rebuilds one current "LDAY" (end-of-day) SA arrears snapshot from governed CI_FT.
-- Matches the Standard Offering SA Snapshot domain column contract.
-- CMS_ACCT_SNAPSHOT is NOT a physical table; Domain SQL aggregates this table by ACCT_ID.
--
-- Balance rule (aligns to CIS SA Current Balance):
--   Only frozen ARS FTs with ARS_DT <= today (excludes CIS "Future" / not-yet-due).
--   CUR_BAL / TOT_BAL include payments/credits so amounts match CIS unpaid / payoff current.
-- Aging rule (FIFO):
--   Positive CUR_AMT rows are aged by their ARS_DT (open bill / charge age).
--   Negative CUR_AMT rows (payments, credits) reduce the oldest open debt first.
--   Excess credit (overpayment) is held in ARS_AMT1 (0-30 / current) as a negative.
--   Bucket sum ARS_AMT1..5 always equals CUR_BAL.
--   Future-dated ARS_DT amounts are not aged and not included in CUR_BAL.

CREATE OR REPLACE PROCEDURE cisadm.refresh_cms_sa_snapshot AS
    v_snapshot_dt DATE := TRUNC(SYSDATE);
    v_load_dt     DATE := TRUNC(SYSDATE) + 1;
BEGIN
    -- Keep only the current LDAY slice when refreshing (domain current-state use).
    DELETE FROM cisadm.cms_sa_snapshot
    WHERE cm_snapshot_type_flg = 'LDAY';
    COMMIT;

    INSERT INTO cisadm.cms_sa_snapshot (
        sa_id,
        c1_snapshot_dt,
        cm_snapshot_type_flg,
        acct_id,
        per_id,
        currency_cd,
        cur_bal,
        tot_bal,
        new_chg_bal,
        ars_amt1,
        ars_amt2,
        ars_amt3,
        ars_amt4,
        ars_amt5,
        ars_amt6,
        ars_amt7,
        ars_amt8,
        ars_amt9,
        ars_amt10,
        sa_snapshot_cnt,
        ilm_dt,
        ilm_arch_sw
    )
    WITH
    sa_main_cust AS (
        SELECT
            ap.acct_id,
            ap.per_id,
            ROW_NUMBER() OVER (
                PARTITION BY ap.acct_id
                ORDER BY
                    CASE WHEN ap.main_cust_sw = 'Y' THEN 0 ELSE 1 END,
                    ap.per_id
            ) AS rn
        FROM cisadm.ci_acct_per ap
    ),
    base_ft AS (
        SELECT
            ft.sa_id,
            TRUNC(ft.ars_dt) AS ars_dt,
            ft.ft_id,
            NVL(ft.cur_amt, 0) AS cur_amt,
            NVL(ft.tot_amt, 0) AS tot_amt,
            CASE WHEN NVL(ft.cur_amt, 0) > 0 THEN NVL(ft.cur_amt, 0) ELSE 0 END AS debt_amt,
            CASE WHEN NVL(ft.cur_amt, 0) < 0 THEN -NVL(ft.cur_amt, 0) ELSE 0 END AS credit_amt
        FROM cisadm.ci_ft ft
        WHERE ft.freeze_sw = 'Y'
          AND ft.not_in_ars_sw = 'N'
          AND ft.ars_dt IS NOT NULL
          -- Match CIS Current / aged past-due; exclude not-yet-due ("Future")
          AND TRUNC(ft.ars_dt) <= TRUNC(SYSDATE)
    ),
    sa_tot AS (
        SELECT
            sa_id,
            SUM(cur_amt) AS cur_bal,
            SUM(tot_amt) AS tot_bal,
            SUM(debt_amt) AS total_debt,
            SUM(credit_amt) AS total_credit
        FROM base_ft
        GROUP BY sa_id
    ),
    debt_rows AS (
        SELECT
            b.sa_id,
            b.ars_dt,
            b.ft_id,
            b.debt_amt,
            SUM(b.debt_amt) OVER (
                PARTITION BY b.sa_id
                ORDER BY b.ars_dt, b.ft_id
                ROWS UNBOUNDED PRECEDING
            ) AS cum_debt
        FROM base_ft b
        WHERE b.debt_amt > 0
    ),
    unpaid_debt AS (
        SELECT
            d.sa_id,
            d.ars_dt,
            GREATEST(0, d.cum_debt - t.total_credit)
                - GREATEST(0, (d.cum_debt - d.debt_amt) - t.total_credit) AS unpaid_amt
        FROM debt_rows d
        INNER JOIN sa_tot t
            ON t.sa_id = d.sa_id
    ),
    aged_debt AS (
        SELECT
            sa_id,
            NVL(SUM(CASE WHEN TRUNC(SYSDATE) - ars_dt BETWEEN 0 AND 30 THEN unpaid_amt ELSE 0 END), 0) AS ars_amt1,
            NVL(SUM(CASE WHEN TRUNC(SYSDATE) - ars_dt BETWEEN 31 AND 60 THEN unpaid_amt ELSE 0 END), 0) AS ars_amt2,
            NVL(SUM(CASE WHEN TRUNC(SYSDATE) - ars_dt BETWEEN 61 AND 90 THEN unpaid_amt ELSE 0 END), 0) AS ars_amt3,
            NVL(SUM(CASE WHEN TRUNC(SYSDATE) - ars_dt BETWEEN 91 AND 120 THEN unpaid_amt ELSE 0 END), 0) AS ars_amt4,
            NVL(SUM(CASE WHEN TRUNC(SYSDATE) - ars_dt > 120 THEN unpaid_amt ELSE 0 END), 0) AS ars_amt5
        FROM unpaid_debt
        GROUP BY sa_id
    ),
    governed_ft AS (
        SELECT
            t.sa_id,
            t.cur_bal,
            t.tot_bal,
            0 AS new_chg_bal,
            -- Excess credit (overpayment) held in current bucket
            NVL(a.ars_amt1, 0) - GREATEST(0, t.total_credit - t.total_debt) AS ars_amt1,
            NVL(a.ars_amt2, 0) AS ars_amt2,
            NVL(a.ars_amt3, 0) AS ars_amt3,
            NVL(a.ars_amt4, 0) AS ars_amt4,
            NVL(a.ars_amt5, 0) AS ars_amt5
        FROM sa_tot t
        LEFT JOIN aged_debt a
            ON a.sa_id = t.sa_id
    )
    SELECT
        sa.sa_id,
        v_snapshot_dt AS c1_snapshot_dt,
        'LDAY' AS cm_snapshot_type_flg,
        sa.acct_id,
        NVL(smc.per_id, '          ') AS per_id,
        NVL(acct.currency_cd, 'USD') AS currency_cd,
        gf.cur_bal,
        gf.tot_bal,
        gf.new_chg_bal,
        gf.ars_amt1,
        gf.ars_amt2,
        gf.ars_amt3,
        gf.ars_amt4,
        gf.ars_amt5,
        0 AS ars_amt6,
        0 AS ars_amt7,
        0 AS ars_amt8,
        0 AS ars_amt9,
        0 AS ars_amt10,
        1 AS sa_snapshot_cnt,
        v_load_dt AS ilm_dt,
        'N' AS ilm_arch_sw
    FROM governed_ft gf
    INNER JOIN cisadm.ci_sa sa
        ON sa.sa_id = gf.sa_id
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = sa.acct_id
    LEFT JOIN sa_main_cust smc
        ON smc.acct_id = sa.acct_id
       AND smc.rn = 1;

    COMMIT;
END;
/
