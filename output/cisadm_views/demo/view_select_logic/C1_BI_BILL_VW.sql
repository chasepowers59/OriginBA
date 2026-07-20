-- SELECT logic for CISADM.C1_BI_BILL_VW
SELECT
     bill_id,
     bill_cyc_cd,
     win_start_dt,
     win_end_dt,
     accounting_dt,
     acct_id,
     per_id,
     bill_stat_flg,
     bill_dt,
     due_dt,
     cre_dttm,
     complete_dttm,
     late_pay_charge_sw,
     late_pay_charge_dt,
     apay_cre_dt,
     apay_amt,
     apay_stop_user_id,
     apay_stop_dttm,
     apay_stop_amt,
     apay_stop_cre_dt,
     ilm_dt,
     ilm_arch_sw,
     cast(cr_note_ind as number(1,0)) cr_note_ind,
     cast(offcyc_bgen_ind as number(1,0)) offcyc_bgen_ind,
     cast(bseg_amt + adj_amt AS number(15,2)) bill_amt,
     cast(bseg_amt AS number(15,2)) bseg_amt,
     cast(incomplete_bseg_cnt as number(10,0)) incomplete_bseg_cnt,
     cast(error_bseg_cnt as number(10,0)) error_bseg_cnt,
     cast(freezable_bseg_cnt as number(10,0)) freezable_bseg_cnt,
     cast(pend_cancel_bseg_cnt as number(10,0)) pend_cancel_bseg_cnt,
     cast(frozen_bseg_cnt as number(10,0)) frozen_bseg_cnt,
     cast(canceled_bseg_cnt as number(10,0)) canceled_bseg_cnt,
     cast(est_bseg_amt AS number(15,2)) est_bseg_amt,
     cast(est_bseg_cnt as number(10,0)) est_bseg_cnt,
     cast(adj_amt AS number(15,2)) adj_amt,
     cast(frozen_adj_cnt as number(10,0)) frozen_adj_cnt,
     cast(canceled_adj_cnt as number(10,0)) canceled_adj_cnt,
     cast(bill_excp_cnt as number(10,0)) bill_excp_cnt,
     cast(bseg_excp_cnt as number(10,0)) bseg_excp_cnt,
     cast(days_completed_after_win_start as number(5,0)) days_completed_after_win_start,
     cast(completed_within_win_ind as number(1,0)) completed_within_win_ind,
     cast(completed_outside_win_ind as number(1,0)) completed_outside_win_ind,
     cast(days_completed_after_win_end as number(5,0)) days_completed_after_win_end,
     cast(days_created_after_win_start as number(5,0)) days_created_after_win_start,
     cast(bill_win_open_ind as number(1,0)) bill_win_open_ind,
     cast(days_before_bill_win_closes as number(5,0)) days_before_bill_win_closes,
     bkt_compl_days_in_win_cd,
     cast(bkt_compl_days_in_win_seq_num as number(3,0)) bkt_compl_days_in_win_seq_num,
     bkt_days_win_closes_cd,
     cast(bkt_days_win_closes_seq_num as number(3,0)) bkt_days_win_closes_seq_num,
     cast(high_bill_cases_cnt as number(10,0)) high_bill_cases_cnt,
     cast(pending_bill_cnt as number(1,0)) pending_bill_cnt,
     cast(completed_bill_cnt as number(1,0)) completed_bill_cnt,
     cast(bill_cnt as number(1,0)) bill_cnt
 FROM
     (
         SELECT
             bill.bill_id,
             bill.bill_cyc_cd,
             bill.win_start_dt,
             bw.win_end_dt,
             bw.accounting_dt,
             bill.acct_id,
             ap.per_id,
             bill.bill_stat_flg,
             bill.bill_dt,
             bill.due_dt,
             bill.cre_dttm,
             bill.complete_dttm,
             bill.late_pay_charge_sw,
             bill.late_pay_charge_dt,
             bill.apay_cre_dt,
             bill.apay_amt,
             bill.apay_stop_user_id,
             bill.apay_stop_dttm,
             bill.apay_stop_amt,
             bill.apay_stop_cre_dt,
             bill.ilm_dt,
             bill.ilm_arch_sw,
             CASE
                 WHEN bill.cr_note_fr_bill_id = ' ' THEN 0
                 ELSE 1
             END AS cr_note_ind,
             CASE
                 WHEN bill.offcyc_bgen_id = ' ' THEN 0
                 ELSE 1
             END AS offcyc_bgen_ind,
             nvl( (
                Select
                  Sum(ft.cur_amt)
                From
                  ci_ft ft
                Where
                  ft.parent_id = bill.bill_id
                  and ft.ft_type_flg in ('BS','BX')
                GROUP BY
                     bill.bill_id
             ),0) AS bseg_amt,
             nvl( (
                 SELECT
                     COUNT(*)
                 FROM
                     ci_bseg bs
                 WHERE
                     bs.bill_id = bill.bill_id
                     AND bs.bseg_stat_flg = '10'
             ),0) AS incomplete_bseg_cnt,
             nvl( (
                 SELECT
                     COUNT(*)
                 FROM
                     ci_bseg bs
                 WHERE
                     bs.bill_id = bill.bill_id
                     AND bs.bseg_stat_flg = '20'
             ),0) AS error_bseg_cnt,
             nvl( (
                 SELECT
                     COUNT(*)
                 FROM
                     ci_bseg bs
                 WHERE
                     bs.bill_id = bill.bill_id
                     AND bs.bseg_stat_flg = '30'
             ),0) AS freezable_bseg_cnt,
             nvl( (
                 SELECT
                     COUNT(*)
                 FROM
                     ci_bseg bs
                 WHERE
                     bs.bill_id = bill.bill_id
                     AND bs.bseg_stat_flg = '40'
             ),0) AS pend_cancel_bseg_cnt,
             nvl( (
                 SELECT
                     COUNT(*)
                 FROM
                     ci_bseg bs
                 WHERE
                     bs.bill_id = bill.bill_id
                     AND bs.bseg_stat_flg = '50'
             ),0) AS frozen_bseg_cnt,
             nvl( (
                 SELECT
                     COUNT(*)
                 FROM
                     ci_bseg bs
                 WHERE
                     bs.bill_id = bill.bill_id
                     AND bs.bseg_stat_flg = '60'
             ),0) AS canceled_bseg_cnt,
             nvl( (
                 SELECT
                     SUM(ft.cur_amt)
                 FROM
                     ci_ft ft,ci_bseg bs
                 WHERE
                    ft.parent_id = bill.bill_id
                     AND bs.bseg_id = ft.sibling_id
                     AND bs.est_sw = 'Y'
                     AND ft.ft_type_flg IN(
                         'BS','BX'
                     )
                 GROUP BY
                     bill.bill_id
             ),0) AS est_bseg_amt,
 nvl( (
                 SELECT
                     COUNT(*)
                 FROM
                     ci_bseg bs
                 WHERE
                     bs.bill_id = bill.bill_id
                     AND bs.bseg_stat_flg <> '60'
                     AND bs.est_sw = 'Y'
             ),0) AS est_bseg_cnt,
             nvl( (
                 SELECT
                     SUM(ft.cur_amt)
                 FROM
                     ci_ft ft
                 WHERE
                     ft.ft_type_flg IN(
                         'AD','AX'
                     )
                     AND ft.correction_sw = 'N'
                     AND ft.bill_id = bill.bill_id
                 GROUP BY
                     bill_id
             ),0) AS adj_amt,
             nvl( (
                 SELECT
                     COUNT(*)
                 FROM
                     ci_adj ad,ci_ft ft
                 WHERE
                     ft.bill_id = bill.bill_id
                     AND ft.ft_type_flg IN(
                         'AD','AX'
                     )
                     AND ad.adj_id = ft.sibling_id
                     AND ad.adj_status_flg = '50'
                 GROUP BY
                     ft.bill_id
             ),0) AS frozen_adj_cnt,
             nvl( (
                 SELECT
                     COUNT(*)
                 FROM
                     ci_adj ad,ci_ft ft
                 WHERE
                     ft.bill_id = bill.bill_id
                     AND ft.ft_type_flg IN(
                         'AD','AX'
                     )
                     AND ad.adj_id = ft.sibling_id
                     AND ad.adj_status_flg = '60'
                 GROUP BY
                     ft.bill_id
             ),0) AS canceled_adj_cnt,
             nvl( (
                 SELECT
                     COUNT(*)
                 FROM
                     ci_bill_excp be
                 WHERE
                     be.bill_id = bill.bill_id
                 GROUP BY
                     be.bill_id
             ),0) AS bill_excp_cnt,
            nvl( (
                 SELECT
                     COUNT(*)
                 FROM
                     ci_bseg_excp bse,ci_bseg bs
                 WHERE
                     bs.bill_id = bill.bill_id
                     AND bse.bseg_id = bs.bseg_id
                 GROUP BY
                     bs.bill_id
             ),0) AS bseg_excp_cnt,
             nvl(days_completed_after_win_start,0) AS days_completed_after_win_start,
             nvl(completed_within_win_ind,0) AS completed_within_win_ind,
             nvl(completed_outside_win_ind,0) AS completed_outside_win_ind,
             nvl(days_completed_after_win_end,0) AS days_completed_after_win_end,
             nvl(days_created_after_win_start,0) AS days_created_after_win_start,
             nvl(bill_win_open_ind,0) AS bill_win_open_ind,
             nvl(days_before_bill_win_closes,0) AS days_before_bill_win_closes,
             bkt.bkt_config_cd    AS bkt_compl_days_in_win_cd,
             bkt.seq_num          AS bkt_compl_days_in_win_seq_num,
             bbwc.bkt_config_cd   AS bkt_days_win_closes_cd,
             bbwc.seq_num         AS bkt_days_win_closes_seq_num,
             nvl( (
                 SELECT
                     COUNT(*)
                 FROM
                     ci_case ca,ci_case_char cc
                 WHERE
                     TRIM(ca.case_type_cd) IN(
                          SELECT
                              TRIM(ex.char_val_fk1)
                          FROM
                              f1_ext_lookup_val_char ex
                          WHERE
                              ex.bus_obj_cd = 'F1-AVAnalyticsOptions'
                              AND ex.char_type_cd = 'C1-CSTYP'
                      )
                      AND NOT TRIM(ca.case_status_cd) IN(
                          SELECT
                              TRIM(ex.adhoc_char_val)
                          FROM
                              f1_ext_lookup_val_char ex
                          WHERE
                              ex.bus_obj_cd = 'F1-AVAnalyticsOptions'
                              AND ex.char_type_cd = 'C1-CASTA'
                      )
                      AND cc.case_id = ca.case_id
                      AND TRIM(cc.char_type_cd) = (
                          SELECT
                              TRIM(ex.char_val_fk1)
                          FROM
                              f1_ext_lookup_val_char ex
                          WHERE
                              ex.bus_obj_cd = 'F1-AVAnalyticsOptions'
                              AND ex.char_type_cd = 'C1-BICHT'
                      )
                      AND cc.srch_char_val = bill.bill_id
              ),0) AS high_bill_cases_cnt,
             CASE
                 WHEN bill.bill_stat_flg = 'P' THEN 1
                 ELSE 0
             END AS pending_bill_cnt,
             CASE
                 WHEN bill.bill_stat_flg = 'C' THEN 1
                 ELSE 0
             END AS completed_bill_cnt,
             1 AS bill_cnt
         FROM
             ci_bill bill
             JOIN ci_acct_per ap ON ap.main_cust_sw = 'Y'
                                    AND ap.acct_id = bill.acct_id
             LEFT OUTER JOIN (
                 SELECT
                     bi.bill_id,
                     CASE
                         WHEN bi.bill_stat_flg = 'C' THEN trunc(bi.complete_dttm) + 1 - bcs.win_start_dt
                         ELSE 0
                     END AS days_completed_after_win_start,
                     CASE
                         WHEN bi.bill_stat_flg = 'C'
                              AND trunc(bi.complete_dttm) <= bcs.win_end_dt THEN 1
                         ELSE 0
                     END AS completed_within_win_ind,
                     CASE
                         WHEN bi.bill_stat_flg = 'C'
                              AND trunc(bi.complete_dttm) > bcs.win_end_dt THEN 1
                         ELSE 0
                     END AS completed_outside_win_ind,
                     CASE
                         WHEN bi.bill_stat_flg = 'C'
                              AND trunc(bi.complete_dttm) > bcs.win_end_dt THEN trunc(bi.complete_dttm) + 1 - bcs.win_end_dt
                         ELSE 0
                     END AS days_completed_after_win_end,
                     trunc(bi.cre_dttm) + 1 - bcs.win_start_dt AS days_created_after_win_start,
                     CASE
                         WHEN current_date <= bcs.win_end_dt THEN 1
                         ELSE 0
                     END AS bill_win_open_ind,
                     CASE
                         WHEN current_date <= bcs.win_end_dt THEN bcs.win_end_dt - current_date
                         ELSE 0
                     END AS days_before_bill_win_closes,
                     bcs.win_end_dt,
                     bcs.accounting_dt
                 FROM
                     ci_bill bi,
                     ci_bill_cyc_sch bcs
                 WHERE
                     bcs.bill_cyc_cd = bi.bill_cyc_cd
                     AND bcs.win_start_dt = bi.win_start_dt
             ) bw ON bw.bill_id = bill.bill_id
             LEFT OUTER JOIN (
                 SELECT
                     vl.bkt_config_cd,
                     vl.seq_num,
                     vl.bkt_start_range,
                     vl.bkt_end_range
                 FROM
                     f1_bkt_config_val vl,
                     f1_bkt_config bk
                 WHERE
                     bk.bus_obj_cd = 'C1-BillingDayInWindow'
                     AND vl.bkt_config_cd = bk.bkt_config_cd
                     AND bkt_type_cd = 'C1IW'
             ) bkt ON completed_within_win_ind = 1
                      AND days_completed_after_win_start > bkt.bkt_start_range
                      AND days_completed_after_win_start <= bkt.bkt_end_range
             LEFT OUTER JOIN (
                 SELECT
                     vl.bkt_config_cd,
                     vl.seq_num,
                     vl.bkt_start_range,
                     vl.bkt_end_range
                 FROM
                     f1_bkt_config_val vl,
                     f1_bkt_config bk
                 WHERE
                     bk.bus_obj_cd = 'C1-DaysBeforeBillWindowCloses'
                     AND vl.bkt_config_cd = bk.bkt_config_cd
                     AND bkt_type_cd = 'C1OP'
             ) bbwc ON bill_win_open_ind = 1
                       AND days_before_bill_win_closes > bbwc.bkt_start_range
                       AND days_before_bill_win_closes <= bbwc.bkt_end_range
     )
      WHERE cre_dttm  between add_months(current_date, -60) and current_date
