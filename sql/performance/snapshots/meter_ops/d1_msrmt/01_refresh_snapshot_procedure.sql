CREATE OR REPLACE PROCEDURE cisadm.refresh_d1_msrmt_rpt_curr AS
    v_window_start DATE := ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12);
BEGIN
    DELETE FROM cisadm.d1_msrmt_rpt_curr
    WHERE msrmt_dttm >= v_window_start;

    INSERT INTO cisadm.d1_msrmt_rpt_curr (
        measr_comp_id,
        msrmt_dttm,
        msrmt_local_dttm,
        msrmt_bus_obj_cd,
        msrmt_bus_obj_desc,
        msrmt_bo_status_cd,
        msrmt_bo_status_desc,
        msrmt_cond_flg,
        msrmt_cond_desc,
        msrmt_use_flg,
        msrmt_use_desc,
        user_edited_flg,
        user_edited_desc,
        orig_init_msrmt_id,
        prev_msrmt_dttm,
        reading_cond_flg,
        reading_cond_desc,
        reading_val,
        combined_multiplier,
        msrmt_val,
        msrmt_val1,
        msrmt_val2,
        msrmt_val3,
        msrmt_val4,
        msrmt_val5,
        msrmt_val6,
        msrmt_val7,
        msrmt_val8,
        msrmt_val9,
        msrmt_val10,
        msrmt_cre_dttm,
        msrmt_status_upd_dttm,
        msrmt_last_update_dttm,
        load_dttm,
        init_msrmt_data_id,
        imd_ext_id,
        imd_from_dttm,
        imd_to_dttm,
        data_src_flg,
        data_src_desc,
        imd_time_zone_cd,
        imd_time_zone_desc,
        imd_bus_obj_cd,
        imd_bus_obj_desc,
        imd_bo_status_cd,
        imd_bo_status_desc,
        imd_bo_status_reason_cd,
        imd_cre_dttm,
        imd_status_upd_dttm,
        imd_last_update_dttm,
        retention_period,
        device_config_id,
        measr_comp_type_cd,
        measr_comp_type_desc,
        measr_comp_usage_flg,
        measr_comp_usage_desc,
        mc_bus_obj_cd,
        mc_bus_obj_desc,
        mc_bo_status_cd,
        mc_bo_status_desc,
        mc_bo_status_reason_cd,
        d1_nbr_of_dgts_lft,
        d1_nbr_of_dgts_rgt,
        measr_comp_multiplier,
        d1_full_scale,
        d1_read_seq,
        mc_time_zone_cd,
        mc_time_zone_desc,
        latest_msrmt_dttm,
        most_recent_msrmt_dttm,
        most_recent_non_est_msrmt_dttm,
        adj_latest_msrmt_dttm,
        most_recent_msrmt_reading_val,
        most_recent_msrmt_reading_cond,
        most_recent_msrmt_reading_cond_desc,
        mc_user_id,
        mc_user_name,
        mc_access_grp_cd,
        mc_access_grp_desc,
        attr_val_id,
        mc_cre_dttm,
        mc_status_upd_dttm,
        install_evt_id,
        install_bo_status_cd,
        install_bo_status_reason_cd,
        install_dttm,
        removal_dttm,
        installation_const,
        arm_stat_flg,
        d1_sp_id,
        d1_sp_type_cd,
        d1_sp_type_desc,
        sp_bus_obj_cd,
        sp_bus_obj_desc,
        sp_bo_status_cd,
        sp_bo_status_desc,
        sp_bo_status_reason_cd,
        sp_src_stat_flg,
        sp_src_stat_desc,
        disconn_loc_flg,
        disconn_loc_desc,
        division_cd,
        mkt_cd,
        d1_ls_sl_flg,
        d1_ls_sl_descr,
        msrmt_cyc_cd,
        msrmt_cyc_desc,
        msrmt_cyc_rte_cd,
        msrmt_cyc_rte_desc,
        msrmt_cyc_rte_seq,
        sp_time_zone_cd,
        sp_time_zone_desc,
        sp_access_grp_cd,
        sp_access_grp_desc,
        country,
        postal,
        address1,
        address2,
        address3,
        address4,
        city,
        county,
        state,
        geo_code,
        house_type,
        in_city_limit,
        num1,
        num2,
        d1_geo_lat,
        d1_geo_long,
        sp_cre_dttm,
        sp_status_upd_dttm
    )
    SELECT
        msrmt.measr_comp_id,
        msrmt.msrmt_dttm,
        msrmt.msrmt_local_dttm,
        msrmt.bus_obj_cd,
        msrmt_bo.descr,
        msrmt.bo_status_cd,
        msrmt_stat.descr,
        msrmt.msrmt_cond_flg,
        msrmt_cond.descr,
        msrmt.msrmt_use_flg,
        msrmt_use.descr,
        msrmt.user_edited_flg,
        user_edited.descr,
        msrmt.orig_init_msrmt_id,
        msrmt.prev_msrmt_dttm,
        msrmt.reading_cond_flg,
        reading_cond.descr,
        msrmt.reading_val,
        msrmt.combined_multiplier,
        msrmt.msrmt_val,
        msrmt.msrmt_val1,
        msrmt.msrmt_val2,
        msrmt.msrmt_val3,
        msrmt.msrmt_val4,
        msrmt.msrmt_val5,
        msrmt.msrmt_val6,
        msrmt.msrmt_val7,
        msrmt.msrmt_val8,
        msrmt.msrmt_val9,
        msrmt.msrmt_val10,
        msrmt.cre_dttm,
        msrmt.status_upd_dttm,
        msrmt.last_update_dttm,
        SYSTIMESTAMP,
        imd.init_msrmt_data_id,
        imd.imd_ext_id,
        imd.d1_from_dttm,
        imd.d1_to_dttm,
        imd.data_src_flg,
        imd_data_src.descr,
        imd.time_zone_cd,
        imd_tz.descr,
        imd.bus_obj_cd,
        imd_bo.descr,
        imd.bo_status_cd,
        imd_stat.descr,
        imd.bo_status_reason_cd,
        imd.cre_dttm,
        imd.status_upd_dttm,
        imd.last_update_dttm,
        imd.retention_period,
        mc.device_config_id,
        mc.measr_comp_type_cd,
        mc_type.descr100,
        mc.measr_comp_usage_flg,
        mc_usage.descr,
        mc.bus_obj_cd,
        mc_bo.descr,
        mc.bo_status_cd,
        mc_stat.descr,
        mc.bo_status_reason_cd,
        mc.d1_nbr_of_dgts_lft,
        mc.d1_nbr_of_dgts_rgt,
        mc.measr_comp_multiplier,
        mc.d1_full_scale,
        mc.d1_read_seq,
        mc.time_zone_cd,
        mc_tz.descr,
        mc.latest_msrmt_dttm,
        mc.most_recent_msrmt_dttm,
        mc.most_recent_non_est_msrmt_dttm,
        mc.adj_latest_msrmt_dttm,
        mc.most_recent_msrmt_reading_val,
        mc.most_recent_msrmt_reading_cond,
        mc_recent_cond.descr,
        mc.user_id,
        TRIM(sc_user.first_name || ' ' || sc_user.last_name),
        mc.access_grp_cd,
        mc_acc_grp.descr,
        mc.attr_val_id,
        mc.cre_dttm,
        mc.status_upd_dttm,
        ie.install_evt_id,
        ie.bo_status_cd,
        ie.bo_status_reason_cd,
        ie.d1_install_dttm,
        ie.d1_removal_dttm,
        ie.installation_const,
        ie.arm_stat_flg,
        sp.d1_sp_id,
        sp.d1_sp_type_cd,
        sp_type.descr100,
        sp.bus_obj_cd,
        sp_bo.descr,
        sp.bo_status_cd,
        sp_stat.descr,
        sp.bo_status_reason_cd,
        sp.sp_src_stat_flg,
        sp_src_stat.descr,
        sp.disconn_loc_flg,
        sp_disconn.descr,
        sp.division_cd,
        sp.mkt_cd,
        sp.d1_ls_sl_flg,
        sp.d1_ls_sl_descr,
        sp.msrmt_cyc_cd,
        sp_cyc.descr100,
        sp.msrmt_cyc_rte_cd,
        sp_rte.descr100,
        sp.msrmt_cyc_rte_seq,
        sp.time_zone_cd,
        sp_tz.descr,
        sp.access_grp_cd,
        sp_acc_grp.descr,
        sp.country,
        sp.postal,
        sp.address1,
        sp.address2,
        sp.address3,
        sp.address4,
        sp.city,
        sp.county,
        sp.state,
        sp.geo_code,
        sp.house_type,
        sp.in_city_limit,
        sp.num1,
        sp.num2,
        sp.d1_geo_lat,
        sp.d1_geo_long,
        sp.cre_dttm,
        sp.status_upd_dttm
    FROM cisadm.d1_msrmt msrmt
    LEFT JOIN cisadm.d1_measr_comp mc
        ON mc.measr_comp_id = msrmt.measr_comp_id
    LEFT JOIN cisadm.d1_init_msrmt_data imd
        ON imd.init_msrmt_data_id = msrmt.orig_init_msrmt_id
    LEFT JOIN cisadm.d1_install_evt ie
        ON ie.device_config_id = mc.device_config_id
       AND (ie.d1_install_dttm IS NULL OR ie.d1_install_dttm <= msrmt.msrmt_dttm)
       AND (ie.d1_removal_dttm IS NULL OR ie.d1_removal_dttm > msrmt.msrmt_dttm)
       AND NOT EXISTS (
            SELECT 1
            FROM cisadm.d1_install_evt ie2
            WHERE ie2.device_config_id = ie.device_config_id
              AND (ie2.d1_install_dttm IS NULL OR ie2.d1_install_dttm <= msrmt.msrmt_dttm)
              AND (ie2.d1_removal_dttm IS NULL OR ie2.d1_removal_dttm > msrmt.msrmt_dttm)
              AND (
                    NVL(ie2.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00') > NVL(ie.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00')
                 OR (
                        NVL(ie2.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00') = NVL(ie.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00')
                    AND ie2.install_evt_id > ie.install_evt_id
                    )
                  )
        )
    LEFT JOIN cisadm.d1_sp sp
        ON sp.d1_sp_id = ie.d1_sp_id
    LEFT JOIN cisadm.f1_bus_obj_l msrmt_bo
        ON msrmt_bo.bus_obj_cd = msrmt.bus_obj_cd
       AND msrmt_bo.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l msrmt_stat
        ON msrmt_stat.bus_obj_cd = msrmt.bus_obj_cd
       AND msrmt_stat.bo_status_cd = msrmt.bo_status_cd
       AND msrmt_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_ext_lookup_val_l msrmt_cond
        ON msrmt_cond.bus_obj_cd = 'D1-MeasurementConditionLookup'
       AND msrmt_cond.f1_ext_lookup_value = msrmt.msrmt_cond_flg
       AND msrmt_cond.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l msrmt_use
        ON msrmt_use.field_name = 'MSRMT_USE_FLG'
       AND msrmt_use.field_value = msrmt.msrmt_use_flg
       AND msrmt_use.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l user_edited
        ON user_edited.field_name = 'USER_EDITED_FLG'
       AND user_edited.field_value = msrmt.user_edited_flg
       AND user_edited.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_ext_lookup_val_l reading_cond
        ON reading_cond.bus_obj_cd = 'D1-MeasurementConditionLookup'
       AND reading_cond.f1_ext_lookup_value = msrmt.reading_cond_flg
       AND reading_cond.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_l imd_bo
        ON imd_bo.bus_obj_cd = imd.bus_obj_cd
       AND imd_bo.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l imd_stat
        ON imd_stat.bus_obj_cd = imd.bus_obj_cd
       AND imd_stat.bo_status_cd = imd.bo_status_cd
       AND imd_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l imd_data_src
        ON imd_data_src.field_name = 'DATA_SRC_FLG'
       AND imd_data_src.field_value = imd.data_src_flg
       AND imd_data_src.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_time_zone_l imd_tz
        ON imd_tz.time_zone_cd = imd.time_zone_cd
       AND imd_tz.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_l mc_bo
        ON mc_bo.bus_obj_cd = mc.bus_obj_cd
       AND mc_bo.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l mc_stat
        ON mc_stat.bus_obj_cd = mc.bus_obj_cd
       AND mc_stat.bo_status_cd = mc.bo_status_cd
       AND mc_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_measr_comp_type_l mc_type
        ON mc_type.measr_comp_type_cd = mc.measr_comp_type_cd
       AND mc_type.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l mc_usage
        ON mc_usage.field_name = 'MEASR_COMP_USAGE_FLG'
       AND mc_usage.field_value = mc.measr_comp_usage_flg
       AND mc_usage.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_time_zone_l mc_tz
        ON mc_tz.time_zone_cd = mc.time_zone_cd
       AND mc_tz.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_ext_lookup_val_l mc_recent_cond
        ON mc_recent_cond.bus_obj_cd = 'D1-MeasurementConditionLookup'
       AND mc_recent_cond.f1_ext_lookup_value = mc.most_recent_msrmt_reading_cond
       AND mc_recent_cond.language_cd = 'ENG'
    LEFT JOIN cisadm.sc_user sc_user
        ON sc_user.user_id = mc.user_id
    LEFT JOIN cisadm.ci_acc_grp_l mc_acc_grp
        ON mc_acc_grp.access_grp_cd = mc.access_grp_cd
       AND mc_acc_grp.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_l sp_bo
        ON sp_bo.bus_obj_cd = sp.bus_obj_cd
       AND sp_bo.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l sp_stat
        ON sp_stat.bus_obj_cd = sp.bus_obj_cd
       AND sp_stat.bo_status_cd = sp.bo_status_cd
       AND sp_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_sp_type_l sp_type
        ON sp_type.d1_sp_type_cd = sp.d1_sp_type_cd
       AND sp_type.language_cd = 'ENG'
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
    LEFT JOIN cisadm.ci_lookup_val_l sp_src_stat
        ON sp_src_stat.field_name = 'SP_SRC_STAT_FLG'
       AND sp_src_stat.field_value = sp.sp_src_stat_flg
       AND sp_src_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l sp_disconn
        ON sp_disconn.field_name = 'DISCONN_LOC_FLG'
       AND sp_disconn.field_value = sp.disconn_loc_flg
       AND sp_disconn.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acc_grp_l sp_acc_grp
        ON sp_acc_grp.access_grp_cd = sp.access_grp_cd
       AND sp_acc_grp.language_cd = 'ENG'
    WHERE msrmt.msrmt_dttm >= v_window_start;

    COMMIT;
END;
/
