CREATE OR REPLACE PROCEDURE cisadm.refresh_ft_rpt_curr AS
    v_window_start DATE := ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12);
BEGIN
    DELETE FROM cisadm.ft_rpt_curr
    WHERE accounting_dt >= v_window_start;

    INSERT INTO cisadm.ft_rpt_curr (
        ft_id,
        ft_type_flg,
        ft_type_flg_desc,
        accounting_dt,
        cre_dttm,
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
        acct_id,
        load_dttm,
        sa_status_flg,
        sa_status_desc,
        sa_type_cd,
        sa_type_desc,
        cust_cl_cd,
        cust_cl_desc,
        coll_cl_cd,
        coll_cl_desc,
        bill_cyc_cd,
        bill_cyc_desc,
        acct_mgmt_grp_cd,
        acct_mgmt_grp_desc,
        bseg_id,
        bseg_stat_flg,
        bseg_stat_desc,
        start_dt,
        end_dt,
        adj_id,
        adj_status_flg,
        adj_status_desc,
        adj_type_cd,
        adj_type_desc,
        adj_amt,
        pay_seg_id,
        pay_id,
        pay_seg_amt
    )
    SELECT
        ft.ft_id,
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
        ft.cre_dttm,
        ft.freeze_dttm,
        ft.freeze_user_id,
        COALESCE(NULLIF(TRIM(u.first_name || ' ' || u.last_name), ''), u.user_id) AS freeze_user_name,
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
        sa.acct_id,
        SYSTIMESTAMP,
        sa.sa_status_flg,
        sa_stat.descr        AS sa_status_desc,
        sa.sa_type_cd,
        sa_type.descr        AS sa_type_desc,
        acct.cust_cl_cd,
        cust_cl_l.descr      AS cust_cl_desc,
        acct.coll_cl_cd,
        coll_cl_l.descr      AS coll_cl_desc,
        acct.bill_cyc_cd,
        bill_cyc_l.descr     AS bill_cyc_desc,
        acct.acct_mgmt_grp_cd,
        acct_mgmt_l.descr    AS acct_mgmt_grp_desc,
        bseg.bseg_id,
        bseg.bseg_stat_flg,
        bseg_stat.descr      AS bseg_stat_desc,
        bseg.start_dt,
        bseg.end_dt,
        adj.adj_id,
        adj.adj_status_flg,
        adj_stat.descr       AS adj_status_desc,
        adj.adj_type_cd,
        adj_type.descr       AS adj_type_desc,
        adj.adj_amt,
        pay.pay_seg_id,
        pay.pay_id,
        pay.pay_seg_amt
    FROM cisadm.ci_ft ft
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = ft.sa_id
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = sa.acct_id
    LEFT JOIN cisadm.sc_user u
        ON u.user_id = ft.freeze_user_id
       AND u.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = ft.sibling_id
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_adj adj
        ON adj.adj_id = ft.sibling_id
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_pay_seg pay
        ON pay.pay_seg_id = ft.sibling_id
       AND pay.pay_id = ft.parent_id
       AND ft.ft_type_flg IN ('PS', 'PX')
    LEFT JOIN cisadm.ci_lookup_val_l sa_stat
        ON sa_stat.field_name  = 'SA_STATUS_FLG'
       AND sa_stat.field_value = sa.sa_status_flg
       AND sa_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_sa_type_l sa_type
        ON sa_type.sa_type_cd  = sa.sa_type_cd
       AND sa_type.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON cust_cl_l.cust_cl_cd = acct.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON coll_cl_l.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l bill_cyc_l
        ON bill_cyc_l.bill_cyc_cd = acct.bill_cyc_cd
       AND bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt_l
        ON acct_mgmt_l.acct_mgmt_grp_cd = acct.acct_mgmt_grp_cd
       AND acct_mgmt_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l bseg_stat
        ON bseg_stat.field_name  = 'BSEG_STAT_FLG'
       AND bseg_stat.field_value = bseg.bseg_stat_flg
       AND bseg_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l adj_stat
        ON adj_stat.field_name  = 'ADJ_STATUS_FLG'
       AND adj_stat.field_value = adj.adj_status_flg
       AND adj_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_adj_type_l adj_type
        ON adj_type.adj_type_cd  = adj.adj_type_cd
       AND adj_type.language_cd  = 'ENG'
    WHERE ft.redundant_sw = 'N'
      AND ft.accounting_dt >= v_window_start;

    COMMIT;
END;
/
