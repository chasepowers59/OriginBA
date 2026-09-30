CREATE OR REPLACE PROCEDURE cisadm.refresh_field_activity_rpt_curr AS
    v_load_dttm TIMESTAMP := SYSTIMESTAMP;
    v_window_start TIMESTAMP := CAST(ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6) AS TIMESTAMP);
BEGIN
    DELETE FROM cisadm.field_activity_rpt_curr
    WHERE act_cre_dttm >= v_window_start
       OR start_dttm >= v_window_start
       OR status_upd_dttm >= v_window_start
       OR end_dttm >= v_window_start;

    INSERT INTO cisadm.field_activity_rpt_curr (
        d1_activity_id,
        parent_activity_id,
        activity_type_cd,
        activity_type_desc,
        bo_status_cd,
        bo_status_desc,
        bo_status_reason_cd,
        bo_status_reason_desc,
        bus_obj_cd,
        bus_obj_desc,
        cancel_reason,
        cancel_reason_desc,
        field_task_type,
        field_task_type_desc,
        reschedule_reason,
        reschedule_reason_desc,
        retention_period,
        act_cre_dttm,
        eff_dttm,
        start_dttm,
        end_dttm,
        status_upd_dttm,
        days_old,
        days_completed,
        days_started_since_create,
        appointment_flg,
        appointment_taken_by,
        appointment_taken_date,
        appointment_window_start_dttm,
        appointment_window_end_dttm,
        cm_ml_is_pickup_flg,
        appointment_comments,
        comments,
        cr_requester_user,
        requester_user_name,
        d1_cellphone,
        d1_cont_external_id,
        d1_contactname,
        d1_customername,
        d1_instructions,
        d1_mainphone,
        email_value,
        expiration_dttm,
        ext_reference_id,
        external_acct_id,
        fa_int_status_flg,
        fa_int_status_desc,
        fa_priority_flg,
        thrd_pty_rep_cd,
        thrd_pty_rep_desc,
        d1_sp_id,
        d1_sp_type_cd,
        d1_sp_type_desc,
        access_grp_cd,
        access_grp_desc,
        sp_bo_status_cd,
        sp_bo_status_desc,
        sp_bo_status_reason_cd,
        sp_bo_status_reason_desc,
        sp_bus_obj_cd,
        sp_bus_obj_desc,
        division_cd,
        mkt_cd,
        mkt_desc,
        msrmt_cyc_cd,
        msrmt_cyc_desc,
        msrmt_cyc_rte_cd,
        msrmt_cyc_rte_desc,
        disconn_loc_flg,
        disconn_loc_desc,
        sp_src_stat_flg,
        sp_src_stat_desc,
        d1_ls_sl_flg,
        d1_ls_sl_descr,
        d1_geo_lat,
        d1_geo_long,
        sp_address1,
        sp_address1_upr,
        sp_address2,
        sp_city,
        sp_city_upr,
        sp_state,
        sp_state_desc,
        sp_postal,
        postal_5,
        sp_county,
        sp_country,
        time_zone_cd,
        time_zone_desc,
        in_city_limit,
        sp_id,
        prem_id,
        acct_id,
        prem_address1,
        prem_city,
        prem_state,
        prem_postal,
        acct_cust_cl_cd,
        acct_cust_cl_desc,
        acct_coll_cl_cd,
        acct_coll_cl_desc,
        acct_customer_name,
        load_dttm
    )
    WITH
    sp_link AS (
        SELECT
            rel.d1_activity_id,
            rel.pk_value1 AS d1_sp_id,
            ROW_NUMBER() OVER (
                PARTITION BY rel.d1_activity_id
                ORDER BY rel.pk_value1, rel.maint_obj_cd
            ) AS rn
        FROM cisadm.d1_activity_rel_obj rel
        WHERE rel.activity_rel_obj_type_flg = 'D1RO'
          AND rel.maint_obj_cd = 'D1-SP'
    ),
    sp_acct AS (
        SELECT
            sp.sp_id,
            sp.prem_id,
            sa.acct_id,
            ROW_NUMBER() OVER (
                PARTITION BY sp.sp_id
                ORDER BY
                    CASE WHEN sa.sa_status_flg = '20' THEN 0 ELSE 1 END,
                    sa.start_dt DESC NULLS LAST,
                    sa.sa_id
            ) AS rn
        FROM cisadm.ci_sp sp
        LEFT JOIN cisadm.ci_sa_sp sa_sp
            ON sa_sp.sp_id = sp.sp_id
        LEFT JOIN cisadm.ci_sa sa
            ON sa.sa_id = sa_sp.sa_id
    ),
    acct_customer AS (
        SELECT
            ap.acct_id,
            pn.entity_name_upr AS acct_customer_name,
            ROW_NUMBER() OVER (
                PARTITION BY ap.acct_id
                ORDER BY
                    CASE WHEN ap.fin_resp_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN ap.main_cust_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN pn.prim_name_sw = 'Y' THEN 0 ELSE 1 END,
                    pn.seq_num,
                    ap.per_id
            ) AS rn
        FROM cisadm.ci_acct_per ap
        JOIN cisadm.ci_per_name pn
            ON pn.per_id = ap.per_id
        WHERE ap.main_cust_sw = 'Y'
          AND (pn.prim_name_sw = 'Y' OR pn.name_type_flg = 'PRIM')
    )
    SELECT
        act.d1_activity_id,
        par_rel.rel_activity_id,
        act.activity_type_cd,
        act_type_l.descr100,
        act.bo_status_cd,
        act_status_l.descr,
        act.bo_status_reason_cd,
        act_status_rsn_l.descr,
        act.bus_obj_cd,
        act_bus_obj_l.descr,
        act.cancel_reason,
        cancel_l.descr,
        act.field_task_type,
        field_task_l.descr,
        act.reschedule_reason,
        reschedule_l.descr,
        act.retention_period,
        act.cre_dttm,
        act.eff_dttm,
        act.start_dttm,
        act.end_dttm,
        act.status_upd_dttm,
        CASE
            WHEN act.cre_dttm IS NOT NULL
            THEN TRUNC(SYSDATE) - TRUNC(CAST(act.cre_dttm AS DATE))
        END,
        CASE
            WHEN act.end_dttm IS NOT NULL AND act.start_dttm IS NOT NULL
            THEN TRUNC(CAST(act.end_dttm AS DATE)) - TRUNC(CAST(act.start_dttm AS DATE))
        END,
        CASE
            WHEN act.start_dttm IS NOT NULL AND act.cre_dttm IS NOT NULL
            THEN TRUNC(CAST(act.start_dttm AS DATE)) - TRUNC(CAST(act.cre_dttm AS DATE))
        END,
        boda.appointment_flg,
        boda.appointment_taken_by,
        CASE
            WHEN NULLIF(TRIM(boda.appointment_taken_date), '') IS NOT NULL
            THEN TO_DATE(boda.appointment_taken_date, 'YYYY-MM-DD')
        END,
        CASE
            WHEN NULLIF(TRIM(boda.appointment_window_start_dttm), '') IS NOT NULL
            THEN TO_TIMESTAMP(boda.appointment_window_start_dttm, 'YYYY-MM-DD-HH24.MI.SS')
        END,
        CASE
            WHEN NULLIF(TRIM(boda.appointment_window_end_dttm), '') IS NOT NULL
            THEN TO_TIMESTAMP(boda.appointment_window_end_dttm, 'YYYY-MM-DD-HH24.MI.SS')
        END,
        boda.cm_ml_is_pickup_flg,
        boda.appointment_comments,
        boda.comments,
        boda.cr_requester_user,
        TRIM(req_user.first_name || ' ' || req_user.last_name),
        boda.d1_cellphone,
        boda.d1_cont_external_id,
        boda.d1_contactname,
        boda.d1_customername,
        boda.d1_instructions,
        boda.d1_mainphone,
        boda.email_value,
        CASE
            WHEN NULLIF(TRIM(boda.expiration_dttm), '') IS NOT NULL
            THEN TO_TIMESTAMP(boda.expiration_dttm, 'YYYY-MM-DD-HH24.MI.SS')
        END,
        boda.ext_reference_id,
        boda.external_acct_id,
        char_vw.fa_int_status_flg,
        fa_int_status_l.descr,
        char_vw.fa_priority_flg,
        char_vw.thrd_pty_rep_cd,
        rep_l.descr100,
        d1_sp.d1_sp_id,
        d1_sp.d1_sp_type_cd,
        sp_type_l.descr100,
        d1_sp.access_grp_cd,
        acc_grp_l.descr,
        d1_sp.bo_status_cd,
        sp_status_l.descr,
        d1_sp.bo_status_reason_cd,
        sp_status_rsn_l.descr,
        d1_sp.bus_obj_cd,
        sp_bus_obj_l.descr,
        d1_sp.division_cd,
        d1_sp.mkt_cd,
        mkt_l.descr100,
        d1_sp.msrmt_cyc_cd,
        msrmt_cyc_l.descr100,
        d1_sp.msrmt_cyc_rte_cd,
        msrmt_cyc_rte_l.descr100,
        d1_sp.disconn_loc_flg,
        disconn_loc_l.descr,
        d1_sp.sp_src_stat_flg,
        sp_src_stat_l.descr,
        d1_sp.d1_ls_sl_flg,
        d1_sp.d1_ls_sl_descr,
        d1_sp.d1_geo_lat,
        d1_sp.d1_geo_long,
        d1_sp.address1,
        d1_sp.address1_upper,
        d1_sp.address2,
        d1_sp.city,
        d1_sp.city_upper,
        d1_sp.state,
        state_l.descr,
        d1_sp.postal,
        SUBSTR(d1_sp.postal, 1, 5),
        d1_sp.county,
        d1_sp.country,
        d1_sp.time_zone_cd,
        time_zone_l.descr,
        d1_sp.in_city_limit,
        ci_sp.sp_id,
        ci_sp.prem_id,
        sp_acct.acct_id,
        prem.address1,
        prem.city,
        prem.state,
        prem.postal,
        acct.cust_cl_cd,
        cust_cl_l.descr,
        acct.coll_cl_cd,
        coll_cl_l.descr,
        acct_cust.acct_customer_name,
        v_load_dttm
    FROM cisadm.d1_activity act
    INNER JOIN cisadm.d1_activity_type act_type
        ON act_type.activity_type_cd = act.activity_type_cd
       AND act_type.activity_type_cat_flg = 'D1FA'
    LEFT JOIN cisadm.cms_d1_activity_d1fa_boda_vw boda
        ON boda.d1_activity_id = act.d1_activity_id
    LEFT JOIN cisadm.d1_activity_rel par_rel
        ON par_rel.d1_activity_id = act.d1_activity_id
       AND par_rel.activity_rel_type_flg = 'D1PR'
    LEFT JOIN sp_link
        ON sp_link.d1_activity_id = act.d1_activity_id
       AND sp_link.rn = 1
    LEFT JOIN cisadm.d1_sp d1_sp
        ON d1_sp.d1_sp_id = sp_link.d1_sp_id
    LEFT JOIN cisadm.ci_sp ci_sp
        ON ci_sp.sp_id = d1_sp.d1_sp_id
    LEFT JOIN sp_acct
        ON sp_acct.sp_id = ci_sp.sp_id
       AND sp_acct.rn = 1
    LEFT JOIN cisadm.ci_prem prem
        ON prem.prem_id = ci_sp.prem_id
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = sp_acct.acct_id
    LEFT JOIN acct_customer acct_cust
        ON acct_cust.acct_id = sp_acct.acct_id
       AND acct_cust.rn = 1
    LEFT JOIN cisadm.cms_d1_activity_char_vw char_vw
        ON char_vw.d1_activity_id = act.d1_activity_id
    LEFT JOIN cisadm.d1_activity_type_l act_type_l
        ON act_type_l.activity_type_cd = act.activity_type_cd
       AND act_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l act_status_l
        ON act_status_l.bus_obj_cd = act.bus_obj_cd
       AND act_status_l.bo_status_cd = act.bo_status_cd
       AND act_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_rsn_l act_status_rsn_l
        ON act_status_rsn_l.bo_status_reason_cd = act.bo_status_reason_cd
       AND act_status_rsn_l.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_l act_bus_obj_l
        ON act_bus_obj_l.bus_obj_cd = act.bus_obj_cd
       AND act_bus_obj_l.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_ext_lookup_val_l cancel_l
        ON cancel_l.f1_ext_lookup_value = act.cancel_reason
       AND cancel_l.bus_obj_cd = 'D1-CancelReasonLookup'
       AND cancel_l.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_ext_lookup_val_l field_task_l
        ON field_task_l.f1_ext_lookup_value = act.field_task_type
       AND field_task_l.bus_obj_cd = 'D1-FieldTaskTypeLookup'
       AND field_task_l.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_ext_lookup_val_l reschedule_l
        ON reschedule_l.f1_ext_lookup_value = act.reschedule_reason
       AND reschedule_l.bus_obj_cd = 'D1-RescheduleReasonLookup'
       AND reschedule_l.language_cd = 'ENG'
    LEFT JOIN cisadm.sc_user req_user
        ON req_user.user_id = boda.cr_requester_user
    LEFT JOIN cisadm.ci_lookup_val_l fa_int_status_l
        ON TRIM(fa_int_status_l.field_name) = 'FA_INT_STATUS_FLG'
       AND TRIM(fa_int_status_l.field_value) = TRIM(char_vw.fa_int_status_flg)
       AND fa_int_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.c1_representative_l rep_l
        ON rep_l.c1_representative_cd = char_vw.thrd_pty_rep_cd
       AND rep_l.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_sp_type_l sp_type_l
        ON sp_type_l.d1_sp_type_cd = d1_sp.d1_sp_type_cd
       AND sp_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acc_grp_l acc_grp_l
        ON acc_grp_l.access_grp_cd = d1_sp.access_grp_cd
       AND acc_grp_l.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l sp_status_l
        ON sp_status_l.bus_obj_cd = d1_sp.bus_obj_cd
       AND sp_status_l.bo_status_cd = d1_sp.bo_status_cd
       AND sp_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_rsn_l sp_status_rsn_l
        ON sp_status_rsn_l.bo_status_reason_cd = d1_sp.bo_status_reason_cd
       AND sp_status_rsn_l.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_l sp_bus_obj_l
        ON sp_bus_obj_l.bus_obj_cd = d1_sp.bus_obj_cd
       AND sp_bus_obj_l.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_mkt_l mkt_l
        ON mkt_l.mkt_cd = d1_sp.mkt_cd
       AND mkt_l.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_msrmt_cyc_l msrmt_cyc_l
        ON msrmt_cyc_l.msrmt_cyc_cd = d1_sp.msrmt_cyc_cd
       AND msrmt_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_msrmt_cyc_rte_l msrmt_cyc_rte_l
        ON msrmt_cyc_rte_l.msrmt_cyc_cd = d1_sp.msrmt_cyc_cd
       AND msrmt_cyc_rte_l.msrmt_cyc_rte_cd = d1_sp.msrmt_cyc_rte_cd
       AND msrmt_cyc_rte_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l disconn_loc_l
        ON TRIM(disconn_loc_l.field_name) = 'DISCONN_LOC_FLG'
       AND TRIM(disconn_loc_l.field_value) = TRIM(d1_sp.disconn_loc_flg)
       AND disconn_loc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l sp_src_stat_l
        ON TRIM(sp_src_stat_l.field_name) = 'SP_SRC_STAT_FLG'
       AND TRIM(sp_src_stat_l.field_value) = TRIM(d1_sp.sp_src_stat_flg)
       AND sp_src_stat_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_state_l state_l
        ON state_l.state = d1_sp.state
       AND state_l.country = d1_sp.country
       AND state_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_time_zone_l time_zone_l
        ON time_zone_l.time_zone_cd = d1_sp.time_zone_cd
       AND time_zone_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON cust_cl_l.cust_cl_cd = acct.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON coll_cl_l.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    WHERE act.cre_dttm >= v_window_start
       OR act.start_dttm >= v_window_start
       OR act.status_upd_dttm >= v_window_start
       OR act.end_dttm >= v_window_start;

    COMMIT;
END;
/
