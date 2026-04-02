CREATE OR REPLACE PROCEDURE cisadm.refresh_d1_usage_rpt_curr AS
BEGIN
    EXECUTE IMMEDIATE 'TRUNCATE TABLE cisadm.d1_usage_rpt_curr';

    INSERT INTO cisadm.d1_usage_rpt_curr (
        d1_usage_id,
        us_id,
        usg_ext_id,
        org_usage_id,
        bus_obj_cd,
        bus_obj_desc,
        bo_status_cd,
        bo_status_desc,
        bo_status_reason_cd,
        start_dttm,
        end_dttm,
        status_upd_dttm,
        sch_selection_dt,
        usg_grp_cd,
        usg_grp_desc,
        d1_usg_cal_type_cd,
        d1_usg_cal_type_desc,
        usg_src_flg,
        usg_src_desc,
        d1_spr_cd,
        d1_spr_desc,
        msrmt_cyc_cd,
        msrmt_cyc_desc,
        msrmt_cyc_rte_cd,
        msrmt_cyc_rte_desc,
        used_on_bill_flg,
        used_on_bill_desc,
        linked_to_frzn_bseg_flg,
        linked_to_frzn_bseg_desc,
        tot_usg_trans_cnt,
        rel_order,
        usage_cre_dttm,
        load_dttm,
        is_estimate_flg,
        is_estimate_desc,
        d1_estimate_time_flg,
        d2_allow_est_flg,
        skip_flg,
        d2_skip_reason_flg,
        date_break,
        estmt_dt,
        profile_factor_cd,
        factor_char_value,
        start_dttm_interval_mc,
        end_from_dttm_interval_mc,
        end_to_dttm_interval_mc,
        start_dttm_scalar_mc,
        end_from_dttm_scalar_mc,
        end_to_dttm_scalar_mc,
        scalar_end_range_opt_flg,
        scalar_min_offset_days,
        scalar_max_offset_days,
        us_bo_status_cd,
        us_bo_status_desc,
        us_bo_status_reason_cd,
        us_type_cd,
        us_type_desc,
        us_d1_spr_cd,
        us_d1_spr_desc,
        d1_bill_cyc_cd,
        d1_bill_cyc_desc,
        division_cd,
        time_zone_cd,
        time_zone_desc,
        access_grp_cd,
        access_grp_desc,
        us_stat_cond_flg,
        us_stat_cond_desc,
        usg_appr_req_flg,
        usg_appr_req_desc,
        us_start_dttm,
        us_end_dttm,
        us_status_upd_dttm,
        most_recent_trans_dttm,
        us_mp_id,
        period_sq_row_count,
        period_sq_period_count,
        period_sq_determinant_count,
        period_sq_total_quantity,
        period_sq_sp_count,
        period_sq_measr_comp_count,
        period_sq_interval_row_count,
        period_sq_extract_interval_count,
        period_sq_sole_uom_cd,
        period_sq_sole_uom_desc,
        period_sq_sole_tou_cd,
        period_sq_sole_tou_desc,
        period_sq_sole_sqi_cd,
        period_sq_sole_sqi_desc,
        scalar_row_count,
        scalar_determinant_count,
        scalar_total_quantity,
        scalar_total_final_quantity,
        scalar_total_start_msrmt,
        scalar_total_end_msrmt,
        scalar_total_use_percent,
        scalar_total_applied_mltr,
        scalar_sp_count,
        scalar_measr_comp_count,
        scalar_sole_final_uom_cd,
        scalar_sole_final_uom_desc,
        scalar_sole_final_tou_cd,
        scalar_sole_final_tou_desc,
        scalar_sole_final_sqi_cd,
        scalar_sole_final_sqi_desc,
        bridge_method,
        c1_match_count,
        c1_usage_id,
        c1_master_usage_id,
        c1_sa_id,
        c1_sp_id,
        c1_bseg_id,
        c1_bill_cyc_cd,
        c1_bill_cyc_desc,
        c1_bo_status_cd,
        c1_bo_status_desc,
        c1_start_dttm,
        c1_end_dttm,
        c1_status_upd_dttm,
        c1_cre_dttm,
        bill_id,
        bseg_stat_flg,
        bseg_stat_desc,
        bseg_start_dt,
        bseg_end_dt,
        bseg_est_sw,
        bseg_bill_cyc_cd,
        bseg_bill_cyc_desc,
        sa_id,
        acct_id,
        per_id,
        customer_name,
        sa_type_cd,
        sa_type_desc,
        sa_status_flg,
        sa_status_desc,
        sa_cis_division,
        sa_currency_cd,
        sa_start_dt,
        sa_end_dt,
        prem_id,
        address1,
        city,
        state,
        postal
    )
    WITH
    period_sq_agg AS (
        SELECT
            sq.d1_usage_id,
            COUNT(*) AS period_sq_row_count,
            COUNT(DISTINCT sq.period_seq_num) AS period_sq_period_count,
            COUNT(
                DISTINCT NVL(TRIM(sq.d1_uom_cd), '~')
                      || ':' || NVL(TRIM(sq.d1_tou_cd), '~')
                      || ':' || NVL(TRIM(sq.d1_sqi_cd), '~')
            ) AS period_sq_determinant_count,
            SUM(NVL(sq.quantity, 0)) AS period_sq_total_quantity,
            COUNT(DISTINCT TRIM(sq.d1_sp_id)) AS period_sq_sp_count,
            COUNT(DISTINCT TRIM(sq.measr_comp_id)) AS period_sq_measr_comp_count,
            SUM(CASE WHEN TRIM(sq.intrvl_data_flg) = 'D2YS' THEN 1 ELSE 0 END) AS period_sq_interval_row_count,
            SUM(CASE WHEN TRIM(sq.extract_intrvl_data_flg) = 'D2YS' THEN 1 ELSE 0 END) AS period_sq_extract_interval_count,
            CASE
                WHEN COUNT(DISTINCT CASE WHEN TRIM(sq.d1_uom_cd) IS NOT NULL THEN TRIM(sq.d1_uom_cd) END) = 1
                    THEN MAX(TRIM(sq.d1_uom_cd))
            END AS period_sq_sole_uom_cd,
            CASE
                WHEN COUNT(DISTINCT CASE WHEN TRIM(sq.d1_tou_cd) IS NOT NULL THEN TRIM(sq.d1_tou_cd) END) = 1
                    THEN MAX(TRIM(sq.d1_tou_cd))
            END AS period_sq_sole_tou_cd,
            CASE
                WHEN COUNT(DISTINCT CASE WHEN TRIM(sq.d1_sqi_cd) IS NOT NULL THEN TRIM(sq.d1_sqi_cd) END) = 1
                    THEN MAX(TRIM(sq.d1_sqi_cd))
            END AS period_sq_sole_sqi_cd
        FROM cisadm.d1_usage_period_sq sq
        GROUP BY
            sq.d1_usage_id
    ),
    scalar_agg AS (
        SELECT
            dtl.d1_usage_id,
            COUNT(*) AS scalar_row_count,
            COUNT(
                DISTINCT NVL(TRIM(dtl.d1_final_uom_cd), '~')
                      || ':' || NVL(TRIM(dtl.d1_final_tou_cd), '~')
                      || ':' || NVL(TRIM(dtl.d1_final_sqi_cd), '~')
            ) AS scalar_determinant_count,
            SUM(NVL(dtl.quantity, 0)) AS scalar_total_quantity,
            SUM(NVL(dtl.final_quantity, 0)) AS scalar_total_final_quantity,
            SUM(NVL(dtl.start_msrmt, 0)) AS scalar_total_start_msrmt,
            SUM(NVL(dtl.end_msrmt, 0)) AS scalar_total_end_msrmt,
            SUM(NVL(dtl.use_percent, 0)) AS scalar_total_use_percent,
            SUM(NVL(dtl.applied_mltr, 0)) AS scalar_total_applied_mltr,
            COUNT(DISTINCT TRIM(dtl.d1_sp_id)) AS scalar_sp_count,
            COUNT(DISTINCT TRIM(dtl.measr_comp_id)) AS scalar_measr_comp_count,
            CASE
                WHEN COUNT(DISTINCT CASE WHEN TRIM(dtl.d1_final_uom_cd) IS NOT NULL THEN TRIM(dtl.d1_final_uom_cd) END) = 1
                    THEN MAX(TRIM(dtl.d1_final_uom_cd))
            END AS scalar_sole_final_uom_cd,
            CASE
                WHEN COUNT(DISTINCT CASE WHEN TRIM(dtl.d1_final_tou_cd) IS NOT NULL THEN TRIM(dtl.d1_final_tou_cd) END) = 1
                    THEN MAX(TRIM(dtl.d1_final_tou_cd))
            END AS scalar_sole_final_tou_cd,
            CASE
                WHEN COUNT(DISTINCT CASE WHEN TRIM(dtl.d1_final_sqi_cd) IS NOT NULL THEN TRIM(dtl.d1_final_sqi_cd) END) = 1
                    THEN MAX(TRIM(dtl.d1_final_sqi_cd))
            END AS scalar_sole_final_sqi_cd
        FROM cisadm.d1_usage_scalar_dtl dtl
        GROUP BY
            dtl.d1_usage_id
    ),
    customer_choice AS (
        SELECT
            ap.acct_id,
            ap.per_id,
            pn.entity_name_upr AS customer_name,
            ROW_NUMBER() OVER (
                PARTITION BY ap.acct_id
                ORDER BY
                    CASE WHEN ap.fin_resp_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN ap.main_cust_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN pn.prim_name_sw = 'Y' THEN 0 ELSE 1 END,
                    pn.seq_num,
                    pn.per_id
            ) AS rn
        FROM cisadm.ci_acct_per ap
        JOIN cisadm.ci_per_name pn
            ON pn.per_id = ap.per_id
        WHERE ap.main_cust_sw = 'Y'
          AND (pn.prim_name_sw = 'Y' OR pn.name_type_flg = 'PRIM')
    ),
    c1_usage_candidates AS (
        SELECT
            u.d1_usage_id,
            'D1_USAGE_ID_TO_C1_USAGE_ID' AS bridge_method,
            1 AS bridge_priority,
            cu.usage_id,
            cu.master_usage_id,
            cu.sa_id,
            cu.sp_id,
            cu.bseg_id,
            cu.bill_cyc_cd,
            cu.bo_status_cd,
            cu.bus_obj_cd,
            cu.start_dttm,
            cu.end_dttm,
            cu.status_upd_dttm,
            cu.cre_dttm
        FROM cisadm.d1_usage u
        JOIN cisadm.c1_usage cu
            ON TRIM(cu.usage_id) = TRIM(u.d1_usage_id)
        UNION ALL
        SELECT
            u.d1_usage_id,
            'D1_USAGE_ID_TO_C1_MASTER_USAGE_ID' AS bridge_method,
            2 AS bridge_priority,
            cu.usage_id,
            cu.master_usage_id,
            cu.sa_id,
            cu.sp_id,
            cu.bseg_id,
            cu.bill_cyc_cd,
            cu.bo_status_cd,
            cu.bus_obj_cd,
            cu.start_dttm,
            cu.end_dttm,
            cu.status_upd_dttm,
            cu.cre_dttm
        FROM cisadm.d1_usage u
        JOIN cisadm.c1_usage cu
            ON TRIM(cu.master_usage_id) = TRIM(u.d1_usage_id)
        UNION ALL
        SELECT
            u.d1_usage_id,
            'USG_EXT_ID_TO_C1_USAGE_ID' AS bridge_method,
            3 AS bridge_priority,
            cu.usage_id,
            cu.master_usage_id,
            cu.sa_id,
            cu.sp_id,
            cu.bseg_id,
            cu.bill_cyc_cd,
            cu.bo_status_cd,
            cu.bus_obj_cd,
            cu.start_dttm,
            cu.end_dttm,
            cu.status_upd_dttm,
            cu.cre_dttm
        FROM cisadm.d1_usage u
        JOIN cisadm.c1_usage cu
            ON TRIM(cu.usage_id) = TRIM(u.usg_ext_id)
        WHERE TRIM(u.usg_ext_id) IS NOT NULL
        UNION ALL
        SELECT
            u.d1_usage_id,
            'USG_EXT_ID_TO_C1_MASTER_USAGE_ID' AS bridge_method,
            4 AS bridge_priority,
            cu.usage_id,
            cu.master_usage_id,
            cu.sa_id,
            cu.sp_id,
            cu.bseg_id,
            cu.bill_cyc_cd,
            cu.bo_status_cd,
            cu.bus_obj_cd,
            cu.start_dttm,
            cu.end_dttm,
            cu.status_upd_dttm,
            cu.cre_dttm
        FROM cisadm.d1_usage u
        JOIN cisadm.c1_usage cu
            ON TRIM(cu.master_usage_id) = TRIM(u.usg_ext_id)
        WHERE TRIM(u.usg_ext_id) IS NOT NULL
    ),
    c1_usage_ranked AS (
        SELECT
            cand.*,
            COUNT(*) OVER (PARTITION BY cand.d1_usage_id) AS c1_match_count,
            ROW_NUMBER() OVER (
                PARTITION BY cand.d1_usage_id
                ORDER BY
                    cand.bridge_priority,
                    CASE WHEN TRIM(cand.bo_status_cd) = 'BD-PROC' THEN 0 ELSE 1 END,
                    cand.status_upd_dttm DESC NULLS LAST,
                    cand.cre_dttm DESC NULLS LAST,
                    cand.usage_id
            ) AS rn
        FROM c1_usage_candidates cand
    ),
    c1_usage_bridge AS (
        SELECT
            bridge.d1_usage_id,
            bridge.bridge_method,
            bridge.c1_match_count,
            bridge.usage_id AS c1_usage_id,
            bridge.master_usage_id AS c1_master_usage_id,
            bridge.sa_id AS c1_sa_id,
            bridge.sp_id AS c1_sp_id,
            bridge.bseg_id AS c1_bseg_id,
            bridge.bill_cyc_cd AS c1_bill_cyc_cd,
            bridge.bo_status_cd AS c1_bo_status_cd,
            bridge.bus_obj_cd AS c1_bus_obj_cd,
            bridge.start_dttm AS c1_start_dttm,
            bridge.end_dttm AS c1_end_dttm,
            bridge.status_upd_dttm AS c1_status_upd_dttm,
            bridge.cre_dttm AS c1_cre_dttm
        FROM c1_usage_ranked bridge
        WHERE bridge.rn = 1
    )
    SELECT
        u.d1_usage_id,
        u.us_id,
        u.usg_ext_id,
        u.org_usage_id,
        u.bus_obj_cd,
        usage_bo.descr,
        u.bo_status_cd,
        usage_status.descr,
        u.bo_status_reason_cd,
        u.start_dttm,
        u.end_dttm,
        u.status_upd_dttm,
        u.sch_selection_dt,
        u.usg_grp_cd,
        usage_grp.descr100,
        u.d1_usg_cal_type_cd,
        usage_cal_type.descr100,
        u.usg_src_flg,
        CASE TRIM(u.usg_src_flg)
            WHEN 'D2SY' THEN 'System'
            WHEN 'D2MN' THEN 'Manual'
            WHEN 'D2EX' THEN 'External'
            ELSE 'Unknown'
        END AS usg_src_desc,
        u.d1_spr_cd,
        usage_spr.descr100,
        u.msrmt_cyc_cd,
        usage_cyc.descr100,
        u.msrmt_cyc_rte_cd,
        usage_rte.descr100,
        u.used_on_bill_flg,
        CASE TRIM(u.used_on_bill_flg)
            WHEN 'D2YS' THEN 'Yes'
            WHEN 'D2NO' THEN 'No'
            ELSE 'Unknown'
        END AS used_on_bill_desc,
        u.linked_to_frzn_bseg_flg,
        CASE TRIM(u.linked_to_frzn_bseg_flg)
            WHEN 'D2YS' THEN 'Yes'
            WHEN 'D2NO' THEN 'No'
            ELSE 'Unknown'
        END AS linked_to_frzn_bseg_desc,
        u.tot_usg_trans_cnt,
        u.rel_order,
        u.cre_dttm,
        SYSTIMESTAMP,
        boda.is_estimate_flg,
        CASE TRIM(boda.is_estimate_flg)
            WHEN 'D2YS' THEN 'Estimated'
            WHEN 'D2NO' THEN 'Not Estimated'
            ELSE 'Unknown'
        END AS is_estimate_desc,
        boda.d1_estimate_time_flg,
        boda.d2_allow_est_flg,
        boda.skip_flg,
        boda.d2_skip_reason_flg,
        boda.date_break,
        boda.estmt_dt,
        boda.profile_factor_cd,
        boda.factor_char_value,
        boda.start_dttm_interval_mc,
        boda.end_from_dttm_interval_mc,
        boda.end_to_dttm_interval_mc,
        boda.start_dttm_scalar_mc,
        boda.end_from_dttm_scalar_mc,
        boda.end_to_dttm_scalar_mc,
        boda.scalar_end_range_opt_flg,
        boda.scalar_min_offset_days,
        boda.scalar_max_offset_days,
        us.bo_status_cd,
        us_status.descr,
        us.bo_status_reason_cd,
        us.us_type_cd,
        us_type.descr100,
        us.d1_spr_cd,
        us_spr.descr100,
        us.d1_bill_cyc_cd,
        d1_bill_cyc.descr100,
        us.division_cd,
        us.time_zone_cd,
        us_time_zone.descr,
        us.access_grp_cd,
        us_access_grp.descr,
        us.us_stat_cond_flg,
        CASE TRIM(us.us_stat_cond_flg)
            WHEN 'D2NO' THEN 'Normal'
            WHEN 'D2PE' THEN 'Pending'
            WHEN 'D2ER' THEN 'Error'
            ELSE 'Unknown'
        END AS us_stat_cond_desc,
        us.usg_appr_req_flg,
        CASE TRIM(us.usg_appr_req_flg)
            WHEN 'D2YS' THEN 'Yes'
            WHEN 'D2NO' THEN 'No'
            ELSE 'Unknown'
        END AS usg_appr_req_desc,
        us.start_dttm,
        us.end_dttm,
        us.status_upd_dttm,
        us.most_recent_trans_dttm,
        us.us_mp_id,
        psq.period_sq_row_count,
        psq.period_sq_period_count,
        psq.period_sq_determinant_count,
        psq.period_sq_total_quantity,
        psq.period_sq_sp_count,
        psq.period_sq_measr_comp_count,
        psq.period_sq_interval_row_count,
        psq.period_sq_extract_interval_count,
        psq.period_sq_sole_uom_cd,
        period_sq_uom.descr100,
        psq.period_sq_sole_tou_cd,
        period_sq_tou.descr100,
        psq.period_sq_sole_sqi_cd,
        period_sq_sqi.descr100,
        sagg.scalar_row_count,
        sagg.scalar_determinant_count,
        sagg.scalar_total_quantity,
        sagg.scalar_total_final_quantity,
        sagg.scalar_total_start_msrmt,
        sagg.scalar_total_end_msrmt,
        sagg.scalar_total_use_percent,
        sagg.scalar_total_applied_mltr,
        sagg.scalar_sp_count,
        sagg.scalar_measr_comp_count,
        sagg.scalar_sole_final_uom_cd,
        scalar_final_uom.descr100,
        sagg.scalar_sole_final_tou_cd,
        scalar_final_tou.descr100,
        sagg.scalar_sole_final_sqi_cd,
        scalar_final_sqi.descr100,
        bridge.bridge_method,
        bridge.c1_match_count,
        bridge.c1_usage_id,
        bridge.c1_master_usage_id,
        bridge.c1_sa_id,
        bridge.c1_sp_id,
        bridge.c1_bseg_id,
        bridge.c1_bill_cyc_cd,
        c1_bill_cyc.descr,
        bridge.c1_bo_status_cd,
        c1_status.descr,
        bridge.c1_start_dttm,
        bridge.c1_end_dttm,
        bridge.c1_status_upd_dttm,
        bridge.c1_cre_dttm,
        bseg.bill_id,
        bseg.bseg_stat_flg,
        bseg_status.descr,
        bseg.start_dt,
        bseg.end_dt,
        bseg.est_sw,
        bseg.bill_cyc_cd,
        bseg_bill_cyc.descr,
        COALESCE(bridge.c1_sa_id, bseg.sa_id) AS sa_id,
        sa.acct_id,
        cust.per_id,
        cust.customer_name,
        sa.sa_type_cd,
        sa_type.descr,
        sa.sa_status_flg,
        sa_status.descr,
        sa.cis_division,
        sa.currency_cd,
        sa.start_dt,
        sa.end_dt,
        COALESCE(bseg.prem_id, sa.char_prem_id) AS prem_id,
        prem.address1,
        prem.city,
        prem.state,
        prem.postal
    FROM cisadm.d1_usage u
    LEFT JOIN cisadm.d1_us us
        ON TRIM(us.us_id) = TRIM(u.us_id)
    LEFT JOIN cisadm.cms_d1_usage_boda_vw boda
        ON TRIM(boda.d1_usage_id) = TRIM(u.d1_usage_id)
    LEFT JOIN period_sq_agg psq
        ON TRIM(psq.d1_usage_id) = TRIM(u.d1_usage_id)
    LEFT JOIN scalar_agg sagg
        ON TRIM(sagg.d1_usage_id) = TRIM(u.d1_usage_id)
    LEFT JOIN c1_usage_bridge bridge
        ON TRIM(bridge.d1_usage_id) = TRIM(u.d1_usage_id)
    LEFT JOIN cisadm.ci_bseg bseg
        ON TRIM(bseg.bseg_id) = TRIM(bridge.c1_bseg_id)
    LEFT JOIN cisadm.ci_sa sa
        ON TRIM(sa.sa_id) = TRIM(COALESCE(bridge.c1_sa_id, bseg.sa_id))
    LEFT JOIN customer_choice cust
        ON cust.acct_id = sa.acct_id
       AND cust.rn = 1
    LEFT JOIN cisadm.ci_prem prem
        ON TRIM(prem.prem_id) = TRIM(COALESCE(bseg.prem_id, sa.char_prem_id))
    LEFT JOIN cisadm.f1_bus_obj_l usage_bo
        ON usage_bo.bus_obj_cd = u.bus_obj_cd
       AND usage_bo.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l usage_status
        ON usage_status.bus_obj_cd = u.bus_obj_cd
       AND usage_status.bo_status_cd = u.bo_status_cd
       AND usage_status.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_usg_grp_l usage_grp
        ON usage_grp.usg_grp_cd = u.usg_grp_cd
       AND usage_grp.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_usg_cal_type_l usage_cal_type
        ON usage_cal_type.d1_usg_cal_type_cd = u.d1_usg_cal_type_cd
       AND usage_cal_type.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_spr_l usage_spr
        ON usage_spr.d1_spr_cd = u.d1_spr_cd
       AND usage_spr.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_msrmt_cyc_l usage_cyc
        ON usage_cyc.msrmt_cyc_cd = u.msrmt_cyc_cd
       AND usage_cyc.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_msrmt_cyc_rte_l usage_rte
        ON usage_rte.msrmt_cyc_cd = u.msrmt_cyc_cd
       AND usage_rte.msrmt_cyc_rte_cd = u.msrmt_cyc_rte_cd
       AND usage_rte.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l us_status
        ON us_status.bus_obj_cd = us.bus_obj_cd
       AND us_status.bo_status_cd = us.bo_status_cd
       AND us_status.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_us_type_l us_type
        ON us_type.us_type_cd = us.us_type_cd
       AND us_type.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_spr_l us_spr
        ON us_spr.d1_spr_cd = us.d1_spr_cd
       AND us_spr.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_bill_cyc_l d1_bill_cyc
        ON d1_bill_cyc.d1_bill_cyc_cd = us.d1_bill_cyc_cd
       AND d1_bill_cyc.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_time_zone_l us_time_zone
        ON us_time_zone.time_zone_cd = us.time_zone_cd
       AND us_time_zone.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acc_grp_l us_access_grp
        ON us_access_grp.access_grp_cd = us.access_grp_cd
       AND us_access_grp.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_uom_l period_sq_uom
        ON period_sq_uom.d1_uom_cd = psq.period_sq_sole_uom_cd
       AND period_sq_uom.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_tou_l period_sq_tou
        ON period_sq_tou.d1_tou_cd = psq.period_sq_sole_tou_cd
       AND period_sq_tou.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_sqi_l period_sq_sqi
        ON period_sq_sqi.d1_sqi_cd = psq.period_sq_sole_sqi_cd
       AND period_sq_sqi.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_uom_l scalar_final_uom
        ON scalar_final_uom.d1_uom_cd = sagg.scalar_sole_final_uom_cd
       AND scalar_final_uom.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_tou_l scalar_final_tou
        ON scalar_final_tou.d1_tou_cd = sagg.scalar_sole_final_tou_cd
       AND scalar_final_tou.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_sqi_l scalar_final_sqi
        ON scalar_final_sqi.d1_sqi_cd = sagg.scalar_sole_final_sqi_cd
       AND scalar_final_sqi.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l c1_status
        ON c1_status.bus_obj_cd = bridge.c1_bus_obj_cd
       AND c1_status.bo_status_cd = bridge.c1_bo_status_cd
       AND c1_status.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l c1_bill_cyc
        ON c1_bill_cyc.bill_cyc_cd = bridge.c1_bill_cyc_cd
       AND c1_bill_cyc.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l bseg_status
        ON TRIM(bseg_status.field_name) = 'BSEG_STAT_FLG'
       AND TRIM(bseg_status.field_value) = TRIM(bseg.bseg_stat_flg)
       AND bseg_status.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l bseg_bill_cyc
        ON bseg_bill_cyc.bill_cyc_cd = bseg.bill_cyc_cd
       AND bseg_bill_cyc.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_sa_type_l sa_type
        ON sa_type.cis_division = sa.cis_division
       AND sa_type.sa_type_cd = sa.sa_type_cd
       AND sa_type.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l sa_status
        ON TRIM(sa_status.field_name) = 'SA_STATUS_FLG'
       AND TRIM(sa_status.field_value) = TRIM(sa.sa_status_flg)
       AND sa_status.language_cd = 'ENG';

    COMMIT;
END;
/
