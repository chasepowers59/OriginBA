CREATE OR REPLACE PROCEDURE cisadm.refresh_d1_usage_scalar_dtl_rpt_curr AS
BEGIN
    EXECUTE IMMEDIATE 'TRUNCATE TABLE cisadm.d1_usage_scalar_dtl_rpt_curr';

    INSERT /*+ APPEND */ INTO cisadm.d1_usage_scalar_dtl_rpt_curr (
        d1_usage_id,
        seq_num,
        load_dttm,
        us_id,
        usg_ext_id,
        org_usage_id,
        usage_start_dttm,
        usage_end_dttm,
        usage_status_upd_dttm,
        usage_cre_dttm,
        bus_obj_cd,
        bus_obj_desc,
        bo_status_cd,
        bo_status_desc,
        bo_status_reason_cd,
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
        d1_sp_id,
        measr_comp_id,
        d1_uom_cd,
        d1_uom_desc,
        d1_tou_cd,
        d1_tou_desc,
        d1_sqi_cd,
        d1_sqi_desc,
        start_dttm,
        end_dttm,
        start_msrmt,
        end_msrmt,
        quantity,
        d1_final_uom_cd,
        d1_final_uom_desc,
        d1_final_tou_cd,
        d1_final_tou_desc,
        d1_final_sqi_cd,
        d1_final_sqi_desc,
        final_quantity,
        d1_usage_flg,
        d1_usage_desc,
        measr_comp_usage_flg,
        measr_comp_usage_desc,
        msr_peak_qty_flg,
        msr_peak_qty_desc,
        applied_mltr,
        use_percent,
        scalar_usg_grp_cd,
        scalar_usg_grp_desc,
        usg_rule_cd,
        usg_rule_desc,
        msrmt_cond_flg,
        msrmt_cond_desc,
        us_bo_status_cd,
        us_bo_status_desc,
        us_type_cd,
        us_type_desc,
        d1_bill_cyc_cd,
        d1_bill_cyc_desc,
        division_cd,
        time_zone_cd,
        time_zone_desc,
        access_grp_cd,
        access_grp_desc,
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
        bill_id,
        bseg_stat_flg,
        bseg_stat_desc,
        bseg_start_dt,
        bseg_end_dt,
        sa_id,
        acct_id,
        cust_cl_cd,
        cust_cl_desc,
        coll_cl_cd,
        coll_cl_desc,
        acct_mgmt_grp_cd,
        acct_mgmt_grp_desc,
        bud_plan_cd,
        bud_plan_desc,
        per_id,
        customer_name,
        sa_type_cd,
        sa_type_desc,
        sa_status_flg,
        sa_status_desc,
        prem_id,
        address1,
        city,
        state,
        postal
    )
    WITH
    batch_usage AS (
        SELECT u.*
        FROM cisadm.d1_usage u
        WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
    ),
    c1_usage_bridge AS (
        SELECT
            bridge.d1_usage_id,
            bridge.bridge_method,
            bridge.c1_match_count,
            bridge.c1_usage_id,
            bridge.c1_master_usage_id,
            bridge.c1_sa_id,
            bridge.c1_sp_id,
            bridge.c1_bseg_id,
            bridge.c1_bill_cyc_cd,
            bridge.c1_bo_status_cd,
            bridge.c1_bus_obj_cd
        FROM (
            SELECT
                u.d1_usage_id,
                'USG_EXT_ID_TO_C1_USAGE_ID' AS bridge_method,
                COUNT(*) OVER (PARTITION BY u.d1_usage_id) AS c1_match_count,
                cu.usage_id AS c1_usage_id,
                cu.master_usage_id AS c1_master_usage_id,
                cu.sa_id AS c1_sa_id,
                cu.sp_id AS c1_sp_id,
                cu.bseg_id AS c1_bseg_id,
                cu.bill_cyc_cd AS c1_bill_cyc_cd,
                cu.bo_status_cd AS c1_bo_status_cd,
                cu.bus_obj_cd AS c1_bus_obj_cd,
                ROW_NUMBER() OVER (
                    PARTITION BY u.d1_usage_id
                    ORDER BY
                        cu.status_upd_dttm DESC NULLS LAST,
                        cu.cre_dttm DESC NULLS LAST,
                        cu.usage_id
                ) AS rn
            FROM batch_usage u
            JOIN cisadm.c1_usage cu
                ON cu.usage_id = u.usg_ext_id
               AND cu.bo_status_cd = 'BD-PROC'
            WHERE u.usg_ext_id IS NOT NULL
        ) bridge
        WHERE bridge.rn = 1
    ),
    batch_sa AS (
        SELECT DISTINCT
            COALESCE(bridge.c1_sa_id, bseg.sa_id) AS sa_id
        FROM batch_usage u
        LEFT JOIN c1_usage_bridge bridge
            ON bridge.d1_usage_id = u.d1_usage_id
        LEFT JOIN cisadm.ci_bseg bseg
            ON bseg.bseg_id = bridge.c1_bseg_id
        WHERE COALESCE(bridge.c1_sa_id, bseg.sa_id) IS NOT NULL
    ),
    batch_accounts AS (
        SELECT DISTINCT sa.acct_id
        FROM batch_sa bsa
        JOIN cisadm.ci_sa sa
            ON sa.sa_id = bsa.sa_id
        WHERE sa.acct_id IS NOT NULL
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
        FROM batch_accounts ba
        JOIN cisadm.ci_acct_per ap
            ON ap.acct_id = ba.acct_id
        JOIN cisadm.ci_per_name pn
            ON pn.per_id = ap.per_id
        WHERE ap.main_cust_sw = 'Y'
          AND (pn.prim_name_sw = 'Y' OR pn.name_type_flg = 'PRIM')
    )
    SELECT
        u.d1_usage_id,
        dtl.seq_num,
        SYSTIMESTAMP,
        u.us_id,
        u.usg_ext_id,
        u.org_usage_id,
        u.start_dttm,
        u.end_dttm,
        u.status_upd_dttm,
        u.cre_dttm,
        u.bus_obj_cd,
        usage_bo.descr,
        u.bo_status_cd,
        usage_status.descr,
        u.bo_status_reason_cd,
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
        END,
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
        END,
        u.linked_to_frzn_bseg_flg,
        CASE TRIM(u.linked_to_frzn_bseg_flg)
            WHEN 'D2YS' THEN 'Yes'
            WHEN 'D2NO' THEN 'No'
            ELSE 'Unknown'
        END,
        dtl.d1_sp_id,
        dtl.measr_comp_id,
        dtl.d1_uom_cd,
        raw_uom.descr100,
        dtl.d1_tou_cd,
        raw_tou.descr100,
        dtl.d1_sqi_cd,
        raw_sqi.descr100,
        dtl.start_dttm,
        dtl.end_dttm,
        dtl.start_msrmt,
        dtl.end_msrmt,
        dtl.quantity,
        dtl.d1_final_uom_cd,
        final_uom.descr100,
        dtl.d1_final_tou_cd,
        final_tou.descr100,
        dtl.d1_final_sqi_cd,
        final_sqi.descr100,
        dtl.final_quantity,
        dtl.d1_usage_flg,
        usage_flag.descr,
        dtl.measr_comp_usage_flg,
        measr_comp_usage.descr,
        dtl.msr_peak_qty_flg,
        msr_peak_qty.descr,
        dtl.applied_mltr,
        dtl.use_percent,
        dtl.usg_grp_cd,
        scalar_grp.descr100,
        dtl.usg_rule_cd,
        usg_rule.descr100,
        dtl.msrmt_cond_flg,
        msrmt_cond.descr,
        us.bo_status_cd,
        us_status.descr,
        us.us_type_cd,
        us_type.descr100,
        us.d1_bill_cyc_cd,
        d1_bill_cyc.descr100,
        us.division_cd,
        us.time_zone_cd,
        us_time_zone.descr,
        us.access_grp_cd,
        us_access_grp.descr,
        bridge.bridge_method,
        bridge.c1_match_count,
        bridge.c1_usage_id,
        bridge.c1_master_usage_id,
        bridge.c1_sa_id,
        bridge.c1_sp_id,
        bridge.c1_bseg_id,
        COALESCE(NULLIF(TRIM(bridge.c1_bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), '')) AS c1_bill_cyc_cd,
            c1_bill_cyc.descr AS c1_bill_cyc_desc,
        bridge.c1_bo_status_cd,
        c1_status.descr,
        bseg.bill_id,
        bseg.bseg_stat_flg,
        bseg_status.descr,
        bseg.start_dt,
        bseg.end_dt,
        COALESCE(bridge.c1_sa_id, bseg.sa_id),
        sa.acct_id,
        acct.cust_cl_cd,
        cust_cl.descr,
        acct.coll_cl_cd,
        coll_cl.descr,
        acct.acct_mgmt_grp_cd,
        acct_mgmt.descr,
        acct.bud_plan_cd,
        bud_plan.descr,
        cust.per_id,
        cust.customer_name,
        sa.sa_type_cd,
        sa_type.descr,
        sa.sa_status_flg,
        sa_status.descr,
        COALESCE(bseg.prem_id, sa.char_prem_id),
        prem.address1,
        prem.city,
        prem.state,
        prem.postal
    FROM batch_usage u
    JOIN cisadm.d1_usage_scalar_dtl dtl
        ON dtl.d1_usage_id = u.d1_usage_id
    LEFT JOIN cisadm.d1_us us
        ON us.us_id = u.us_id
    LEFT JOIN c1_usage_bridge bridge
        ON bridge.d1_usage_id = u.d1_usage_id
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = bridge.c1_bseg_id
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = COALESCE(bridge.c1_sa_id, bseg.sa_id)
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = sa.acct_id
    LEFT JOIN customer_choice cust
        ON cust.acct_id = sa.acct_id
       AND cust.rn = 1
    LEFT JOIN cisadm.ci_prem prem
        ON prem.prem_id = COALESCE(bseg.prem_id, sa.char_prem_id)
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
    LEFT JOIN cisadm.d1_usg_grp_l scalar_grp
        ON scalar_grp.usg_grp_cd = dtl.usg_grp_cd
       AND scalar_grp.language_cd = 'ENG'
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
    LEFT JOIN cisadm.d1_uom_l raw_uom
        ON raw_uom.d1_uom_cd = dtl.d1_uom_cd
       AND raw_uom.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_tou_l raw_tou
        ON raw_tou.d1_tou_cd = dtl.d1_tou_cd
       AND raw_tou.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_sqi_l raw_sqi
        ON raw_sqi.d1_sqi_cd = dtl.d1_sqi_cd
       AND raw_sqi.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_uom_l final_uom
        ON final_uom.d1_uom_cd = dtl.d1_final_uom_cd
       AND final_uom.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_tou_l final_tou
        ON final_tou.d1_tou_cd = dtl.d1_final_tou_cd
       AND final_tou.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_sqi_l final_sqi
        ON final_sqi.d1_sqi_cd = dtl.d1_final_sqi_cd
       AND final_sqi.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l usage_flag
        ON TRIM(usage_flag.field_name) = 'D1_USAGE_FLG'
       AND TRIM(usage_flag.field_value) = TRIM(dtl.d1_usage_flg)
       AND usage_flag.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l measr_comp_usage
        ON TRIM(measr_comp_usage.field_name) = 'MEASR_COMP_USAGE_FLG'
       AND TRIM(measr_comp_usage.field_value) = TRIM(dtl.measr_comp_usage_flg)
       AND measr_comp_usage.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l msr_peak_qty
        ON TRIM(msr_peak_qty.field_name) = 'MSR_PEAK_QTY_FLG'
       AND TRIM(msr_peak_qty.field_value) = TRIM(dtl.msr_peak_qty_flg)
       AND msr_peak_qty.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_ext_lookup_val_l msrmt_cond
        ON msrmt_cond.bus_obj_cd = 'D1-MeasurementConditionLookup'
       AND TRIM(msrmt_cond.f1_ext_lookup_value) = TRIM(dtl.msrmt_cond_flg)
       AND msrmt_cond.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_usg_rule_l usg_rule
        ON usg_rule.usg_grp_cd = dtl.usg_grp_cd
       AND usg_rule.usg_rule_cd = dtl.usg_rule_cd
       AND usg_rule.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l us_status
        ON us_status.bus_obj_cd = us.bus_obj_cd
       AND us_status.bo_status_cd = us.bo_status_cd
       AND us_status.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_us_type_l us_type
        ON us_type.us_type_cd = us.us_type_cd
       AND us_type.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_bill_cyc_l d1_bill_cyc
        ON d1_bill_cyc.d1_bill_cyc_cd = us.d1_bill_cyc_cd
       AND d1_bill_cyc.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_time_zone_l us_time_zone
        ON us_time_zone.time_zone_cd = us.time_zone_cd
       AND us_time_zone.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acc_grp_l us_access_grp
        ON us_access_grp.access_grp_cd = us.access_grp_cd
       AND us_access_grp.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l c1_status
        ON c1_status.bus_obj_cd = bridge.c1_bus_obj_cd
       AND c1_status.bo_status_cd = bridge.c1_bo_status_cd
       AND c1_status.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l c1_bill_cyc
        ON c1_bill_cyc.bill_cyc_cd = COALESCE(NULLIF(TRIM(bridge.c1_bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))
       AND c1_bill_cyc.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l bseg_status
        ON TRIM(bseg_status.field_name) = 'BSEG_STAT_FLG'
       AND TRIM(bseg_status.field_value) = TRIM(bseg.bseg_stat_flg)
       AND bseg_status.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_sa_type_l sa_type
        ON sa_type.cis_division = sa.cis_division
       AND sa_type.sa_type_cd = sa.sa_type_cd
       AND sa_type.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cust_cl_l cust_cl
        ON cust_cl.cust_cl_cd = acct.cust_cl_cd
       AND cust_cl.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl
        ON coll_cl.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt
        ON acct_mgmt.acct_mgmt_grp_cd = acct.acct_mgmt_grp_cd
       AND acct_mgmt.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bud_plan_l bud_plan
        ON bud_plan.bud_plan_cd = acct.bud_plan_cd
       AND bud_plan.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l sa_status
        ON TRIM(sa_status.field_name) = 'SA_STATUS_FLG'
       AND TRIM(sa_status.field_value) = TRIM(sa.sa_status_flg)
       AND sa_status.language_cd = 'ENG';

    COMMIT;
END;
/
