CREATE OR REPLACE PROCEDURE cisadm.refresh_new_service_pipeline_rpt_curr AS
    v_window_start DATE := ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6);
    v_load_dttm    TIMESTAMP := SYSTIMESTAMP;
BEGIN
    DELETE FROM cisadm.new_service_pipeline_rpt_curr snap
    WHERE NULLIF(TRIM(snap.sa_status_flg), '') = '10'
       OR snap.start_dt >= v_window_start
       OR (snap.end_dt IS NOT NULL AND snap.end_dt >= v_window_start);
    COMMIT;

    INSERT INTO cisadm.new_service_pipeline_rpt_curr (
        sa_id,
        acct_id,
        cis_division,
        cis_division_desc,
        sa_type_cd,
        sa_type_desc,
        svc_type_cd,
        svc_type_desc,
        sa_status_flg,
        sa_status_desc,
        prop_sa_stat_flg,
        prop_sa_stat_desc,
        prop_sa_id,
        prop_dcl_rsn_cd,
        prop_dcl_rsn_desc,
        enrl_id,
        sa_rel_id,
        old_acct_id,
        currency_cd,
        start_dt,
        end_dt,
        expire_dt,
        renewal_dt,
        cre_dttm,
        start_opt_cd,
        start_opt_desc,
        strt_rsn_flg,
        strt_rsn_desc,
        stop_rsn_flg,
        stop_rsn_desc,
        strt_reqed_by,
        stop_reqed_by,
        nb_rule_cd,
        nb_rule_desc,
        sic_cd,
        sic_desc,
        special_usage_flg,
        special_usage_desc,
        char_prem_id,
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
        acct_setup_dt,
        bill_prt_intercept,
        bill_prt_intercept_name,
        prem_id,
        address1,
        address2,
        address3,
        address4,
        city,
        state,
        state_desc,
        postal,
        postal_5,
        county,
        country,
        prem_type_cd,
        prem_type_desc,
        trend_area_cd,
        trend_area_desc,
        mr_instr_cd,
        mr_instr_desc,
        mr_warn_cd,
        mr_warn_desc,
        time_zone_cd,
        time_zone_desc,
        in_city_limit,
        ls_sl_flg,
        ft_bal_cur_amt,
        ft_bal_tot_amt,
        days_since_created,
        days_until_start,
        stale_pending_sw,
        load_dttm
    )
    SELECT
        sa.sa_id,
        sa.acct_id,
        sa.cis_division,
        cis_div.descr,
        sa.sa_type_cd,
        sa_type_l.descr,
        sa_type.svc_type_cd,
        svc_type_l.descr,
        sa.sa_status_flg,
        sa_status_l.descr,
        sa.prop_sa_stat_flg,
        prop_sa_status_l.descr,
        sa.prop_sa_id,
        sa.prop_dcl_rsn_cd,
        prop_dcl_rsn_l.descr,
        sa.enrl_id,
        sa.sa_rel_id,
        sa.old_acct_id,
        sa.currency_cd,
        sa.start_dt,
        sa.end_dt,
        sa.expire_dt,
        sa.renewal_dt,
        enrl.start_dt,
        sa.start_opt_cd,
        start_opt_l.descr90,
        sa.strt_rsn_flg,
        strt_rsn_l.descr,
        sa.stop_rsn_flg,
        stop_rsn_l.descr,
        sa.strt_reqed_by,
        sa.stop_reqed_by,
        sa.nb_rule_cd,
        nb_rule_l.descr,
        sa.sic_cd,
        sic_l.descr,
        sa.special_usage_flg,
        special_usage_l.descr,
        sa.char_prem_id,
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
        acct.setup_dt,
        acct.bill_prt_intercept,
        COALESCE(
            NULLIF(TRIM(bill_user.first_name || ' ' || bill_user.last_name), ''),
            bill_user.user_id
        ),
        prem.prem_id,
        prem.address1,
        prem.address2,
        prem.address3,
        prem.address4,
        prem.city,
        prem.state,
        state_l.descr,
        prem.postal,
        SUBSTR(TRIM(prem.postal), 1, 5),
        prem.county,
        prem.country,
        prem.prem_type_cd,
        prem_type_l.descr,
        prem.trend_area_cd,
        trend_area_l.descr,
        prem.mr_instr_cd,
        mr_instr_l.descr,
        prem.mr_warn_cd,
        mr_warn_l.descr,
        prem.time_zone_cd,
        time_zone_l.descr,
        prem.in_city_limit,
        prem.ls_sl_flg,
        CAST(NULL AS NUMBER(18,2)),
        CAST(NULL AS NUMBER(18,2)),
        CASE
            WHEN enrl.start_dt IS NOT NULL THEN TRUNC(SYSDATE) - TRUNC(enrl.start_dt)
        END,
        CASE
            WHEN sa.start_dt IS NOT NULL THEN TRUNC(sa.start_dt) - TRUNC(SYSDATE)
        END,
        CASE
            WHEN NULLIF(TRIM(sa.sa_status_flg), '') = '10'
             AND sa.start_dt IS NOT NULL
             AND TRUNC(sa.start_dt) < TRUNC(SYSDATE) THEN 'Y'
            ELSE 'N'
        END,
        v_load_dttm
    FROM cisadm.ci_sa sa
    INNER JOIN cisadm.ci_sa_type sa_type
        ON sa_type.cis_division = sa.cis_division
       AND sa_type.sa_type_cd = sa.sa_type_cd
    INNER JOIN cisadm.ci_sa_type_l sa_type_l
        ON sa_type_l.cis_division = sa_type.cis_division
       AND sa_type_l.sa_type_cd = sa_type.sa_type_cd
       AND sa_type_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_acct acct
        ON acct.acct_id = sa.acct_id
    INNER JOIN cisadm.ci_acct_per acct_per
        ON acct_per.acct_id = sa.acct_id
       AND acct_per.main_cust_sw = 'Y'
    INNER JOIN cisadm.ci_per_name per_name
        ON per_name.per_id = acct_per.per_id
       AND per_name.name_type_flg = 'PRIM'
    INNER JOIN cisadm.ci_cis_division_l cis_div
        ON cis_div.cis_division = sa.cis_division
       AND cis_div.language_cd = 'ENG'
    INNER JOIN cisadm.ci_lookup_val_l sa_status_l
        ON TRIM(sa_status_l.field_name) = 'SA_STATUS_FLG'
       AND TRIM(sa_status_l.field_value) = TRIM(sa.sa_status_flg)
       AND sa_status_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON coll_cl_l.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    INNER JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON cust_cl_l.cust_cl_cd = acct.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_prem prem
        ON prem.prem_id = sa.char_prem_id
    LEFT JOIN cisadm.ci_bill_cyc_l bill_cyc_l
        ON bill_cyc_l.bill_cyc_cd = acct.bill_cyc_cd
       AND bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt_l
        ON acct_mgmt_l.acct_mgmt_grp_cd = acct.acct_mgmt_grp_cd
       AND acct_mgmt_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bud_plan_l bud_plan_l
        ON bud_plan_l.bud_plan_cd = acct.bud_plan_cd
       AND bud_plan_l.language_cd = 'ENG'
    LEFT JOIN cisadm.sc_user bill_user
        ON bill_user.user_id = acct.bill_prt_intercept
       AND bill_user.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_nb_rule_l nb_rule_l
        ON nb_rule_l.nb_rule_cd = sa.nb_rule_cd
       AND nb_rule_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_prop_dcl_rsn_l prop_dcl_rsn_l
        ON prop_dcl_rsn_l.prop_dcl_rsn_cd = sa.prop_dcl_rsn_cd
       AND prop_dcl_rsn_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l prop_sa_status_l
        ON TRIM(prop_sa_status_l.field_name) = 'PROP_SA_STAT_FLG'
       AND TRIM(prop_sa_status_l.field_value) = TRIM(sa.prop_sa_stat_flg)
       AND prop_sa_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_sic_l sic_l
        ON sic_l.sic_cd = sa.sic_cd
       AND sic_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l special_usage_l
        ON TRIM(special_usage_l.field_name) = 'SPECIAL_USAGE_FLG'
       AND TRIM(special_usage_l.field_value) = TRIM(sa.special_usage_flg)
       AND special_usage_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_ss_opt_l start_opt_l
        ON start_opt_l.start_opt_cd = sa.start_opt_cd
       AND start_opt_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l strt_rsn_l
        ON TRIM(strt_rsn_l.field_name) = 'STRT_RSN_FLG'
       AND TRIM(strt_rsn_l.field_value) = TRIM(sa.strt_rsn_flg)
       AND strt_rsn_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l stop_rsn_l
        ON TRIM(stop_rsn_l.field_name) = 'STOP_RSN_FLG'
       AND TRIM(stop_rsn_l.field_value) = TRIM(sa.stop_rsn_flg)
       AND stop_rsn_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_svc_type_l svc_type_l
        ON svc_type_l.svc_type_cd = sa_type.svc_type_cd
       AND svc_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_prem_type_l prem_type_l
        ON prem_type_l.prem_type_cd = prem.prem_type_cd
       AND prem_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_mr_instr_l mr_instr_l
        ON mr_instr_l.mr_instr_cd = prem.mr_instr_cd
       AND mr_instr_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_mr_warn_l mr_warn_l
        ON mr_warn_l.mr_warn_cd = prem.mr_warn_cd
       AND mr_warn_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_trend_area_l trend_area_l
        ON trend_area_l.trend_area_cd = prem.trend_area_cd
       AND trend_area_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_state_l state_l
        ON state_l.state = prem.state
       AND state_l.country = prem.country
       AND state_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_time_zone_l time_zone_l
        ON time_zone_l.time_zone_cd = prem.time_zone_cd
       AND time_zone_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_enrl enrl
        ON enrl.enrl_id = sa.enrl_id
    WHERE NULLIF(TRIM(sa.sa_status_flg), '') IN ('10', '20')
      AND (
          NULLIF(TRIM(sa.prop_sa_stat_flg), '') IS NULL
          OR NULLIF(TRIM(sa.prop_sa_stat_flg), '') IN ('10', '20')
      )
      AND (
          NULLIF(TRIM(sa.sa_status_flg), '') = '10'
          OR sa.start_dt >= v_window_start
          OR (sa.end_dt IS NOT NULL AND sa.end_dt >= v_window_start)
      );

    COMMIT;
END;
/
