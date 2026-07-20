CREATE OR REPLACE PROCEDURE cisadm.refresh_d1_usage_rpt_curr AS
    v_batch_start       TIMESTAMP;
    v_batch_end         TIMESTAMP;
    v_batch_upper_bound TIMESTAMP;
BEGIN
    DELETE FROM cisadm.d1_usage_rpt_curr;
    COMMIT;

    SELECT
        CAST(TRUNC(MIN(NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm))), 'MM') AS TIMESTAMP),
        CAST(ADD_MONTHS(TRUNC(MAX(NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm))), 'MM'), 1) AS TIMESTAMP)
    INTO
        v_batch_start,
        v_batch_upper_bound
    FROM cisadm.d1_usage u
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL;

    WHILE v_batch_start < v_batch_upper_bound LOOP
        v_batch_end := ADD_MONTHS(v_batch_start, 1);

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
        batch_usage AS (
            SELECT u.*
            FROM cisadm.d1_usage u
            WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) >= v_batch_start
              AND NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) < v_batch_end
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
                bridge.c1_bus_obj_cd,
                bridge.c1_start_dttm,
                bridge.c1_end_dttm,
                bridge.c1_status_upd_dttm,
                bridge.c1_cre_dttm
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
                    cu.start_dttm AS c1_start_dttm,
                    cu.end_dttm AS c1_end_dttm,
                    cu.status_upd_dttm AS c1_status_upd_dttm,
                    cu.cre_dttm AS c1_cre_dttm,
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
            COALESCE(NULLIF(TRIM(bseg.bill_cyc_cd), ''), NULLIF(TRIM(bridge.c1_bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), '')) AS bseg_bill_cyc_cd,
            bseg_bill_cyc.descr AS bseg_bill_cyc_desc,
            COALESCE(bridge.c1_sa_id, bseg.sa_id) AS sa_id,
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
            sa.cis_division,
            sa.currency_cd,
            sa.start_dt,
            sa.end_dt,
            COALESCE(bseg.prem_id, sa.char_prem_id) AS prem_id,
            prem.address1,
            prem.city,
            prem.state,
            prem.postal
        FROM batch_usage u
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
        LEFT JOIN cisadm.ci_bill_cyc_l bseg_bill_cyc
            ON bseg_bill_cyc.bill_cyc_cd = COALESCE(NULLIF(TRIM(bseg.bill_cyc_cd), ''), NULLIF(TRIM(bridge.c1_bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))
           AND bseg_bill_cyc.language_cd = 'ENG'
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
        v_batch_start := v_batch_end;
    END LOOP;
END;
/
