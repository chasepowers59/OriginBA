CREATE OR REPLACE PROCEDURE cisadm.refresh_sa_aged_bal_rpt_curr AS
    v_load_dttm TIMESTAMP := SYSTIMESTAMP;
BEGIN
    EXECUTE IMMEDIATE 'TRUNCATE TABLE cisadm.sa_aged_bal_rpt_curr';

    INSERT INTO cisadm.sa_aged_bal_rpt_curr (
        sa_id,
        acct_id,
        cis_division,
        cis_division_desc,
        sa_type_cd,
        sa_type_desc,
        sa_status_flg,
        sa_status_desc,
        debt_cl_cd,
        debt_cl_desc,
        char_prem_id,
        sa_start_dt,
        sa_end_dt,
        per_id,
        customer_name,
        bill_cyc_cd,
        bill_cyc_desc,
        coll_cl_cd,
        coll_cl_desc,
        cust_cl_cd,
        cust_cl_desc,
        acct_mgmt_grp_cd,
        acct_mgmt_grp_desc,
        bud_plan_cd,
        bud_plan_desc,
        prem_id,
        address1,
        city,
        state,
        state_desc,
        postal,
        governed_arrears_ft_count,
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
        HAVING SUM(ft.cur_amt) > 0
    )
    SELECT
        sa.sa_id,
        sa.acct_id,
        sa.cis_division,
        cis_div.descr,
        sa.sa_type_cd,
        sa_type_l.descr,
        sa.sa_status_flg,
        sa_status_l.descr,
        sa_type.debt_cl_cd,
        debt_cl_l.descr,
        sa.char_prem_id,
        sa.start_dt,
        sa.end_dt,
        acct_per.per_id,
        per_name.entity_name_upr,
        acct.bill_cyc_cd,
        bill_cyc_l.descr,
        acct.coll_cl_cd,
        coll_cl_l.descr,
        acct.cust_cl_cd,
        cust_cl_l.descr,
        acct.acct_mgmt_grp_cd,
        acct_mgmt_l.descr,
        acct.bud_plan_cd,
        bud_plan_l.descr,
        prem.prem_id,
        prem.address1,
        prem.city,
        prem.state,
        state_l.descr,
        prem.postal,
        gf.governed_arrears_ft_count,
        gf.total_debt,
        gf.debt_0_30,
        gf.debt_31_60,
        gf.debt_61_90,
        gf.debt_over_90,
        gf.oldest_age_days,
        gf.newest_age_days,
        gf.oldest_ars_dt,
        gf.newest_ars_dt,
        v_load_dttm
    FROM governed_ft gf
    INNER JOIN cisadm.ci_sa sa
        ON sa.sa_id = gf.sa_id
    LEFT JOIN cisadm.ci_sa_type sa_type
        ON sa_type.cis_division = sa.cis_division
       AND sa_type.sa_type_cd = sa.sa_type_cd
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = sa.acct_id
    LEFT JOIN cisadm.ci_acct_per acct_per
        ON acct_per.acct_id = sa.acct_id
       AND acct_per.main_cust_sw = 'Y'
    LEFT JOIN cisadm.ci_per_name per_name
        ON per_name.per_id = acct_per.per_id
       AND per_name.name_type_flg = 'PRIM'
    LEFT JOIN cisadm.ci_cis_division_l cis_div
        ON cis_div.cis_division = sa.cis_division
       AND cis_div.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_sa_type_l sa_type_l
        ON sa_type_l.cis_division = sa_type.cis_division
       AND sa_type_l.sa_type_cd = sa_type.sa_type_cd
       AND sa_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l sa_status_l
        ON TRIM(sa_status_l.field_name) = 'SA_STATUS_FLG'
       AND TRIM(sa_status_l.field_value) = TRIM(sa.sa_status_flg)
       AND sa_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON coll_cl_l.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON cust_cl_l.cust_cl_cd = acct.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_debt_cl_l debt_cl_l
        ON debt_cl_l.debt_cl_cd = sa_type.debt_cl_cd
       AND debt_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l bill_cyc_l
        ON bill_cyc_l.bill_cyc_cd = acct.bill_cyc_cd
       AND bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt_l
        ON acct_mgmt_l.acct_mgmt_grp_cd = acct.acct_mgmt_grp_cd
       AND acct_mgmt_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bud_plan_l bud_plan_l
        ON bud_plan_l.bud_plan_cd = acct.bud_plan_cd
       AND bud_plan_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_prem prem
        ON prem.prem_id = sa.char_prem_id
    LEFT JOIN cisadm.ci_state_l state_l
        ON state_l.state = prem.state
       AND state_l.country = prem.country
       AND state_l.language_cd = 'ENG';

    COMMIT;
END;
/
