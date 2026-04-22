CREATE OR REPLACE PROCEDURE cisadm.refresh_ft_gl_distribution_rpt_curr AS
BEGIN
    EXECUTE IMMEDIATE 'TRUNCATE TABLE cisadm.ft_gl_distribution_rpt_curr';

    INSERT INTO cisadm.ft_gl_distribution_rpt_curr (
        ft_id,
        gl_seq_nbr,
        gl_acct,
        dst_id,
        dst_desc,
        gl_amount,
        debit_amt,
        credit_amt,
        statistic_amount,
        tot_amt_sw,
        char_type_cd,
        char_val,
        batch_cd,
        batch_nbr,
        is_latest_batch_nbr,
        load_dttm,
        ft_type_flg,
        ft_type_flg_desc,
        accounting_dt,
        ars_dt,
        ft_cre_dttm,
        freeze_sw,
        freeze_dttm,
        freeze_user_id,
        freeze_user_name,
        cur_amt,
        tot_amt,
        currency_cd,
        bill_id,
        sa_id,
        parent_id,
        sibling_id,
        gl_distrib_status,
        gl_distrib_status_desc,
        gl_division,
        gl_division_desc,
        cis_division,
        sched_distrib_dt,
        xferred_out_sw,
        xfer_to_gl_dt,
        match_evt_id,
        bal_ctl_grp_id,
        correction_sw,
        new_debit_sw,
        show_on_bill_sw,
        not_in_ars_sw,
        acct_id,
        per_id,
        customer_name_upr,
        sa_status_flg,
        sa_status_desc,
        sa_type_cd,
        sa_type_desc,
        char_prem_id,
        bill_cyc_cd,
        bill_cyc_desc,
        cust_cl_cd,
        cust_cl_desc,
        coll_cl_cd,
        coll_cl_desc,
        acct_mgmt_grp_cd,
        acct_mgmt_grp_desc,
        balancing_stat_flg,
        balancing_stat_desc,
        bcg_cur_amt,
        bcg_tot_amt,
        bcg_cur_bal,
        bcg_tot_bal,
        bcg_cre_dttm,
        bseg_id,
        bseg_stat_flg,
        bseg_stat_desc,
        bseg_bill_cyc_cd,
        bseg_bill_cyc_desc,
        bseg_start_dt,
        bseg_end_dt,
        bseg_prem_id,
        bseg_est_sw,
        bseg_closing_sw,
        bseg_can_rsn_cd,
        bseg_can_rsn_desc,
        adj_id,
        adj_status_flg,
        adj_status_desc,
        adj_type_cd,
        adj_type_desc,
        adj_can_rsn_cd,
        adj_can_rsn_desc,
        adj_amt,
        xfer_adj_id,
        behalf_sa_id,
        base_amt,
        gen_ref_dt,
        appr_req_id,
        pay_seg_id,
        pay_id,
        pay_seg_amt,
        pay_match_evt_id
    )
    SELECT
        ft.ft_id,
        ft_gl.gl_seq_nbr,
        ft_gl.gl_acct,
        ft_gl.dst_id,
        dst_l.descr,
        ft_gl.amount,
        CASE
            WHEN NVL(ft_gl.amount, 0) >= 0 THEN NVL(ft_gl.amount, 0)
            ELSE 0
        END AS debit_amt,
        CASE
            WHEN NVL(ft_gl.amount, 0) < 0 THEN ABS(ft_gl.amount)
            ELSE 0
        END AS credit_amt,
        ft_gl.statistic_amount,
        ft_gl.tot_amt_sw,
        ft_gl.char_type_cd,
        ft_gl.char_val,
        ft_proc.batch_cd,
        ft_proc.batch_nbr,
        NULL AS is_latest_batch_nbr,
        SYSTIMESTAMP,
        ft.ft_type_flg,
        CASE ft.ft_type_flg
            WHEN 'AD' THEN 'Adjustment'
            WHEN 'AX' THEN 'Adjustment Cancellation'
            WHEN 'BS' THEN 'Bill Segment'
            WHEN 'BX' THEN 'Bill Segment Cancellation'
            WHEN 'PS' THEN 'Pay Segment'
            WHEN 'PX' THEN 'Pay Segment Cancellation'
        END AS ft_type_flg_desc,
        ft.accounting_dt,
        ft.ars_dt,
        ft.cre_dttm,
        ft.freeze_sw,
        ft.freeze_dttm,
        ft.freeze_user_id,
        TRIM(sc_user.first_name || ' ' || sc_user.last_name),
        ft.cur_amt,
        ft.tot_amt,
        ft.currency_cd,
        ft.bill_id,
        ft.sa_id,
        ft.parent_id,
        ft.sibling_id,
        ft.gl_distrib_status,
        CASE ft.gl_distrib_status
            WHEN 'D' THEN 'Distributed'
            WHEN 'G' THEN 'Generated'
            WHEN 'M' THEN 'Modified'
            WHEN 'N' THEN 'Pending'
        END AS gl_distrib_status_desc,
        ft.gl_division,
        gl_div_l.descr,
        ft.cis_division,
        ft.sched_distrib_dt,
        ft.xferred_out_sw,
        ft.xfer_to_gl_dt,
        ft.match_evt_id,
        ft.bal_ctl_grp_id,
        ft.correction_sw,
        ft.new_debit_sw,
        ft.show_on_bill_sw,
        ft.not_in_ars_sw,
        sa.acct_id,
        cust.per_id,
        cust.entity_name_upr,
        sa.sa_status_flg,
        sa_status_l.descr,
        sa.sa_type_cd,
        sa_type_l.descr,
        sa.char_prem_id,
        acct.bill_cyc_cd,
        acct_bill_cyc_l.descr,
        acct.cust_cl_cd,
        cust_cl_l.descr,
        acct.coll_cl_cd,
        coll_cl_l.descr,
        acct.acct_mgmt_grp_cd,
        acct_mgmt_l.descr,
        bcg.balancing_stat_flg,
        bcg_status_l.descr,
        bcg.cur_amt,
        bcg.tot_amt,
        bcg.cur_bal,
        bcg.tot_bal,
        bcg.cre_dttm,
        bseg.bseg_id,
        bseg.bseg_stat_flg,
        bseg_status_l.descr,
        bseg.bill_cyc_cd,
        bseg_bill_cyc_l.descr,
        bseg.start_dt,
        bseg.end_dt,
        bseg.prem_id,
        bseg.est_sw,
        bseg.closing_bseg_sw,
        bseg.can_rsn_cd,
        bseg_can_rsn_l.descr,
        adj.adj_id,
        adj.adj_status_flg,
        adj_status_l.descr,
        adj.adj_type_cd,
        adj_type_l.descr,
        adj.can_rsn_cd,
        adj_can_rsn_l.descr,
        adj.adj_amt,
        adj.xfer_adj_id,
        adj.behalf_sa_id,
        adj.base_amt,
        adj.gen_ref_dt,
        adj.appr_req_id,
        pay_seg.pay_seg_id,
        pay_seg.pay_id,
        pay_seg.pay_seg_amt,
        pay_seg.match_evt_id
    FROM cisadm.ci_ft_gl ft_gl
    INNER JOIN cisadm.ci_ft ft
        ON ft.ft_id = ft_gl.ft_id
       AND ft.redundant_sw = 'N'
    LEFT JOIN cisadm.ci_ft_proc_vw ft_proc_vw
        ON ft_proc_vw.ft_id = ft.ft_id
    LEFT JOIN cisadm.ci_ft_proc ft_proc
        ON ft_proc.ft_id = ft_proc_vw.ft_id
       AND ft_proc.seq_num = ft_proc_vw.max_seq_num
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = ft.sibling_id
       AND bseg.bill_id = ft.bill_id
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_adj adj
        ON adj.adj_id = ft.sibling_id
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_pay_seg pay_seg
        ON pay_seg.pay_seg_id = ft.sibling_id
       AND pay_seg.pay_id = ft.parent_id
       AND ft.ft_type_flg IN ('PS', 'PX')
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = ft.sa_id
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = sa.acct_id
    LEFT JOIN (
        SELECT
            ap.acct_id,
            ap.per_id,
            pn.entity_name_upr,
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
        INNER JOIN cisadm.ci_per_name pn
            ON pn.per_id = ap.per_id
        WHERE ap.main_cust_sw = 'Y'
           OR ap.fin_resp_sw = 'Y'
    ) cust
        ON cust.acct_id = sa.acct_id
       AND cust.rn = 1
    LEFT JOIN cisadm.ci_gl_division_l gl_div_l
        ON gl_div_l.gl_division = ft.gl_division
       AND gl_div_l.language_cd = 'ENG'
    LEFT JOIN cisadm.sc_user sc_user
        ON sc_user.user_id = ft.freeze_user_id
    LEFT JOIN cisadm.ci_lookup_val_l sa_status_l
        ON sa_status_l.field_name = 'SA_STATUS_FLG'
       AND sa_status_l.field_value = sa.sa_status_flg
       AND sa_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_sa_type_l sa_type_l
        ON sa_type_l.cis_division = sa.cis_division
       AND sa_type_l.sa_type_cd = sa.sa_type_cd
       AND sa_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l acct_bill_cyc_l
        ON acct_bill_cyc_l.bill_cyc_cd = acct.bill_cyc_cd
       AND acct_bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON cust_cl_l.cust_cl_cd = acct.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON coll_cl_l.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt_l
        ON acct_mgmt_l.acct_mgmt_grp_cd = acct.acct_mgmt_grp_cd
       AND acct_mgmt_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bal_ctl_grp bcg
        ON bcg.bal_ctl_grp_id = ft.bal_ctl_grp_id
    LEFT JOIN cisadm.ci_lookup_val_l bcg_status_l
        ON bcg_status_l.field_name = 'BALANCING_STAT_FLG'
       AND bcg_status_l.field_value = bcg.balancing_stat_flg
       AND bcg_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l bseg_status_l
        ON bseg_status_l.field_name = 'BSEG_STAT_FLG'
       AND bseg_status_l.field_value = bseg.bseg_stat_flg
       AND bseg_status_l.language_cd = 'ENG'
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_bill_cyc_l bseg_bill_cyc_l
        ON bseg_bill_cyc_l.bill_cyc_cd = bseg.bill_cyc_cd
       AND bseg_bill_cyc_l.language_cd = 'ENG'
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_bill_can_rsn_l bseg_can_rsn_l
        ON bseg_can_rsn_l.can_rsn_cd = bseg.can_rsn_cd
       AND bseg_can_rsn_l.language_cd = 'ENG'
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_lookup_val_l adj_status_l
        ON adj_status_l.field_name = 'ADJ_STATUS_FLG'
       AND adj_status_l.field_value = adj.adj_status_flg
       AND adj_status_l.language_cd = 'ENG'
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_adj_type_l adj_type_l
        ON adj_type_l.adj_type_cd = adj.adj_type_cd
       AND adj_type_l.language_cd = 'ENG'
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_adj_can_rsn_l adj_can_rsn_l
        ON adj_can_rsn_l.can_rsn_cd = adj.can_rsn_cd
       AND adj_can_rsn_l.language_cd = 'ENG'
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_dst_code_l dst_l
        ON dst_l.dst_id = ft_gl.dst_id
       AND dst_l.language_cd = 'ENG';

    COMMIT;
END;
/
