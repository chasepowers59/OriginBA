CREATE OR REPLACE PROCEDURE cisadm.refresh_ops_exception_rpt_curr AS
    v_load_dttm      TIMESTAMP := SYSTIMESTAMP;
    v_window_start   TIMESTAMP := CAST(ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6) AS TIMESTAMP);
BEGIN
    DELETE FROM cisadm.ops_exception_rpt_curr snap
    WHERE snap.excp_cre_dttm < v_window_start
      AND NVL(snap.bseg_review_comp, 'N') = 'Y'
      AND NVL(snap.open_close_flg, 'C') <> 'O'
      AND NVL(snap.td_entry_status_flg, 'C') <> 'O';
    COMMIT;

    DELETE FROM cisadm.ops_exception_rpt_curr snap
    WHERE snap.excp_cre_dttm >= v_window_start
       OR NVL(snap.bseg_review_comp, 'N') <> 'Y'
       OR snap.open_close_flg = 'O'
       OR snap.td_entry_status_flg = 'O';
    COMMIT;

    INSERT INTO cisadm.ops_exception_rpt_curr (
        excp_source,
        excp_natural_key,
        excp_cre_dttm,
        open_close_flg,
        open_close_desc,
        excp_severity_flg,
        excp_severity_desc,
        bus_obj_cd,
        bus_obj_desc,
        bo_status_cd,
        bo_status_desc,
        bo_status_reason_cd,
        status_upd_dttm,
        bseg_id,
        bseg_excp_flg,
        bseg_excp_desc,
        bseg_excp_msg,
        bseg_excp_comments,
        bseg_review_comp,
        bseg_review_dt,
        bseg_review_user_id,
        bseg_review_user_name,
        bseg_excp_user_id,
        bseg_excp_user_name,
        sa_id,
        acct_id,
        customer_name_upr,
        bill_cyc_cd,
        bill_cyc_desc,
        cust_cl_cd,
        cust_cl_desc,
        coll_cl_cd,
        coll_cl_desc,
        acct_mgmt_grp_cd,
        acct_mgmt_grp_desc,
        bud_plan_cd,
        bud_plan_desc,
        sa_type_cd,
        sa_type_desc,
        sa_status_flg,
        sa_status_desc,
        usage_excp_id,
        d1_usage_id,
        usage_excp_type_cd,
        usage_excp_type_desc,
        usg_grp_cd,
        usg_grp_desc,
        usg_rule_cd,
        usg_rule_desc,
        vee_excp_id,
        init_msrmt_data_id,
        excp_type_cd,
        excp_type_desc,
        vee_grp_cd,
        vee_grp_desc,
        vee_rule_cd,
        vee_rule_desc,
        d1_sp_id,
        sp_address1,
        sp_city,
        sp_state,
        sp_postal,
        sp_division_cd,
        sp_division_desc,
        sp_mkt_cd,
        sp_mkt_desc,
        sp_type_cd,
        sp_type_desc,
        td_entry_id,
        td_type_cd,
        td_type_desc,
        td_entry_status_flg,
        td_entry_status_desc,
        td_priority_flg,
        td_priority_desc,
        td_role_id,
        td_role_desc,
        td_assigned_to,
        td_assigned_to_name,
        td_assigned_user_id,
        td_assigned_user_name,
        td_complete_user_id,
        td_complete_user_name,
        td_cre_dttm,
        td_assigned_dttm,
        td_complete_dttm,
        td_batch_cd,
        td_batch_nbr,
        td_message_cat_nbr,
        td_message_nbr,
        td_comments,
        load_dttm
    )
    WITH
    usage_sp_ranked AS (
        SELECT
            us_sp.us_id,
            us_sp.d1_sp_id,
            ROW_NUMBER() OVER (
                PARTITION BY us_sp.us_id
                ORDER BY us_sp.d1_sp_id
            ) AS rn
        FROM cisadm.d1_us_sp us_sp
    ),
    vee_sp_ranked AS (
        SELECT
            imd.init_msrmt_data_id,
            sp.d1_sp_id,
            sp.address1,
            sp.city,
            sp.state,
            sp.postal,
            sp.division_cd,
            sp.mkt_cd,
            sp.d1_sp_type_cd,
            ROW_NUMBER() OVER (
                PARTITION BY imd.init_msrmt_data_id
                ORDER BY inst.d1_install_dttm DESC NULLS LAST, sp.d1_sp_id
            ) AS rn
        FROM cisadm.d1_init_msrmt_data imd
        JOIN cisadm.d1_measr_comp mc
            ON mc.measr_comp_id = imd.measr_comp_id
        JOIN cisadm.d1_dvc_cfg dvc
            ON dvc.device_config_id = mc.device_config_id
        JOIN cisadm.d1_install_evt inst
            ON inst.device_config_id = dvc.device_config_id
        JOIN cisadm.d1_sp sp
            ON sp.d1_sp_id = inst.d1_sp_id
    ),
    refresh_scope AS (
        SELECT 'BSEG' AS excp_source, excp.bseg_id || '~' || excp.bseg_excp_flg AS excp_natural_key
        FROM cisadm.ci_bseg_excp excp
        WHERE excp.cre_dttm >= v_window_start
           OR NVL(excp.review_comp, 'N') <> 'Y'
        UNION ALL
        SELECT 'USAGE', excp.usage_excp_id
        FROM cisadm.d1_usage_excp excp
        WHERE excp.cre_dttm >= v_window_start
           OR excp.open_close_flg = 'O'
        UNION ALL
        SELECT 'VEE', excp.vee_excp_id
        FROM cisadm.d1_vee_excp excp
        WHERE excp.cre_dttm >= v_window_start
           OR excp.open_close_flg = 'O'
    ),
    td_ranked AS (
        SELECT
            drl.key_value,
            ty.tbl_name,
            ty.fld_name,
            td.td_entry_id,
            td.td_type_cd,
            td.entry_status_flg,
            td.td_priority_flg,
            td.role_id,
            td.assigned_to,
            td.assigned_user_id,
            td.complete_user_id,
            td.cre_dttm,
            td.assigned_dttm,
            td.complete_dttm,
            td.batch_cd,
            td.batch_nbr,
            td.message_cat_nbr,
            td.message_nbr,
            td.comments,
            ROW_NUMBER() OVER (
                PARTITION BY drl.key_value, ty.tbl_name, ty.fld_name
                ORDER BY
                    CASE WHEN td.entry_status_flg = 'O' THEN 0 ELSE 1 END,
                    td.cre_dttm DESC,
                    td.td_entry_id
            ) AS rn
        FROM cisadm.ci_td_drlkey drl
        JOIN cisadm.ci_td_drlkey_ty ty
            ON ty.seq_num = drl.seq_num
        JOIN cisadm.ci_td_entry td
            ON td.td_entry_id = drl.td_entry_id
           AND td.td_type_cd = ty.td_type_cd
    ),
    bseg_main_cust AS (
        SELECT
            ap.acct_id,
            pn.entity_name_upr AS customer_name_upr,
            ROW_NUMBER() OVER (
                PARTITION BY ap.acct_id
                ORDER BY
                    CASE WHEN ap.main_cust_sw = 'Y' THEN 0 ELSE 1 END,
                    ap.per_id
            ) AS rn
        FROM cisadm.ci_acct_per ap
        JOIN cisadm.ci_per_name pn
            ON pn.per_id = ap.per_id
           AND pn.name_type_flg = 'PRIM'
        WHERE ap.main_cust_sw = 'Y'
    ),
    bseg_rows AS (
        SELECT
            'BSEG' AS excp_source,
            excp.bseg_id || '~' || excp.bseg_excp_flg AS excp_natural_key,
            excp.cre_dttm AS excp_cre_dttm,
            CAST(NULL AS VARCHAR2(4)) AS open_close_flg,
            CAST(NULL AS VARCHAR2(240)) AS open_close_desc,
            CAST(NULL AS VARCHAR2(4)) AS excp_severity_flg,
            CAST(NULL AS VARCHAR2(240)) AS excp_severity_desc,
            CAST(NULL AS VARCHAR2(48)) AS bus_obj_cd,
            CAST(NULL AS VARCHAR2(240)) AS bus_obj_desc,
            CAST(NULL AS VARCHAR2(48)) AS bo_status_cd,
            CAST(NULL AS VARCHAR2(240)) AS bo_status_desc,
            CAST(NULL AS VARCHAR2(48)) AS bo_status_reason_cd,
            CAST(NULL AS TIMESTAMP) AS status_upd_dttm,
            excp.bseg_id,
            excp.bseg_excp_flg,
            bseg_excp_l.descr AS bseg_excp_desc,
            excp.exp_msg AS bseg_excp_msg,
            excp.comments AS bseg_excp_comments,
            excp.review_comp AS bseg_review_comp,
            excp.review_dt AS bseg_review_dt,
            excp.review_user_id AS bseg_review_user_id,
            review_user.first_name || ' ' || review_user.last_name AS bseg_review_user_name,
            excp.user_id AS bseg_excp_user_id,
            excp_user.first_name || ' ' || excp_user.last_name AS bseg_excp_user_name,
            sa.sa_id,
            acct.acct_id,
            mc.customer_name_upr,
            acct.bill_cyc_cd,
            bill_cyc_l.descr AS bill_cyc_desc,
            acct.cust_cl_cd,
            cust_cl_l.descr AS cust_cl_desc,
            acct.coll_cl_cd,
            coll_cl_l.descr AS coll_cl_desc,
            acct.acct_mgmt_grp_cd,
            acct_mgmt_l.descr AS acct_mgmt_grp_desc,
            acct.bud_plan_cd,
            bud_plan_l.descr AS bud_plan_desc,
            sa.sa_type_cd,
            sa_type_l.descr AS sa_type_desc,
            sa.sa_status_flg,
            sa_status_l.descr AS sa_status_desc,
            CAST(NULL AS VARCHAR2(40)) AS usage_excp_id,
            CAST(NULL AS VARCHAR2(40)) AS d1_usage_id,
            CAST(NULL AS VARCHAR2(48)) AS usage_excp_type_cd,
            CAST(NULL AS VARCHAR2(240)) AS usage_excp_type_desc,
            CAST(NULL AS VARCHAR2(48)) AS usg_grp_cd,
            CAST(NULL AS VARCHAR2(240)) AS usg_grp_desc,
            CAST(NULL AS VARCHAR2(48)) AS usg_rule_cd,
            CAST(NULL AS VARCHAR2(240)) AS usg_rule_desc,
            CAST(NULL AS VARCHAR2(40)) AS vee_excp_id,
            CAST(NULL AS VARCHAR2(40)) AS init_msrmt_data_id,
            CAST(NULL AS VARCHAR2(48)) AS excp_type_cd,
            CAST(NULL AS VARCHAR2(240)) AS excp_type_desc,
            CAST(NULL AS VARCHAR2(48)) AS vee_grp_cd,
            CAST(NULL AS VARCHAR2(240)) AS vee_grp_desc,
            CAST(NULL AS VARCHAR2(48)) AS vee_rule_cd,
            CAST(NULL AS VARCHAR2(240)) AS vee_rule_desc,
            CAST(NULL AS VARCHAR2(40)) AS d1_sp_id,
            CAST(NULL AS VARCHAR2(254)) AS sp_address1,
            CAST(NULL AS VARCHAR2(90)) AS sp_city,
            CAST(NULL AS VARCHAR2(24)) AS sp_state,
            CAST(NULL AS VARCHAR2(48)) AS sp_postal,
            CAST(NULL AS VARCHAR2(48)) AS sp_division_cd,
            CAST(NULL AS VARCHAR2(240)) AS sp_division_desc,
            CAST(NULL AS VARCHAR2(48)) AS sp_mkt_cd,
            CAST(NULL AS VARCHAR2(240)) AS sp_mkt_desc,
            CAST(NULL AS VARCHAR2(48)) AS sp_type_cd,
            CAST(NULL AS VARCHAR2(240)) AS sp_type_desc,
            td.td_entry_id,
            td.td_type_cd,
            td_type_l.descr AS td_type_desc,
            td.entry_status_flg AS td_entry_status_flg,
            td_status_l.descr AS td_entry_status_desc,
            td.td_priority_flg,
            td_priority_l.descr AS td_priority_desc,
            td.role_id AS td_role_id,
            role_l.descr AS td_role_desc,
            td.assigned_to AS td_assigned_to,
            assigned_to_user.first_name || ' ' || assigned_to_user.last_name AS td_assigned_to_name,
            td.assigned_user_id AS td_assigned_user_id,
            assigned_by_user.first_name || ' ' || assigned_by_user.last_name AS td_assigned_user_name,
            td.complete_user_id AS td_complete_user_id,
            complete_user.first_name || ' ' || complete_user.last_name AS td_complete_user_name,
            td.cre_dttm AS td_cre_dttm,
            td.assigned_dttm AS td_assigned_dttm,
            td.complete_dttm AS td_complete_dttm,
            td.batch_cd AS td_batch_cd,
            td.batch_nbr AS td_batch_nbr,
            td.message_cat_nbr AS td_message_cat_nbr,
            td.message_nbr AS td_message_nbr,
            td.comments AS td_comments
        FROM cisadm.ci_bseg_excp excp
        JOIN refresh_scope rs
            ON rs.excp_source = 'BSEG'
           AND rs.excp_natural_key = excp.bseg_id || '~' || excp.bseg_excp_flg
        JOIN cisadm.ci_bseg bseg
            ON bseg.bseg_id = excp.bseg_id
        JOIN cisadm.ci_sa sa
            ON sa.sa_id = bseg.sa_id
        JOIN cisadm.ci_acct acct
            ON acct.acct_id = sa.acct_id
        LEFT JOIN bseg_main_cust mc
            ON mc.acct_id = acct.acct_id
           AND mc.rn = 1
        LEFT JOIN td_ranked td
            ON td.key_value = excp.bseg_id
           AND td.tbl_name = 'CI_BSEG'
           AND td.fld_name = 'BSEG_ID'
           AND td.rn = 1
        LEFT JOIN cisadm.ci_lookup_val_l bseg_excp_l
            ON TRIM(bseg_excp_l.field_name) = 'BSEG_EXCP_FLG'
           AND TRIM(bseg_excp_l.field_value) = TRIM(excp.bseg_excp_flg)
           AND bseg_excp_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_bill_cyc_l bill_cyc_l
            ON bill_cyc_l.bill_cyc_cd = acct.bill_cyc_cd
           AND bill_cyc_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_cust_cl_l cust_cl_l
            ON cust_cl_l.cust_cl_cd = acct.cust_cl_cd
           AND cust_cl_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_coll_cl_l coll_cl_l
            ON coll_cl_l.coll_cl_cd = acct.coll_cl_cd
           AND coll_cl_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt_l
            ON acct_mgmt_l.acct_mgmt_grp_cd = acct.acct_mgmt_grp_cd
           AND acct_mgmt_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_bud_plan_l bud_plan_l
            ON bud_plan_l.bud_plan_cd = acct.bud_plan_cd
           AND bud_plan_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_sa_type_l sa_type_l
            ON sa_type_l.sa_type_cd = sa.sa_type_cd
           AND sa_type_l.cis_division = sa.cis_division
           AND sa_type_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_lookup_val_l sa_status_l
            ON TRIM(sa_status_l.field_name) = 'SA_STATUS_FLG'
           AND TRIM(sa_status_l.field_value) = TRIM(sa.sa_status_flg)
           AND sa_status_l.language_cd = 'ENG'
        LEFT JOIN cisadm.sc_user review_user
            ON review_user.user_id = excp.review_user_id
        LEFT JOIN cisadm.sc_user excp_user
            ON excp_user.user_id = excp.user_id
        LEFT JOIN cisadm.ci_td_type_l td_type_l
            ON td_type_l.td_type_cd = td.td_type_cd
           AND td_type_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_lookup_val_l td_status_l
            ON TRIM(td_status_l.field_name) = 'ENTRY_STATUS_FLG'
           AND TRIM(td_status_l.field_value) = TRIM(td.entry_status_flg)
           AND td_status_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_lookup_val_l td_priority_l
            ON TRIM(td_priority_l.field_name) = 'TD_PRIORITY_FLG'
           AND TRIM(td_priority_l.field_value) = TRIM(td.td_priority_flg)
           AND td_priority_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_role_l role_l
            ON role_l.role_id = td.role_id
           AND role_l.language_cd = 'ENG'
        LEFT JOIN cisadm.sc_user assigned_to_user
            ON assigned_to_user.user_id = td.assigned_to
        LEFT JOIN cisadm.sc_user assigned_by_user
            ON assigned_by_user.user_id = td.assigned_user_id
        LEFT JOIN cisadm.sc_user complete_user
            ON complete_user.user_id = td.complete_user_id
    ),
    usage_rows AS (
        SELECT
            'USAGE' AS excp_source,
            excp.usage_excp_id AS excp_natural_key,
            excp.cre_dttm AS excp_cre_dttm,
            excp.open_close_flg,
            open_close_l.descr AS open_close_desc,
            excp.excp_severity_flg,
            severity_l.descr AS excp_severity_desc,
            excp.bus_obj_cd,
            bus_obj_l.descr AS bus_obj_desc,
            excp.bo_status_cd,
            bus_status_l.descr AS bo_status_desc,
            CAST(NULL AS VARCHAR2(48)) AS bo_status_reason_cd,
            excp.status_upd_dttm,
            CAST(NULL AS VARCHAR2(40)) AS bseg_id,
            CAST(NULL AS VARCHAR2(16)) AS bseg_excp_flg,
            CAST(NULL AS VARCHAR2(240)) AS bseg_excp_desc,
            CAST(NULL AS VARCHAR2(4000)) AS bseg_excp_msg,
            CAST(NULL AS VARCHAR2(4000)) AS bseg_excp_comments,
            CAST(NULL AS VARCHAR2(4)) AS bseg_review_comp,
            CAST(NULL AS DATE) AS bseg_review_dt,
            CAST(NULL AS VARCHAR2(40)) AS bseg_review_user_id,
            CAST(NULL AS VARCHAR2(200)) AS bseg_review_user_name,
            CAST(NULL AS VARCHAR2(40)) AS bseg_excp_user_id,
            CAST(NULL AS VARCHAR2(200)) AS bseg_excp_user_name,
            CAST(NULL AS VARCHAR2(40)) AS sa_id,
            CAST(NULL AS VARCHAR2(40)) AS acct_id,
            pn.entity_name_upr AS customer_name_upr,
            CAST(NULL AS VARCHAR2(40)) AS bill_cyc_cd,
            CAST(NULL AS VARCHAR2(240)) AS bill_cyc_desc,
            CAST(NULL AS VARCHAR2(40)) AS cust_cl_cd,
            CAST(NULL AS VARCHAR2(240)) AS cust_cl_desc,
            CAST(NULL AS VARCHAR2(40)) AS coll_cl_cd,
            CAST(NULL AS VARCHAR2(240)) AS coll_cl_desc,
            CAST(NULL AS VARCHAR2(40)) AS acct_mgmt_grp_cd,
            CAST(NULL AS VARCHAR2(240)) AS acct_mgmt_grp_desc,
            CAST(NULL AS VARCHAR2(40)) AS bud_plan_cd,
            CAST(NULL AS VARCHAR2(240)) AS bud_plan_desc,
            CAST(NULL AS VARCHAR2(40)) AS sa_type_cd,
            CAST(NULL AS VARCHAR2(240)) AS sa_type_desc,
            CAST(NULL AS VARCHAR2(8)) AS sa_status_flg,
            CAST(NULL AS VARCHAR2(240)) AS sa_status_desc,
            excp.usage_excp_id,
            excp.d1_usage_id,
            excp.usage_excp_type_cd,
            excp_type_l.descr100 AS usage_excp_type_desc,
            excp.usg_grp_cd,
            usg_grp_l.descr100 AS usg_grp_desc,
            excp.usg_rule_cd,
            usg_rule_l.descr100 AS usg_rule_desc,
            CAST(NULL AS VARCHAR2(40)) AS vee_excp_id,
            CAST(NULL AS VARCHAR2(40)) AS init_msrmt_data_id,
            CAST(NULL AS VARCHAR2(48)) AS excp_type_cd,
            CAST(NULL AS VARCHAR2(240)) AS excp_type_desc,
            CAST(NULL AS VARCHAR2(48)) AS vee_grp_cd,
            CAST(NULL AS VARCHAR2(240)) AS vee_grp_desc,
            CAST(NULL AS VARCHAR2(48)) AS vee_rule_cd,
            CAST(NULL AS VARCHAR2(240)) AS vee_rule_desc,
            sp.d1_sp_id,
            sp.address1 AS sp_address1,
            sp.city AS sp_city,
            sp.state AS sp_state,
            sp.postal AS sp_postal,
            sp.division_cd AS sp_division_cd,
            division_l.descr100 AS sp_division_desc,
            sp.mkt_cd AS sp_mkt_cd,
            mkt_l.descr100 AS sp_mkt_desc,
            sp.d1_sp_type_cd AS sp_type_cd,
            sp_type_l.descr100 AS sp_type_desc,
            td.td_entry_id,
            td.td_type_cd,
            td_type_l.descr AS td_type_desc,
            td.entry_status_flg AS td_entry_status_flg,
            td_status_l.descr AS td_entry_status_desc,
            td.td_priority_flg,
            td_priority_l.descr AS td_priority_desc,
            td.role_id AS td_role_id,
            role_l.descr AS td_role_desc,
            td.assigned_to AS td_assigned_to,
            assigned_to_user.first_name || ' ' || assigned_to_user.last_name AS td_assigned_to_name,
            td.assigned_user_id AS td_assigned_user_id,
            assigned_by_user.first_name || ' ' || assigned_by_user.last_name AS td_assigned_user_name,
            td.complete_user_id AS td_complete_user_id,
            complete_user.first_name || ' ' || complete_user.last_name AS td_complete_user_name,
            td.cre_dttm AS td_cre_dttm,
            td.assigned_dttm AS td_assigned_dttm,
            td.complete_dttm AS td_complete_dttm,
            td.batch_cd AS td_batch_cd,
            td.batch_nbr AS td_batch_nbr,
            td.message_cat_nbr AS td_message_cat_nbr,
            td.message_nbr AS td_message_nbr,
            td.comments AS td_comments
        FROM cisadm.d1_usage_excp excp
        JOIN refresh_scope rs
            ON rs.excp_source = 'USAGE'
           AND rs.excp_natural_key = excp.usage_excp_id
        LEFT JOIN cisadm.d1_usage usg
            ON usg.d1_usage_id = excp.d1_usage_id
        LEFT JOIN usage_sp_ranked us_sp
            ON us_sp.us_id = usg.us_id
           AND us_sp.rn = 1
        LEFT JOIN cisadm.d1_sp sp
            ON sp.d1_sp_id = us_sp.d1_sp_id
           AND sp.bo_status_cd = 'ACTIVE'
        LEFT JOIN cisadm.d1_us_contact us_contact
            ON us_contact.us_id = usg.us_id
        LEFT JOIN cisadm.d1_contact_identifier contact_id
            ON contact_id.contact_id = us_contact.contact_id
           AND contact_id.contact_id_type_flg = 'D1EI'
        LEFT JOIN cisadm.ci_per_name pn
            ON pn.per_id = contact_id.id_value
           AND pn.name_type_flg = 'PRIM'
        LEFT JOIN td_ranked td
            ON td.key_value = excp.d1_usage_id
           AND td.tbl_name = 'D1_USAGE'
           AND td.fld_name = 'D1_USAGE_ID'
           AND td.rn = 1
        LEFT JOIN cisadm.ci_lookup_val_l open_close_l
            ON TRIM(open_close_l.field_name) = 'OPEN_CLOSE_FLG'
           AND TRIM(open_close_l.field_value) = TRIM(excp.open_close_flg)
           AND open_close_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_lookup_val_l severity_l
            ON TRIM(severity_l.field_name) = 'EXCP_SEVERITY_FLG'
           AND TRIM(severity_l.field_value) = TRIM(excp.excp_severity_flg)
           AND severity_l.language_cd = 'ENG'
        LEFT JOIN cisadm.f1_bus_obj_l bus_obj_l
            ON bus_obj_l.bus_obj_cd = excp.bus_obj_cd
           AND bus_obj_l.language_cd = 'ENG'
        LEFT JOIN cisadm.f1_bus_obj_status_l bus_status_l
            ON bus_status_l.bus_obj_cd = excp.bus_obj_cd
           AND bus_status_l.bo_status_cd = excp.bo_status_cd
           AND bus_status_l.language_cd = 'ENG'
        LEFT JOIN cisadm.d1_usage_excp_type_l excp_type_l
            ON excp_type_l.usage_excp_type_cd = excp.usage_excp_type_cd
           AND excp_type_l.language_cd = 'ENG'
        LEFT JOIN cisadm.d1_usg_grp_l usg_grp_l
            ON usg_grp_l.usg_grp_cd = excp.usg_grp_cd
           AND usg_grp_l.language_cd = 'ENG'
        LEFT JOIN cisadm.d1_usg_rule_l usg_rule_l
            ON usg_rule_l.usg_grp_cd = excp.usg_grp_cd
           AND usg_rule_l.usg_rule_cd = excp.usg_rule_cd
           AND usg_rule_l.language_cd = 'ENG'
        LEFT JOIN cisadm.d1_division_l division_l
            ON division_l.division_cd = sp.division_cd
           AND division_l.language_cd = 'ENG'
        LEFT JOIN cisadm.d1_mkt_l mkt_l
            ON mkt_l.mkt_cd = sp.mkt_cd
           AND mkt_l.language_cd = 'ENG'
        LEFT JOIN cisadm.d1_sp_type_l sp_type_l
            ON sp_type_l.d1_sp_type_cd = sp.d1_sp_type_cd
           AND sp_type_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_td_type_l td_type_l
            ON td_type_l.td_type_cd = td.td_type_cd
           AND td_type_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_lookup_val_l td_status_l
            ON TRIM(td_status_l.field_name) = 'ENTRY_STATUS_FLG'
           AND TRIM(td_status_l.field_value) = TRIM(td.entry_status_flg)
           AND td_status_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_lookup_val_l td_priority_l
            ON TRIM(td_priority_l.field_name) = 'TD_PRIORITY_FLG'
           AND TRIM(td_priority_l.field_value) = TRIM(td.td_priority_flg)
           AND td_priority_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_role_l role_l
            ON role_l.role_id = td.role_id
           AND role_l.language_cd = 'ENG'
        LEFT JOIN cisadm.sc_user assigned_to_user
            ON assigned_to_user.user_id = td.assigned_to
        LEFT JOIN cisadm.sc_user assigned_by_user
            ON assigned_by_user.user_id = td.assigned_user_id
        LEFT JOIN cisadm.sc_user complete_user
            ON complete_user.user_id = td.complete_user_id
    ),
    vee_rows AS (
        SELECT
            'VEE' AS excp_source,
            excp.vee_excp_id AS excp_natural_key,
            excp.cre_dttm AS excp_cre_dttm,
            excp.open_close_flg,
            open_close_l.descr AS open_close_desc,
            excp.excp_severity_flg,
            severity_l.descr AS excp_severity_desc,
            excp.bus_obj_cd,
            bus_obj_l.descr AS bus_obj_desc,
            excp.bo_status_cd,
            bus_status_l.descr AS bo_status_desc,
            excp.bo_status_reason_cd,
            excp.status_upd_dttm,
            CAST(NULL AS VARCHAR2(40)) AS bseg_id,
            CAST(NULL AS VARCHAR2(16)) AS bseg_excp_flg,
            CAST(NULL AS VARCHAR2(240)) AS bseg_excp_desc,
            CAST(NULL AS VARCHAR2(4000)) AS bseg_excp_msg,
            CAST(NULL AS VARCHAR2(4000)) AS bseg_excp_comments,
            CAST(NULL AS VARCHAR2(4)) AS bseg_review_comp,
            CAST(NULL AS DATE) AS bseg_review_dt,
            CAST(NULL AS VARCHAR2(40)) AS bseg_review_user_id,
            CAST(NULL AS VARCHAR2(200)) AS bseg_review_user_name,
            CAST(NULL AS VARCHAR2(40)) AS bseg_excp_user_id,
            CAST(NULL AS VARCHAR2(200)) AS bseg_excp_user_name,
            CAST(NULL AS VARCHAR2(40)) AS sa_id,
            CAST(NULL AS VARCHAR2(40)) AS acct_id,
            CAST(NULL AS VARCHAR2(200)) AS customer_name_upr,
            CAST(NULL AS VARCHAR2(40)) AS bill_cyc_cd,
            CAST(NULL AS VARCHAR2(240)) AS bill_cyc_desc,
            CAST(NULL AS VARCHAR2(40)) AS cust_cl_cd,
            CAST(NULL AS VARCHAR2(240)) AS cust_cl_desc,
            CAST(NULL AS VARCHAR2(40)) AS coll_cl_cd,
            CAST(NULL AS VARCHAR2(240)) AS coll_cl_desc,
            CAST(NULL AS VARCHAR2(40)) AS acct_mgmt_grp_cd,
            CAST(NULL AS VARCHAR2(240)) AS acct_mgmt_grp_desc,
            CAST(NULL AS VARCHAR2(40)) AS bud_plan_cd,
            CAST(NULL AS VARCHAR2(240)) AS bud_plan_desc,
            CAST(NULL AS VARCHAR2(40)) AS sa_type_cd,
            CAST(NULL AS VARCHAR2(240)) AS sa_type_desc,
            CAST(NULL AS VARCHAR2(8)) AS sa_status_flg,
            CAST(NULL AS VARCHAR2(240)) AS sa_status_desc,
            CAST(NULL AS VARCHAR2(40)) AS usage_excp_id,
            CAST(NULL AS VARCHAR2(40)) AS d1_usage_id,
            CAST(NULL AS VARCHAR2(48)) AS usage_excp_type_cd,
            CAST(NULL AS VARCHAR2(240)) AS usage_excp_type_desc,
            CAST(NULL AS VARCHAR2(48)) AS usg_grp_cd,
            CAST(NULL AS VARCHAR2(240)) AS usg_grp_desc,
            CAST(NULL AS VARCHAR2(48)) AS usg_rule_cd,
            CAST(NULL AS VARCHAR2(240)) AS usg_rule_desc,
            excp.vee_excp_id,
            excp.init_msrmt_data_id,
            excp.excp_type_cd,
            excp_type_l.descr100 AS excp_type_desc,
            excp.vee_grp_cd,
            vee_grp_l.descr100 AS vee_grp_desc,
            excp.vee_rule_cd,
            vee_rule_l.descr100 AS vee_rule_desc,
            sp_pick.d1_sp_id,
            sp_pick.address1 AS sp_address1,
            sp_pick.city AS sp_city,
            sp_pick.state AS sp_state,
            sp_pick.postal AS sp_postal,
            sp_pick.division_cd AS sp_division_cd,
            division_l.descr100 AS sp_division_desc,
            sp_pick.mkt_cd AS sp_mkt_cd,
            mkt_l.descr100 AS sp_mkt_desc,
            sp_pick.d1_sp_type_cd AS sp_type_cd,
            sp_type_l.descr100 AS sp_type_desc,
            td.td_entry_id,
            td.td_type_cd,
            td_type_l.descr AS td_type_desc,
            td.entry_status_flg AS td_entry_status_flg,
            td_status_l.descr AS td_entry_status_desc,
            td.td_priority_flg,
            td_priority_l.descr AS td_priority_desc,
            td.role_id AS td_role_id,
            role_l.descr AS td_role_desc,
            td.assigned_to AS td_assigned_to,
            assigned_to_user.first_name || ' ' || assigned_to_user.last_name AS td_assigned_to_name,
            td.assigned_user_id AS td_assigned_user_id,
            assigned_by_user.first_name || ' ' || assigned_by_user.last_name AS td_assigned_user_name,
            td.complete_user_id AS td_complete_user_id,
            complete_user.first_name || ' ' || complete_user.last_name AS td_complete_user_name,
            td.cre_dttm AS td_cre_dttm,
            td.assigned_dttm AS td_assigned_dttm,
            td.complete_dttm AS td_complete_dttm,
            td.batch_cd AS td_batch_cd,
            td.batch_nbr AS td_batch_nbr,
            td.message_cat_nbr AS td_message_cat_nbr,
            td.message_nbr AS td_message_nbr,
            td.comments AS td_comments
        FROM cisadm.d1_vee_excp excp
        JOIN refresh_scope rs
            ON rs.excp_source = 'VEE'
           AND rs.excp_natural_key = excp.vee_excp_id
        LEFT JOIN vee_sp_ranked sp_pick
            ON sp_pick.init_msrmt_data_id = excp.init_msrmt_data_id
           AND sp_pick.rn = 1
        LEFT JOIN td_ranked td
            ON td.key_value = excp.init_msrmt_data_id
           AND td.tbl_name = 'D1_INIT_MSRMT_DATA'
           AND td.fld_name = 'INIT_MSRMT_DATA_ID'
           AND td.rn = 1
        LEFT JOIN cisadm.ci_lookup_val_l open_close_l
            ON TRIM(open_close_l.field_name) = 'OPEN_CLOSE_FLG'
           AND TRIM(open_close_l.field_value) = TRIM(excp.open_close_flg)
           AND open_close_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_lookup_val_l severity_l
            ON TRIM(severity_l.field_name) = 'EXCP_SEVERITY_FLG'
           AND TRIM(severity_l.field_value) = TRIM(excp.excp_severity_flg)
           AND severity_l.language_cd = 'ENG'
        LEFT JOIN cisadm.f1_bus_obj_l bus_obj_l
            ON bus_obj_l.bus_obj_cd = excp.bus_obj_cd
           AND bus_obj_l.language_cd = 'ENG'
        LEFT JOIN cisadm.f1_bus_obj_status_l bus_status_l
            ON bus_status_l.bus_obj_cd = excp.bus_obj_cd
           AND bus_status_l.bo_status_cd = excp.bo_status_cd
           AND bus_status_l.language_cd = 'ENG'
        LEFT JOIN cisadm.d1_excp_type_l excp_type_l
            ON excp_type_l.excp_type_cd = excp.excp_type_cd
           AND excp_type_l.language_cd = 'ENG'
        LEFT JOIN cisadm.d1_vee_grp_l vee_grp_l
            ON vee_grp_l.vee_grp_cd = excp.vee_grp_cd
           AND vee_grp_l.language_cd = 'ENG'
        LEFT JOIN cisadm.d1_vee_rule_l vee_rule_l
            ON vee_rule_l.vee_grp_cd = excp.vee_grp_cd
           AND vee_rule_l.vee_rule_cd = excp.vee_rule_cd
           AND vee_rule_l.language_cd = 'ENG'
        LEFT JOIN cisadm.d1_division_l division_l
            ON division_l.division_cd = sp_pick.division_cd
           AND division_l.language_cd = 'ENG'
        LEFT JOIN cisadm.d1_mkt_l mkt_l
            ON mkt_l.mkt_cd = sp_pick.mkt_cd
           AND mkt_l.language_cd = 'ENG'
        LEFT JOIN cisadm.d1_sp_type_l sp_type_l
            ON sp_type_l.d1_sp_type_cd = sp_pick.d1_sp_type_cd
           AND sp_type_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_td_type_l td_type_l
            ON td_type_l.td_type_cd = td.td_type_cd
           AND td_type_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_lookup_val_l td_status_l
            ON TRIM(td_status_l.field_name) = 'ENTRY_STATUS_FLG'
           AND TRIM(td_status_l.field_value) = TRIM(td.entry_status_flg)
           AND td_status_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_lookup_val_l td_priority_l
            ON TRIM(td_priority_l.field_name) = 'TD_PRIORITY_FLG'
           AND TRIM(td_priority_l.field_value) = TRIM(td.td_priority_flg)
           AND td_priority_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_role_l role_l
            ON role_l.role_id = td.role_id
           AND role_l.language_cd = 'ENG'
        LEFT JOIN cisadm.sc_user assigned_to_user
            ON assigned_to_user.user_id = td.assigned_to
        LEFT JOIN cisadm.sc_user assigned_by_user
            ON assigned_by_user.user_id = td.assigned_user_id
        LEFT JOIN cisadm.sc_user complete_user
            ON complete_user.user_id = td.complete_user_id
    )
    SELECT
        src.*,
        v_load_dttm
    FROM (
        SELECT * FROM bseg_rows
        UNION ALL
        SELECT * FROM usage_rows
        UNION ALL
        SELECT * FROM vee_rows
    ) src;

    COMMIT;
END;
/
