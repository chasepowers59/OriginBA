CREATE OR REPLACE PROCEDURE cisadm.refresh_case_prem_contact_rpt_curr AS
    v_window_start TIMESTAMP := CAST(ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6) AS TIMESTAMP);
BEGIN
    DELETE FROM cisadm.case_prem_contact_rpt_curr
    WHERE case_cre_dttm >= v_window_start;

    INSERT INTO cisadm.case_prem_contact_rpt_curr (
        case_id,
        acct_id,
        prem_id,
        per_id,
        contact_per_id,
        c1_contact_id,
        case_type_cd,
        case_type_desc,
        case_status_cd,
        case_status_desc,
        case_cond_flg,
        case_cond_desc,
        case_cre_dttm,
        closed_dttm,
        case_dur_minutes,
        case_dur_days,
        contact_meth_flg,
        contact_meth_desc,
        contact_instr,
        phone_type_cd,
        phone_type_desc,
        phone,
        extension,
        comment_long,
        user_id,
        resp_user_name,
        case_person_name_upr,
        acct_main_per_id,
        acct_customer_name_upr,
        acct_cis_division,
        access_grp_cd,
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
        acct_alert_info,
        acct_currency_cd,
        prem_address1,
        prem_address1_upr,
        prem_address2,
        prem_address3,
        prem_address4,
        prem_city,
        prem_city_upr,
        prem_state,
        prem_postal,
        prem_county,
        prem_country,
        prem_cis_division,
        prem_type_cd,
        prem_type_desc,
        prem_geo_code,
        trend_area_cd,
        trend_area_desc,
        mr_instr_cd,
        mr_instr_desc,
        mr_warn_cd,
        mr_warn_desc,
        time_zone_cd,
        time_zone_desc,
        ls_sl_flg,
        ls_sl_descr,
        ok_to_enter_sw,
        in_city_limit,
        mail_addr_sw,
        cc_count,
        first_cc_dttm,
        latest_cc_id,
        latest_cc_dttm,
        latest_cc_cl_cd,
        latest_cc_cl_desc,
        latest_cc_type_cd,
        latest_cc_type_desc,
        latest_cc_status_flg,
        latest_cc_status_desc,
        latest_cc_entity_flg,
        latest_cc_entity_desc,
        latest_cc_contact_meth_flg,
        latest_cc_contact_meth_desc,
        latest_cc_descr_long,
        latest_cc_user_id,
        latest_cc_user_name,
        load_dttm
    )
    WITH
    acct_customer AS (
        SELECT
            ap.acct_id,
            ap.per_id,
            pn.entity_name_upr AS acct_customer_name_upr,
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
    ),
    case_cc_link AS (
        SELECT
            cs.case_id,
            cc.cc_id,
            cc.cc_dttm,
            cc.cc_cl_cd,
            cc.cc_type_cd,
            cc.cc_status_flg,
            cc.cc_entity_flg,
            cc.contact_meth_flg,
            cc.descrlong,
            cc.user_id
        FROM cisadm.ci_case cs
        LEFT JOIN cisadm.cms_ci_case_vw case_vw
            ON case_vw.case_id = cs.case_id
        WHERE case_vw.case_cre_dttm >= v_window_start
        LEFT JOIN cisadm.ci_cc cc
            ON (
                (cs.c1_contact_id IS NOT NULL AND cc.c1_contact_id = cs.c1_contact_id)
                OR (
                    cc.acct_id = cs.acct_id
                    AND NVL(cc.prem_id, '~') = NVL(cs.prem_id, '~')
                    AND NVL(cc.per_id, '~') = NVL(cs.per_id, '~')
                )
            )
    ),
    cc_rollup AS (
        SELECT
            link.case_id,
            COUNT(DISTINCT link.cc_id) AS cc_count,
            MIN(link.cc_dttm) AS first_cc_dttm
        FROM case_cc_link link
        WHERE link.cc_id IS NOT NULL
        GROUP BY link.case_id
    ),
    latest_cc AS (
        SELECT
            picked.case_id,
            picked.cc_id,
            picked.cc_dttm,
            picked.cc_cl_cd,
            picked.cc_type_cd,
            picked.cc_status_flg,
            picked.cc_entity_flg,
            picked.contact_meth_flg,
            picked.descrlong,
            picked.user_id
        FROM (
            SELECT
                link.case_id,
                link.cc_id,
                link.cc_dttm,
                link.cc_cl_cd,
                link.cc_type_cd,
                link.cc_status_flg,
                link.cc_entity_flg,
                link.contact_meth_flg,
                link.descrlong,
                link.user_id,
                ROW_NUMBER() OVER (
                    PARTITION BY link.case_id
                    ORDER BY link.cc_dttm DESC, link.cc_id DESC
                ) AS rn
            FROM case_cc_link link
            WHERE link.cc_id IS NOT NULL
        ) picked
        WHERE picked.rn = 1
    )
    SELECT
        cs.case_id,
        cs.acct_id,
        cs.prem_id,
        cs.per_id,
        cs.contact_per_id,
        cs.c1_contact_id,
        cs.case_type_cd,
        case_type_l.descr,
        cs.case_status_cd,
        case_status_l.status_lbl,
        cs.case_cond_flg,
        case_cond_l.descr,
        case_vw.case_cre_dttm,
        case_vw.closed_dttm,
        case_vw.case_dur,
        CASE
            WHEN case_vw.case_dur IS NOT NULL THEN case_vw.case_dur / 1440
        END,
        cs.contact_meth_flg,
        case_contact_meth_l.descr,
        cs.contact_instr,
        cs.phone_type_cd,
        phone_type_l.descr,
        cs.phone,
        cs.extension,
        cs.comment_long,
        cs.user_id,
        TRIM(resp_user.first_name || ' ' || resp_user.last_name),
        case_person.entity_name_upr,
        acct_cust.per_id,
        acct_cust.acct_customer_name_upr,
        acct.cis_division,
        acct.access_grp_cd,
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
        acct.alert_info,
        acct.currency_cd,
        prem.address1,
        prem.address1_upr,
        prem.address2,
        prem.address3,
        prem.address4,
        prem.city,
        prem.city_upr,
        prem.state,
        prem.postal,
        prem.county,
        prem.country,
        prem.cis_division,
        prem.prem_type_cd,
        prem_type_l.descr,
        prem.geo_code,
        prem.trend_area_cd,
        trend_area_l.descr,
        prem.mr_instr_cd,
        mr_instr_l.descr,
        prem.mr_warn_cd,
        mr_warn_l.descr,
        prem.time_zone_cd,
        time_zone_l.descr,
        prem.ls_sl_flg,
        prem.ls_sl_descr,
        prem.ok_to_enter_sw,
        prem.in_city_limit,
        prem.mail_addr_sw,
        NVL(cc_roll.cc_count, 0),
        cc_roll.first_cc_dttm,
        latest_cc.cc_id,
        latest_cc.cc_dttm,
        latest_cc.cc_cl_cd,
        latest_cc_cl_l.descr,
        latest_cc.cc_type_cd,
        latest_cc_type_l.descr,
        latest_cc.cc_status_flg,
        latest_cc_status_l.descr,
        latest_cc.cc_entity_flg,
        latest_cc_entity_l.descr,
        latest_cc.contact_meth_flg,
        latest_cc_contact_meth_l.descr,
        latest_cc.descrlong,
        latest_cc.user_id,
        TRIM(latest_cc_user.first_name || ' ' || latest_cc_user.last_name),
        SYSTIMESTAMP
    FROM cisadm.ci_case cs
    LEFT JOIN cisadm.cms_ci_case_vw case_vw
        ON case_vw.case_id = cs.case_id
       AND case_vw.case_cre_dttm >= v_window_start
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = cs.acct_id
    LEFT JOIN acct_customer acct_cust
        ON acct_cust.acct_id = cs.acct_id
       AND acct_cust.rn = 1
    LEFT JOIN cisadm.ci_per_name case_person
        ON case_person.per_id = cs.per_id
       AND case_person.name_type_flg = 'PRIM'
    LEFT JOIN cisadm.ci_prem prem
        ON prem.prem_id = cs.prem_id
    LEFT JOIN cc_rollup cc_roll
        ON cc_roll.case_id = cs.case_id
    LEFT JOIN latest_cc
        ON latest_cc.case_id = cs.case_id
    LEFT JOIN cisadm.ci_case_type_l case_type_l
        ON case_type_l.case_type_cd = cs.case_type_cd
       AND case_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_case_status_l case_status_l
        ON case_status_l.case_type_cd = cs.case_type_cd
       AND case_status_l.case_status_cd = cs.case_status_cd
       AND case_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l case_cond_l
        ON TRIM(case_cond_l.field_name) = 'CASE_COND_FLG'
       AND TRIM(case_cond_l.field_value) = TRIM(cs.case_cond_flg)
       AND case_cond_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l case_contact_meth_l
        ON TRIM(case_contact_meth_l.field_name) = 'CONTACT_METH_FLG'
       AND TRIM(case_contact_meth_l.field_value) = TRIM(cs.contact_meth_flg)
       AND case_contact_meth_l.language_cd = 'ENG'
    LEFT JOIN cisadm.sc_user resp_user
        ON resp_user.user_id = cs.user_id
    LEFT JOIN cisadm.ci_phone_type_l phone_type_l
        ON phone_type_l.phone_type_cd = cs.phone_type_cd
       AND phone_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l bill_cyc_l
        ON bill_cyc_l.bill_cyc_cd = acct.bill_cyc_cd
       AND bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON coll_cl_l.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON cust_cl_l.cust_cl_cd = acct.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt_l
        ON acct_mgmt_l.acct_mgmt_grp_cd = acct.acct_mgmt_grp_cd
       AND acct_mgmt_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bud_plan_l bud_plan_l
        ON bud_plan_l.bud_plan_cd = acct.bud_plan_cd
       AND bud_plan_l.language_cd = 'ENG'
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
    LEFT JOIN cisadm.ci_time_zone_l time_zone_l
        ON time_zone_l.time_zone_cd = prem.time_zone_cd
       AND time_zone_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cc_cl_l latest_cc_cl_l
        ON latest_cc_cl_l.cc_cl_cd = latest_cc.cc_cl_cd
       AND latest_cc_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cc_type_l latest_cc_type_l
        ON latest_cc_type_l.cc_cl_cd = latest_cc.cc_cl_cd
       AND latest_cc_type_l.cc_type_cd = latest_cc.cc_type_cd
       AND latest_cc_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l latest_cc_status_l
        ON TRIM(latest_cc_status_l.field_name) = 'CC_STATUS_FLG'
       AND TRIM(latest_cc_status_l.field_value) = TRIM(latest_cc.cc_status_flg)
       AND latest_cc_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l latest_cc_entity_l
        ON TRIM(latest_cc_entity_l.field_name) = 'CC_ENTITY_FLG'
       AND TRIM(latest_cc_entity_l.field_value) = TRIM(latest_cc.cc_entity_flg)
       AND latest_cc_entity_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l latest_cc_contact_meth_l
        ON TRIM(latest_cc_contact_meth_l.field_name) = 'CONTACT_METH_FLG'
       AND TRIM(latest_cc_contact_meth_l.field_value) = TRIM(latest_cc.contact_meth_flg)
       AND latest_cc_contact_meth_l.language_cd = 'ENG'
    LEFT JOIN cisadm.sc_user latest_cc_user
        ON latest_cc_user.user_id = latest_cc.user_id;

    COMMIT;
END;
/
