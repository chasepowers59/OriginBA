CREATE OR REPLACE PROCEDURE cisadm.refresh_acct_debt_rpt_curr AS
    v_load_dttm TIMESTAMP := SYSTIMESTAMP;
BEGIN
    DELETE FROM cisadm.acct_debt_rpt_curr;
    COMMIT;

    -- Base debt fact load: keep the first pass limited to account debt truth and
    -- low-risk account/debt-class context so the heavy CI_FT aggregation finishes
    -- before optional enrichments run.
    -- Avoid APPEND/direct-path here. The FT scan is the slowest part of the
    -- refresh, and APPEND holds a stronger table lock for the life of the
    -- statement, which makes the snapshot feel "stuck" to users.
    INSERT INTO cisadm.acct_debt_rpt_curr (
        acct_id,
        coll_cl_cd,
        coll_cl_desc,
        cr_review_dt,
        postpone_cr_rvw_dt,
        per_id,
        customer_name,
        active_sa_count,
        debt_cl_count,
        sole_debt_cl_cd,
        sole_debt_cl_desc,
        governed_arrears_ft_count,
        governed_arrears_sa_count,
        total_debt,
        debt_0_30,
        debt_31_60,
        debt_61_90,
        debt_over_90,
        oldest_age_days,
        newest_age_days,
        oldest_ars_dt,
        newest_ars_dt,
        load_dttm
    )
    WITH
    governed_ft AS (
        SELECT /*+ MATERIALIZE */
            ft.sa_id,
            COUNT(*) AS governed_arrears_ft_count,
            SUM(ft.cur_amt) AS total_debt,
            SUM(CASE WHEN TRUNC(SYSDATE) - ft.ars_dt <= 30 THEN ft.cur_amt ELSE 0 END) AS debt_0_30,
            SUM(CASE WHEN TRUNC(SYSDATE) - ft.ars_dt BETWEEN 31 AND 60 THEN ft.cur_amt ELSE 0 END) AS debt_31_60,
            SUM(CASE WHEN TRUNC(SYSDATE) - ft.ars_dt BETWEEN 61 AND 90 THEN ft.cur_amt ELSE 0 END) AS debt_61_90,
            SUM(CASE WHEN TRUNC(SYSDATE) - ft.ars_dt > 90 THEN ft.cur_amt ELSE 0 END) AS debt_over_90,
            MAX(TRUNC(SYSDATE) - ft.ars_dt) AS oldest_age_days,
            MIN(TRUNC(SYSDATE) - ft.ars_dt) AS newest_age_days,
            MIN(ft.ars_dt) AS oldest_ars_dt,
            MAX(ft.ars_dt) AS newest_ars_dt
        FROM cisadm.ci_ft ft
        WHERE ft.freeze_sw = 'Y'
          AND ft.not_in_ars_sw = 'N'
          AND ft.ft_type_flg NOT IN ('PS', 'PX')
          AND ft.ars_dt IS NOT NULL
        GROUP BY ft.sa_id
    ),
    debt_sa AS (
        SELECT /*+ MATERIALIZE */
            sa.sa_id,
            sa.acct_id,
            gf.governed_arrears_ft_count,
            gf.total_debt,
            gf.debt_0_30,
            gf.debt_31_60,
            gf.debt_61_90,
            gf.debt_over_90,
            gf.oldest_age_days,
            gf.newest_age_days,
            gf.oldest_ars_dt,
            gf.newest_ars_dt
        FROM governed_ft gf
        JOIN cisadm.ci_sa sa
            ON sa.sa_id = gf.sa_id
           AND sa.sa_status_flg = '20'
    ),
    debt_by_acct AS (
        SELECT /*+ MATERIALIZE */
            dsa.acct_id,
            SUM(dsa.governed_arrears_ft_count) AS governed_arrears_ft_count,
            COUNT(*) AS governed_arrears_sa_count,
            SUM(dsa.total_debt) AS total_debt,
            SUM(dsa.debt_0_30) AS debt_0_30,
            SUM(dsa.debt_31_60) AS debt_31_60,
            SUM(dsa.debt_61_90) AS debt_61_90,
            SUM(dsa.debt_over_90) AS debt_over_90,
            MAX(dsa.oldest_age_days) AS oldest_age_days,
            MIN(dsa.newest_age_days) AS newest_age_days,
            MIN(dsa.oldest_ars_dt) AS oldest_ars_dt,
            MAX(dsa.newest_ars_dt) AS newest_ars_dt
        FROM debt_sa dsa
        GROUP BY dsa.acct_id
        HAVING SUM(dsa.total_debt) > 0
    ),
    debt_accounts AS (
        SELECT /*+ MATERIALIZE */ debt.acct_id
        FROM debt_by_acct debt
    ),
    active_sa_for_debt_accounts AS (
        SELECT /*+ MATERIALIZE */
            sa.sa_id,
            sa.acct_id,
            st.debt_cl_cd
        FROM cisadm.ci_sa sa
        JOIN debt_accounts da
            ON da.acct_id = sa.acct_id
        LEFT JOIN cisadm.ci_sa_type st
            ON st.sa_type_cd = sa.sa_type_cd
           AND st.cis_division = sa.cis_division
        WHERE sa.sa_status_flg = '20'
    ),
    sa_profile AS (
        SELECT
            asa.acct_id,
            COUNT(*) AS active_sa_count,
            COUNT(DISTINCT asa.debt_cl_cd) AS debt_cl_count,
            CASE
                WHEN COUNT(DISTINCT asa.debt_cl_cd) = 1 THEN MIN(asa.debt_cl_cd)
            END AS sole_debt_cl_cd
        FROM active_sa_for_debt_accounts asa
        GROUP BY asa.acct_id
    )
    SELECT
        debt.acct_id,
        acct.coll_cl_cd,
        coll_cl.descr,
        acct.cr_review_dt,
        acct.postpone_cr_rvw_dt,
        CAST(NULL AS VARCHAR2(40)) AS per_id,
        CAST(NULL AS VARCHAR2(200)) AS customer_name,
        NVL(sa_prof.active_sa_count, 0),
        NVL(sa_prof.debt_cl_count, 0),
        sa_prof.sole_debt_cl_cd,
        debt_cl.descr,
        debt.governed_arrears_ft_count,
        debt.governed_arrears_sa_count,
        debt.total_debt,
        debt.debt_0_30,
        debt.debt_31_60,
        debt.debt_61_90,
        debt.debt_over_90,
        debt.oldest_age_days,
        debt.newest_age_days,
        debt.oldest_ars_dt,
        debt.newest_ars_dt,
        v_load_dttm
    FROM debt_by_acct debt
    JOIN cisadm.ci_acct acct
        ON acct.acct_id = debt.acct_id
    LEFT JOIN sa_profile sa_prof
        ON sa_prof.acct_id = debt.acct_id
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl
        ON coll_cl.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_debt_cl_l debt_cl
        ON debt_cl.debt_cl_cd = sa_prof.sole_debt_cl_cd
       AND debt_cl.language_cd = 'ENG';

    COMMIT;

    -- Optional enrichment pass: account name, last bill, collections, and
    -- write-off context are updated after the debt fact is committed.
    MERGE INTO cisadm.acct_debt_rpt_curr tgt
    USING (
        SELECT
            ap.acct_id,
            MAX(ap.per_id) KEEP (
                DENSE_RANK FIRST ORDER BY
                    CASE WHEN ap.fin_resp_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN ap.main_cust_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN pn.prim_name_sw = 'Y' THEN 0 ELSE 1 END,
                    pn.seq_num,
                    pn.per_id
            ) AS per_id,
            MAX(pn.entity_name_upr) KEEP (
                DENSE_RANK FIRST ORDER BY
                    CASE WHEN ap.fin_resp_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN ap.main_cust_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN pn.prim_name_sw = 'Y' THEN 0 ELSE 1 END,
                    pn.seq_num,
                    pn.per_id
            ) AS customer_name
        FROM cisadm.ci_acct_per ap
        JOIN cisadm.ci_per_name pn
            ON pn.per_id = ap.per_id
        JOIN (SELECT acct_id FROM cisadm.acct_debt_rpt_curr) debt
            ON debt.acct_id = ap.acct_id
        WHERE ap.main_cust_sw = 'Y'
          AND (pn.prim_name_sw = 'Y' OR pn.name_type_flg = 'PRIM')
        GROUP BY ap.acct_id
    ) src
        ON (tgt.acct_id = src.acct_id)
    WHEN MATCHED THEN UPDATE SET
        tgt.per_id = src.per_id,
        tgt.customer_name = src.customer_name;

    MERGE INTO cisadm.acct_debt_rpt_curr tgt
    USING (
        SELECT
            bill.acct_id,
            MAX(bill.bill_dt) AS last_bill_dt
        FROM cisadm.ci_bill bill
        JOIN (SELECT acct_id FROM cisadm.acct_debt_rpt_curr) debt
            ON debt.acct_id = bill.acct_id
        GROUP BY bill.acct_id
    ) src
        ON (tgt.acct_id = src.acct_id)
    WHEN MATCHED THEN UPDATE SET
        tgt.last_bill_dt = src.last_bill_dt;

    MERGE INTO cisadm.acct_debt_rpt_curr tgt
    USING (
        SELECT
            latest.acct_id,
            latest.coll_proc_count,
            latest.coll_proc_id AS latest_coll_proc_id,
            latest.cre_dttm AS latest_coll_proc_cre_dttm,
            latest.coll_status_flg AS latest_coll_status_flg,
            coll_status.descr AS latest_coll_status_desc,
            latest.coll_stat_rsn_flg AS latest_coll_stat_rsn_flg,
            latest.coll_proc_tmpl_cd AS latest_coll_proc_tmpl_cd,
            coll_tmpl.descr AS latest_coll_proc_tmpl_desc,
            latest.coll_ars_dt AS latest_coll_ars_dt,
            latest.ars_amt AS latest_coll_ars_amt
        FROM (
            SELECT
                cp.acct_id,
                COUNT(*) OVER (PARTITION BY cp.acct_id) AS coll_proc_count,
                cp.coll_proc_id,
                cp.cre_dttm,
                cp.coll_status_flg,
                cp.coll_stat_rsn_flg,
                cp.coll_proc_tmpl_cd,
                cp.coll_ars_dt,
                cp.ars_amt,
                ROW_NUMBER() OVER (
                    PARTITION BY cp.acct_id
                    ORDER BY cp.cre_dttm DESC, cp.coll_proc_id DESC
                ) AS rn
            FROM cisadm.ci_coll_proc cp
            JOIN (SELECT acct_id FROM cisadm.acct_debt_rpt_curr) debt
                ON debt.acct_id = cp.acct_id
        ) latest
        LEFT JOIN cisadm.ci_lookup_val_l coll_status
            ON TRIM(coll_status.field_name) = 'COLL_STATUS_FLG'
           AND TRIM(coll_status.field_value) = TRIM(latest.coll_status_flg)
           AND coll_status.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_coll_proc_tm_l coll_tmpl
            ON coll_tmpl.coll_proc_tmpl_cd = latest.coll_proc_tmpl_cd
           AND coll_tmpl.language_cd = 'ENG'
        WHERE latest.rn = 1
    ) src
        ON (tgt.acct_id = src.acct_id)
    WHEN MATCHED THEN UPDATE SET
        tgt.coll_proc_count = src.coll_proc_count,
        tgt.latest_coll_proc_id = src.latest_coll_proc_id,
        tgt.latest_coll_proc_cre_dttm = src.latest_coll_proc_cre_dttm,
        tgt.latest_coll_status_flg = src.latest_coll_status_flg,
        tgt.latest_coll_status_desc = src.latest_coll_status_desc,
        tgt.latest_coll_stat_rsn_flg = src.latest_coll_stat_rsn_flg,
        tgt.latest_coll_proc_tmpl_cd = src.latest_coll_proc_tmpl_cd,
        tgt.latest_coll_proc_tmpl_desc = src.latest_coll_proc_tmpl_desc,
        tgt.latest_coll_ars_dt = src.latest_coll_ars_dt,
        tgt.latest_coll_ars_amt = src.latest_coll_ars_amt;

    MERGE INTO cisadm.acct_debt_rpt_curr tgt
    USING (
        SELECT
            latest.acct_id,
            latest.wo_proc_count,
            latest.uncoll_proc_id AS latest_wo_proc_id,
            latest.cre_dttm AS latest_wo_proc_cre_dttm,
            latest.wo_status_flg AS latest_wo_status_flg,
            wo_status.descr AS latest_wo_status_desc,
            latest.wo_stat_rsn_flg AS latest_wo_stat_rsn_flg,
            latest.wo_proc_tmpl_cd AS latest_wo_proc_tmpl_cd,
            wo_tmpl.descr AS latest_wo_proc_tmpl_desc,
            latest.wo_proc_compl_dt AS latest_wo_proc_compl_dt,
            latest.ars_at_start AS latest_wo_ars_at_start,
            latest.ars_at_end AS latest_wo_ars_at_end,
            NVL(agency.coll_agy_ref_count, 0) AS coll_agy_ref_count
        FROM (
            SELECT
                vw.acct_id,
                COUNT(*) OVER (PARTITION BY vw.acct_id) AS wo_proc_count,
                vw.uncoll_proc_id,
                vw.cre_dttm,
                vw.wo_status_flg,
                vw.wo_stat_rsn_flg,
                vw.wo_proc_tmpl_cd,
                vw.wo_proc_compl_dt,
                vw.ars_at_start,
                vw.ars_at_end,
                ROW_NUMBER() OVER (
                    PARTITION BY vw.acct_id
                    ORDER BY vw.cre_dttm DESC, vw.uncoll_proc_id DESC
                ) AS rn
            FROM cisadm.c1_bi_woproc_vw vw
            JOIN (SELECT acct_id FROM cisadm.acct_debt_rpt_curr) debt
                ON debt.acct_id = vw.acct_id
        ) latest
        LEFT JOIN (
            SELECT
                vw.acct_id,
                COUNT(*) AS coll_agy_ref_count
            FROM cisadm.c1_bi_woproc_vw vw
            JOIN (SELECT acct_id FROM cisadm.acct_debt_rpt_curr) debt
                ON debt.acct_id = vw.acct_id
            JOIN cisadm.ci_coll_agy_ref agy
                ON agy.wo_proc_id = vw.uncoll_proc_id
            GROUP BY vw.acct_id
        ) agency
            ON agency.acct_id = latest.acct_id
        LEFT JOIN cisadm.ci_lookup_val_l wo_status
            ON TRIM(wo_status.field_name) = 'WO_STATUS_FLG'
           AND TRIM(wo_status.field_value) = TRIM(latest.wo_status_flg)
           AND wo_status.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_wo_proc_tmpl_l wo_tmpl
            ON wo_tmpl.wo_proc_tmpl_cd = latest.wo_proc_tmpl_cd
           AND wo_tmpl.language_cd = 'ENG'
        WHERE latest.rn = 1
    ) src
        ON (tgt.acct_id = src.acct_id)
    WHEN MATCHED THEN UPDATE SET
        tgt.wo_proc_count = src.wo_proc_count,
        tgt.latest_wo_proc_id = src.latest_wo_proc_id,
        tgt.latest_wo_proc_cre_dttm = src.latest_wo_proc_cre_dttm,
        tgt.latest_wo_status_flg = src.latest_wo_status_flg,
        tgt.latest_wo_status_desc = src.latest_wo_status_desc,
        tgt.latest_wo_stat_rsn_flg = src.latest_wo_stat_rsn_flg,
        tgt.latest_wo_proc_tmpl_cd = src.latest_wo_proc_tmpl_cd,
        tgt.latest_wo_proc_tmpl_desc = src.latest_wo_proc_tmpl_desc,
        tgt.latest_wo_proc_compl_dt = src.latest_wo_proc_compl_dt,
        tgt.latest_wo_ars_at_start = src.latest_wo_ars_at_start,
        tgt.latest_wo_ars_at_end = src.latest_wo_ars_at_end,
        tgt.coll_agy_ref_count = src.coll_agy_ref_count;

    COMMIT;
END;
/
