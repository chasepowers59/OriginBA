CREATE OR REPLACE PROCEDURE cisadm.refresh_device_sp_rpt_curr AS
    v_load_dttm TIMESTAMP := SYSTIMESTAMP;
BEGIN
    EXECUTE IMMEDIATE 'TRUNCATE TABLE cisadm.device_sp_rpt_curr';

    INSERT INTO cisadm.device_sp_rpt_curr (
        d1_dvc_id,
        device_type_cd,
        device_type_desc,
        bus_obj_cd,
        bus_obj_desc,
        bo_status_cd,
        bo_status_desc,
        bo_status_reason_cd,
        manufacturer_cd,
        manufacturer_desc,
        d1_model_cd,
        model_desc,
        d1_spr_cd,
        spr_desc,
        access_grp_cd,
        access_grp_desc,
        arming_req_flg,
        arming_req_desc,
        head_end_registr_status_flg,
        head_end_registr_status_desc,
        in_data_shift_flg,
        in_data_shift_desc,
        d1_cmd_set_cd,
        cmd_set_desc,
        dvc_cre_dttm,
        dvc_status_upd_dttm,
        asset_id,
        serial_number,
        badge_number,
        external_id,
        utility_device_id,
        identifier_name,
        mdm_external_id,
        mxu_type,
        mxu_type_desc,
        asset_type_cd,
        asset_type_desc,
        asset_bo_status_cd,
        asset_bo_status_desc,
        asset_cond_flg,
        asset_cond_desc,
        asset_ownership_flg,
        asset_ownership_desc,
        asset_specification_cd,
        asset_specification_desc,
        asset_in_service_dt,
        asset_acquisition_dt,
        asset_serial_number,
        device_config_id,
        device_config_type_cd,
        device_config_type_desc,
        cfg_bo_status_cd,
        cfg_bo_status_desc,
        cfg_eff_dttm,
        cfg_time_zone_cd,
        cfg_time_zone_desc,
        install_evt_id,
        install_bo_status_cd,
        install_bo_status_desc,
        install_dttm,
        removal_dttm,
        arm_stat_flg,
        arm_stat_desc,
        d1_sp_id,
        d1_sp_type_cd,
        d1_sp_type_desc,
        sp_bo_status_cd,
        sp_bo_status_desc,
        sp_src_stat_flg,
        sp_src_stat_desc,
        msrmt_cyc_cd,
        msrmt_cyc_desc,
        msrmt_cyc_rte_cd,
        msrmt_cyc_rte_desc,
        division_cd,
        mkt_cd,
        d1_ls_sl_flg,
        d1_ls_sl_descr,
        sp_address1,
        sp_city,
        sp_state,
        sp_postal,
        sp_country,
        sp_time_zone_cd,
        sp_time_zone_desc,
        ci_sp_id,
        sp_status_flg,
        sp_status_desc,
        prem_id,
        prem_type_cd,
        prem_type_desc,
        prem_address1,
        prem_city,
        prem_state,
        prem_postal,
        prem_country,
        us_id,
        us_type_cd,
        us_type_desc,
        us_bo_status_cd,
        us_bo_status_desc,
        us_start_dttm,
        us_end_dttm,
        active_us_link_count,
        install_event_count,
        device_config_count,
        currently_installed_sw,
        load_dttm
    )
    WITH
    cfg_agg AS (
        SELECT
            cfg.d1_device_id,
            COUNT(*) AS device_config_count
        FROM cisadm.d1_dvc_cfg cfg
        GROUP BY cfg.d1_device_id
    ),
    install_agg AS (
        SELECT
            cfg.d1_device_id,
            COUNT(DISTINCT ie.install_evt_id) AS install_event_count
        FROM cisadm.d1_dvc_cfg cfg
        JOIN cisadm.d1_install_evt ie
            ON ie.device_config_id = cfg.device_config_id
        GROUP BY cfg.d1_device_id
    ),
    effective_cfg AS (
        SELECT
            cfg.d1_device_id,
            cfg.device_config_id,
            cfg.device_config_type_cd,
            cfg.bus_obj_cd AS cfg_bus_obj_cd,
            cfg.bo_status_cd AS cfg_bo_status_cd,
            cfg.eff_dttm AS cfg_eff_dttm,
            cfg.time_zone_cd AS cfg_time_zone_cd
        FROM (
            SELECT
                cfg.d1_device_id,
                cfg.device_config_id,
                cfg.device_config_type_cd,
                cfg.bus_obj_cd,
                cfg.bo_status_cd,
                cfg.eff_dttm,
                cfg.time_zone_cd,
                ROW_NUMBER() OVER (
                    PARTITION BY cfg.d1_device_id
                    ORDER BY
                        NVL(cfg.eff_dttm, TIMESTAMP '1900-01-01 00:00:00') DESC,
                        cfg.device_config_id DESC
                ) AS rn
            FROM cisadm.d1_dvc_cfg cfg
            WHERE cfg.eff_dttm IS NULL
               OR cfg.eff_dttm <= SYSTIMESTAMP
        ) cfg
        WHERE cfg.rn = 1
    ),
    current_install AS (
        SELECT
            cfg.d1_device_id,
            ie.install_evt_id,
            ie.bo_status_cd AS install_bo_status_cd,
            ie.d1_install_dttm AS install_dttm,
            ie.d1_removal_dttm AS removal_dttm,
            ie.arm_stat_flg,
            ie.d1_sp_id
        FROM cisadm.d1_dvc_cfg cfg
        JOIN cisadm.d1_install_evt ie
            ON ie.device_config_id = cfg.device_config_id
        WHERE (ie.d1_install_dttm IS NULL OR ie.d1_install_dttm <= SYSTIMESTAMP)
          AND (ie.d1_removal_dttm IS NULL OR ie.d1_removal_dttm > SYSTIMESTAMP)
          AND NOT EXISTS (
              SELECT 1
              FROM cisadm.d1_install_evt ie2
              JOIN cisadm.d1_dvc_cfg cfg2
                  ON cfg2.device_config_id = ie2.device_config_id
              WHERE cfg2.d1_device_id = cfg.d1_device_id
                AND (ie2.d1_install_dttm IS NULL OR ie2.d1_install_dttm <= SYSTIMESTAMP)
                AND (ie2.d1_removal_dttm IS NULL OR ie2.d1_removal_dttm > SYSTIMESTAMP)
                AND (
                    NVL(ie2.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00')
                        > NVL(ie.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00')
                 OR (
                        NVL(ie2.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00')
                            = NVL(ie.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00')
                    AND ie2.install_evt_id > ie.install_evt_id
                    )
                )
          )
    ),
    us_link_agg AS (
        SELECT
            ussp.d1_sp_id,
            COUNT(*) AS active_us_link_count
        FROM cisadm.d1_us_sp ussp
        WHERE (ussp.start_dttm IS NULL OR ussp.start_dttm <= SYSTIMESTAMP)
          AND (ussp.d1_stop_dttm IS NULL OR ussp.d1_stop_dttm > SYSTIMESTAMP)
        GROUP BY ussp.d1_sp_id
    ),
    primary_us AS (
        SELECT
            ussp.d1_sp_id,
            ussp.us_id,
            us.us_type_cd,
            us.bo_status_cd AS us_bo_status_cd,
            us.start_dttm AS us_start_dttm,
            us.end_dttm AS us_end_dttm
        FROM cisadm.d1_us_sp ussp
        JOIN cisadm.d1_us us
            ON us.us_id = ussp.us_id
        WHERE (ussp.start_dttm IS NULL OR ussp.start_dttm <= SYSTIMESTAMP)
          AND (ussp.d1_stop_dttm IS NULL OR ussp.d1_stop_dttm > SYSTIMESTAMP)
          AND NOT EXISTS (
              SELECT 1
              FROM cisadm.d1_us_sp ussp2
              WHERE ussp2.d1_sp_id = ussp.d1_sp_id
                AND (ussp2.start_dttm IS NULL OR ussp2.start_dttm <= SYSTIMESTAMP)
                AND (ussp2.d1_stop_dttm IS NULL OR ussp2.d1_stop_dttm > SYSTIMESTAMP)
                AND (
                    NVL(ussp2.start_dttm, TIMESTAMP '1900-01-01 00:00:00')
                        > NVL(ussp.start_dttm, TIMESTAMP '1900-01-01 00:00:00')
                 OR (
                        NVL(ussp2.start_dttm, TIMESTAMP '1900-01-01 00:00:00')
                            = NVL(ussp.start_dttm, TIMESTAMP '1900-01-01 00:00:00')
                    AND ussp2.us_id > ussp.us_id
                    )
                )
          )
    )
    SELECT
        dvc.d1_device_id,
        dvc.device_type_cd,
        dvc_type.descr100,
        dvc.bus_obj_cd,
        dvc_bo.descr,
        dvc.bo_status_cd,
        dvc_stat.descr,
        dvc.bo_status_reason_cd,
        dvc.manufacturer_cd,
        mfr.descr100,
        dvc.d1_model_cd,
        model.descr100,
        dvc.d1_spr_cd,
        spr.descr100,
        dvc.access_grp_cd,
        acc_grp.descr,
        dvc.arming_req_flg,
        arming_req.descr,
        dvc.head_end_registr_status_flg,
        head_end.descr,
        dvc.in_data_shift_flg,
        in_shift.descr,
        dvc.d1_cmd_set_cd,
        cmd_set.descr100,
        dvc.cre_dttm,
        dvc.status_upd_dttm,
        ident.asset_id,
        ident.serial_number,
        ident.badge_number,
        ident.external_id,
        ident.utility_device_id,
        ident.name,
        ident.mdm_external_id,
        dvc_char.mxu_type,
        mxu_type_l.descr,
        asset.asset_type_cd,
        asset_type.descr100,
        asset.bo_status_cd,
        asset_stat.descr,
        asset.asset_cond_flg,
        asset_cond.descr,
        asset.asset_ownership_flg,
        asset_own.descr,
        asset.specification_cd,
        asset_spec.descr100,
        asset.in_service_dt,
        asset.acquisition_dt,
        asset_ident.serial_number,
        eff_cfg.device_config_id,
        eff_cfg.device_config_type_cd,
        cfg_type.descr100,
        eff_cfg.cfg_bo_status_cd,
        cfg_stat.descr,
        eff_cfg.cfg_eff_dttm,
        eff_cfg.cfg_time_zone_cd,
        cfg_tz.descr,
        cur_ie.install_evt_id,
        cur_ie.install_bo_status_cd,
        install_stat.descr,
        cur_ie.install_dttm,
        cur_ie.removal_dttm,
        cur_ie.arm_stat_flg,
        arm_stat.descr,
        cur_ie.d1_sp_id,
        sp.d1_sp_type_cd,
        sp_type.descr100,
        sp.bo_status_cd,
        sp_stat.descr,
        sp.sp_src_stat_flg,
        sp_src_stat.descr,
        sp.msrmt_cyc_cd,
        sp_cyc.descr100,
        sp.msrmt_cyc_rte_cd,
        sp_rte.descr100,
        sp.division_cd,
        sp.mkt_cd,
        sp.d1_ls_sl_flg,
        sp.d1_ls_sl_descr,
        sp.address1,
        sp.city,
        sp.state,
        sp.postal,
        sp.country,
        sp.time_zone_cd,
        sp_tz.descr,
        ci_sp.sp_id,
        ci_sp.sp_status_flg,
        ci_sp_status.descr,
        ci_sp.prem_id,
        prem.prem_type_cd,
        prem_type.descr,
        prem.address1,
        prem.city,
        prem.state,
        prem.postal,
        prem.country,
        pus.us_id,
        pus.us_type_cd,
        us_type.descr100,
        pus.us_bo_status_cd,
        us_stat.descr,
        pus.us_start_dttm,
        pus.us_end_dttm,
        NVL(ula.active_us_link_count, 0),
        NVL(ia.install_event_count, 0),
        NVL(ca.device_config_count, 0),
        CASE WHEN cur_ie.install_evt_id IS NOT NULL THEN 'Y' ELSE 'N' END,
        v_load_dttm
    FROM cisadm.d1_dvc dvc
    LEFT JOIN cfg_agg ca
        ON ca.d1_device_id = dvc.d1_device_id
    LEFT JOIN install_agg ia
        ON ia.d1_device_id = dvc.d1_device_id
    LEFT JOIN effective_cfg eff_cfg
        ON eff_cfg.d1_device_id = dvc.d1_device_id
    LEFT JOIN current_install cur_ie
        ON cur_ie.d1_device_id = dvc.d1_device_id
    LEFT JOIN cisadm.cms_d1_dvc_identifier_vw ident
        ON ident.d1_device_id = dvc.d1_device_id
    LEFT JOIN cisadm.cms_d1_dvc_char_vw dvc_char
        ON dvc_char.d1_device_id = dvc.d1_device_id
    LEFT JOIN cisadm.w1_asset asset
        ON asset.asset_id = ident.asset_id
    LEFT JOIN cisadm.cms_w1_asset_identifier_vw asset_ident
        ON asset_ident.asset_id = asset.asset_id
    LEFT JOIN cisadm.d1_sp sp
        ON sp.d1_sp_id = cur_ie.d1_sp_id
    LEFT JOIN cisadm.ci_sp ci_sp
        ON ci_sp.sp_id = cur_ie.d1_sp_id
    LEFT JOIN cisadm.ci_prem prem
        ON prem.prem_id = ci_sp.prem_id
    LEFT JOIN us_link_agg ula
        ON ula.d1_sp_id = cur_ie.d1_sp_id
    LEFT JOIN primary_us pus
        ON pus.d1_sp_id = cur_ie.d1_sp_id
    LEFT JOIN cisadm.d1_dvc_type_l dvc_type
        ON dvc_type.device_type_cd = dvc.device_type_cd
       AND dvc_type.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_l dvc_bo
        ON dvc_bo.bus_obj_cd = dvc.bus_obj_cd
       AND dvc_bo.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l dvc_stat
        ON dvc_stat.bus_obj_cd = dvc.bus_obj_cd
       AND dvc_stat.bo_status_cd = dvc.bo_status_cd
       AND dvc_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_manufacturer_l mfr
        ON mfr.manufacturer_cd = dvc.manufacturer_cd
       AND mfr.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_model_l model
        ON model.manufacturer_cd = dvc.manufacturer_cd
       AND model.d1_model_cd = dvc.d1_model_cd
       AND model.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_spr_l spr
        ON spr.d1_spr_cd = dvc.d1_spr_cd
       AND spr.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acc_grp_l acc_grp
        ON acc_grp.access_grp_cd = dvc.access_grp_cd
       AND acc_grp.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l arming_req
        ON TRIM(arming_req.field_name) = 'ARMING_REQ_FLG'
       AND TRIM(arming_req.field_value) = TRIM(dvc.arming_req_flg)
       AND arming_req.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l head_end
        ON TRIM(head_end.field_name) = 'HEAD_END_REGISTR_STATUS_FLG'
       AND TRIM(head_end.field_value) = TRIM(dvc.head_end_registr_status_flg)
       AND head_end.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l in_shift
        ON TRIM(in_shift.field_name) = 'IN_DATA_SHIFT_FLG'
       AND TRIM(in_shift.field_value) = TRIM(dvc.in_data_shift_flg)
       AND in_shift.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_command_set_l cmd_set
        ON cmd_set.d1_cmd_set_cd = dvc.d1_cmd_set_cd
       AND cmd_set.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_char_val_l mxu_type_l
        ON mxu_type_l.char_type_cd = 'CMCMXUTY'
       AND mxu_type_l.char_val = dvc_char.mxu_type
       AND mxu_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.w1_asset_type_l asset_type
        ON asset_type.asset_type_cd = asset.asset_type_cd
       AND asset_type.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l asset_stat
        ON asset_stat.bus_obj_cd = asset.bus_obj_cd
       AND asset_stat.bo_status_cd = asset.bo_status_cd
       AND asset_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l asset_cond
        ON TRIM(asset_cond.field_name) = 'ASSET_COND_FLG'
       AND TRIM(asset_cond.field_value) = TRIM(asset.asset_cond_flg)
       AND asset_cond.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l asset_own
        ON TRIM(asset_own.field_name) = 'ASSET_OWNERSHIP_FLG'
       AND TRIM(asset_own.field_value) = TRIM(asset.asset_ownership_flg)
       AND asset_own.language_cd = 'ENG'
    LEFT JOIN cisadm.w1_specification_l asset_spec
        ON asset_spec.specification_cd = asset.specification_cd
       AND asset_spec.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_dvc_cfg_type_l cfg_type
        ON cfg_type.device_config_type_cd = eff_cfg.device_config_type_cd
       AND cfg_type.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l cfg_stat
        ON cfg_stat.bus_obj_cd = eff_cfg.cfg_bus_obj_cd
       AND cfg_stat.bo_status_cd = eff_cfg.cfg_bo_status_cd
       AND cfg_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_time_zone_l cfg_tz
        ON cfg_tz.time_zone_cd = eff_cfg.cfg_time_zone_cd
       AND cfg_tz.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l install_stat
        ON install_stat.bus_obj_cd = 'D1-InstallEvent'
       AND install_stat.bo_status_cd = cur_ie.install_bo_status_cd
       AND install_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l arm_stat
        ON TRIM(arm_stat.field_name) = 'ARM_STAT_FLG'
       AND TRIM(arm_stat.field_value) = TRIM(cur_ie.arm_stat_flg)
       AND arm_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_sp_type_l sp_type
        ON sp_type.d1_sp_type_cd = sp.d1_sp_type_cd
       AND sp_type.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l sp_stat
        ON sp_stat.bus_obj_cd = sp.bus_obj_cd
       AND sp_stat.bo_status_cd = sp.bo_status_cd
       AND sp_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l sp_src_stat
        ON TRIM(sp_src_stat.field_name) = 'SP_SRC_STAT_FLG'
       AND TRIM(sp_src_stat.field_value) = TRIM(sp.sp_src_stat_flg)
       AND sp_src_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_msrmt_cyc_l sp_cyc
        ON sp_cyc.msrmt_cyc_cd = sp.msrmt_cyc_cd
       AND sp_cyc.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_msrmt_cyc_rte_l sp_rte
        ON sp_rte.msrmt_cyc_cd = sp.msrmt_cyc_cd
       AND sp_rte.msrmt_cyc_rte_cd = sp.msrmt_cyc_rte_cd
       AND sp_rte.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_time_zone_l sp_tz
        ON sp_tz.time_zone_cd = sp.time_zone_cd
       AND sp_tz.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l ci_sp_status
        ON TRIM(ci_sp_status.field_name) = 'SP_STATUS_FLG'
       AND TRIM(ci_sp_status.field_value) = TRIM(ci_sp.sp_status_flg)
       AND ci_sp_status.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_prem_type_l prem_type
        ON prem_type.prem_type_cd = prem.prem_type_cd
       AND prem_type.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_us_type_l us_type
        ON us_type.us_type_cd = pus.us_type_cd
       AND us_type.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l us_stat
        ON us_stat.bus_obj_cd = 'D1-UsageSubscription'
       AND us_stat.bo_status_cd = pus.us_bo_status_cd
       AND us_stat.language_cd = 'ENG';

    COMMIT;
END;
/
