CREATE OR REPLACE PROCEDURE cisadm.refresh_bseg_billed_usage_rpt_curr AS
    v_window_start DATE := ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12);
BEGIN
    DELETE FROM cisadm.bseg_billed_usage_rpt_curr
    WHERE bill_dt >= v_window_start;

    INSERT INTO cisadm.bseg_billed_usage_rpt_curr (
        bseg_id,
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
        load_dttm,
        cust_cl_cd,
        cust_cl_desc,
        coll_cl_cd,
        coll_cl_desc,
        acct_mgmt_grp_cd,
        acct_mgmt_grp_desc,
        bud_plan_cd,
        bud_plan_desc,
        sq_line_count,
        determinant_count,
        total_init_sq,
        total_bill_sq,
        sole_uom_cd,
        sole_uom_desc,
        sole_tou_cd,
        sole_tou_desc,
        sole_sqi_cd,
        sole_sqi_desc,
        read_line_count,
        total_msr_qty,
        total_final_reg_qty,
        min_start_read_dttm,
        max_end_read_dttm,
        calc_header_count,
        total_calc_amt,
        rs_count,
        sole_rs_cd,
        sole_rs_desc,
        min_calc_effdt,
        max_calc_effdt,
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
        bseg.bseg_id,
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
        SYSTIMESTAMP,
        acct.cust_cl_cd,
        cust_cl_l.descr,
        acct.coll_cl_cd,
        coll_cl_l.descr,
        acct.acct_mgmt_grp_cd,
        acct_mgmt_l.descr,
        acct.bud_plan_cd,
        bud_plan_l.descr,
        sq_agg.sq_line_count,
        sq_agg.determinant_count,
        sq_agg.total_init_sq,
        sq_agg.total_bill_sq,
        CASE WHEN sq_agg.determinant_count = 1 THEN sq_agg.min_uom_cd END,
        sole_uom_l.descr,
        CASE WHEN sq_agg.determinant_count = 1 THEN sq_agg.min_tou_cd END,
        sole_tou_l.descr,
        CASE WHEN sq_agg.determinant_count = 1 THEN sq_agg.min_sqi_cd END,
        sole_sqi_l.descr,
        read_agg.read_line_count,
        read_agg.total_msr_qty,
        read_agg.total_final_reg_qty,
        read_agg.min_start_read_dttm,
        read_agg.max_end_read_dttm,
        calc_agg.calc_header_count,
        calc_agg.total_calc_amt,
        calc_agg.rs_count,
        CASE WHEN calc_agg.rs_count = 1 THEN calc_agg.min_rs_cd END,
        sole_rs_l.descr,
        calc_agg.min_calc_effdt,
        calc_agg.max_calc_effdt,
        bseg.est_sw,
        bseg.closing_bseg_sw,
        bseg.sq_override_sw,
        bseg.item_override_sw,
        bseg.can_rsn_cd,
        can_rsn_l.descr,
        bseg.rebill_seg_id,
        bseg.can_bseg_id,
        bseg.master_bseg_id
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
       AND bill.bill_stat_flg = 'C '
       AND bill.bill_dt >= v_window_start
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
        SELECT st.sa_type_cd, MIN(st.svc_type_cd) AS svc_type_cd
        FROM cisadm.ci_sa_type st
        GROUP BY st.sa_type_cd
    ) sa_type_base
        ON sa_type_base.sa_type_cd = sa.sa_type_cd
    LEFT JOIN (
        SELECT
            sq.bseg_id,
            COUNT(*) AS sq_line_count,
            COUNT(DISTINCT NVL(sq.uom_cd, '~') || ':' || NVL(sq.tou_cd, '~') || ':' || NVL(sq.sqi_cd, '~')) AS determinant_count,
            SUM(NVL(sq.init_sq, 0)) AS total_init_sq,
            SUM(NVL(sq.bill_sq, 0)) AS total_bill_sq,
            MIN(sq.uom_cd) AS min_uom_cd,
            MIN(sq.tou_cd) AS min_tou_cd,
            MIN(sq.sqi_cd) AS min_sqi_cd
        FROM cisadm.ci_bseg_sq sq
        GROUP BY sq.bseg_id
    ) sq_agg
        ON sq_agg.bseg_id = bseg.bseg_id
    LEFT JOIN (
        SELECT
            rd.bseg_id,
            COUNT(*) AS read_line_count,
            SUM(NVL(rd.msr_qty, 0)) AS total_msr_qty,
            SUM(NVL(rd.final_reg_qty, 0)) AS total_final_reg_qty,
            MIN(rd.start_read_dttm) AS min_start_read_dttm,
            MAX(rd.end_read_dttm) AS max_end_read_dttm
        FROM cisadm.ci_bseg_read rd
        GROUP BY rd.bseg_id
    ) read_agg
        ON read_agg.bseg_id = bseg.bseg_id
    LEFT JOIN (
        SELECT
            calc.bseg_id,
            COUNT(*) AS calc_header_count,
            SUM(NVL(calc.calc_amt, 0)) AS total_calc_amt,
            COUNT(DISTINCT calc.rs_cd) AS rs_count,
            MIN(calc.rs_cd) AS min_rs_cd,
            MIN(calc.effdt) AS min_calc_effdt,
            MAX(calc.effdt) AS max_calc_effdt
        FROM cisadm.ci_bseg_calc calc
        GROUP BY calc.bseg_id
    ) calc_agg
        ON calc_agg.bseg_id = bseg.bseg_id
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
    LEFT JOIN cisadm.ci_uom_l sole_uom_l
        ON sole_uom_l.uom_cd = sq_agg.min_uom_cd
       AND sole_uom_l.language_cd = 'ENG'
       AND sq_agg.determinant_count = 1
    LEFT JOIN cisadm.ci_tou_l sole_tou_l
        ON sole_tou_l.tou_cd = sq_agg.min_tou_cd
       AND sole_tou_l.language_cd = 'ENG'
       AND sq_agg.determinant_count = 1
    LEFT JOIN cisadm.ci_sqi_l sole_sqi_l
        ON sole_sqi_l.sqi_cd = sq_agg.min_sqi_cd
       AND sole_sqi_l.language_cd = 'ENG'
       AND sq_agg.determinant_count = 1
    LEFT JOIN cisadm.ci_rs_l sole_rs_l
        ON sole_rs_l.rs_cd = calc_agg.min_rs_cd
       AND sole_rs_l.language_cd = 'ENG'
       AND calc_agg.rs_count = 1;

    COMMIT;
END;
/
