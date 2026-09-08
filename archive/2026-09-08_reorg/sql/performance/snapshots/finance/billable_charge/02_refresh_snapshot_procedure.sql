CREATE OR REPLACE PROCEDURE cisadm.refresh_billable_charge_rpt_curr AS
    v_window_start DATE := ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6);
    v_load_dttm    TIMESTAMP := SYSTIMESTAMP;
BEGIN
    DELETE FROM cisadm.billable_charge_rpt_curr snap
    WHERE snap.charge_start_dt < v_window_start
      AND snap.charge_end_dt IS NOT NULL
      AND snap.charge_end_dt < v_window_start;

    DELETE FROM cisadm.billable_charge_rpt_curr snap
    WHERE snap.charge_start_dt >= v_window_start
       OR snap.charge_end_dt IS NULL
       OR snap.charge_end_dt >= v_window_start;
    COMMIT;

    INSERT INTO cisadm.billable_charge_rpt_curr (
        billable_chg_id,
        line_seq,
        sa_id,
        acct_id,
        charge_start_dt,
        charge_end_dt,
        charge_descr_on_bill,
        billable_chg_stat,
        billable_chg_stat_desc,
        bill_chg_tmplt_cd,
        ilm_dt,
        ilm_arch_sw,
        line_descr_on_bill,
        charge_amt,
        currency_cd,
        show_on_bill_sw,
        app_in_summ_sw,
        dst_id,
        memo_sw,
        cis_division,
        cis_division_desc,
        sa_type_cd,
        sa_type_desc,
        sa_status_flg,
        sa_status_desc,
        char_prem_id,
        per_id,
        customer_name,
        bill_cyc_cd,
        bill_cyc_desc,
        coll_cl_cd,
        coll_cl_desc,
        cust_cl_cd,
        cust_cl_desc,
        bud_plan_cd,
        bud_plan_desc,
        load_dttm
    )
    SELECT
        bcl.billable_chg_id,
        bcl.line_seq,
        bc.sa_id,
        sa.acct_id,
        bc.start_dt,
        bc.end_dt,
        bc.descr_on_bill,
        bc.billable_chg_stat,
        billable_chg_stat_l.descr,
        bc.bill_chg_tmplt_cd,
        bc.ilm_dt,
        bc.ilm_arch_sw,
        bcl.descr_on_bill,
        bcl.charge_amt,
        bcl.currency_cd,
        bcl.show_on_bill_sw,
        bcl.app_in_summ_sw,
        bcl.dst_id,
        bcl.memo_sw,
        sa.cis_division,
        cis_div.descr,
        sa.sa_type_cd,
        sa_type_l.descr,
        sa.sa_status_flg,
        sa_status_l.descr,
        sa.char_prem_id,
        acct_per.per_id,
        per_name.entity_name_upr,
        acct.bill_cyc_cd,
        bill_cyc_l.descr,
        acct.coll_cl_cd,
        coll_cl_l.descr,
        acct.cust_cl_cd,
        cust_cl_l.descr,
        acct.bud_plan_cd,
        bud_plan_l.descr,
        v_load_dttm
    FROM cisadm.ci_b_chg_line bcl
    INNER JOIN cisadm.ci_bill_chg bc
        ON bc.billable_chg_id = bcl.billable_chg_id
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = bc.sa_id
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
    LEFT JOIN cisadm.ci_sa_type sa_type
        ON sa_type.cis_division = sa.cis_division
       AND sa_type.sa_type_cd = sa.sa_type_cd
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
    LEFT JOIN cisadm.ci_bill_cyc_l bill_cyc_l
        ON bill_cyc_l.bill_cyc_cd = acct.bill_cyc_cd
       AND bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bud_plan_l bud_plan_l
        ON bud_plan_l.bud_plan_cd = acct.bud_plan_cd
       AND bud_plan_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l billable_chg_stat_l
        ON TRIM(billable_chg_stat_l.field_name) = 'BILLABLE_CHG_STAT'
       AND TRIM(billable_chg_stat_l.field_value) = TRIM(bc.billable_chg_stat)
       AND billable_chg_stat_l.language_cd = 'ENG'
    WHERE bc.start_dt >= v_window_start
       OR bc.end_dt IS NULL
       OR bc.end_dt >= v_window_start;

    COMMIT;
END;
/
