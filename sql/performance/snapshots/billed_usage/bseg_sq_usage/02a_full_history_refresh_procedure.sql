CREATE OR REPLACE PROCEDURE cisadm.refresh_bseg_sq_usage_rpt_curr AS
BEGIN
    EXECUTE IMMEDIATE 'TRUNCATE TABLE cisadm.bseg_sq_usage_rpt_curr';

    INSERT INTO cisadm.bseg_sq_usage_rpt_curr (
        bseg_id,
        uom_cd,
        uom_desc,
        tou_cd,
        tou_desc,
        sqi_cd,
        sqi_desc,
        sq_line_count,
        bseg_determinant_count,
        total_init_sq,
        total_bill_sq,
        load_dttm,
        bill_id,
        acct_id,
        customer_name,
        sa_id,
        sa_type_cd,
        sa_type_desc,
        utility_type_cd,
        prem_id,
        bseg_stat_flg,
        bseg_stat_desc,
        bill_stat_flg,
        bill_stat_desc,
        bill_dt,
        due_dt,
        bseg_start_dt,
        bseg_end_dt,
        win_start_dt,
        bseg_bill_cyc_cd,
        bseg_bill_cyc_desc,
        bill_bill_cyc_cd,
        bill_bill_cyc_desc,
        cust_cl_cd,
        cust_cl_desc,
        coll_cl_cd,
        coll_cl_desc,
        acct_mgmt_grp_cd,
        acct_mgmt_grp_desc,
        bud_plan_cd,
        bud_plan_desc,
        est_sw,
        closing_bseg_sw,
        sq_override_sw,
        item_override_sw,
        can_rsn_cd,
        can_rsn_desc,
        rebill_seg_id,
        can_bseg_id,
        master_bseg_id
    )
    SELECT
        sq_det.bseg_id,
        sq_det.uom_cd,
        uom_l.descr,
        sq_det.tou_cd,
        tou_l.descr,
        sq_det.sqi_cd,
        sqi_l.descr,
        sq_det.sq_line_count,
        sq_bseg_agg.bseg_determinant_count,
        sq_det.total_init_sq,
        sq_det.total_bill_sq,
        SYSTIMESTAMP,
        bseg.bill_id,
        bill.acct_id,
        cust_name.entity_name,
        bseg.sa_id,
        sa.sa_type_cd,
        sa_type_l.descr,
        sa_type_base.svc_type_cd,
        bseg.prem_id,
        bseg.bseg_stat_flg,
        bseg_status_l.descr,
        bill.bill_stat_flg,
        bill_status_l.descr,
        bill.bill_dt,
        bill.due_dt,
        bseg.start_dt,
        bseg.end_dt,
        bseg.win_start_dt,
        COALESCE(NULLIF(TRIM(bseg.bill_cyc_cd), ''), NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), '')) AS bseg_bill_cyc_cd,
        bseg_bill_cyc_l.descr AS bseg_bill_cyc_desc,
        COALESCE(NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), '')) AS bill_bill_cyc_cd,
        bill_bill_cyc_l.descr AS bill_bill_cyc_desc,
        acct.cust_cl_cd,
        cust_cl_l.descr,
        acct.coll_cl_cd,
        coll_cl_l.descr,
        acct.acct_mgmt_grp_cd,
        acct_mgmt_l.descr,
        acct.bud_plan_cd,
        bud_plan_l.descr,
        bseg.est_sw,
        bseg.closing_bseg_sw,
        bseg.sq_override_sw,
        bseg.item_override_sw,
        bseg.can_rsn_cd,
        can_rsn_l.descr,
        bseg.rebill_seg_id,
        bseg.can_bseg_id,
        bseg.master_bseg_id
    FROM (
        SELECT
            sq.bseg_id,
            sq.uom_cd,
            sq.tou_cd,
            sq.sqi_cd,
            COUNT(*) AS sq_line_count,
            SUM(NVL(sq.init_sq, 0)) AS total_init_sq,
            SUM(NVL(sq.bill_sq, 0)) AS total_bill_sq
        FROM cisadm.ci_bseg_sq sq
        INNER JOIN cisadm.ci_bseg bseg
            ON bseg.bseg_id = sq.bseg_id
        INNER JOIN cisadm.ci_bill bill
            ON bill.bill_id = bseg.bill_id
           AND bill.bill_stat_flg = 'C '
        GROUP BY
            sq.bseg_id,
            sq.uom_cd,
            sq.tou_cd,
            sq.sqi_cd
    ) sq_det
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = sq_det.bseg_id
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
       AND bill.bill_stat_flg = 'C '
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = bseg.sa_id
    LEFT JOIN (
        SELECT
            ap.acct_id,
            pn.entity_name,
            ROW_NUMBER() OVER (
                PARTITION BY ap.acct_id
                ORDER BY
                    CASE WHEN pn.prim_name_sw = 'Y' THEN 0 ELSE 1 END,
                    pn.seq_num,
                    pn.per_id
            ) AS rn
        FROM cisadm.ci_acct_per ap
        INNER JOIN cisadm.ci_per_name pn
            ON pn.per_id = ap.per_id
        WHERE ap.main_cust_sw = 'Y'
          AND (pn.prim_name_sw = 'Y' OR pn.name_type_flg = 'PRIM')
    ) cust_name
        ON cust_name.acct_id = bill.acct_id
       AND cust_name.rn = 1
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = bill.acct_id
    LEFT JOIN (
        SELECT
            st.sa_type_cd,
            MIN(st.svc_type_cd) AS svc_type_cd
        FROM cisadm.ci_sa_type st
        GROUP BY
            st.sa_type_cd
    ) sa_type_base
        ON sa_type_base.sa_type_cd = sa.sa_type_cd
    LEFT JOIN (
        SELECT
            sq.bseg_id,
            COUNT(DISTINCT NVL(sq.uom_cd, '~') || ':' || NVL(sq.tou_cd, '~') || ':' || NVL(sq.sqi_cd, '~')) AS bseg_determinant_count
        FROM cisadm.ci_bseg_sq sq
        INNER JOIN cisadm.ci_bseg bseg
            ON bseg.bseg_id = sq.bseg_id
        INNER JOIN cisadm.ci_bill bill
            ON bill.bill_id = bseg.bill_id
           AND bill.bill_stat_flg = 'C '
        GROUP BY
            sq.bseg_id
    ) sq_bseg_agg
        ON sq_bseg_agg.bseg_id = sq_det.bseg_id
    LEFT JOIN cisadm.ci_lookup_val_l bill_status_l
        ON bill_status_l.field_name = 'BILL_STAT_FLG'
       AND bill_status_l.field_value = bill.bill_stat_flg
       AND bill_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l bseg_status_l
        ON bseg_status_l.field_name = 'BSEG_STAT_FLG'
       AND bseg_status_l.field_value = bseg.bseg_stat_flg
       AND bseg_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l bill_bill_cyc_l
        ON bill_bill_cyc_l.bill_cyc_cd = COALESCE(NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))
       AND bill_bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l bseg_bill_cyc_l
        ON bseg_bill_cyc_l.bill_cyc_cd = COALESCE(NULLIF(TRIM(bseg.bill_cyc_cd), ''), NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))
       AND bseg_bill_cyc_l.language_cd = 'ENG'
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
        ON sa_type_l.cis_division = sa.cis_division
       AND sa_type_l.sa_type_cd = sa.sa_type_cd
       AND sa_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_can_rsn_l can_rsn_l
        ON can_rsn_l.can_rsn_cd = bseg.can_rsn_cd
       AND can_rsn_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_uom_l uom_l
        ON uom_l.uom_cd = sq_det.uom_cd
       AND uom_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_tou_l tou_l
        ON tou_l.tou_cd = sq_det.tou_cd
       AND tou_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_sqi_l sqi_l
        ON sqi_l.sqi_cd = sq_det.sqi_cd
       AND sqi_l.language_cd = 'ENG';

    COMMIT;
END;
/
