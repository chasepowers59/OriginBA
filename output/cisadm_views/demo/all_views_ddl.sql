-- CISADM view DDL export
-- Client: demo
-- Schema: CISADM
-- Exported: 2026-06-18 19:32:55 UTC
-- View count: 282

-- ----- C1_BI_BILLED_USAGE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_BI_BILLED_USAGE_VW" ("BSEG_ID", "RS_CD", "UOM_CD", "TOU_CD", "SQI_CD", "BILL_ID", "FT_TYPE_FLG", "ACCOUNTING_DT", "FREEZE_DTTM", "BSEG_START_DT", "BSEG_END_DT", "BSEG_DAYS", "BILL_CRE_DTTM", "SA_ID", "ACCT_ID", "PREM_ID", "PER_ID", "ILM_DT", "ILM_ARCH_SW", "BILL_SQ", "BILLED_AMT", "BILL_LAG_DAYS", "BSEG_SQ_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
      bsq.bseg_id,
      bsq.rs_cd,
      bsq.uom_cd,
      bsq.tou_cd,
      bsq.sqi_cd,
      bs.bill_id,
      ft.ft_type_flg,
      ft.accounting_dt,
      ft.freeze_dttm,
      bs.start_dt       AS bseg_start_dt,
      bs.end_dt         AS bseg_end_dt,
      ( bs.end_dt - bs.start_dt ) AS bseg_days,
      bi.cre_dttm as bill_cre_dttm,
      sa.sa_id,
      sa.acct_id,
      sa.char_prem_id   AS prem_id,
      acp.per_id,
	  bi.ilm_dt,
      bi.ilm_arch_sw,
      case when ft.ft_type_flg = 'BS'
         then bsq.bill_sq
         else bsq.bill_sq * -1
         end as bill_sq,
      case when ft.ft_type_flg = 'BS'
        then bsq.billed_amt
        else bsq.billed_amt * -1
        end as billed_amt,
      trunc(ft.freeze_dttm) - bs.end_dt AS bill_lag_days,
      1 AS bseg_sq_cnt
  FROM
      ci_ft ft,
      ci_bseg bs,
      ci_sa sa,
      ci_acct_per acp,
      ci_bill bi,
      (
          SELECT
              bseg_id,
              rs_cd,
              uom_cd,
              tou_cd,
              sqi_cd,
              SUM(final_reg_qty) AS bill_sq,
              SUM(billed_amt) AS billed_amt
          FROM
              (
                  SELECT
                      bch.bseg_id,
                      bch.rs_cd,
                      sq.uom_cd,
                      sq.tou_cd,
                      sq.sqi_cd,
                      br.final_reg_qty,
                      SUM(amt.calc_amt) AS billed_amt
                  FROM
                      ci_bseg_sq sq,
                      ci_bseg_calc bch,
                      ci_bseg_read br,
                      ci_bseg_calc_ln amt
                  WHERE
                      bch.bseg_id = sq.bseg_id
                      AND br.bseg_id = bch.bseg_id
                      AND br.uom_cd = sq.uom_cd
                      AND br.final_tou_cd = sq.tou_cd
                      AND br.sqi_cd = sq.sqi_cd
                      AND trunc(br.start_read_dttm) >= bch.start_dt - 1
                      AND trunc(br.end_read_dttm) <= bch.end_dt + 1
                      AND br.usage_flg = 'S'
                      AND br.sp_id = ' '
                      AND amt.bseg_id = sq.bseg_id
                      AND amt.uom_cd = sq.uom_cd
                      AND amt.tou_cd = sq.tou_cd
                      AND amt.sqi_cd = sq.sqi_cd
                      AND amt.header_seq = bch.header_seq
                      AND amt.prt_sw = 'Y'
                  GROUP BY
                      bch.bseg_id,
                      bch.rs_cd,
                      sq.uom_cd,
                      sq.tou_cd,
                      sq.sqi_cd,
                      br.final_reg_qty
              )
          GROUP BY
              bseg_id,
              rs_cd,
              uom_cd,
              tou_cd,
              sqi_cd
        ) bsq
  WHERE
      ft.freeze_sw = 'Y'
      AND ft.ft_type_flg IN (          'BS',          'BX'      )
      AND bsq.bseg_id = ft.sibling_id
      AND bs.bseg_id = bsq.bseg_id
      AND sa.sa_id = bs.sa_id
      AND acp.acct_id = sa.acct_id
      AND acp.main_cust_sw = 'Y'
      AND bi.bill_id = bs.bill_id
      AND bi.cre_dttm  between add_months(current_date, -60) and current_date;

-- ----- C1_BI_BILL_DAY_IN_WIN_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_BI_BILL_DAY_IN_WIN_VW" ("BKT_CONFIG_CD", "SEQ_NUM", "BKT_START_RANGE", "BKT_END_RANGE", "RANGE_DESCR", "BILL_WINDOW_CAT_FLG", "BILL_WINDOW_CAT_DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
      vl.bkt_config_cd,
      vl.seq_num,
      vl.bkt_start_range,
      vl.bkt_end_range,
      vll.descr   AS range_descr,
      vl.bkt_val_type_cd,
      lv.descr    AS bill_window_cat_descr
  FROM
      f1_bkt_config_val vl
      JOIN f1_bkt_config bk ON bk.bus_obj_cd = 'C1-BillingDayInWindow'
                               AND bk.bkt_config_cd = vl.bkt_config_cd
                               AND bk.bkt_type_cd = 'C1IW'
      JOIN f1_bkt_config_val_l vll ON vll.bkt_config_cd = vl.bkt_config_cd
                                      AND vll.seq_num = vl.seq_num
                                      AND vll.language_cd = 'ENG'
      LEFT OUTER JOIN ci_lookup_val_l lv ON lv.field_name = 'BILL_WINDOW_CAT_FLG'
                                      AND lv.field_value = vl.bkt_val_type_cd
                                      AND lv.language_cd = 'ENG';

-- ----- C1_BI_BILL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_BI_BILL_VW" ("BILL_ID", "BILL_CYC_CD", "WIN_START_DT", "WIN_END_DT", "ACCOUNTING_DT", "ACCT_ID", "PER_ID", "BILL_STAT_FLG", "BILL_DT", "DUE_DT", "CRE_DTTM", "COMPLETE_DTTM", "LATE_PAY_CHARGE_SW", "LATE_PAY_CHARGE_DT", "APAY_CRE_DT", "APAY_AMT", "APAY_STOP_USER_ID", "APAY_STOP_DTTM", "APAY_STOP_AMT", "APAY_STOP_CRE_DT", "ILM_DT", "ILM_ARCH_SW", "CR_NOTE_IND", "OFFCYC_BGEN_IND", "BILL_AMT", "BSEG_AMT", "INCOMPLETE_BSEG_CNT", "ERROR_BSEG_CNT", "FREEZABLE_BSEG_CNT", "PEND_CANCEL_BSEG_CNT", "FROZEN_BSEG_CNT", "CANCELED_BSEG_CNT", "EST_BSEG_AMT", "EST_BSEG_CNT", "ADJ_AMT", "FROZEN_ADJ_CNT", "CANCELED_ADJ_CNT", "BILL_EXCP_CNT", "BSEG_EXCP_CNT", "DAYS_COMPLETED_AFTER_WIN_START", "COMPLETED_WITHIN_WIN_IND", "COMPLETED_OUTSIDE_WIN_IND", "DAYS_COMPLETED_AFTER_WIN_END", "DAYS_CREATED_AFTER_WIN_START", "BILL_WIN_OPEN_IND", "DAYS_BEFORE_BILL_WIN_CLOSES", "BKT_COMPL_DAYS_IN_WIN_CD", "BKT_COMPL_DAYS_IN_WIN_SEQ_NUM", "BKT_DAYS_WIN_CLOSES_CD", "BKT_DAYS_WIN_CLOSES_SEQ_NUM", "HIGH_BILL_CASE_CNT", "PENDING_BILL_CNT", "COMPLETED_BILL_CNT", "BILL_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
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
      WHERE cre_dttm  between add_months(current_date, -60) and current_date;

-- ----- C1_BI_COLLEVTTYPE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_BI_COLLEVTTYPE_VW" ("COLLECTIBLE_EVT_TYPE_CD", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
      cast(concat('C',cl.coll_evt_typ_cd) as char(12)) collectible_evt_type_cd,
      cl.descr
  FROM
      ci_coll_evt_typ_l cl
  WHERE
      language_cd = 'ENG'
  UNION
  SELECT
      cast(concat('S',sl.sev_evt_type_cd) as char(12)) collectible_evt_type_cd,
      sl.descr
  FROM
      ci_sev_evt_type_l sl
  WHERE
      language_cd = 'ENG';

-- ----- C1_BI_COLLPROC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_BI_COLLPROC_VW" ("COLL_PROC_ID", "COLL_PROC_TMPL_CD", "COLL_CL_CNTL_CD", "ACCT_ID", "PER_ID", "CURRENCY_CD", "CRE_DTTM", "COLL_STATUS_FLG", "COLL_STAT_RSN_FLG", "COLL_CAT_PRIO_FLG", "CRIT_PRIO_FLG", "COLL_ARS_DT", "COMMENTS", "OVERALL_COLLECTIBLE_STAT_FLG", "COLL_PROC_COMPL_DT", "COLLECTIBLE_PROC_COMPL_DT", "CURR_COLL_EVT_TYP_CD", "CURR_SEV_EVT_TYPE_CD", "CURR_COLLECTIBLE_EVT_TYPE_CD", "EFF_COLL_EVT_TYP_CD", "EFF_SEV_EVT_TYPE_CD", "EFF_COLLECTIBLE_EVT_TYPE_CD", "ACTIVE_COLL_PROC_CNT", "INACTIVE_COLL_PROC_CNT", "COMPL_COLL_PROC_CNT", "CANCL_SYS_COLL_PROC_CNT", "CANCL_USER_COLL_PROC_CNT", "ACTIVE_SEV_PROC_CNT", "INACTIVE_SEV_PROC_CNT", "SEV_PROC_CNT", "COLL_PROC_CNT", "OVERALL_ACTIVE_COLL_CNT", "OVERALL_EFF_COLL_CNT", "OVERALL_INEFF_COLL_CNT", "INACTIVE_COLLECTIBLE_CNT", "CURR_ARS_AMT", "ARS_AT_START_AMT", "ARS_AT_END_AMT", "COLLECTIBLE_ARS_AT_END_AMT", "ARS_DIFF_AMT", "COLLECTIBLE_ARS_DIFF_AMT", "COLL_PROC_DURATION", "COLLECTIBLE_DURATION") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT coll_proc_id,
  coll_proc_tmpl_cd,
  coll_cl_cntl_cd,
  acct_id,
  per_id,
  currency_cd,
  cre_dttm,
  coll_status_flg,
  coll_stat_rsn_flg,
  coll_cat_prio_flg,
  crit_prio_flg,
  coll_ars_dt,
  comments,
  CAST(overall_collectible_stat_flg AS CHAR(4)) overall_collectible_stat_flg,
  coll_proc_compl_dt,
  collectible_proc_compl_dt,
  CAST(NVL(curr_coll_evt_typ_cd, ' ') AS CHAR(12)) curr_coll_evt_typ_cd,
  CAST(NVL(curr_sev_evt_type_cd, ' ') AS CHAR(12)) curr_sev_evt_type_cd,
  CAST(NVL(collectible_evt_type_cd, ' ') AS CHAR(12)) CURR_COLLECTIBLE_EVT_TYPE_CD,
  CAST(NVL(eff_coll_evt_typ_cd, ' ') AS CHAR(12)) eff_coll_evt_typ_cd,
  CAST(NVL(eff_sev_evt_type_cd, ' ') AS CHAR(12)) eff_sev_evt_type_cd,
  CAST(NVL(eff_collectible_evt_type_cd, ' ') AS CHAR(12)) eff_collectible_evt_type_cd,
  active_coll_proc_cnt,
  inactive_coll_proc_cnt,
  compl_coll_proc_cnt,
  cancl_sys_coll_proc_cnt,
  cancl_user_coll_proc_cnt,
  active_sev_proc_cnt,
  inactive_sev_proc_cnt,
  sev_proc_cnt,
  coll_proc_cnt,
  overall_active_coll_cnt,
  overall_eff_coll_cnt,
  overall_ineff_coll_cnt,
  overall_eff_coll_cnt + overall_ineff_coll_cnt as inactive_collectible_cnt,
  CAST (curr_ars_amt AS                                  NUMBER(15,2)) curr_ars_amt,
  CAST (ars_at_start_amt AS                              NUMBER(15,2)) ars_at_start_amt,
  CAST (
  CASE
        WHEN ars_at_end_amt < 0 or overall_active_coll_cnt = 1 THEN 0
        ELSE ars_at_end_amt
  END AS NUMBER(15,2)) ars_at_end_amt,
  CAST (
  CASE
        WHEN collectible_ars_at_end_amt < 0 or overall_active_coll_cnt = 1 THEN 0
        ELSE collectible_ars_at_end_amt
  END AS NUMBER(15,2)) collectible_ars_at_end_amt,
  CAST (ars_at_start_amt - ars_at_end_amt AS             NUMBER(15,2)) ars_diff_amt,
  CAST (ars_at_start_amt - collectible_ars_at_end_amt AS NUMBER(15,2)) collectible_ars_diff_amt,
  CAST (coll_proc_duration AS                            NUMBER(5,0)) coll_proc_duration,
  CAST (
  CASE
    WHEN coll_status_flg = '20' and collectible_proc_compl_dt is not NULL THEN round(collectible_proc_compl_dt - trunc(cre_dttm),0)
    ELSE ROUND(CURRENT_DATE              - cre_dttm,0)
    END AS NUMBER(5,0)) collectible_duration
FROM
  (SELECT coll_proc_id,
    coll_proc_tmpl_cd,
    coll_cl_cntl_cd,
    acct_id,
    per_id,
    currency_cd,
    cre_dttm,
    coll_status_flg,
    coll_stat_rsn_flg,
    coll_cat_prio_flg,
    crit_prio_flg,
    coll_ars_dt,
    comments,
    overall_collectible_stat_flg,
    coll_proc_compl_dt,
    CASE
      WHEN overall_collectible_stat_flg <> 'C1AC'
      THEN NVL(NVL(latest_se_completion_dt,latest_ce_completion_dt),TRUNC(cre_dttm ) )
      ELSE NULL
    END AS collectible_proc_compl_dt,
    curr_coll_evt_typ_cd,
    curr_sev_evt_type_cd,
    CASE
      WHEN curr_sev_evt_type_cd <> ' '
      THEN concat('S',curr_sev_evt_type_cd)
      WHEN curr_coll_evt_typ_cd <> ' '
      THEN concat('C',curr_coll_evt_typ_cd)
      ELSE ' '
    END AS collectible_evt_type_cd,
    CASE
      WHEN overall_collectible_stat_flg = 'C1EF'
      AND sev_proc_cnt                  = 0
      THEN last_comp_coll_evt_typ_cd
      ELSE NULL
    END AS eff_coll_evt_typ_cd,
    CASE
      WHEN overall_collectible_stat_flg = 'C1EF'
      AND sev_proc_cnt                  > 0
      THEN last_comp_sev_evt_type_cd
      ELSE NULL
    END AS eff_sev_evt_type_cd,
    CASE
      WHEN overall_collectible_stat_flg = 'C1EF'
      AND last_comp_sev_evt_type_cd    <> ' '
      THEN concat('S',last_comp_sev_evt_type_cd)
      WHEN overall_collectible_stat_flg = 'C1EF'
      AND last_comp_coll_evt_typ_cd    <> ' '
      THEN concat('C',last_comp_coll_evt_typ_cd)
      ELSE ' '
    END AS eff_collectible_evt_type_cd,
    active_coll_proc_cnt,
    inactive_coll_proc_cnt,
    compl_coll_proc_cnt,
    cancl_sys_coll_proc_cnt,
    cancl_user_coll_proc_cnt,
    active_sev_proc_cnt,
    inactive_sev_proc_cnt,
    sev_proc_cnt,
    1 AS coll_proc_cnt,
    CASE
      WHEN overall_collectible_stat_flg = 'C1AC'
      THEN 1
      ELSE 0
    END AS overall_active_coll_cnt,
    CASE
      WHEN overall_collectible_stat_flg = 'C1EF'
      THEN 1
      ELSE 0
    END AS overall_eff_coll_cnt,
    CASE
      WHEN overall_collectible_stat_flg = 'C1IN'
      THEN 1
      ELSE 0
    END  AS overall_ineff_coll_cnt,
    CASE
      WHEN overall_collectible_stat_flg = 'C1AC' THEN  ( debit_amt + current_credit_amt )
      ELSE 0
      END AS curr_ars_amt,
    ( debit_amt + at_start_credit_amt ) AS ars_at_start_amt,
    CASE
      WHEN coll_status_flg         = '20'
      AND latest_ce_completion_dt IS NOT NULL
      THEN ( debit_amt + NVL(ce_compl_at_end_credit_amt,0) )
      WHEN coll_status_flg = '20'
      THEN ( debit_amt + at_start_credit_amt )
      ELSE 0
    END AS ars_at_end_amt,
    CASE
      WHEN coll_status_flg         = '20'
      AND non_canc_sp_cnt          = 0
      AND latest_se_completion_dt IS NOT NULL
      THEN ( debit_amt + NVL(se_compl_at_end_credit_amt,0) )
      WHEN coll_status_flg         = '20'
      AND latest_ce_completion_dt IS NOT NULL
      THEN ( debit_amt + NVL(ce_compl_at_end_credit_amt,0) )
      WHEN coll_status_flg = '20' 
      THEN ( debit_amt + at_start_credit_amt )
      ELSE 0
    END AS collectible_ars_at_end_amt,
    CASE
      WHEN coll_status_flg = '20'
      THEN ROUND(latest_ce_completion_dt - TRUNC(cre_dttm),0)
      ELSE ROUND(CURRENT_DATE            - cre_dttm,0)
    END AS coll_proc_duration
  FROM
    (SELECT coll_proc_id,
      coll_proc_tmpl_cd,
      coll_cl_cntl_cd,
      acct_id,
      per_id,
      currency_cd,
      cre_dttm,
      coll_status_flg,
      coll_stat_rsn_flg,
      coll_cat_prio_flg,
      crit_prio_flg,
      coll_ars_dt,
      ars_amt,
      comments,
      CASE
        WHEN coll_status_flg = '10'
        THEN 'C1AC'
        WHEN coll_stat_rsn_flg  = '20'
        AND active_sev_proc_cnt > 0
        THEN 'C1AC'
        WHEN coll_stat_rsn_flg IN ( '30', '40' )
        THEN 'C1EF'
        WHEN ( coll_stat_rsn_flg = '20'
        AND non_canc_sp_cnt      = 0 )
        THEN 'C1EF'
        ELSE 'C1IN'
      END AS overall_collectible_stat_flg,
      CASE
        WHEN coll_status_flg = '20'
        THEN NVL(latest_ce_completion_dt,TRUNC(cre_dttm) )
        ELSE NULL
      END AS coll_proc_compl_dt,
      latest_ce_completion_dt,
      latest_se_completion_dt,
      CASE
        WHEN coll_status_flg = '10'
        THEN curr_coll_evt_typ_cd
        ELSE ' '
      END AS curr_coll_evt_typ_cd,
      CASE
        WHEN coll_stat_rsn_flg = '20'
        THEN curr_sev_evt_type_cd
        ELSE ' '
      END AS curr_sev_evt_type_cd,
      last_comp_coll_evt_typ_cd,
      last_comp_sev_evt_type_cd,
      active_coll_proc_cnt,
      inactive_coll_proc_cnt,
      compl_coll_proc_cnt,
      cancl_sys_coll_proc_cnt,
      cancl_user_coll_proc_cnt,
      active_sev_proc_cnt,
      inactive_sev_proc_cnt,
      non_canc_sp_cnt,
      active_sev_proc_cnt + inactive_sev_proc_cnt AS sev_proc_cnt,
      NVL(debit_amt,0)                            AS debit_amt,
      NVL(current_credit_amt,0)                   AS current_credit_amt,
      NVL(at_start_credit_amt,0)                  AS at_start_credit_amt,
      CASE
        WHEN latest_ce_completion_dt IS NOT NULL
        THEN
          (SELECT SUM(cur_amt)
          FROM ci_ft ft,
            ci_coll_proc_sa csa,
            ci_acct ac,
            ci_cust_cl cc
          WHERE csa.coll_proc_id            = a.coll_proc_id
          AND csa.coll_sa_stat_flg          = '10'
          AND ac.acct_id                    = a.acct_id
          AND cc.cust_cl_cd                 = ac.cust_cl_cd
          AND ft.sa_id                      = csa.sa_id
          AND ft.redundant_sw               = 'N'
          AND ft.cur_amt                   <= 0
          AND ft.freeze_sw                  = 'Y'
          AND ( ft.ars_dt                  IS NOT NULL
          AND ft.ars_dt                    <= a.latest_ce_completion_dt )
          AND ( ( cc.open_item_sw           = 'N'
          AND ft.not_in_ars_sw             <> 'Y' )
          OR ( cc.open_item_sw              = 'Y'
          AND ( SUBSTR(ft.match_evt_id,1,1) = ' '
          OR ft.match_evt_id               IN
            (SELECT me.match_evt_id
            FROM ci_match_evt me
            WHERE me.acct_id       = a.acct_id
            AND me.dispute_sw      = 'N'
            AND me.mevt_status_flg = 'O'
            ) ) ) )
          )
        ELSE 0
      END AS ce_compl_at_end_credit_amt,
      CASE
        WHEN latest_se_completion_dt IS NOT NULL
        THEN
          (SELECT SUM(cur_amt)
          FROM ci_ft ft,
            ci_coll_proc_sa csa,
            ci_acct ac,
            ci_cust_cl cc
          WHERE csa.coll_proc_id            = a.coll_proc_id
          AND csa.coll_sa_stat_flg          = '10'
          AND ac.acct_id                    = a.acct_id
          AND cc.cust_cl_cd                 = ac.cust_cl_cd
          AND ft.sa_id                      = csa.sa_id
          AND ft.redundant_sw               = 'N'
          AND ft.cur_amt                   <= 0
          AND ft.freeze_sw                  = 'Y'
          AND ( ft.ars_dt                  IS NOT NULL
          AND ft.ars_dt                    <= a.latest_se_completion_dt )
          AND ( ( cc.open_item_sw           = 'N'
          AND ft.not_in_ars_sw             <> 'Y' )
          OR ( cc.open_item_sw              = 'Y'
          AND ( SUBSTR(ft.match_evt_id,1,1) = ' '
          OR ft.match_evt_id               IN
            (SELECT me.match_evt_id
            FROM ci_match_evt me
            WHERE me.acct_id       = a.acct_id
            AND me.dispute_sw      = 'N'
            AND me.mevt_status_flg = 'O'
            ) ) ) )
          )
        ELSE 0
      END                     AS se_compl_at_end_credit_amt
    FROM
      (SELECT cp.coll_proc_id,
        cp.coll_proc_tmpl_cd,
        cp.coll_cl_cntl_cd,
        cp.acct_id,
        ap.per_id,
        cp.currency_cd,
        cp.cre_dttm,
        cp.coll_status_flg,
        cp.coll_stat_rsn_flg,
        cp.coll_cat_prio_flg,
        cp.crit_prio_flg,
        cp.coll_ars_dt,
        cp.ars_amt,
        cp.comments,
        (SELECT COUNT(*)
        FROM ci_sev_proc sp
        WHERE sp.coll_proc_id = cp.coll_proc_id
        AND sp.sev_status_flg = '10'
        ) AS active_sev_proc_cnt,
        (SELECT COUNT(*)
        FROM ci_sev_proc sp
        WHERE sp.coll_proc_id = cp.coll_proc_id
        AND sp.sev_status_flg = '20'
        ) AS inactive_sev_proc_cnt,
        (SELECT COUNT(*)
        FROM ci_sev_proc sp
        WHERE sp.coll_proc_id        = cp.coll_proc_id
        AND NOT sp.sev_stat_rsn_flg IN ( '30', '40' )
        ) AS non_canc_sp_cnt,
        (SELECT COUNT(*)
        FROM ci_sev_proc sp
        WHERE sp.coll_proc_id   = cp.coll_proc_id
        AND sp.sev_stat_rsn_flg = '20'
        ) AS comp_sp_cnt,
        (SELECT MAX(ce.completion_dt)
        FROM ci_coll_evt ce
        WHERE ce.coll_proc_id = cp.coll_proc_id
        ) AS latest_ce_completion_dt,
        (SELECT MAX(se.completion_dt)
        FROM ci_sev_evt se,
          ci_sev_proc sp
        WHERE sp.coll_proc_id = cp.coll_proc_id
        AND se.sev_proc_id    = sp.sev_proc_id
        ) AS latest_se_completion_dt,
        (SELECT ce.coll_evt_typ_cd
        FROM ci_coll_evt ce
        WHERE ce.coll_proc_id    = cp.coll_proc_id
        AND ce.coll_evt_stat_flg = '10'
        AND ce.evt_seq           =
          (SELECT MIN(ce2.evt_seq)
          FROM ci_coll_evt ce2
          WHERE ce2.coll_proc_id    = ce.coll_proc_id
          AND ce2.coll_evt_stat_flg = '10'
          )
        ) AS curr_coll_evt_typ_cd,
        (SELECT MIN(se.sev_evt_type_cd)
        FROM ci_sev_evt se,
          ci_sev_proc sp
        WHERE sp.coll_proc_id   = cp.coll_proc_id
        AND se.sev_proc_id      = sp.sev_proc_id
        AND se.sev_evt_stat_flg = '10'
        AND se.evt_seq          =
          (SELECT MIN(se2.evt_seq)
          FROM ci_sev_evt se2
          WHERE se2.sev_proc_id    = se.sev_proc_id
          AND se2.sev_evt_stat_flg = '10'
          )
        ) AS curr_sev_evt_type_cd,
        (SELECT coll_evt_typ_cd
        FROM ci_coll_evt ce
        WHERE ce.coll_proc_id    = cp.coll_proc_id
        AND ce.coll_evt_stat_flg = '30'
        AND ce.evt_seq           =
          (SELECT MAX(ce2.evt_seq)
          FROM ci_coll_evt ce2
          WHERE ce2.coll_proc_id    = ce.coll_proc_id
          AND ce2.coll_evt_stat_flg = '30'
          )
        ) AS last_comp_coll_evt_typ_cd,
        (SELECT MIN(se.sev_evt_type_cd)
        FROM ci_sev_evt se,
          ci_sev_proc sp
        WHERE sp.coll_proc_id   = cp.coll_proc_id
        AND se.sev_proc_id      = sp.sev_proc_id
        AND se.sev_evt_stat_flg = '30'
        AND se.evt_seq          =
          (SELECT MAX(se2.evt_seq)
          FROM ci_sev_evt se2
          WHERE se2.sev_proc_id    = se.sev_proc_id
          AND se2.sev_evt_stat_flg = '30'
          )
        ) AS last_comp_sev_evt_type_cd,
        CASE
          WHEN coll_status_flg = '10'
          THEN 1
          ELSE 0
        END AS active_coll_proc_cnt,
        CASE
          WHEN coll_status_flg = '20'
          THEN 1
          ELSE 0
        END AS inactive_coll_proc_cnt,
        CASE
          WHEN coll_stat_rsn_flg = '20'
          THEN 1
          ELSE 0
        END AS compl_coll_proc_cnt,
        CASE
          WHEN coll_stat_rsn_flg = '30'
          THEN 1
          ELSE 0
        END AS cancl_sys_coll_proc_cnt,
        CASE
          WHEN coll_stat_rsn_flg = '40'
          THEN 1
          ELSE 0
        END AS cancl_user_coll_proc_cnt,
        (SELECT SUM(cur_amt)
        FROM ci_ft ft,
          ci_coll_proc_sa csa,
          ci_acct ac,
          ci_cust_cl cc
        WHERE csa.coll_proc_id            = cp.coll_proc_id
        AND csa.coll_sa_stat_flg          = '10'
        AND ac.acct_id                    = cp.acct_id
        AND cc.cust_cl_cd                 = ac.cust_cl_cd
        AND ft.sa_id                      = csa.sa_id
        AND ft.redundant_sw               = 'N'
        AND ft.cur_amt                    > 0
        AND ft.freeze_sw                  = 'Y'
        AND ( ft.ars_dt                  IS NOT NULL
        AND ft.ars_dt                    <= cp.coll_ars_dt )
        AND ( ( cc.open_item_sw           = 'N'
        AND ft.not_in_ars_sw             <> 'Y' )
        OR ( cc.open_item_sw              = 'Y'
        AND ( SUBSTR(ft.match_evt_id,1,1) = ' '
        OR ft.match_evt_id               IN
          (SELECT me.match_evt_id
          FROM ci_match_evt me
          WHERE me.acct_id       = cp.acct_id
          AND me.dispute_sw      = 'N'
          AND me.mevt_status_flg = 'O'
          ) ) ) )
        ) AS debit_amt,
        (SELECT SUM(cur_amt)
        FROM ci_ft ft,
          ci_coll_proc_sa csa,
          ci_acct ac,
          ci_cust_cl cc
        WHERE csa.coll_proc_id            = cp.coll_proc_id
        AND csa.coll_sa_stat_flg          = '10'
        AND ac.acct_id                    = cp.acct_id
        AND cc.cust_cl_cd                 = ac.cust_cl_cd
        AND ft.sa_id                      = csa.sa_id
        AND ft.redundant_sw               = 'N'
        AND ft.cur_amt                   <= 0
        AND ft.freeze_sw                  = 'Y'
        AND ( ft.ars_dt                  IS NOT NULL
        AND ft.ars_dt                    <= CURRENT_DATE )
        AND ( ( cc.open_item_sw           = 'N'
        AND ft.not_in_ars_sw             <> 'Y' )
        OR ( cc.open_item_sw              = 'Y'
        AND ( SUBSTR(ft.match_evt_id,1,1) = ' '
        OR ft.match_evt_id               IN
          (SELECT me.match_evt_id
          FROM ci_match_evt me
          WHERE me.acct_id       = cp.acct_id
          AND me.dispute_sw      = 'N'
          AND me.mevt_status_flg = 'O'
          ) ) ) )
        ) AS current_credit_amt,
        (SELECT SUM(cur_amt)
        FROM ci_ft ft,
          ci_coll_proc_sa csa,
          ci_acct ac,
          ci_cust_cl cc
        WHERE csa.coll_proc_id            = cp.coll_proc_id
        AND csa.coll_sa_stat_flg          = '10'
        AND ac.acct_id                    = cp.acct_id
        AND cc.cust_cl_cd                 = ac.cust_cl_cd
        AND ft.sa_id                      = csa.sa_id
        AND ft.redundant_sw               = 'N'
        AND ft.cur_amt                   <= 0
        AND ft.freeze_sw                  = 'Y'
        AND ( ft.ars_dt                  IS NOT NULL
        AND ft.ars_dt                    <= TRUNC(cp.cre_dttm) )
        AND ( ( cc.open_item_sw           = 'N'
        AND ft.not_in_ars_sw             <> 'Y' )
        OR ( cc.open_item_sw              = 'Y'
        AND ( SUBSTR(ft.match_evt_id,1,1) = ' '
        OR ft.match_evt_id               IN
          (SELECT me.match_evt_id
          FROM ci_match_evt me
          WHERE me.acct_id       = cp.acct_id
          AND me.dispute_sw      = 'N'
          AND me.mevt_status_flg = 'O'
          ) ) ) )
        ) AS at_start_credit_amt
      FROM ci_coll_proc cp,
        ci_acct_per ap
      WHERE ap.acct_id    = cp.acct_id
      AND ap.main_cust_sw = 'Y'
      ) a
    )
  );

-- ----- C1_BI_DAYS_B4_WIN_CLOSES_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_BI_DAYS_B4_WIN_CLOSES_VW" ("BKT_CONFIG_CD", "SEQ_NUM", "BKT_START_RANGE", "BKT_END_RANGE", "RANGE_DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
      vl.bkt_config_cd,
      vl.seq_num,
      vl.bkt_start_range,
      vl.bkt_end_range,
      vll.descr   AS range_descr
  FROM
      f1_bkt_config_val vl
      JOIN f1_bkt_config bk ON bk.bus_obj_cd = 'C1-DaysBeforeBillWindowCloses'
                               AND bk.bkt_config_cd = vl.bkt_config_cd
                               AND bk.bkt_type_cd = 'C1OP'
      JOIN f1_bkt_config_val_l vll ON vll.bkt_config_cd = vl.bkt_config_cd
                                      AND vll.seq_num = vl.seq_num
                                      AND vll.language_cd = 'ENG';

-- ----- C1_BI_FTGL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_BI_FTGL_VW" ("FT_ID", "GL_SEQ_NBR", "BILL_ID", "BSEG_ID", "ADJ_ID", "PAY_SEG_ID", "SA_ID", "ACCT_ID", "PREM_ID", "PER_ID", "RS_CD", "CURRENCY_CD", "FT_TYPE_FLG", "CRE_DTTM", "FREEZE_DTTM", "ACCOUNTING_DT", "DST_ID", "GL_DIVISION", "CIS_DIVISION", "GL_ACCT", "STATISTICS_CD", "FT_GL_DEBIT_AMT", "FT_GL_CREDIT_AMT", "FT_GL_AMT", "STATISTIC_AMT", "FT_GL_REV_AMT", "FT_GL_TAX_AMT", "BF_CHAR_TYPE_CD", "BF_CHAR_VAL", "FT_GL_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
     ftgl.ft_id,
     ftgl.gl_seq_nbr,
     ft.bill_id,
     CASE
         WHEN ft_type_flg IN (
             'BS',
             'BX'
         ) THEN ft.sibling_id
         ELSE NULL
     END AS bseg_id,
     CASE
         WHEN ft_type_flg IN (
             'AD',
             'AX'
         ) THEN ft.sibling_id
         ELSE NULL
     END AS adj_id,
     CASE
         WHEN ft_type_flg IN (
             'PS',
             'PX'
         ) THEN ft.sibling_id
         ELSE NULL
     END AS pay_seg_id,
     ft.sa_id,
     sa.acct_id,
     sa.char_prem_id   AS prem_id,
     ap.per_id,
     CASE
         WHEN ft.ft_type_flg IN (
             'BS',
             'BX'
         ) THEN (
             SELECT
                 ch.rs_cd
             FROM
                 ci_bseg_calc ch
             WHERE
                 ch.bseg_id = ft.sibling_id
                 AND ch.rs_cd <> ' '
                 AND ch.header_seq = 1
         )
         WHEN ft.ft_type_flg IN (
             'AD',
             'AX'
         ) THEN (
             SELECT
                 MIN(ac.rs_cd)
             FROM
                 ci_adj_calc_ln ac
             WHERE
                 ac.adj_id = ft.sibling_id
                 AND ac.rs_cd <> ' '
         )
         ELSE NULL
     END AS rs_cd,
     ft.currency_cd,
     ft.ft_type_flg,
     ft.cre_dttm,
     ft.freeze_dttm,
     ft.accounting_dt,
     ftgl.dst_id,
     ft.gl_division,
     ft.cis_division,
     ftgl.gl_acct,
     dce.statistics_cd,
     CASE
         WHEN ftgl.amount < 0 THEN ftgl.amount
         ELSE cast(0 as number(15,2))
     END AS ft_gl_debit_amount,
     CASE
         WHEN ftgl.amount > 0 THEN ftgl.amount
         ELSE cast(0 as number(15,2))
     END AS ft_gl_credit_amount,
     ftgl.amount       AS ft_gl_amount,
 ftgl.statistic_amount as statistic_amt,
     cast(nvl( (
         SELECT
             ftgl.amount *-1
         FROM
             ci_dst_cd_char ch
         WHERE
             ch.dst_id = ftgl.dst_id
             AND ch.effdt = (
                 SELECT
                     MAX(eff.effdt)
                 FROM
                     ci_dst_code_eff eff
                 WHERE
                     eff.dst_id = ftgl.dst_id
                     AND eff.effdt <= current_date
             )
             AND TRIM(ch.char_type_cd) = (
                 SELECT
                     TRIM(MIN(ex.char_val_fk1) )
                 FROM
                     f1_ext_lookup_val_char ex
                 WHERE
                     ex.bus_obj_cd = 'F1-AVAnalyticsOptions'
                     AND ex.char_type_cd = 'C1-GLACT'
             )
             AND TRIM(ch.char_val) IN(
                 SELECT
                     TRIM(ex.adhoc_char_val)
                 FROM
                     f1_ext_lookup_val_char ex
                 WHERE
                     ex.bus_obj_cd = 'F1-AVAnalyticsOptions'
                     AND ex.char_type_cd = 'C1-REVCH'
             )
     ),0) as number(15,2)) ft_gl_rev_amt,
     cast(nvl( (
         SELECT
             ftgl.amount *-1
         FROM
             ci_dst_cd_char ch
         WHERE
             ch.dst_id = ftgl.dst_id
             AND ch.effdt = (
                 SELECT
                     MAX(eff.effdt)
                 FROM
                     ci_dst_code_eff eff
                 WHERE
                     eff.dst_id = ftgl.dst_id
                     AND eff.effdt <= current_date
             )
             AND TRIM(ch.char_type_cd) = (
                 SELECT
                     TRIM(MIN(ex.char_val_fk1) )
                 FROM
                     f1_ext_lookup_val_char ex
                 WHERE
                     ex.bus_obj_cd = 'F1-AVAnalyticsOptions'
                     AND ex.char_type_cd = 'C1-GLACT'
             )
             AND TRIM(ch.char_val) IN(
                 SELECT
                     TRIM(ex.adhoc_char_val)
                 FROM
                     f1_ext_lookup_val_char ex
                 WHERE
                     ex.bus_obj_cd = 'F1-AVAnalyticsOptions'
                     AND ex.char_type_cd = 'C1-TAXCH'
             )
     ),0) as number(15,2)) ft_gl_tax_amt,
     ftgl.char_type_cd,
     ftgl.char_val,
 cast(1 AS char(1)) ft_gl_cnt
 FROM
     ci_ft_gl ftgl,
     ci_ft ft,
     ci_sa sa,
     ci_acct_per ap,
     ci_dst_code_eff dce
 WHERE
     ftgl.gl_acct <> ' '
     AND ft.ft_id = ftgl.ft_id
     AND sa.sa_id = ft.sa_id
     AND ap.acct_id = sa.acct_id
     AND ap.main_cust_sw = 'Y'
     AND dce.dst_id = ftgl.dst_id
     AND dce.effdt = (
         SELECT
             MAX(dce2.effdt)
         FROM
             ci_dst_code_eff dce2
         WHERE
             dce2.effdt <= ft.accounting_dt
             AND dce2.dst_id = ftgl.dst_id
     )
     AND ft.cre_dttm BETWEEN add_months(current_date,-60) AND current_date
 ORDER BY
     ftgl.ft_id,
     ftgl.gl_seq_nbr;

-- ----- C1_BI_FT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_BI_FT_VW" ("FT_ID", "BILL_ID", "BSEG_ID", "ADJ_ID", "PAY_SEG_ID", "SA_ID", "ACCT_ID", "PREM_ID", "PER_ID", "GL_DIVISION", "CIS_DIVISION", "FT_TYPE_FLG", "CUR_AMT", "TOT_AMT", "CRE_DTTM", "FREEZE_USER_ID", "FREEZE_DTTM", "ACCOUNTING_DT", "ARS_DT", "RS_CD", "FT_GL_REV_AMT", "FT_GL_TAX_AMT", "FT_OTHER_AMT", "FT_CNT", "XFER_TO_GL_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
      ft_id,
      bill_id,
      bseg_id,
      adj_id,
      pay_seg_id,
      sa_id,
      acct_id,
      prem_id,
      per_id,
      gl_division,
      cis_division,
      ft_type_flg,
      cur_amt,
      tot_amt,
      cre_dttm,
      freeze_user_id,
      freeze_dttm,
      accounting_dt,
      ars_dt,
      rs_cd,
      cast(ft_gl_rev_amt as number(15,2)) ft_gl_rev_amt,
      cast(ft_gl_tax_amt as number (15,2)) ft_gl_tax_amt,
    cast((tot_amt - ft_gl_rev_amt - ft_gl_tax_amt) as number (15,2)) as ft_other_amt,
  cast(1 AS number(1,0)) ft_cnt,
      XFER_TO_GL_DT
  FROM
      (
          SELECT
              ft.ft_id,
              ft.bill_id,
              CASE
                  WHEN ft_type_flg IN (
                      'BS',
                      'BX'
                  ) THEN ft.sibling_id
                  ELSE NULL
              END AS bseg_id,
              CASE
                  WHEN ft_type_flg IN (
                      'AD',
                      'AX'
                  ) THEN ft.sibling_id
                  ELSE NULL
              END AS adj_id,
              CASE
                  WHEN ft_type_flg IN (
                      'PS',
                      'PX'
                  ) THEN ft.sibling_id
                  ELSE NULL
              END AS pay_seg_id,
              ft.sa_id,
              sa.acct_id,
              sa.char_prem_id   AS prem_id,
              ap.per_id,
              ft.gl_division,
              ft.cis_division,
              ft.ft_type_flg,
              ft.cur_amt,
              ft.tot_amt,
              ft.cre_dttm,
              ft.freeze_user_id,
              ft.freeze_dttm,
              ft.accounting_dt,
              ft.ars_dt,
              CASE
                   WHEN ft.ft_type_flg IN (
                     'BS',
                     'BX'
                 ) THEN (
                   SELECT
                        ch.rs_cd
                   FROM
                        ci_bseg_calc ch
                   WHERE
                        ch.bseg_id = ft.sibling_id
                        AND ch.rs_cd <> ' '
                        AND ch.header_seq = 1
                 )
                   WHEN ft.ft_type_flg IN (
                    'AD',
                    'AX'
                ) THEN (
                  SELECT
                     MIN(ac.rs_cd)
                  FROM
                     ci_adj_calc_ln ac
                  WHERE
                     ac.adj_id = ft.sibling_id
                     AND ac.rs_cd <> ' '
                )
                  ELSE NULL
              END AS rs_cd,
              nvl((
                  SELECT
                      SUM(gl.amount) *-1
                  FROM
                      ci_ft_gl gl,
                      ci_dst_cd_char ch
                  WHERE
                      gl.ft_id = ft.ft_id
                      AND ch.dst_id = gl.dst_id
                      AND ch.effdt = (
                          SELECT
                              MAX(eff.effdt)
                          FROM
                              ci_dst_code_eff eff
                          WHERE
                              eff.dst_id = gl.dst_id
                              AND eff.effdt <= current_date
                      )
                     AND TRIM(ch.char_type_cd) = (
                          SELECT
                              TRIM(MIN(ex.char_val_fk1) )
                          FROM
                              f1_ext_lookup_val_char ex
                          WHERE
                              ex.bus_obj_cd = 'F1-AVAnalyticsOptions'
                              AND ex.char_type_cd = 'C1-GLACT'
                      )
                      AND TRIM(ch.char_val) IN(
                          SELECT
                              TRIM(ex.adhoc_char_val)
                          FROM
                              f1_ext_lookup_val_char ex
                          WHERE
                              ex.bus_obj_cd = 'F1-AVAnalyticsOptions'
                              AND ex.char_type_cd = 'C1-REVCH'
                      )
              ),0) AS ft_gl_rev_amt,
              nvl((
                  SELECT
                      SUM(gl.amount) *-1
                  FROM
                      ci_ft_gl gl,
                      ci_dst_cd_char ch
                  WHERE
                      gl.ft_id = ft.ft_id
                      AND ch.dst_id = gl.dst_id
                      AND ch.effdt = (
                          SELECT
                              MAX(eff.effdt)
                          FROM
                              ci_dst_code_eff eff
                          WHERE
                              eff.dst_id = gl.dst_id
                              AND eff.effdt <= current_date
                      )
                     AND TRIM(ch.char_type_cd) = (
                          SELECT
                              TRIM(MIN(ex.char_val_fk1) )
                          FROM
                              f1_ext_lookup_val_char ex
                          WHERE
                              ex.bus_obj_cd = 'F1-AVAnalyticsOptions'
                              AND ex.char_type_cd = 'C1-GLACT'
                      )
                      AND TRIM(ch.char_val) IN(
                          SELECT
                              TRIM(ex.adhoc_char_val)
                          FROM
                              f1_ext_lookup_val_char ex
                          WHERE
                              ex.bus_obj_cd = 'F1-AVAnalyticsOptions'
                              AND ex.char_type_cd = 'C1-TAXCH'
                      )
              ),0) AS ft_gl_tax_amt,
              ft.XFER_TO_GL_DT
         FROM
              ci_ft ft,
              ci_sa sa,
              ci_acct_per ap
          WHERE
              ft.freeze_sw = 'Y'
              AND sa.sa_id = ft.sa_id
              AND ap.acct_id = sa.acct_id
              AND ap.main_cust_sw = 'Y'
              AND ft.cre_dttm BETWEEN add_months(current_date,-60) AND current_date
              AND EXISTS (
                  SELECT
                      *
                  FROM
                      ci_ft_gl gl
                  WHERE
                      gl.ft_id = ft.ft_id
              )
      );

-- ----- C1_BI_SEVPROC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_BI_SEVPROC_VW" ("SEV_PROC_ID", "COLL_PROC_ID", "EVT_SEQ", "SEV_PROC_TMPL_CD", "SA_ID", "ACCT_ID", "PER_ID", "PREM_ID", "CURRENCY_CD", "MESSAGE_CAT_NBR", "MESSAGE_NBR", "CRE_DTTM", "SEV_STATUS_FLG", "SEV_STAT_RSN_FLG", "SEV_ARS_DT", "COMMENTS", "COMPLETE_DT", "CURR_SEV_EVT_TYPE_CD", "EFF_SEV_EVT_TYPE_CD", "DISCONN_WARN_DT", "SVC_DISCONN_DT", "SVC_RECONN_DT", "SEV_PROC_CNT", "ACTIVE_SEV_PROC_CNT", "INACTIVE_SEV_PROC_CNT", "COMPLETED_SEV_PROC_CNT", "CANCL_SYS_SEV_PROC_CNT", "CANCL_USER_SEV_PROC_CNT", "CURR_ARS_AMT", "ARS_AT_START_AMT", "ARS_AT_END_AMT", "ARS_DIFF_AMT", "SEV_PROC_DURATION", "DISCONN_WARN_CNT", "RECONN_CNT", "DISCONN_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
      sev_proc_id,
      coll_proc_id,
      evt_seq,
      sev_proc_tmpl_cd,
      sa_id,
      acct_id,
      per_id,
      prem_id,
      currency_cd,
      message_cat_nbr,
      message_nbr,
      cre_dttm,
      sev_status_flg,
      sev_stat_rsn_flg,
      sev_ars_dt,
      comments,
      CASE
          WHEN sev_status_flg = '20' THEN nvl(latest_se_completion_dt,trunc(cre_dttm) )
          ELSE null
      END AS COMPLETE_DT ,
      CASE
          WHEN sev_status_flg = '10' then NVL(curr_sev_evt_type_cd, ' ')
      else ' '
      end as curr_sev_evt_Type_cd,
      CASE when cancl_sys_sev_proc_cnt = 1 then NVL(eff_sev_evt_type_cd, ' ')
      else ' '
      end as eff_sev_evt_type_cd,
      disconn_warn_dt,
      svc_disconn_dt,
      svc_reconn_dt,
      1 AS sev_proc_cnt,
      active_sev_proc_cnt,
      inactive_sev_proc_cnt,
      completed_sev_proc_cnt,
      cancl_sys_sev_proc_cnt,
      cancl_user_sev_proc_cnt,
      case when sev_status_flg = '10' then ( debit_amt + current_credit_amt )
      else 0
      end AS CURR_ARS_AMT,
      ( debit_amt + at_start_credit_amt ) AS ARS_AT_START_AMT ,
      CASE
          WHEN sev_status_flg = '20' and (debit_amt + at_end_credit_amt) > 0 THEN ( debit_amt + at_end_credit_amt )
          ELSE 0
      END AS ARS_AT_END_AMT ,
      CASE
          WHEN sev_status_flg = '20' THEN ( ( debit_amt + at_start_credit_amt ) - ( debit_amt + at_end_credit_amt ) )
          ELSE 0
      END AS ARS_DIFF_AMT,
      CASE
          WHEN sev_status_flg = '20' THEN round(nvl(latest_se_completion_dt,trunc(cre_dttm) ) - trunc(cre_dttm),2)
          ELSE round(current_date - trunc(cre_dttm),2)
      END AS sev_proc_duration,
      sev_disconn_warn_cnt AS DISCONN_WARN_CNT,
      sev_reconn_cnt AS RECONN_CNT,
      sev_disconn_cnt AS DISCONN_CNT
  FROM
     (
          SELECT
              sp.sev_proc_id,
              sp.coll_proc_id,
              sp.evt_seq,
              sp.sev_proc_tmpl_cd,
              sp.sa_id,
              sa.acct_id,
              ap.per_id,
              nvl(sa.char_prem_id, (
                  SELECT
                      ac.mailing_prem_id
                  FROM
                      ci_acct ac
                  WHERE
                      ac.acct_id = sa.acct_id
              ) ) AS prem_id,
              sp.currency_cd,
              sp.message_cat_nbr,
              sp.message_nbr,
              sp.cre_dttm,
              sp.sev_status_flg,
              sp.sev_stat_rsn_flg,
              sp.sev_ars_dt,
              sp.comments,
              CASE
                  WHEN sev_status_flg = '10' THEN 1
                  ELSE 0
              END AS active_sev_proc_cnt,
              CASE
                  WHEN sp.sev_status_flg = '20' THEN 1
                  ELSE 0
              END AS inactive_sev_proc_cnt,
              CASE
                  WHEN sp.sev_stat_rsn_flg = '20' THEN 1
                  ELSE 0
              END AS completed_sev_proc_cnt,
              CASE
                  WHEN sev_stat_rsn_flg = '30' THEN 1
                  ELSE 0
              END AS cancl_sys_sev_proc_cnt,
              CASE
                  WHEN sev_stat_rsn_flg = '40' THEN 1
                  ELSE 0
              END AS cancl_user_sev_proc_cnt,
              (
                  SELECT
                      MAX(se.completion_dt)
                  FROM
                      ci_sev_evt se
                  WHERE
                      se.sev_proc_id = sp.sev_proc_id
              ) AS latest_se_completion_dt,
             (
                  SELECT
                      MIN(se.sev_evt_type_cd)
                  FROM
                      ci_sev_evt se
                  WHERE
                      se.sev_proc_id = sp.sev_proc_id
                      AND se.sev_evt_stat_flg IN (
                          '10',
                          '20'
                      )
                      AND se.evt_seq = (
                          SELECT
                              MIN(se2.evt_seq)
                          FROM
                              ci_sev_evt se2
                          WHERE
                              se2.sev_proc_id = se.sev_proc_id
                              AND se2.sev_evt_stat_flg IN (
                                  '10',
                                  '20'
                              )
                      )
              ) AS curr_sev_evt_type_cd,
              (
                  SELECT
                      MIN(se.sev_evt_type_cd)
                  FROM
                      ci_sev_evt se
                  WHERE
                      se.sev_proc_id = sp.sev_proc_id
                      AND se.sev_evt_stat_flg = '30'
                      AND se.evt_seq = (
                          SELECT
                              MAX(se2.evt_seq)
                          FROM
                              ci_sev_evt se2
                          WHERE
                              se2.sev_proc_id = se.sev_proc_id
                              AND se2.sev_evt_stat_flg = '30'
                      )
              ) AS eff_sev_evt_type_cd,
              (
                  SELECT
                      MIN(se.completion_dt)
                  FROM
                      ci_sev_evt se,
                      ci_sev_evt_type st
                  WHERE
                      se.sev_proc_id = sp.sev_proc_id
                      AND se.sev_evt_stat_flg = '30'
                      AND st.sev_evt_type_cd = se.sev_evt_type_cd
                      AND st.cust_evt_flg = 'DIWA'
                      AND se.evt_seq = (
                          SELECT
                              MIN(se2.evt_seq)
                          FROM
                              ci_sev_evt se2,
                              ci_sev_evt_type st2
                          WHERE
                              se2.sev_proc_id = se.sev_proc_id
                              AND se2.sev_evt_stat_flg = '30'
                              AND st2.sev_evt_type_cd = se2.sev_evt_type_cd
                              AND st2.cust_evt_flg = 'DIWA'
                      )
              ) AS disconn_warn_dt,
              (
                  SELECT
                      MIN(se.completion_dt)
                  FROM
                      ci_sev_evt se,
                      ci_sev_evt_type st
                  WHERE
                      se.sev_proc_id = sp.sev_proc_id
                      AND se.sev_evt_stat_flg = '30'
                      AND st.sev_evt_type_cd = se.sev_evt_type_cd
                      AND st.cust_evt_flg = 'CNP'
                      AND se.evt_seq = (
                          SELECT
                              MIN(se2.evt_seq)
                          FROM
                              ci_sev_evt se2,
                              ci_sev_evt_type st2
                          WHERE
                              se2.sev_proc_id = se.sev_proc_id
                              AND se2.sev_evt_stat_flg = '30'
                              AND st2.sev_evt_type_cd = se2.sev_evt_type_cd
                              AND st2.cust_evt_flg = 'CNP'
                      )
              ) AS svc_disconn_dt,
              (
                  SELECT
                      MIN(se.completion_dt)
                  FROM
                      ci_sev_evt se,
                      ci_sev_evt_type st
                  WHERE
                      se.sev_proc_id = sp.sev_proc_id
                      AND se.sev_evt_stat_flg = '30'
                      AND st.sev_evt_type_cd = se.sev_evt_type_cd
                      AND st.cust_evt_flg = 'REPY'
                      AND se.evt_seq = (
                          SELECT
                              MIN(se2.evt_seq)
                          FROM
                              ci_sev_evt se2,
                              ci_sev_evt_type st2
                          WHERE
                              se2.sev_proc_id = se.sev_proc_id
                              AND se2.sev_evt_stat_flg = '30'
                              AND st2.sev_evt_type_cd = se2.sev_evt_type_cd
                              AND st2.cust_evt_flg = 'REPY'
                      )
              ) AS svc_reconn_dt,
              (
                  SELECT
                      COUNT(*)
                  FROM
                      ci_sev_evt se,
                      ci_sev_evt_type st
                  WHERE
                      se.sev_proc_id = sp.sev_proc_id
                      AND se.sev_evt_stat_flg = '30'
                      AND st.sev_evt_type_cd = se.sev_evt_type_cd
                      AND st.cust_evt_flg = 'CNP'
              ) AS sev_disconn_cnt,
              (
                  SELECT
                      COUNT(*)
                  FROM
                      ci_sev_evt se,
                      ci_sev_evt_type st
                  WHERE
                      se.sev_proc_id = sp.sev_proc_id
                      AND se.sev_evt_stat_flg = '30'
                      AND st.sev_evt_type_cd = se.sev_evt_type_cd
                      AND st.cust_evt_flg = 'DIWA'
              ) AS sev_disconn_warn_cnt,
              (
                  SELECT
                      COUNT(*)
                  FROM
                      ci_sev_evt se,
                      ci_sev_evt_type st
                  WHERE
                      se.sev_proc_id = sp.sev_proc_id
                      AND se.sev_evt_stat_flg = '30'
                      AND st.sev_evt_type_cd = se.sev_evt_type_cd
                      AND st.cust_evt_flg = 'REPY'
              ) AS sev_reconn_cnt,
              nvl( (
                  SELECT
                      SUM(cur_amt)
                  FROM
                      ci_ft ft,ci_acct ac,ci_cust_cl cc
                  WHERE
                      ac.acct_id = sa.acct_id
                      AND cc.cust_cl_cd = ac.cust_cl_cd
                      AND ft.sa_id = sa.sa_id
                      AND ft.redundant_sw = 'N'
                      AND ft.cur_amt > 0
                      AND ft.freeze_sw = 'Y'
                      AND(ft.ars_dt IS NOT NULL
                            AND ft.ars_dt <= sp.sev_ars_dt)
                      AND( (cc.open_item_sw = 'N'
                              AND ft.not_in_ars_sw <> 'Y')
                            OR(cc.open_item_sw = 'Y'
                                 AND(substr(ft.match_evt_id,1,1) = ' '
                                       OR ft.match_evt_id IN(
                          SELECT
                              me.match_evt_id
                          FROM
                              ci_match_evt me
                          WHERE
                              me.acct_id = sa.acct_id
                             AND me.dispute_sw = 'N'
                              AND me.mevt_status_flg = 'O'
                      ) ) ) )
              ),0) AS debit_amt,
              nvl( (
                  SELECT
                      SUM(cur_amt)
                  FROM
                      ci_ft ft,ci_acct ac,ci_cust_cl cc
                  WHERE
                      ac.acct_id = sa.acct_id
                      AND cc.cust_cl_cd = ac.cust_cl_cd
                      AND ft.sa_id = sa.sa_id
                      AND ft.redundant_sw = 'N'
                      AND ft.cur_amt <= 0
                      AND ft.freeze_sw = 'Y'
                      AND(ft.ars_dt IS NOT NULL
                            AND ft.ars_dt <= current_date)
                      AND( (cc.open_item_sw = 'N'
                              AND ft.not_in_ars_sw <> 'Y')
                            OR(cc.open_item_sw = 'Y'
                                 AND(substr(ft.match_evt_id,1,1) = ' '
                                       OR ft.match_evt_id IN(
                          SELECT
                              me.match_evt_id
                          FROM
                              ci_match_evt me
                          WHERE
                              me.acct_id = sa.acct_id
                              AND me.dispute_sw = 'N'
                              AND me.mevt_status_flg = 'O'
                      ) ) ) )
              ),0) AS current_credit_amt,
              nvl( (
                  SELECT
                      SUM(cur_amt)
                  FROM
                      ci_ft ft,ci_acct ac,ci_cust_cl cc
                  WHERE
                      ac.acct_id = sa.acct_id
                      AND cc.cust_cl_cd = ac.cust_cl_cd
                      AND ft.sa_id = sa.sa_id
                      AND ft.redundant_sw = 'N'
                      AND ft.cur_amt <= 0
                      AND ft.freeze_sw = 'Y'
                      AND(ft.ars_dt IS NOT NULL
                            AND ft.ars_dt <= trunc(sp.cre_dttm) )
                      AND( (cc.open_item_sw = 'N'
                              AND ft.not_in_ars_sw <> 'Y')
                            OR(cc.open_item_sw = 'Y'
                                 AND(substr(ft.match_evt_id,1,1) = ' '
                                       OR ft.match_evt_id IN(
                          SELECT
                              me.match_evt_id
                          FROM
                              ci_match_evt me
                          WHERE
                              me.acct_id = sa.acct_id
                              AND me.dispute_sw = 'N'
                              AND me.mevt_status_flg = 'O'
                      ) ) ) )
              ),0) AS at_start_credit_amt,
              nvl( (
                  SELECT
                      SUM(cur_amt)
                  FROM
                      ci_ft ft,ci_acct ac,ci_cust_cl cc
                  WHERE
                      ac.acct_id = sa.acct_id
                      AND cc.cust_cl_cd = ac.cust_cl_cd
                      AND ft.sa_id = sa.sa_id
                      AND ft.redundant_sw = 'N'
                      AND ft.cur_amt <= 0
                      AND ft.freeze_sw = 'Y'
                      AND(ft.ars_dt IS NOT NULL
                            AND ft.ars_dt <= (
                          SELECT
                              MAX(se.completion_dt)
                          FROM
                              ci_sev_evt se
                          WHERE
                              se.sev_proc_id = sp.sev_proc_id
                      ) )
                     AND( (cc.open_item_sw = 'N'
                              AND ft.not_in_ars_sw <> 'Y')
                            OR(cc.open_item_sw = 'Y'
                                 AND(substr(ft.match_evt_id,1,1) = ' '
                                       OR ft.match_evt_id IN(
                          SELECT
                              me.match_evt_id
                          FROM
                              ci_match_evt me
                          WHERE
                              me.acct_id = sa.acct_id
                              AND me.dispute_sw = 'N'
                              AND me.mevt_status_flg = 'O'
                      ) ) ) )
              ),0) AS at_end_credit_amt
          FROM
              ci_sev_proc sp,
              ci_sa sa,
              ci_acct_per ap
          WHERE
              sa.sa_id = sp.sa_id
              AND ap.acct_id = sa.acct_id
              AND ap.main_cust_sw = 'Y'
      );

-- ----- C1_BI_WOPROC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_BI_WOPROC_VW" ("UNCOLL_PROC_ID", "WO_STATUS_FLG", "WO_STAT_RSN_FLG", "UNCOLL_PROC_STAT_FLG", "COMMENTS", "WO_PROC_CNT", "ACTIVE_WO_PROC_CNT", "INACTIVE_WO_PROC_CNT", "COMPL_WO_PROC_CNT", "CANCL_SYS_WO_PROC_CNT", "CANCL_USER_WO_PROC_CNT", "EFF_WO_PROC_CNT", "INEFF_WO_PROC_CNT", "ARS_AT_START", "ARS_AT_END", "ARS_DIFF", "UNCOLL_PROC_DUR", "WO_PROC_TOT_SA_CNT", "WO_PROC_ACT_SA_CNT", "WO_PROC_INACT_SA_CNT", "ACCT_ID", "WO_PROC_COMPL_DT", "CRE_DTTM", "CURRENCY_CD", "EFF_WO_EVT_TYP_CD", "NEXT_WO_EVT_TRIGGER_DT", "NEXT_WO_EVT_TYP_CD", "PER_ID", "WO_CNTL_CD", "WO_PROC_TMPL_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  WITH unc_attr AS (
    SELECT wp.wo_proc_id
    ,      wp.wo_status_flg
    ,      wp.wo_stat_rsn_flg
    ,      CASE
            WHEN wp.wo_status_flg = '10'
                THEN 'C1AC'
            WHEN wp.wo_status_flg = '20' AND wp.wo_stat_rsn_flg = '20'
                THEN 'C1IN'
            ELSE 'C1EF'
           END  uncoll_proc_stat_flg
    ,      wp.comments
    ,      wp.acct_id
    ,      acct.currency_cd
    ,      wp.cre_dttm
    ,      ap.per_id
    ,      wp.wo_cntl_cd
    ,      wp.wo_proc_tmpl_cd
    ,      NVL(MAX(completion_dt),TRUNC(cre_dttm)) max_completion_dt
    ,      CASE
            WHEN wp.wo_status_flg = '10'
                THEN TRUNC(wp.cre_dttm)
                ELSE NVL(MAX(completion_dt),TRUNC(cre_dttm))
           END  ARS_END_DT
    ,      COUNT( wesa.wo_proc_id) wo_proc_tot_sa_cnt
    ,      SUM(
            CASE
                WHEN wesa.wo_sa_stat_flg = '10' THEN 1
                ELSE 0
            END
           ) wo_proc_act_sa_cnt
    ,      SUM(
            CASE
                WHEN wesa.wo_sa_stat_flg = '20' THEN 1
                ELSE 0
            END
           ) wo_proc_inact_sa_cnt
    FROM ci_wo_proc wp
    LEFT JOIN (SELECT we.*
                FROM ci_wo_evt we
                WHERE we.evt_seq = (SELECT we2.evt_seq
                                    FROM   ci_wo_evt we2
                                    WHERE  we2.wo_proc_id = we.wo_proc_id
                                    AND    we2.completion_dt is not null
                                    ORDER BY we2.completion_dt desc, we2.evt_seq desc
                                    FETCH FIRST 1 ROW ONLY)
                ) we
        ON we.wo_proc_id = wp.wo_proc_id
    LEFT JOIN ci_wo_proc_sa wesa
        ON wesa.wo_proc_id = wp.wo_proc_id
    LEFT JOIN ci_acct acct
        ON acct.acct_id = wp.acct_id
    LEFT JOIN ci_acct_per ap
        ON ap.acct_id = wp.acct_id
        AND ap.main_cust_sw = 'Y'
    GROUP BY wp.wo_proc_id
    ,      wp.wo_proc_tmpl_cd
    ,      wp.wo_status_flg
    ,      wp.wo_stat_rsn_flg
    ,      CASE
            WHEN wp.wo_status_flg = '10'
                THEN 'C1AC'
            WHEN wp.wo_status_flg = '20' AND wp.wo_stat_rsn_flg = '20'
                THEN 'C1IN'
            ELSE 'C1EF'
           END
    ,      wp.comments
    ,      wp.acct_id
    ,      acct.currency_cd
    ,      ap.per_id
    ,      wp.cre_dttm
    ,      wp.wo_cntl_cd
)
, next_we as (
    SELECT nextwe.evt_seq
    ,      nextwe.wo_proc_id
    ,      nextwe.wo_evt_typ_cd next_wo_evt_typ_cd
    ,      nextwe.trigger_dt next_wo_evt_trigger_dt
    FROM   unc_attr ua
    INNER JOIN ci_wo_evt nextwe
        ON nextwe.wo_proc_id = ua.wo_proc_id
        AND    nextwe.wo_evt_stat_flg = '10'
    WHERE  ua.wo_status_flg = '10'
    AND nextwe.evt_seq = (
        SELECT evt_seq
        FROM   ci_wo_evt nextwe2
        WHERE  nextwe2.wo_proc_id = nextwe.wo_proc_id
        AND    nextwe2.wo_evt_stat_flg = '10'
        ORDER BY trigger_dt ASC
        ,        evt_seq ASC
        FETCH FIRST 1 ROW ONLY
    )
)
, ars_amts as (
    SELECT  wsa.wo_proc_id
    ,       sum(
                CASE
                    WHEN ft.ars_dt <= TRUNC(ua.cre_dttm)
                        THEN ft.cur_amt
                        ELSE 0
                END
            ) ars_at_start
    ,       sum(
               CASE
                    WHEN ft.cur_amt > 0 and ft.ars_dt <= TRUNC(ua.cre_dttm)
                        THEN ft.cur_amt
                    WHEN ft.cur_amt <= 0 and ft.ars_dt <= ua.ars_end_dt
                        THEN ft.cur_amt
                    ELSE 0
                END
            ) ars_at_end
    FROM unc_attr ua
    INNER JOIN ci_wo_proc_sa wsa
        ON wsa.wo_proc_id = ua.wo_proc_id
    INNER JOIN ci_ft ft
        ON ft.sa_id = wsa.sa_id
    INNER JOIN ci_acct ac
        ON AC.acct_id = ua.acct_id
    INNER JOIN ci_cust_cl cc
        ON cc.cust_cl_cd = ac.cust_cl_cd
    WHERE ft.redundant_sw               = 'N'
    AND ft.freeze_sw                  = 'Y'
    AND ( ft.ars_dt                  IS NOT NULL
        AND ft.ars_dt                    <= ua.ars_end_dt )
    AND ((
            cc.open_item_sw           = 'N'
            AND ft.not_in_ars_sw             <> 'Y' )
        OR (
            cc.open_item_sw              = 'Y'
            AND (
                SUBSTR(ft.match_evt_id,1,1) = ' '
                OR ft.match_evt_id IN (
                    SELECT me.match_evt_id
                    FROM ci_match_evt me
                    WHERE me.acct_id       = ua.acct_id
                    AND me.dispute_sw      = 'N'
                    AND me.mevt_status_flg = 'O'
                )
            )
        )
    )
    group by wsa.wo_proc_id
)
/*****ATTRIBUTES*****/
SELECT ua.wo_proc_id uncoll_proc_id
,      ua.wo_status_flg
,      ua.wo_stat_rsn_flg
,      ua.uncoll_proc_stat_flg
,      ua.comments
/*****METRICS*****/
,     1 wo_proc_cnt
,     CASE
        WHEN ua.wo_status_flg = '10'
            THEN 1 ELSE 0
      END active_wo_proc_cnt
,     CASE
        WHEN ua.wo_status_flg = '20'
            THEN 1 ELSE 0
      END inactive_wo_proc_cnt
,     CASE
        WHEN ua.wo_status_flg = '20' AND ua.wo_stat_rsn_flg = '20'
            THEN 1 ELSE 0
      END compl_wo_proc_cnt
,     CASE
        WHEN ua.wo_status_flg = '20' AND ua.wo_stat_rsn_flg = '30'
            THEN 1 ELSE 0
      END cancl_sys_wo_proc_cnt
,     CASE
        WHEN ua.wo_status_flg = '20' AND ua.wo_stat_rsn_flg = '40'
            THEN 1 ELSE 0
      END cancl_user_wo_proc_cnt
,     CASE
        WHEN ua.uncoll_proc_stat_flg = 'C1EF'
            THEN 1 ELSE 0
      END eff_wo_proc_cnt
,     CASE
        WHEN ua.uncoll_proc_stat_flg = 'C1IN'
            THEN 1 ELSE 0
      END ineff_wo_proc_cnt
,     nvl(aa.ars_at_start,0) ars_at_start
,     CASE
        WHEN ua.wo_status_flg = '20'
            THEN nvl(aa.ars_at_end,0)
            ELSE 0
      END ars_at_end
,     CASE
        WHEN ua.wo_status_flg = '20'
            THEN nvl(aa.ars_at_start,0) - nvl(aa.ars_at_end,0)
            ELSE 0
      END ars_diff
 ,     CASE
        WHEN ua.wo_status_flg = '20'
            THEN FLOOR(ua.max_completion_dt - TRUNC(ua.cre_dttm))
        ELSE FLOOR(current_date - TRUNC(ua.cre_dttm))
      END uncoll_proc_dur
,     ua.wo_proc_tot_sa_cnt
,     ua.wo_proc_act_sa_cnt
,     ua.wo_proc_inact_sa_cnt
/*****DIMENSIONS****/
,     ua.acct_id
,     CASE
        WHEN ua.wo_status_flg = '20'
            THEN ua.ars_end_dt
            ELSE NULL
      END wo_proc_compl_dt
,     ua.cre_dttm
,     ua.currency_cd
,     (
        SELECT effwe.wo_evt_typ_cd
        FROM   ci_wo_evt effwe
        WHERE  ua.wo_status_flg = '20'
        AND    effwe.wo_proc_id = ua.wo_proc_id
        AND    effwe.completion_dt IS NOT NULL
        ORDER BY effwe.completion_dt DESC, effwe.evt_seq DESC
        FETCH FIRST 1 ROW ONLY
      ) eff_wo_evt_typ_cd
,     nwe.next_wo_evt_trigger_dt
,     nwe.next_wo_evt_typ_cd
,     ua.per_id
,     ua.wo_cntl_cd
,     ua.wo_proc_tmpl_cd
FROM   unc_attr ua
LEFT JOIN next_we nwe
    ON nwe.wo_proc_id = ua.wo_proc_id
LEFT JOIN ars_amts aa
    ON aa.wo_proc_id = ua.wo_proc_id;

-- ----- C1_SA_RCHG_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_SA_RCHG_VW" ("SA_ID", "EFFDT", "RCR_CHG_AMT", "CURRENCY_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    "SA_ID","EFFDT","RCR_CHG_AMT","CURRENCY_CD"
FROM
    ci_sa_rchg_hist a
WHERE
    a.effdt = (
        SELECT
            MAX(b.effdt)
        FROM
            ci_sa_rchg_hist b
        WHERE
            a.sa_id = b.sa_id
            AND   b.effdt <= CURRENT_DATE
    );

-- ----- C1_SA_RS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_SA_RS_VW" ("SA_ID", "EFFDT", "RS_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    "SA_ID","EFFDT","RS_CD"
FROM
    ci_sa_rs_hist a
WHERE
    a.effdt = (
        SELECT
            MAX(b.effdt)
        FROM
            ci_sa_rs_hist b
        WHERE
            a.sa_id = b.sa_id
            AND   b.effdt <= CURRENT_DATE
    );

-- ----- C1_SYRQ_PER_ALL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_SYRQ_PER_ALL_VW" ("CRE_DTTM", "F1_SYNC_REQ_ID", "ACCT_ID", "PER_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_SP SASP,
    CI_SA SA,
    CI_ACCT_PER AP
  WHERE SR.MAINT_OBJ_CD = 'SP'
  AND SR.PK_VALUE1      = SASP.SP_ID
  AND SA.SA_ID          = SASP.SA_ID
  AND AP.ACCT_ID        = SA.ACCT_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_SA SA,
    CI_ACCT_PER AP
  WHERE SR.MAINT_OBJ_CD = 'SA'
  AND SR.PK_VALUE1      = SA.SA_ID
  AND AP.ACCT_ID        = SA.ACCT_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_ACCT_PER AP
  WHERE SR.MAINT_OBJ_CD = 'PERSON'
  AND SR.PK_VALUE1      = AP.PER_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    ' ' AS ACCT_ID,
    PN.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_PER_NAME PN
  WHERE SR.MAINT_OBJ_CD = 'PERSON'
  AND SR.PK_VALUE1      = PN.PER_ID
  AND NOT EXISTS
    ( SELECT 'X' FROM CI_ACCT_PER AP WHERE AP.PER_ID = PN.PER_ID
    )
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_FA FA,
    CI_SA_SP SASP,
    CI_SA SA,
    CI_ACCT_PER AP
  WHERE SR.MAINT_OBJ_CD = 'FA'
  AND SR.PK_VALUE1      = FA.FA_ID
  AND SASP.SP_ID        = FA.SP_ID
  AND SA.SA_ID          = SASP.SA_ID
  AND AP.ACCT_ID        = SA.ACCT_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_BSEG BS,
    CI_SA SA,
    CI_ACCT_PER AP
  WHERE SR.MAINT_OBJ_CD = 'BILL SEG'
  AND SR.PK_VALUE1      = BS.BSEG_ID
  AND SA.SA_ID          = BS.SA_ID
  AND AP.ACCT_ID        = SA.ACCT_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_COP SACO,
    CI_SA SA,
    CI_ACCT_PER AP
  WHERE SR.MAINT_OBJ_CD = 'CONTRACT OPT'
  AND SR.PK_VALUE1      = SACO.CONT_OPT_ID
  AND SA.SA_ID          = SACO.SA_ID
  AND AP.ACCT_ID        = SA.ACCT_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_COP_EVT COE,
    CI_SA_COP SACO,
    CI_SA SA,
    CI_ACCT_PER AP
  WHERE SR.MAINT_OBJ_CD = 'COP EVENT'
  AND SR.PK_VALUE1      = COE.CONT_OPT_EVT_ID
  AND SACO.CONT_OPT_ID  = COE.CONT_OPT_ID
  AND SA.SA_ID          = SACO.SA_ID
  AND AP.ACCT_ID        = SA.ACCT_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_REL SAR,
    CI_SA SA,
    CI_ACCT_PER AP
  WHERE SR.MAINT_OBJ_CD = 'SA REL'
  AND SR.PK_VALUE1      = SAR.SA_REL_ID
  AND SAR.SA_ID         = SA.SA_ID
  AND SA.ACCT_ID        = AP.ACCT_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_SA SA,
    CI_ACCT_PER AP
  WHERE SR.MAINT_OBJ_CD = 'SA REL'
  AND SR.PK_VALUE1      = SA.SA_REL_ID
  AND SA.ACCT_ID        = AP.ACCT_ID
  UNION
SELECT SR.CRE_DTTM, SR.F1_SYNC_REQ_ID, AP.ACCT_ID, AP.PER_ID
FROM F1_SYNC_REQ SR, CI_BILL BILL, CI_BSEG BS, CI_SA SA, CI_ACCT_PER AP
WHERE SR.MAINT_OBJ_CD = 'BILL'
    AND SR.PK_VALUE1 = BILL.BILL_ID
    AND BILL.BILL_ID = BS.BILL_ID
    AND SA.SA_ID = BS.SA_ID
    AND AP.ACCT_ID = SA.ACCT_ID
UNION
SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_ACCT_PER AP
  WHERE SR.MAINT_OBJ_CD = 'ACCOUNT'
  AND SR.PK_VALUE1      = AP.ACCT_ID
UNION
SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    C1_NTF_PREF NT,
    CI_ACCT_PER AP
  WHERE SR.MAINT_OBJ_CD = 'C1-NTF-PREF'
  AND SR.PK_VALUE1 = NT.NTF_PREF_ID
  AND AP.ACCT_ID = NT.ACCT_ID;

-- ----- C1_SYRQ_PER_NF_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_SYRQ_PER_NF_VW" ("CRE_DTTM", "F1_SYNC_REQ_ID", "ACCT_ID", "PER_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_SP SASP,
    CI_SA SA,
    CI_ACCT_PER AP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'SP'
  AND SR.PK_VALUE1            = SASP.SP_ID
  AND SASP.SA_ID              = SA.SA_ID
  AND SA.ACCT_ID              = AP.ACCT_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_SA SA,
    CI_ACCT_PER AP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'SA'
  AND SR.PK_VALUE1            = SA.SA_ID
  AND SA.ACCT_ID              = AP.ACCT_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_ACCT_PER AP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'PERSON'
  AND SR.PK_VALUE1            = AP.PER_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT DISTINCT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    ' ' AS ACCT_ID,
    PN.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_PER_NAME PN,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'PERSON'
  AND SR.PK_VALUE1            = PN.PER_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  AND NOT EXISTS
    ( SELECT 'X' FROM CI_ACCT_PER AP WHERE AP.PER_ID = PN.PER_ID
    )
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_FA FA,
    CI_SA_SP SASP,
    CI_SA SA,
    CI_ACCT_PER AP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'FA'
  AND SR.PK_VALUE1            = FA.FA_ID
  AND FA.SP_ID                = SASP.SP_ID
  AND SASP.SA_ID              = SA.SA_ID
  AND SA.ACCT_ID              = AP.ACCT_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_BSEG BS,
    CI_SA SA,
    CI_ACCT_PER AP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'BILL SEG'
  AND SR.PK_VALUE1            = BS.BSEG_ID
  AND BS.SA_ID                = SA.SA_ID
  AND SA.ACCT_ID              = AP.ACCT_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_COP SACO,
    CI_SA SA,
    CI_ACCT_PER AP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'CONTRACT OPT'
  AND SR.PK_VALUE1            = SACO.CONT_OPT_ID
  AND SACO.SA_ID              = SA.SA_ID
  AND SA.ACCT_ID              = AP.ACCT_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_COP_EVT COE,
    CI_SA_COP SACO,
    CI_SA SA,
    CI_ACCT_PER AP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'COP EVENT'
  AND SR.PK_VALUE1            = COE.CONT_OPT_EVT_ID
  AND COE.CONT_OPT_ID         = SACO.CONT_OPT_ID
  AND SACO.SA_ID              = SA.SA_ID
  AND SA.ACCT_ID              = AP.ACCT_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_REL SAR,
    CI_SA SA,
    CI_ACCT_PER AP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'SA REL'
  AND SR.PK_VALUE1            = SAR.SA_REL_ID
  AND SAR.SA_ID               = SA.SA_ID
  AND SA.ACCT_ID              = AP.ACCT_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
  FROM F1_SYNC_REQ SR,
    CI_SA SA,
    CI_ACCT_PER AP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'SA REL'
  AND SR.PK_VALUE1            = SA.SA_REL_ID
  AND SA.ACCT_ID              = AP.ACCT_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM, 
    SR.F1_SYNC_REQ_ID, 
    AP.ACCT_ID, 
    AP.PER_ID
  FROM F1_SYNC_REQ SR, 
    CI_BILL BILL, 
    CI_BSEG BS, 
    CI_SA SA, 
    CI_ACCT_PER AP, 
    F1_BUS_OBJ_STATUS BOS, 
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD = 'BILL'
    AND SR.PK_VALUE1 = BILL.BILL_ID
    AND BILL.BILL_ID = BS.BILL_ID
    AND BS.SA_ID = SA.SA_ID
    AND SA.ACCT_ID = AP.ACCT_ID
    AND BO.BUS_OBJ_CD = SR.BUS_OBJ_CD
    AND BOS.BUS_OBJ_CD = BO.LIFE_CYCLE_BO_CD
    AND BOS.BO_STATUS_CD = SR.BO_STATUS_CD
    AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
UNION
SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
FROM F1_SYNC_REQ SR,
    CI_ACCT_PER AP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
WHERE SR.MAINT_OBJ_CD       = 'ACCOUNT'
    AND SR.PK_VALUE1            = AP.ACCT_ID
    AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
    AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
    AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
    AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
UNION
SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    AP.ACCT_ID,
    AP.PER_ID
FROM F1_SYNC_REQ SR,
    C1_NTF_PREF NT,
    CI_ACCT_PER AP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
WHERE SR.MAINT_OBJ_CD = 'C1-NTF-PREF'
    AND SR.PK_VALUE1 = NT.NTF_PREF_ID
    AND AP.ACCT_ID = NT.ACCT_ID
    AND BO.BUS_OBJ_CD = SR.BUS_OBJ_CD
    AND BOS.BUS_OBJ_CD = BO.LIFE_CYCLE_BO_CD
    AND BOS.BO_STATUS_CD = SR.BO_STATUS_CD
    AND BOS.BO_STATUS_COND_FLG <> 'F1FL';

-- ----- C1_SYRQ_PREM_ALL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_SYRQ_PREM_ALL_VW" ("CRE_DTTM", "F1_SYNC_REQ_ID", "PREM_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_SP SASP,
    CI_SP SP
  WHERE SR.MAINT_OBJ_CD = 'SA'
  AND SR.PK_VALUE1      = SASP.SA_ID
  AND SP.SP_ID          = SASP.SP_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA SA
  WHERE SR.MAINT_OBJ_CD = 'SA'
  AND SR.PK_VALUE1      = SA.SA_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SP SP
  WHERE SR.MAINT_OBJ_CD = 'SP'
  AND SR.PK_VALUE1      = SP.SP_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_FA FA,
    CI_SP SP
  WHERE SR.MAINT_OBJ_CD = 'FA'
  AND SR.PK_VALUE1      = FA.FA_ID
  AND SP.SP_ID          = FA.SP_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_BSEG BS,
    CI_SA_SP SASP,
    CI_SP SP
  WHERE SR.MAINT_OBJ_CD = 'BILL SEG'
  AND SR.PK_VALUE1      = BS.BSEG_ID
  AND SASP.SA_ID        = BS.SA_ID
  AND SP.SP_ID          = SASP.SP_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_BSEG BS,
    CI_SA SA
  WHERE SR.MAINT_OBJ_CD = 'BILL SEG'
  AND SR.PK_VALUE1      = BS.BSEG_ID
  AND SA.SA_ID          = BS.SA_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SP_MTR_HIST SPMH,
    CI_SP SP
  WHERE SR.MAINT_OBJ_CD = 'SP/MTR HIST'
  AND SR.PK_VALUE1      = SPMH.SP_MTR_HIST_ID
  AND SP.SP_ID          = SPMH.SP_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_COP SACO,
    CI_SA_SP SASP,
    CI_SP SP
  WHERE SR.MAINT_OBJ_CD = 'CONTRACT OPT'
  AND SR.PK_VALUE1      = SACO.CONT_OPT_ID
  AND SASP.SA_ID        = SACO.SA_ID
  AND SP.SP_ID          = SASP.SP_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_COP SACO,
    CI_SA SA
  WHERE SR.MAINT_OBJ_CD = 'CONTRACT OPT'
  AND SR.PK_VALUE1      = SACO.CONT_OPT_ID
  AND SA.SA_ID          = SACO.SA_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_COP_EVT COE,
    CI_SA_COP SACO,
    CI_SA_SP SASP,
    CI_SP SP
  WHERE SR.MAINT_OBJ_CD = 'COP EVENT'
  AND SR.PK_VALUE1      = COE.CONT_OPT_EVT_ID
  AND SACO.CONT_OPT_ID  = COE.CONT_OPT_ID
  AND SASP.SA_ID        = SACO.SA_ID
  AND SP.SP_ID          = SASP.SP_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_COP_EVT COE,
    CI_SA_COP SACO,
    CI_SA SA
  WHERE SR.MAINT_OBJ_CD = 'COP EVENT'
  AND SR.PK_VALUE1      = COE.CONT_OPT_EVT_ID
  AND SACO.CONT_OPT_ID  = COE.CONT_OPT_ID
  AND SA.SA_ID          = SACO.SA_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_REL SAR,
    CI_SA_SP SASP,
    CI_SP SP
  WHERE SR.MAINT_OBJ_CD = 'SA REL'
  AND SR.PK_VALUE1      = SAR.SA_REL_ID
  AND SASP.SA_ID        = SAR.SA_ID
  AND SP.SP_ID          = SASP.SP_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_REL SAR,
    CI_SA SA
  WHERE SR.MAINT_OBJ_CD = 'SA REL'
  AND SR.PK_VALUE1      = SAR.SA_REL_ID
  AND SA.SA_ID          = SAR.SA_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA SA,
    CI_SA_SP SASP,
    CI_SP SP
  WHERE SR.MAINT_OBJ_CD = 'SA REL'
  AND SR.PK_VALUE1      = SA.SA_REL_ID
  AND SASP.SA_ID        = SA.SA_ID
  AND SP.SP_ID          = SASP.SP_ID
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA SA
  WHERE SR.MAINT_OBJ_CD = 'SA REL'
  AND SR.PK_VALUE1      = SA.SA_REL_ID
  UNION
  SELECT SR.CRE_DTTM, 
    SR.F1_SYNC_REQ_ID, 
    SP.PREM_ID
  FROM F1_SYNC_REQ SR, 
    CI_BILL BILL, 
    CI_BSEG BS, 
    CI_SA_SP SASP, 
    CI_SP SP
  WHERE SR.MAINT_OBJ_CD = 'BILL'
  AND SR.PK_VALUE1 = BILL.BILL_ID
  AND BILL.BILL_ID = BS.BILL_ID
  AND BS.SA_ID = SASP.SA_ID
  AND  SASP.SP_ID = SP.SP_ID
  UNION
  SELECT SR.CRE_DTTM, 
    SR.F1_SYNC_REQ_ID, 
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR, CI_BILL BILL, CI_BSEG BS, CI_SA SA
  WHERE SR.MAINT_OBJ_CD = 'BILL'
  AND SR.PK_VALUE1 = BILL.BILL_ID
  AND BILL.BILL_ID = BS.BILL_ID
  AND BS.SA_ID = SA.SA_ID
UNION
SELECT SR.CRE_DTTM, SR.F1_SYNC_REQ_ID, SP.PREM_ID
FROM F1_SYNC_REQ SR, CI_ACCT AC, CI_SA_SP SASP, CI_SP SP, CI_SA SA
WHERE SR.MAINT_OBJ_CD = 'ACCOUNT'
    AND SR.PK_VALUE1 = AC.ACCT_ID
    AND AC.ACCT_ID = SA.ACCT_ID
    AND SA.SA_ID = SASP.SA_ID
    AND SASP.SP_ID = SP.SP_ID
UNION
SELECT SR.CRE_DTTM, SR.F1_SYNC_REQ_ID, SA.CHAR_PREM_ID AS PREM_ID
FROM F1_SYNC_REQ SR, CI_ACCT AC, CI_SA SA
WHERE SR.MAINT_OBJ_CD = 'ACCOUNT'
    AND SR.PK_VALUE1 = AC.ACCT_ID
    AND AC.ACCT_ID = SA.ACCT_ID;

-- ----- C1_SYRQ_PREM_NF_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_SYRQ_PREM_NF_VW" ("CRE_DTTM", "F1_SYNC_REQ_ID", "PREM_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_SP SASP,
    CI_SP SP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'SA'
  AND SR.PK_VALUE1            = SASP.SA_ID
  AND SASP.SP_ID              = SP.SP_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA SA,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'SA'
  AND SR.PK_VALUE1            = SA.SA_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SP SP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'SP'
  AND SR.PK_VALUE1            = SP.SP_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_FA FA,
    CI_SP SP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'FA'
  AND SR.PK_VALUE1            = FA.FA_ID
  AND FA.SP_ID                = SP.SP_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_BSEG BS,
    CI_SA_SP SASP,
    CI_SP SP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'BILL SEG'
  AND SR.PK_VALUE1            = BS.BSEG_ID
  AND BS.SA_ID                = SASP.SA_ID
  AND SASP.SP_ID              = SP.SP_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_BSEG BS,
    CI_SA SA,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'BILL SEG'
  AND SR.PK_VALUE1            = BS.BSEG_ID
  AND BS.SA_ID                = SA.SA_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SP_MTR_HIST SPMH,
    CI_SP SP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'SP/MTR HIST'
  AND SR.PK_VALUE1            = SPMH.SP_MTR_HIST_ID
  AND SPMH.SP_ID              = SP.SP_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_COP SACO,
    CI_SA_SP SASP,
    CI_SP SP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'CONTRACT OPT'
  AND SR.PK_VALUE1            = SACO.CONT_OPT_ID
  AND SACO.SA_ID              = SASP.SA_ID
  AND SASP.SP_ID              = SP.SP_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_COP SACO,
    CI_SA SA,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'CONTRACT OPT'
  AND SR.PK_VALUE1            = SACO.CONT_OPT_ID
  AND SACO.SA_ID              = SA.SA_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_COP_EVT COE,
    CI_SA_COP SACO,
    CI_SA_SP SASP,
    CI_SP SP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'COP EVENT'
  AND SR.PK_VALUE1            = COE.CONT_OPT_EVT_ID
  AND COE.CONT_OPT_ID         = SACO.CONT_OPT_ID
  AND SACO.SA_ID              = SASP.SA_ID
  AND SASP.SP_ID              = SP.SP_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_COP_EVT COE,
    CI_SA_COP SACO,
    CI_SA SA,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'COP EVENT'
  AND SR.PK_VALUE1            = COE.CONT_OPT_EVT_ID
  AND COE.CONT_OPT_ID         = SACO.CONT_OPT_ID
  AND SACO.SA_ID              = SA.SA_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_REL SAR,
    CI_SA_SP SASP,
    CI_SP SP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'SA REL'
  AND SR.PK_VALUE1            = SAR.SA_REL_ID
  AND SAR.SA_ID               = SASP.SA_ID
  AND SASP.SP_ID              = SP.SP_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA_REL SAR,
    CI_SA SA,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'SA REL'
  AND SR.PK_VALUE1            = SAR.SA_REL_ID
  AND SAR.SA_ID               = SA.SA_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SP.PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA SA,
    CI_SA_SP SASP,
    CI_SP SP,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'SA REL'
  AND SR.PK_VALUE1            = SA.SA_REL_ID
  AND SA.SA_ID                = SASP.SA_ID
  AND SASP.SP_ID              = SP.SP_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM,
    SR.F1_SYNC_REQ_ID,
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR,
    CI_SA SA,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD       = 'SA REL'
  AND SR.PK_VALUE1            = SA.SA_REL_ID
  AND BO.BUS_OBJ_CD           = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD          = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD        = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM, 
    SR.F1_SYNC_REQ_ID, 
    SP.PREM_ID
  FROM F1_SYNC_REQ SR, 
    CI_BILL BILL, 
    CI_BSEG BS, 
    CI_SA_SP SASP, 
    CI_SP SP, 
    F1_BUS_OBJ_STATUS BOS, 
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD = 'BILL'
  AND SR.PK_VALUE1 = BILL.BILL_ID
  AND BILL.BILL_ID = BS.BILL_ID
  AND BS.SA_ID = SASP.SA_ID
  AND SASP.SP_ID = SP.SP_ID
  AND BO.BUS_OBJ_CD = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SR.CRE_DTTM, 
    SR.F1_SYNC_REQ_ID, 
    SA.CHAR_PREM_ID AS PREM_ID
  FROM F1_SYNC_REQ SR, 
    CI_BILL BILL, 
    CI_BSEG BS, 
    CI_SA SA, 
    F1_BUS_OBJ_STATUS BOS, 
    F1_BUS_OBJ BO
  WHERE SR.MAINT_OBJ_CD = 'BILL'
  AND SR.PK_VALUE1 = BILL.BILL_ID
  AND BILL.BILL_ID = BS.BILL_ID
  AND BS.SA_ID = SA.SA_ID
  AND BO.BUS_OBJ_CD = SR.BUS_OBJ_CD
  AND BOS.BUS_OBJ_CD = BO.LIFE_CYCLE_BO_CD
  AND BOS.BO_STATUS_CD = SR.BO_STATUS_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
UNION
SELECT SR.CRE_DTTM, SR.F1_SYNC_REQ_ID, SP.PREM_ID
FROM F1_SYNC_REQ SR, CI_ACCT AC, CI_SA SA, CI_SA_SP SASP, CI_SP SP, F1_BUS_OBJ_STATUS BOS, F1_BUS_OBJ BO
WHERE SR.MAINT_OBJ_CD = 'ACCOUNT'
    AND SR.PK_VALUE1 = AC.ACCT_ID
    AND AC.ACCT_ID = SA.ACCT_ID   
    AND SA.SA_ID = SASP.SA_ID
    AND SASP.SP_ID = SP.SP_ID
    AND BO.BUS_OBJ_CD = SR.BUS_OBJ_CD
    AND BOS.BUS_OBJ_CD = BO.LIFE_CYCLE_BO_CD
    AND BOS.BO_STATUS_CD = SR.BO_STATUS_CD
    AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
UNION
SELECT SR.CRE_DTTM, SR.F1_SYNC_REQ_ID, SA.CHAR_PREM_ID AS PREM_ID
FROM F1_SYNC_REQ SR, CI_ACCT AC, CI_SA SA, F1_BUS_OBJ_STATUS BOS, F1_BUS_OBJ BO
WHERE SR.MAINT_OBJ_CD = 'ACCOUNT'
    AND SR.PK_VALUE1 = AC.ACCT_ID
    AND AC.ACCT_ID = SA.ACCT_ID
    AND BO.BUS_OBJ_CD = SR.BUS_OBJ_CD
    AND BOS.BUS_OBJ_CD = BO.LIFE_CYCLE_BO_CD
    AND BOS.BO_STATUS_CD = SR.BO_STATUS_CD
    AND BOS.BO_STATUS_COND_FLG <> 'F1FL';

-- ----- CI_ACCTG_DAYS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ACCTG_DAYS_VW" ("BEGIN_DT", "END_DT", "OPEN_FROM_DT", "OPEN_TO_DT", "CALENDAR_ID", "GL_DIVISION", "FISCAL_YEAR", "ACCOUNTING_PERIOD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CAL.BEGIN_DT, CAL.END_DT, CAL.OPEN_FROM_DT, CAL.OPEN_TO_DT, GL.CALENDAR_ID, GL.GL_DIVISION, CAL.FISCAL_YEAR, CAL.ACCOUNTING_PERIOD
       FROM CI_GL_DIVISION GL, CI_CAL_PERIOD CAL
       WHERE GL.CALENDAR_ID = CAL.CALENDAR_ID
 ;

-- ----- CI_ACCT_CR_R_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ACCT_CR_R_VW" ("ACCT_ID", "CR_RATING_PTS", "CASH_ONLY_PTS", "START_DT", "END_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT HI.ACCT_ID, SUM(HI.CR_RATING_PTS), SUM(HI.CASH_ONLY_PTS), TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD'), TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD')
       FROM CI_CR_RAT_HIST HI
       WHERE HI.START_DT <=  TO_DATE(TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD'), 'YYYY-MM-DD') AND (HI.END_DT >=  TO_DATE(TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD'), 'YYYY-MM-DD') OR HI.END_DT IS NULL)
       GROUP BY HI.ACCT_ID;

-- ----- CI_ACCT_FT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ACCT_FT_HST_VW" ("ACCT_ID", "ARS_DT", "FT_TYPE_FLG", "PARENT_ID", "CUR_AMT", "TOT_AMT", "CURRENCY_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
  SA.ACCT_ID,
  FT.ARS_DT,
  FT.FT_TYPE_FLG,
  FT.PARENT_ID,
  SUM(FT.CUR_AMT),
  SUM(FT.TOT_AMT),
  FT.CURRENCY_CD
FROM
  CI_FT FT, CI_SA SA
WHERE
  FT.SA_ID=SA.SA_ID AND
  FT.FREEZE_DTTM IS NOT NULL
GROUP BY
 SA.ACCT_ID, FT.ARS_DT, FT.FT_TYPE_FLG, FT.PARENT_ID, FT.CURRENCY_CD
 ;

-- ----- CI_ACDC_WOSA_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ACDC_WOSA_VW" ("ACCT_ID", "WO_DEBT_CL_CD", "SA_ID", "SA_STATUS_FLG", "ELIG_FOR_WO_SW", "POSTPONE_CR_RVW_DT", "SPECIAL_ROLE_FLG", "SUB_SA_SW", "ALLOW_BILLING_SW") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
   AC.ACCT_ID,
   WDC.WO_DEBT_CL_CD,
   SA.SA_ID,
   SA.SA_STATUS_FLG,
   WDC.ELIG_FOR_WO_SW,
   AC.POSTPONE_CR_RVW_DT,
   SAT.SPECIAL_ROLE_FLG,
   SAT.SUB_SA_SW,
   SAT.ALLOW_BILLING_SW
FROM
   CI_SA SA,
   CI_ACCT AC,
   CI_SA_TYPE SAT,
   CI_WO_DEBT_CL WDC,
   CI_COLL_CL CCL
WHERE
   SA.SA_STATUS_FLG IN ('40', '50')
AND
   SA.ACCT_ID = AC.ACCT_ID
AND
   SA.SA_TYPE_CD = SAT.SA_TYPE_CD
AND
   SA.CIS_DIVISION = SAT.CIS_DIVISION
AND
   SAT.WO_DEBT_CL_CD = WDC.WO_DEBT_CL_CD
AND
   AC.COLL_CL_CD = CCL.COLL_CL_CD
AND
CCL.COLL_METH_FLG = 'CSWO'
 ;

-- ----- CI_ADJTSAT_S_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ADJTSAT_S_VW" ("LANGUAGE_CD", "CIS_DIVISION", "SA_TYPE_CD", "ADJ_TYPE_CD", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT DISTINCT ADJTL.LANGUAGE_CD, SATPROF.CIS_DIVISION, SATPROF.SA_TYPE_CD, AAPROF.ADJ_TYPE_CD, ADJTL.DESCR
       FROM CI_SAT_ADJ_PROF SATPROF, CI_ADJT_ADJTPRF AAPROF, CI_ADJ_TYPE ADJT, CI_ADJ_TYPE_L ADJTL
       WHERE SATPROF.ADJ_TYPE_PROF_CD =  AAPROF.ADJ_TYPE_PROF_CD AND AAPROF.ADJ_TYPE_CD =  ADJT.ADJ_TYPE_CD AND ADJTL.ADJ_TYPE_CD =  ADJT.ADJ_TYPE_CD
 ;

-- ----- CI_ALG_ADHC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_ADHC_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALGL.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_TYPE ATY, CI_ALG ALG, CI_ALG_L ALGL
       WHERE ATY.ALG_ENTITY_FLG =  'ZCHV' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_ADJT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_ADJT_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD,
ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG ALG, CI_ALG_TYPE ATY
       WHERE ATY.ALG_ENTITY_FLG =  'ADJT' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_BSBF_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_BSBF_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD,
ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG ALG, CI_ALG_TYPE ATY
       WHERE ATY.ALG_ENTITY_FLG =  'BSBF' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_BSBS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_BSBS_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD,
ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG ALG, CI_ALG_TYPE ATY
       WHERE ATY.ALG_ENTITY_FLG =  'BSBS' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_CCAL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_CCAL_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_TYPE ATY, CI_ALG_L ALGL, CI_ALG ALG
       WHERE ATY.ALG_ENTITY_FLG =  'CCAL' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_CNSMP_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_CNSMP_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG ALG, CI_ALG_TYPE ATY
       WHERE ATY.ALG_ENTITY_FLG =  'BSGC' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_COCN_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_COCN_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ATY.ALG_TYPE_CD, ALGL.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG_TYPE ATY, CI_ALG ALG
       WHERE ATY.ALG_ENTITY_FLG =  'COCN' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_COEV_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_COEV_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG ALG, CI_ALG_TYPE ATY
       WHERE ATY.ALG_ENTITY_FLG =  'COEV' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_ERAC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_ERAC_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ATY.ALG_TYPE_CD, ALGL.ALG_CD, ALGL.DESCR50
       FROM CI_ALG ALG, CI_ALG_L ALGL, CI_ALG_TYPE ATY
       WHERE ATY.ALG_ENTITY_FLG =  'ERAC'  AND
ALG.ALG_TYPE_CD =  ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_FACM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_FACM_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALGL.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_TYPE ATY, CI_ALG ALG, CI_ALG_L ALGL
       WHERE ATY.ALG_ENTITY_FLG =  'OCMP' AND
ALG.ALG_TYPE_CD =  ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_GLAC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_GLAC_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALGL.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_TYPE ATY, CI_ALG ALG, CI_ALG_L ALGL
       WHERE ATY.ALG_ENTITY_FLG =  'FGCT' AND
ALG.ALG_TYPE_CD =  ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_GVFM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_GVFM_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALGL.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG ALG, CI_ALG_TYPE ATY
       WHERE ATY.ALG_ENTITY_FLG =  'GVFM'  AND
ALG.ALG_TYPE_CD =  ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_IDFM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_IDFM_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ATY.ALG_TYPE_CD, ALGL.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_TYPE ATY, CI_ALG ALG, CI_ALG_L ALGL
       WHERE ATY.ALG_ENTITY_FLG =  'IDFM' AND
ALG.ALG_TYPE_CD =  ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_LPCC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_LPCC_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALGL.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_TYPE ATY, CI_ALG ALG, CI_ALG_L ALGL
       WHERE ATY.ALG_ENTITY_FLG =  'BLPC' AND
ALG.ALG_TYPE_CD =  ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_LPCE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_LPCE_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALGL.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_TYPE ATY, CI_ALG ALG, CI_ALG_L ALGL
       WHERE ATY.ALG_ENTITY_FLG =  'BLPE' AND
ALG.ALG_TYPE_CD =  ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_ODSP_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_ODSP_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_TYPE ATY, CI_ALG_L ALGL, CI_ALG ALG
       WHERE ATY.ALG_ENTITY_FLG =  'ODSP' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_PHFM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_PHFM_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ATY.ALG_TYPE_CD, ALGL.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_TYPE ATY, CI_ALG ALG, CI_ALG_L ALGL
       WHERE ATY.ALG_ENTITY_FLG =  'PHFM' AND
ALG.ALG_TYPE_CD =  ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_PKCC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_PKCC_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG ALG, CI_ALG_TYPE ATY
       WHERE ATY.ALG_ENTITY_FLG =  'PKCC' AND ALG.ALG_TYPE_CD =  ATY.ALG_TYPE_CD AND ALGL.ALG_CD =  ALG.ALG_CD
 ;

-- ----- CI_ALG_PKEL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_PKEL_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG ALG, CI_ALG_TYPE ATY
       WHERE ATY.ALG_ENTITY_FLG =  'PKEL' AND ALG.ALG_TYPE_CD =  ATY.ALG_TYPE_CD AND ALGL.ALG_CD =  ALG.ALG_CD
 ;

-- ----- CI_ALG_PPBR_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_PPBR_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALGL.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_TYPE ATY, CI_ALG ALG, CI_ALG_L ALGL
       WHERE ATY.ALG_ENTITY_FLG =  'PPBR' AND
ALG.ALG_TYPE_CD =  ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
 ;

-- ----- CI_ALG_PPOA_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_PPOA_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_TYPE ATY, CI_ALG_L ALGL, CI_ALG ALG
       WHERE ATY.ALG_ENTITY_FLG =  'PPOA' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_PSEG_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_PSEG_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD,
ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG ALG, CI_ALG_TYPE ATY
       WHERE ATY.ALG_ENTITY_FLG =  'PSEG' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_PSPR_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_PSPR_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG ALG, CI_ALG_L ALGL, CI_ALG_TYPE ATY
       WHERE ATY.ALG_ENTITY_FLG =  'PSPR' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_PYDT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_PYDT_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ATY.ALG_TYPE_CD, ALGL.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG_TYPE ATY, CI_ALG ALG
       WHERE ATY.ALG_ENTITY_FLG =  'PYDT' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_SATBC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_SATBC_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG_TYPE ATY, CI_ALG ALG
       WHERE ATY.ALG_ENTITY_FLG =  'BCMP' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_SATFT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_SATFT_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG_TYPE ATY, CI_ALG ALG
       WHERE ATY.ALG_ENTITY_FLG =  'FTFZ' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_SVCR_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_SVCR_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ATY.ALG_TYPE_CD, ALGL.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG_TYPE ATY, CI_ALG ALG
       WHERE ATY.ALG_ENTITY_FLG =  'SVCR' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_SVEV_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_SVEV_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD,
ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG ALG, CI_ALG_TYPE ATY
       WHERE ATY.ALG_ENTITY_FLG =  'SVEV' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_ALG_XAR_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ALG_XAR_VW" ("LANGUAGE_CD", "ALG_TYPE_CD", "ALG_CD", "DESCR50") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ALGL.LANGUAGE_CD, ALG.ALG_TYPE_CD, ALG.ALG_CD, ALGL.DESCR50
       FROM CI_ALG_L ALGL, CI_ALG_TYPE ATY, CI_ALG ALG
       WHERE ATY.ALG_ENTITY_FLG =  'PXAR' AND
ALG.ALG_TYPE_CD = ATY.ALG_TYPE_CD AND
ALGL.ALG_CD = ALG.ALG_CD
ORDER BY ALGL.LANGUAGE_CD
 ;

-- ----- CI_BAL_CTL_MEM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_BAL_CTL_MEM_VW" ("BAL_CTL_GRP_ID", "CIS_DIVISION", "SA_TYPE_CD", "FT_TYPE_FLG", "NBR_OF_FTS", "CUR_AMT", "TOT_AMT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT BAL_CTL_GRP_ID, CIS_DIVISION, SA_TYPE_CD, FT_TYPE_FLG, SUM(NBR_OF_FTS), SUM(CUR_AMT), SUM(TOT_AMT)
FROM CI_BAL_CTL_MEM
WHERE BAL_CTL_TYPE_FLG = 'PROD'
GROUP BY BAL_CTL_GRP_ID, CIS_DIVISION, SA_TYPE_CD, FT_TYPE_FLG
 ;

-- ----- CI_BCHG_READ_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_BCHG_READ_VW" ("BILLABLE_CHG_ID", "SP_ID", "SEQNO", "REG_CONST", "USAGE_FLG", "USE_PCT", "HOW_TO_USE_FLG", "MSR_PEAK_QTY_SW", "UOM_CD", "TOU_CD", "SQI_CD", "START_REG_READ_ID", "START_READ_DTTM", "START_REG_READING", "END_REG_READ_ID", "END_READ_DTTM", "END_REG_READING", "MSR_QTY", "FINAL_UOM_CD", "FINAL_TOU_CD", "FINAL_REG_QTY", "FINAL_SQI", "VERSION", "GC_MULTIPLIER") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_BCHG_READ.BILLABLE_CHG_ID, CI_BCHG_READ.SP_ID, CI_BCHG_READ.SEQNO,
CI_BCHG_READ.REG_CONST, CI_BCHG_READ.USAGE_FLG, CI_BCHG_READ.USE_PCT,
CI_BCHG_READ.HOW_TO_USE_FLG, CI_BCHG_READ.MSR_PEAK_QTY_SW, CI_BCHG_READ.UOM_CD,
CI_BCHG_READ.TOU_CD, CI_BCHG_READ.SQI_CD, CI_BCHG_READ.START_REG_READ_ID,
CI_BCHG_READ.START_READ_DTTM, CI_BCHG_READ.START_REG_READING, CI_BCHG_READ.END_REG_READ_ID,
CI_BCHG_READ.END_READ_DTTM, CI_BCHG_READ.END_REG_READING, CI_BCHG_READ.MSR_QTY,
CI_BCHG_READ.FINAL_UOM_CD, CI_BCHG_READ.FINAL_TOU_CD, CI_BCHG_READ.FINAL_REG_QTY,
CI_BCHG_READ.FINAL_SQI, CI_BCHG_READ.VERSION, DECODE(MSR_QTY, 0, 0, ROUND(FINAL_REG_QTY/MSR_QTY,6))
       FROM CI_BCHG_READ
 ;

-- ----- CI_BCHG_UP_READ_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_BCHG_UP_READ_VW" ("BCHG_UP_ID", "SP_ID", "SEQNO", "REG_CONST", "USAGE_FLG", "USE_PCT", "HOW_TO_USE_FLG", "MSR_PEAK_QTY_SW", "UOM_CD", "TOU_CD", "SQI_CD", "START_REG_READ_ID", "START_READ_DTTM", "START_REG_READING", "END_REG_READ_ID", "END_READ_DTTM", "END_REG_READING", "MSR_QTY", "FINAL_UOM_CD", "FINAL_TOU_CD", "FINAL_REG_QTY", "FINAL_SQI", "VERSION", "GC_MULTIPLIER") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_BCHG_UP_READ.BCHG_UP_ID, CI_BCHG_UP_READ.SP_ID, CI_BCHG_UP_READ.SEQNO,
CI_BCHG_UP_READ.REG_CONST, CI_BCHG_UP_READ.USAGE_FLG, CI_BCHG_UP_READ.USE_PCT,
CI_BCHG_UP_READ.HOW_TO_USE_FLG, CI_BCHG_UP_READ.MSR_PEAK_QTY_SW, CI_BCHG_UP_READ.UOM_CD,
CI_BCHG_UP_READ.TOU_CD, CI_BCHG_UP_READ.SQI_CD, CI_BCHG_UP_READ.START_REG_READ_ID,
CI_BCHG_UP_READ.START_READ_DTTM, CI_BCHG_UP_READ.START_REG_READING,
CI_BCHG_UP_READ.END_REG_READ_ID, CI_BCHG_UP_READ.END_READ_DTTM,
CI_BCHG_UP_READ.END_REG_READING, CI_BCHG_UP_READ.MSR_QTY, CI_BCHG_UP_READ.FINAL_UOM_CD,
CI_BCHG_UP_READ.FINAL_TOU_CD, CI_BCHG_UP_READ.FINAL_REG_QTY, CI_BCHG_UP_READ.FINAL_SQI,
CI_BCHG_UP_READ.VERSION, DECODE(MSR_QTY, 0, 0, ROUND(FINAL_REG_QTY/MSR_QTY,6))
       FROM CI_BCHG_UP_READ
 ;

-- ----- CI_BF_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_BF_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SA.ACCT_ID ,
    LU.LANGUAGE_CD ,
    BF.BUS_FLG_ID ,
    '          ',
    BF.BUS_FLG_DTTM ,
    LU.FIELD_VALUE ,
    LU.DESCR ,
    TO_CHAR(BF.BUS_FLG_DTTM,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM F1_BUS_FLG BF ,
    CI_SA_SP SASP ,
    CI_SA SA ,
    CI_LOOKUP LU,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE BF.MAINT_OBJ_CD       = 'SP'
  AND BF.PK_VALUE1            = SASP.SP_ID
  AND SASP.SA_ID              = SA.SA_ID
  AND SA.SA_STATUS_FLG        < '60'
  AND LU.FIELD_NAME           = 'ACT_TYPE_FLG'
  AND LU.FIELD_VALUE          = 'BF'
  AND BF.BUS_OBJ_CD           = BO.BUS_OBJ_CD
  AND BF.BO_STATUS_CD         = BOS.BO_STATUS_CD
  AND BO.LIFE_CYCLE_BO_CD     = BOS.BUS_OBJ_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL'
  UNION
  SELECT SA.ACCT_ID ,
    LU.LANGUAGE_CD ,
    BF.BUS_FLG_ID ,
    '          ',
    BF.BUS_FLG_DTTM ,
    LU.FIELD_VALUE ,
    LU.DESCR ,
    TO_CHAR(BF.BUS_FLG_DTTM,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM F1_BUS_FLG BF ,
    CI_SP SP,
    CI_SA SA ,
    CI_LOOKUP LU,
    F1_BUS_OBJ_STATUS BOS,
    F1_BUS_OBJ BO
  WHERE BF.MAINT_OBJ_CD       = 'SP'
  AND BF.PK_VALUE1            = SP.SP_ID
  AND SP.PREM_ID              = SA.CHAR_PREM_ID
  AND SA.SA_STATUS_FLG        < '60'
  AND LU.FIELD_NAME           = 'ACT_TYPE_FLG'
  AND LU.FIELD_VALUE          = 'BF'
  AND BF.BUS_OBJ_CD           = BO.BUS_OBJ_CD
  AND BF.BO_STATUS_CD         = BOS.BO_STATUS_CD
  AND BO.LIFE_CYCLE_BO_CD     = BOS.BUS_OBJ_CD
  AND BOS.BO_STATUS_COND_FLG <> 'F1FL';

-- ----- CI_BSEG_READ_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_BSEG_READ_VW" ("BSEG_ID", "SP_ID", "SEQNO", "REG_CONST", "USAGE_FLG", "USE_PCT", "HOW_TO_USE_FLG", "MSR_PEAK_QTY_SW", "UOM_CD", "TOU_CD", "SQI_CD", "START_REG_READ_ID", "START_READ_DTTM", "START_REG_READING", "END_REG_READ_ID", "END_READ_DTTM", "END_REG_READING", "MSR_QTY", "FINAL_UOM_CD", "FINAL_TOU_CD", "VERSION", "FINAL_SQI_CD", "FINAL_REG_QTY", "GC_MULTIPLIER") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_BSEG_READ.BSEG_ID, CI_BSEG_READ.SP_ID, CI_BSEG_READ.SEQNO,
    CI_BSEG_READ.REG_CONST, CI_BSEG_READ.USAGE_FLG, CI_BSEG_READ.USE_PCT,
    CI_BSEG_READ.HOW_TO_USE_FLG, CI_BSEG_READ.MSR_PEAK_QTY_SW, CI_BSEG_READ.UOM_CD,
    CI_BSEG_READ.TOU_CD, CI_BSEG_READ.SQI_CD, CI_BSEG_READ.START_REG_READ_ID,
    CI_BSEG_READ.START_READ_DTTM, CI_BSEG_READ.START_REG_READING,
    CI_BSEG_READ.END_REG_READ_ID, CI_BSEG_READ.END_READ_DTTM,
    CI_BSEG_READ.END_REG_READING, CI_BSEG_READ.MSR_QTY,
    CI_BSEG_READ.FINAL_UOM_CD, CI_BSEG_READ.FINAL_TOU_CD,
    CI_BSEG_READ.VERSION, CI_BSEG_READ.FINAL_SQI_CD,
    CI_BSEG_READ.FINAL_REG_QTY, DECODE(MSR_QTY, 0, 0, ROUND(FINAL_REG_QTY/MSR_QTY,6))
    FROM CI_BSEG_READ
 ;

-- ----- CI_CASE_ST_ALG_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CASE_ST_ALG_VW" ("SORT_SEQ", "CASE_TYPE_CD", "CASE_STATUS_CD", "CASE_ST_SEVT_FLG", "SEQ_NUM", "ALG_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT DECODE(CASE_ST_SEVT_FLG, 'CSEV', 1, 'CSEN', 2, 'CSAT', 3, 'CSXV', 4,
'CSXT', 5, 'C1SL', 6), CASE_TYPE_CD, CASE_STATUS_CD, CASE_ST_SEVT_FLG, SEQ_NUM, ALG_CD
FROM CI_CASE_ST_ALG
WHERE CASE_ST_SEVT_FLG IN ('CSEV', 'CSEN','CSAT','CSXV', 'CSXT', 'C1SL')
WITH READ ONLY
 ;

-- ----- CI_CA_ACCT_HIS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CA_ACCT_HIS_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       CA.ACCT_ID
      ,LU.LANGUAGE_CD
      ,CA.CASE_ID
      ,'          '
      ,CL.LOG_DTTM
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,TO_CHAR(CL.LOG_DTTM,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM CI_CASE         CA
      ,CI_CASE_LOG     CL
      ,CI_LOOKUP       LU
   WHERE
       LU.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LU.FIELD_VALUE = 'CA'
   AND CA.ACCT_ID <> ' '
   AND CL.CASE_ID = CA.CASE_ID
   AND CL.CASE_LOG_TYPE_FLG = 'CASC'
WITH READ ONLY
 ;

-- ----- CI_CC_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CC_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    AP.ACCT_ID,
    LU.LANGUAGE_CD,
    CC.CC_ID,
    AP.PER_ID,
    CC.CC_DTTM,
    LU.FIELD_VALUE,
    LU.DESCR,
    TO_CHAR(CC.CC_DTTM, 'YYYY-MM-DD-HH24.MI.SS') || '.000000'
FROM
    CI_CC CC,
    CI_ACCT_PER AP,
    CI_LOOKUP LU
WHERE
    AP.PER_ID = CC.PER_ID
    AND LU.FIELD_NAME = 'ACT_TYPE_FLG'
    AND LU.FIELD_VALUE = 'CC'
    AND CC.ACCT_ID IS NULL
UNION
SELECT
    CC.ACCT_ID,
    LU.LANGUAGE_CD,
    CC.CC_ID,
    CC.PER_ID,
    CC.CC_DTTM,
    LU.FIELD_VALUE,
    LU.DESCR,
    TO_CHAR(CC.CC_DTTM, 'YYYY-MM-DD-HH24.MI.SS') || '.000000'
FROM
    CI_CC CC,
    CI_LOOKUP LU
WHERE
    LU.FIELD_NAME = 'ACT_TYPE_FLG'
    AND LU.FIELD_VALUE = 'CC'
    AND CC.ACCT_ID IS NOT NULL

WITH READ ONLY;

-- ----- CI_CEVTD_ACCHST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CEVTD_ACCHST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SA.ACCT_ID
     ,LP.LANGUAGE_CD
      ,CE.CUT_PROC_ID
      , RPAD(LPAD(TO_CHAR(CE.EVT_SEQ), 3, '0'),10,' ')
      ,CE.TRIGGER_DT
      ,LP.FIELD_VALUE
      ,LP.DESCR
      ,'4712-12-31-00.00.00.000000'
FROM CI_SA SA , CI_CUT_PROC CP, CI_CUT_EVT CE , CI_CUT_EVT_DEP CED, CI_LOOKUP LP
WHERE
       CE.CUT_EVT_STAT_FLG IN ('10','20')
   AND CE.CUT_PROC_ID = CP.CUT_PROC_ID
   AND CE.TRIGGER_DT IS NULL
   AND CP.SA_ID = SA.SA_ID
   AND CED.CUT_PROC_ID = CE.CUT_PROC_ID
   AND CED.EVT_SEQ = CE.EVT_SEQ
   AND LP.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LP.FIELD_VALUE = 'C1'
 ;

-- ----- CI_CEVT_ACCHST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CEVT_ACCHST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SA.ACCT_ID
     ,LP.LANGUAGE_CD
      ,CE.CUT_PROC_ID
      , RPAD(LPAD(TO_CHAR(CE.EVT_SEQ), 3, '0'),10,' ')
      ,CE.TRIGGER_DT
      ,LP.FIELD_VALUE
      ,LP.DESCR
      ,TO_CHAR(CE.CUT_EVT_STAT_DTTM,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
 FROM CI_SA SA , CI_CUT_PROC CP, CI_CUT_EVT CE , CI_LOOKUP LP
 WHERE
       CE.CUT_EVT_STAT_FLG IN ('10','20')
   AND CE.CUT_PROC_ID = CP.CUT_PROC_ID
   AND CE.TRIGGER_DT IS NOT NULL
   AND CP.SA_ID = SA.SA_ID
   AND LP.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LP.FIELD_VALUE = 'C1'
 ;

-- ----- CI_CE_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CE_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       CP.ACCT_ID
      ,LU.LANGUAGE_CD
      ,CP.COLL_PROC_ID
      ,RPAD(LPAD(TO_CHAR(CE.EVT_SEQ), 3, '0'),10,' ')
      ,CE.TRIGGER_DT
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,TO_CHAR(CE.TRIGGER_DT,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM CI_COLL_PROC   CP
      ,CI_COLL_EVT    CE
      ,CI_LOOKUP       LU
   WHERE CE.COLL_PROC_ID = CP.COLL_PROC_ID
   AND CE.COLL_EVT_STAT_FLG = '10'
   AND LU.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LU.FIELD_VALUE = 'CE'
WITH READ ONLY
 ;

-- ----- CI_CFG_SPMR2_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CFG_SPMR2_VW" ("SP_MTR_HIST_ID", "SP_ID", "MTR_CONFIG_ID", "INSTALL_CONST", "INSTALL_MR_ID", "REMOVAL_MR_ID", "INSTALL_DT", "INSTALL_TM", "REMOVAL_DT", "REMOVAL_TM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
              A.SP_MTR_HIST_ID,
              A.SP_ID,
              A.MTR_CONFIG_ID,
              A.INSTALL_CONST,
              B.MR_ID,
              A.REMOVAL_MR_ID,
              TO_CHAR(C.READ_DTTM,'YYYY-MM-DD'),
              TO_CHAR(C.READ_DTTM,'HH24.MI.SS."000000"'),
              TO_CHAR(A.REMOVAL_DTTM,'YYYY-MM-DD'),
              TO_CHAR(A.REMOVAL_DTTM,'HH24.MI.SS."000000"')
         FROM
              CI_SP_MTR_HIST A,
              CI_SP_MTR_EVT B,
              CI_MR C
        WHERE
              A.SP_MTR_HIST_ID =  B.SP_MTR_HIST_ID
          AND B.SP_MTR_EVT_FLG =  'I'
          AND B.MR_ID =  C.MR_ID
 ;

-- ----- CI_CFG_SPMR_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CFG_SPMR_VW" ("SP_MTR_HIST_ID", "SP_ID", "MTR_CONFIG_ID", "INSTALL_CONST", "INSTALL_MR_ID", "REMOVAL_MR_ID", "INSTALL_DTTM", "REMOVAL_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT A.SP_MTR_HIST_ID, A.SP_ID, A.MTR_CONFIG_ID, A.INSTALL_CONST, B.MR_ID, A.REMOVAL_MR_ID, C.READ_DTTM, A.REMOVAL_DTTM
       FROM CI_SP_MTR_HIST A, CI_SP_MTR_EVT B, CI_MR C
       WHERE A.SP_MTR_HIST_ID =  B.SP_MTR_HIST_ID AND B.SP_MTR_EVT_FLG =  'I' AND B.MR_ID =  C.MR_ID
 ;

-- ----- CI_CHTY_ACC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_ACC_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE C, CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E
       WHERE E.CHAR_ENTITY_FLG =  'ACCT'  AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_ADJT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_ADJT_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE C, CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E
       WHERE E.CHAR_ENTITY_FLG =  'ADJT' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_BCTL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_BCTL_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE C, CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E
       WHERE E.CHAR_ENTITY_FLG =  'BCTL' AND C.CHAR_TYPE_CD =  L.CHAR_TYPE_CD AND C.CHAR_TYPE_CD =  E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_BSCL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_BSCL_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_ENTITY E, CI_CHAR_TYPE_L L, CI_CHAR_TYPE C
       WHERE E.CHAR_ENTITY_FLG =  'BSCL' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_DIV_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_DIV_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE C, CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E
       WHERE E.CHAR_ENTITY_FLG =  'CDIV' AND C.CHAR_TYPE_CD =  L.CHAR_TYPE_CD AND C.CHAR_TYPE_CD =  E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_ITMTY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_ITMTY_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE C, CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E
       WHERE E.CHAR_ENTITY_FLG =  'ITTY' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_ITM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_ITM_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E, CI_CHAR_TYPE C
       WHERE E.CHAR_ENTITY_FLG =  'ITEM' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_MTRTY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_MTRTY_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE C, CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E
       WHERE E.CHAR_ENTITY_FLG =  'MTTY' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_MTR_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_MTR_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E, CI_CHAR_TYPE C
       WHERE E.CHAR_ENTITY_FLG =  'METR' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_PER_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_PER_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE C, CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E
       WHERE E.CHAR_ENTITY_FLG =  'PERS' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_PREM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_PREM_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE C, CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E
       WHERE E.CHAR_ENTITY_FLG =  'PREM' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_SATY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_SATY_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE C, CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E
       WHERE E.CHAR_ENTITY_FLG =  'SATY' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_SA_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_SA_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE C, CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E
       WHERE E.CHAR_ENTITY_FLG =  'SA'  AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_SCMT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_SCMT_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE C, CI_CHAR_ENTITY E, CI_CHAR_TYPE_L L
       WHERE E.CHAR_ENTITY_FLG =  'SCM' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_SPTY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_SPTY_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE C, CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E
       WHERE E.CHAR_ENTITY_FLG =  'SPTY' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CHTY_SP_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CHTY_SP_VW" ("LANGUAGE_CD", "CHAR_TYPE_CD", "ADHOC_VAL_ALG_CD", "CHAR_TYPE_FLG", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.CHAR_TYPE_CD, C.ADHOC_VAL_ALG_CD, C.CHAR_TYPE_FLG, L.DESCR
       FROM CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E, CI_CHAR_TYPE C
       WHERE E.CHAR_ENTITY_FLG =  'SP' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_CO_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CO_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       CRH.ACCT_ID
      ,LU.LANGUAGE_CD
      ,CRH.CR_RATING_HIST_ID
      ,'          '
      ,CRH.START_DT
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,TO_CHAR(CRH.START_DT,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM CI_CR_RAT_HIST CRH
       ,CI_LOOKUP       LU
  WHERE CRH.CASH_ONLY_PTS <> 0
       AND LU.FIELD_NAME = 'ACT_TYPE_FLG'
       AND LU.FIELD_VALUE = 'CO'
WITH READ ONLY
 ;

-- ----- CI_CPROC_ACCHST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CPROC_ACCHST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SA.ACCT_ID
      ,LP.LANGUAGE_CD
      ,CP.CUT_PROC_ID
      , '          '
      ,CP.CRE_DTTM
      ,LP.FIELD_VALUE
      ,LP.DESCR
      ,TO_CHAR(CP.CRE_DTTM,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
 FROM CI_SA SA , CI_CUT_PROC CP, CI_LOOKUP LP
 WHERE
   CP.CUT_STATUS_FLG = '20'
   AND CP.SA_ID = SA.SA_ID
   AND LP.FIELD_NAME = 'ACT_TYPE_FLG'
      AND LP.FIELD_VALUE = 'C2'
WITH READ ONLY
 ;

-- ----- CI_CP_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CP_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CP.ACCT_ID
      ,LU.LANGUAGE_CD
      ,CP.COLL_PROC_ID
      ,'          '
      ,CP.CRE_DTTM
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,TO_CHAR(CP.CRE_DTTM,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM CI_COLL_PROC   CP
      ,CI_LOOKUP       LU
   WHERE
   LU.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LU.FIELD_VALUE = 'CP'
   AND CP.COLL_STATUS_FLG = '20'
WITH READ ONLY
 ;

-- ----- CI_CR_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CR_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       CRH.ACCT_ID
      ,LU.LANGUAGE_CD
      ,CRH.CR_RATING_HIST_ID
      ,'          '
      ,CRH.START_DT
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,TO_CHAR(CRH.START_DT,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM CI_CR_RAT_HIST CRH
      ,CI_LOOKUP       LU
   WHERE CRH.CR_RATING_PTS <> 0
   AND LU.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LU.FIELD_VALUE = 'CR'
WITH READ ONLY
 ;

-- ----- CI_CURRENCY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CURRENCY_VW" ("CURRENCY_CD", "CUR_SYMBOL") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_CURRENCY_CD.CURRENCY_CD, CI_CURRENCY_CD.CUR_SYMBOL
       FROM CI_CURRENCY_CD
 ;

-- ----- CI_CURR_CUST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_CURR_CUST_VW" ("SP_ID", "MTR_ID", "BADGE_NBR", "SVC_TYPE_CD", "ACCT_ID", "CUST_CL_CD", "ADDRESS1_UPR", "ADDRESS1", "ADDRESS2", "ADDRESS3", "ADDRESS4", "COUNTY", "CITY", "STATE", "POSTAL", "LS_SL_FLG") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT /*+RULE */
SP.SP_ID
,MTR.MTR_ID
,MTR.BADGE_NBR
,SPTY.SVC_TYPE_CD
,ACCT.ACCT_ID
,ACCT.CUST_CL_CD
,PREM.ADDRESS1_UPR
,PREM.ADDRESS1
,PREM.ADDRESS2
,PREM.ADDRESS3
,PREM.ADDRESS4
,PREM.COUNTY
,PREM.CITY
,PREM.STATE
,PREM.POSTAL
,PREM.LS_SL_FLG
FROM CI_SP SP
,CI_SP_TYPE SPTY
,CI_PREM PREM
,CI_CFG_SPMR_VW SPM
,CI_MTR_CONFIG MCFG
,CI_MTR MTR
,CI_SA SA
,CI_ACCT ACCT
WHERE SP_STATUS_FLG='R' AND SP_SRC_STATUS_FLG='C'
AND SPTY.SP_TYPE_CD = SP.SP_TYPE_CD
AND PREM.PREM_ID = SP.PREM_ID
AND SPM.SP_ID = SP.SP_ID
AND SPM.REMOVAL_DTTM IS NULL
AND MCFG.MTR_CONFIG_ID = SPM.MTR_CONFIG_ID
AND MTR.MTR_ID = MCFG.MTR_ID
AND ACCT.ACCT_ID = SA.ACCT_ID
AND SA.SA_ID = (SELECT MIN(SASP.SA_ID) FROM CI_SA_SP SASP, CI_SA T
WHERE SASP.SP_ID = SP.SP_ID
AND SASP.START_DTTM <= CURRENT_DATE
AND (SASP.STOP_DTTM >= CURRENT_DATE
OR SASP.STOP_DTTM IS NULL)
AND T.SA_ID = SASP.SA_ID
AND T.SA_STATUS_FLG <> '60'
AND T.SA_STATUS_FLG <> '70'
AND T.SA_STATUS_FLG <> '10' );

-- ----- CI_DEG_MONTH_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_DEG_MONTH_VW" ("TREND_AREA_CD", "YEAR_MONTH", "START_DT", "START_NEXT_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT DISTINCT CI_DEG_DAY.TREND_AREA_CD,
TO_NUMBER(TO_CHAR(DEG_DAY_DT,'YYYYMM'),'999999'),
TO_DATE(TO_CHAR(DEG_DAY_DT,'YYYYMM') || '01', 'YYYYMMDD' ),
ADD_MONTHS(TO_DATE(TO_CHAR(DEG_DAY_DT,'YYYYMM')||'01', 'YYYYMMDD'),1)
FROM CI_DEG_DAY
 ;

-- ----- CI_DVTY_CHTY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_DVTY_CHTY_VW" ("DV_TEST_TYPE_CD", "CHAR_TYPE_CD", "REQURED_SW", "LANGUAGE_CD", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT DTY.DV_TEST_TYPE_CD, DTY.CHAR_TYPE_CD, DTY.REQURED_SW, CTYL.LANGUAGE_CD, CTYL.DESCR
       FROM CI_CHTY_DV_TTYP DTY, CI_CHAR_TYPE_L CTYL
       WHERE DTY.CHAR_TYPE_CD = CTYL.CHAR_TYPE_CD
 ;

-- ----- CI_FA_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_FA_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SA.ACCT_ID
      ,LU.LANGUAGE_CD
      ,FA.FA_ID
      ,FA.SP_ID
      ,FA.SCHED_DTTM
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,TO_CHAR(FA.SCHED_DTTM,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM CI_FA     FA
      ,CI_SA_SP  SASP
      ,CI_SA     SA
      ,CI_LOOKUP       LU
   WHERE FA.SP_ID = SASP.SP_ID
   AND SASP.SA_ID = SA.SA_ID
   AND SA.SA_STATUS_FLG < '60'
   AND FA.FA_STATUS_FLG <> 'X'
   AND LU.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LU.FIELD_VALUE = 'FA'
WITH READ ONLY
 ;

-- ----- CI_FT_GL_XTR_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_FT_GL_XTR_VW" ("FT_ID", "GL_DISTRIB_STATUS") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
                FT.FT_ID, FT.GL_DISTRIB_STATUS
	FROM CI_FT   FT
                WHERE
                 FT.GL_DISTRIB_STATUS IN
                                ( 'M' , 'G' )
                 AND
		NOT EXISTS
		(SELECT 'X' FROM CI_FT_GL GL
			WHERE GL.FT_ID = FT.FT_ID
			        AND GL.GL_ACCT = ' ')
	AND
		EXISTS
		(SELECT 'X' FROM CI_FT_GL GL
			WHERE GL.FT_ID = FT.FT_ID
			        AND GL.GL_ACCT <> ' ')
 ;

-- ----- CI_FT_PROC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_FT_PROC_VW" ("FT_ID", "MAX_SEQ_NUM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_FT_PROC.FT_ID, MAX(CI_FT_PROC.SEQ_NUM)
       FROM CI_FT_PROC
       GROUP BY FT_ID
 ;

-- ----- CI_INSTALLATION -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_INSTALLATION" ("INSTALL_OPT_ID", "QTE_RTE_TYPE_CD", "CAMPAIGN_CD", "TIME_ZONE_CD", "CURRENCY_CD", "LANGUAGE_CD", "COUNTRY", "ID_TYPE_CD_BUS", "ID_TYPE_CD_PER", "CUST_CL_CD_BUS", "CUST_CL_CD_PER", "ACCT_REL_TYPE_CD", "ROLLOVR_THRSH_FACT", "BILL_RTE_TYPE_CD", "OVERRIDE_BIL_DT_SW", "MIN_BILL_PRT_AMT", "START_CASH_ONL_PTS", "START_CR_RAT_PTS", "CASH_ONLY_PTS_THRS", "CR_RAT_THRS", "MAX_DAY_AGE", "HILO_FAILS_SW", "GL_BATCH_CD", "AP_BATCH_CD", "VERSION", "CIS_RELEASE_ID", "QUK_ADD_TNDR_TYP", "STRT_BAL_TNDR_TYP", "CRE_FA_SS_SW", "CHAR_DFLT_DT", "CM_RELEASE_ID", "IB_BASE_TM", "IB_BASE_TM_DAY_FLG", "LICENSE_KEY", "USE_ALT_BILL_ID_SW", "SEAS_TM_SH_REQ_SW", "APAY_CRE_OPT_FLG", "BS_FRZ_OPT_FLG", "ALT_PER_ID_REQ_FLG", "ACTGDT_FRZ_OPT_FLG", "PREM_GEOTY_REQ_FLG", "ALT_REP_FLG", "ADMIN_MENU_ORD_FLG", "CTI_INTGR_FLG", "ENV_ID", "START_STOP_DTL_MAX", "FUND_ACTG_FLG", "BILL_CORR_OPT_FLG", "ALT_BILL_ID_OPT_FLG", "ALT_CURRENCY_FLG", "USR_DIV_CTRL_FLG", "USR_DIV_RESTRICT_FLG", "USE_NAME_SEPARATOR_SW", "NAME_SEPARATOR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT a.INSTALL_OPT_ID,
    a.QTE_RTE_TYPE_CD,
    a.CAMPAIGN_CD,
    b.TIME_ZONE_CD,
    b.CURRENCY_CD,
    b.LANGUAGE_CD,
    b.COUNTRY,
    a.ID_TYPE_CD_BUS,
    a.ID_TYPE_CD_PER,
    a.CUST_CL_CD_BUS,
    a.CUST_CL_CD_PER,
    a.ACCT_REL_TYPE_CD,
    a.ROLLOVR_THRSH_FACT,
    a.BILL_RTE_TYPE_CD,
    a.OVERRIDE_BIL_DT_SW,
    a.MIN_BILL_PRT_AMT,
    a.START_CASH_ONL_PTS,
    a.START_CR_RAT_PTS,
    a.CASH_ONLY_PTS_THRS,
    a.CR_RAT_THRS,
    a.MAX_DAY_AGE,
    a.HILO_FAILS_SW,
    a.GL_BATCH_CD,
    a.AP_BATCH_CD,
    a.VERSION,
    c.RELEASE_ID,
    a.QUK_ADD_TNDR_TYP,
    a.STRT_BAL_TNDR_TYP,
    a.CRE_FA_SS_SW,
    b.CHAR_DFLT_DT,
    d.RELEASE_ID,
    a.IB_BASE_TM,
    a.IB_BASE_TM_DAY_FLG,
    b.LICENSE_KEY,
    a.USE_ALT_BILL_ID_SW,
    b.SEAS_TM_SH_REQ_SW,
    a.APAY_CRE_OPT_FLG,
    a.BS_FRZ_OPT_FLG,
    a.ALT_PER_ID_REQ_FLG,
    a.ACTGDT_FRZ_OPT_FLG,
    a.PREM_GEOTY_REQ_FLG,
    a.ALT_REP_FLG,
    b.ADMIN_MENU_ORD_FLG,
    a.CTI_INTGR_FLG,
    b.ENV_ID,
    a.START_STOP_DTL_MAX,
    a.FUND_ACTG_FLG,
    a.BILL_CORR_OPT_FLG,
    a.ALT_BILL_ID_OPT_FLG,
    a.ALT_CURRENCY_FLG,
    a.USR_DIV_CTRL_FLG,
    a.USR_DIV_RESTRICT_FLG,
	a.USE_NAME_SEPARATOR_SW,
	a.NAME_SEPARATOR
  FROM C0_INSTALLATION a,
    F1_INSTALLATION b,
    cI_INSTALL_PROD c,
    CI_INSTALL_PROD d
  WHERE a.INSTALL_OPT_ID = b.INSTALL_OPT_ID
  AND a.INSTALL_OPT_ID   = c.INSTALL_OPT_ID (+)
  AND a.INSTALL_OPT_ID   = d.INSTALL_OPT_ID
  AND c.OWNER_FLG (+)    = 'C1'
  AND d.OWNER_FLG        = 'CM';

-- ----- CI_ITEEVI_SP_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ITEEVI_SP_VW" ("SP_ITEM_HIST_ID", "SEQNO", "EVENT_DTTM", "SP_ITEM_EVT_FLG", "ITEM_ON_OFF_FLG") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_SP_ITEM_EVT.SP_ITEM_HIST_ID, CI_SP_ITEM_EVT.SEQNO, CI_SP_ITEM_EVT.EVENT_DTTM, CI_SP_ITEM_EVT.SP_ITEM_EVT_FLG, CI_SP_ITEM_EVT.ITEM_ON_OFF_FLG
       FROM CI_SP_ITEM_EVT
       WHERE SP_ITEM_EVT_FLG =  'I'
 ;

-- ----- CI_ITEM_CHTY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ITEM_CHTY_VW" ("LANGUAGE_CD", "ITEM_TYPE_CD", "CHAR_TYPE_CD", "DESCR", "REQUIRED_SW") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.ITEM_TYPE_CD, C.CHAR_TYPE_CD, L.DESCR, C.REQUIRED_SW
       FROM CI_CHTY_ITTY C, CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E
       WHERE E.CHAR_ENTITY_FLG =  'ITEM' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_ITEM_SP_E_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ITEM_SP_E_VW" ("SP_ITEM_HIST_ID", "SP_ID", "INSTALL_DTTM", "ITEM_ID", "REMOVAL_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT HSI.SP_ITEM_HIST_ID, HSI.SP_ID, EVI.EVENT_DTTM, HSI.ITEM_ID, HSI.REMOVAL_DTTM
       FROM CI_SP_ITEM_HIST HSI, CI_ITEEVI_SP_VW EVI
       WHERE HSI.SP_ITEM_HIST_ID = EVI.SP_ITEM_HIST_ID
 ;

-- ----- CI_LOOKUP -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_LOOKUP" ("FIELD_NAME", "FIELD_VALUE", "LANGUAGE_CD", "EFF_STATUS", "VERSION", "DESCR", "OWNER_FLG") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT A.FIELD_NAME, A.FIELD_VALUE, B.LANGUAGE_CD, A.EFF_STATUS, B.VERSION, CASE TRIM(B.DESCR_OVRD) || 'BLANK' WHEN 'BLANK'
THEN B.DESCR ELSE B.DESCR_OVRD END DESCR ,B.OWNER_FLG
FROM CI_LOOKUP_VAL A, CI_LOOKUP_VAL_L B  WHERE A.FIELD_NAME = B.FIELD_NAME  AND A.FIELD_VALUE = B.FIELD_VALUE;

-- ----- CI_MR_RTEGEN_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_MR_RTEGEN_VW" ("MR_CYC_CD", "MR_RTE_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT RTE.MR_CYC_CD, RTE.MR_RTE_CD
       FROM CI_MR_RTE RTE, CI_MR_RTE_TYPE TYP
       WHERE RTE.MR_RTE_TYPE_CD =  TYP.MR_RTE_TYPE_CD AND TYP.CYCLE_GEN_SW =  'Y'
 ;

-- ----- CI_MR_STGUP2_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_MR_STGUP2_VW" ("MR_STAGE_UP_ID_CH", "BADGE_NBR", "READ_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SUBSTR(TO_CHAR(CI_MR_STAGE_UP.MR_STAGE_UP_ID),1,12), CI_MR_STAGE_UP.BADGE_NBR, CI_MR_STAGE_UP.READ_DTTM
       FROM CI_MR_STAGE_UP
 ;

-- ----- CI_MR_STG_UP_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_MR_STG_UP_VW" ("BADGE_NBR", "READ_DTTM", "MR_UP_STATUS_FLG", "MR_ID", "MTR_CONFIG_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_MR_STAGE_UP.BADGE_NBR, TO_CHAR(READ_DTTM, 'YYYY-MM-DD') || ' ' || TO_CHAR(READ_DTTM, 'HH24.MI.SS."000000"'), CI_MR_STAGE_UP.MR_UP_STATUS_FLG, CI_MR_STAGE_UP.MR_ID, CI_MR_STAGE_UP.MTR_CONFIG_ID
       FROM CI_MR_STAGE_UP
 ;

-- ----- CI_MR_ST_EXC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_MR_ST_EXC_VW" ("MR_STAGE_UP_ID_CH", "REVIEW_USER_ID", "MESSAGE_CAT_NBR", "MESSAGE_NBR", "EXP_MSG", "MESSAGE_PARM1", "MESSAGE_PARM2", "MESSAGE_PARM3", "MESSAGE_PARM4", "MESSAGE_PARM5", "MESSAGE_PARM6", "MESSAGE_PARM7", "MESSAGE_PARM8", "MESSAGE_PARM9", "CALL_SEQ", "CRE_DTTM", "REVIEW_COMP", "REVIEW_DT", "VERSION", "USER_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SUBSTR(TO_CHAR(CI_MR_STGUP_EXC.MR_STAGE_UP_ID),1,12), CI_MR_STGUP_EXC.REVIEW_USER_ID, CI_MR_STGUP_EXC.MESSAGE_CAT_NBR, CI_MR_STGUP_EXC.MESSAGE_NBR, CI_MR_STGUP_EXC.EXP_MSG, CI_MR_STGUP_EXC.MESSAGE_PARM1, CI_MR_STGUP_EXC.MESSAGE_PARM2, CI_MR_STGUP_EXC.MESSAGE_PARM3, CI_MR_STGUP_EXC.MESSAGE_PARM4, CI_MR_STGUP_EXC.MESSAGE_PARM5, CI_MR_STGUP_EXC.MESSAGE_PARM6, CI_MR_STGUP_EXC.MESSAGE_PARM7, CI_MR_STGUP_EXC.MESSAGE_PARM8, CI_MR_STGUP_EXC.MESSAGE_PARM9, CI_MR_STGUP_EXC.CALL_SEQ, CI_MR_STGUP_EXC.CRE_DTTM, CI_MR_STGUP_EXC.REVIEW_COMP, CI_MR_STGUP_EXC.REVIEW_DT, CI_MR_STGUP_EXC.VERSION, CI_MR_STGUP_EXC.USER_ID
       FROM CI_MR_STGUP_EXC
 ;

-- ----- CI_MR_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_MR_VW" ("MR_ID", "MTR_CONFIG_ID", "READ_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_MR.MR_ID, CI_MR.MTR_CONFIG_ID, TO_DATE(TO_CHAR(CI_MR.READ_DTTM,'YYYYMMDD')
,'YYYYMMDD') FROM CI_MR
 ;

-- ----- CI_MTR_CHTY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_MTR_CHTY_VW" ("LANGUAGE_CD", "MTR_TYPE_CD", "CHAR_TYPE_CD", "DESCR", "REQUIRED_SW") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.MTR_TYPE_CD, C.CHAR_TYPE_CD, L.DESCR, C.REQUIRED_SW
       FROM CI_CHTY_MTTY C, CI_CHAR_TYPE_L L, CI_CHAR_ENTITY E
       WHERE E.CHAR_ENTITY_FLG =  'METR' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
 ;

-- ----- CI_MTR_CNFG2_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_MTR_CNFG2_VW" ("MTR_CONFIG_TY_CD", "MTR_ID", "MTR_CONFIG_ID", "EFF_DT", "EFF_TM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_MTR_CONFIG.MTR_CONFIG_TY_CD, CI_MTR_CONFIG.MTR_ID, CI_MTR_CONFIG.MTR_CONFIG_ID, TO_CHAR(EFF_DTTM, 'YYYY-MM-DD'), TO_CHAR(EFF_DTTM, 'HH24.MI.SS."000000"')
       FROM CI_MTR_CONFIG
 ;

-- ----- CI_MTR_CNFG_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_MTR_CNFG_VW" ("MTR_ID", "MTR_CONFIG_ID", "READ_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_MTR_CONFIG.MTR_ID, CI_MTR_CONFIG.MTR_CONFIG_ID, TO_CHAR(EFF_DTTM, 'YYYY-MM-DD') || ' ' || TO_CHAR(EFF_DTTM, 'HH24.MI.SS."000000"')
       FROM CI_MTR_CONFIG
 ;

-- ----- CI_NT_UP_EXC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_NT_UP_EXC_VW" ("NT_UP_ID", "NT_UP_ID_CH", "MESSAGE_CAT_NBR", "MESSAGE_NBR", "EXP_MSG", "MESSAGE_PARM1", "MESSAGE_PARM2", "MESSAGE_PARM3", "MESSAGE_PARM4", "MESSAGE_PARM5", "MESSAGE_PARM6", "MESSAGE_PARM7", "MESSAGE_PARM8", "MESSAGE_PARM9") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_UP_ID, SUBSTR(TO_CHAR(CI_NT_UP_EXCP.NT_UP_ID),1,12),
CI_NT_UP_EXCP.MESSAGE_CAT_NBR, CI_NT_UP_EXCP.MESSAGE_NBR,
CI_NT_UP_EXCP.EXP_MSG,
CI_NT_UP_EXCP.MESSAGE_PARM1, CI_NT_UP_EXCP.MESSAGE_PARM2,
CI_NT_UP_EXCP.MESSAGE_PARM3,
CI_NT_UP_EXCP.MESSAGE_PARM4, CI_NT_UP_EXCP.MESSAGE_PARM5,
CI_NT_UP_EXCP.MESSAGE_PARM6,
CI_NT_UP_EXCP.MESSAGE_PARM7, CI_NT_UP_EXCP.MESSAGE_PARM8,
CI_NT_UP_EXCP.MESSAGE_PARM9
FROM CI_NT_UP_EXCP
 ;

-- ----- CI_ODEVTD_ACCHST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ODEVTD_ACCHST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT OP.ACCT_ID
,LP.LANGUAGE_CD
,OE.OD_PROC_ID
,RPAD(LPAD(TO_CHAR(OE.EVT_SEQ), 3, '0'),10,' ')
,OE.TRIGGER_DT
,LP.FIELD_VALUE
,LP.DESCR
,'4712-12-31-00.00.00.000000'
FROM CI_OD_PROC OP, CI_OD_EVT OE , CI_OD_EVT_DEP OED, CI_LOOKUP LP
WHERE
OE.OD_EVT_STAT_FLG IN ('10','20')
AND OE.OD_PROC_ID = OP.OD_PROC_ID
AND OE.TRIGGER_DT IS NULL
AND OED.OD_PROC_ID = OE.OD_PROC_ID
AND OED.EVT_SEQ = OE.EVT_SEQ
AND LP.FIELD_NAME = 'ACT_TYPE_FLG'
AND LP.FIELD_VALUE = 'OE'
 ;

-- ----- CI_ODEVT_ACCHST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ODEVT_ACCHST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT OP.ACCT_ID
,LP.LANGUAGE_CD
,OE.OD_PROC_ID
,RPAD(LPAD(TO_CHAR(OE.EVT_SEQ), 3, '0'),10,' ')
,OE.TRIGGER_DT
,LP.FIELD_VALUE
,LP.DESCR
,TO_CHAR(OE.OD_EVT_STAT_DTTM,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
FROM CI_OD_PROC OP, CI_OD_EVT OE , CI_LOOKUP LP
WHERE
OE.OD_EVT_STAT_FLG IN ('10','20')
AND OE.OD_PROC_ID = OP.OD_PROC_ID
AND OE.TRIGGER_DT IS NOT NULL
AND LP.FIELD_NAME = 'ACT_TYPE_FLG'
AND LP.FIELD_VALUE = 'OE'
 ;

-- ----- CI_ODPRC_ACCHST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ODPRC_ACCHST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT OP.ACCT_ID
      ,LP.LANGUAGE_CD
      ,OP.OD_PROC_ID
      , '          '
      ,OP.CRE_DTTM
      ,LP.FIELD_VALUE
      ,LP.DESCR
      ,TO_CHAR(OP.CRE_DTTM,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
 FROM CI_OD_PROC OP, CI_LOOKUP LP
 WHERE
       OP.OD_STATUS_FLG = '20'
   AND LP.FIELD_NAME = 'ACT_TYPE_FLG'
      AND LP.FIELD_VALUE = 'OP'
WITH READ ONLY
 ;

-- ----- CI_OMS_DEVICE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_OMS_DEVICE_VW" ("SP_ID", "DEVICE_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SPG_DEV.SP_ID SP_ID,
       SPG_DEV.GEO_VAL DEVICE_ID
  FROM CI_SP_GEO SPG_DEV
 WHERE TRIM (SPG_DEV.GEO_TYPE_CD)=
              (SELECT TRIM (WFO.WFM_OPT_VAL)
                     FROM CI_WFM WFM,
                       CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='DVCE')
UNION
SELECT SP.SP_ID SP_ID, NULL DEVICE_ID
  FROM CI_SP SP
 WHERE NOT EXISTS (SELECT 'X'
	   FROM CI_SP_GEO SPG_DEV
			  WHERE SPG_DEV.SP_ID = SP.SP_ID
			    AND TRIM (SPG_DEV.GEO_TYPE_CD)
 = (SELECT TRIM (WFO.WFM_OPT_VAL)
   FROM CI_WFM WFM,
        CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='DVCE'))
 ;

-- ----- CI_OMS_FEEDER_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_OMS_FEEDER_VW" ("SP_ID", "FEEDER_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SPG_DEV.SP_ID SP_ID ,
       SPG_DEV.GEO_VAL FEEDER_ID
  FROM CI_SP_GEO SPG_DEV
 WHERE TRIM(SPG_DEV.GEO_TYPE_CD)
             = (SELECT TRIM(WFO.WFM_OPT_VAL)
                     FROM CI_WFM WFM,
                       CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='FEED')
UNION
SELECT SP.SP_ID SP_ID, NULL FEEDER_ID
  FROM CI_SP SP
 WHERE NOT EXISTS(SELECT 'X'
	  		   FROM CI_SP_GEO SPG_DEV
			  WHERE SPG_DEV.SP_ID = SP.SP_ID
			    AND TRIM(SPG_DEV.GEO_TYPE_CD)
 = (SELECT TRIM(WFO.WFM_OPT_VAL)
   FROM CI_WFM WFM,
        CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='FEED'))
 ;

-- ----- CI_OMS_PHONE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_OMS_PHONE_VW" ("PER_ID", "COUNTRY_CODE", "PHONE", "EXTENSION", "PHONE_TYPE_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT PER.PER_ID,
       COUNTRY_CODE,
       PHONE,
       EXTENSION,
       PHONE_TYPE_CD
  FROM CI_PER PER
	   ,CI_PER_PHONE PHONE
 WHERE PHONE.PER_ID = PER.PER_ID
   AND PER.PER_OR_BUS_FLG = 'P'
   AND TRIM(PHONE_TYPE_CD)
     = (SELECT TRIM(WFO.WFM_OPT_VAL)
       FROM CI_WFM WFM,
      CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='PPHN')
   AND PHONE.SEQ_NUM
= (SELECT MIN(SEQ_NUM)
     FROM CI_PER_PHONE PHONE2
  	  	    WHERE PHONE2.PER_ID = PER.PER_ID
		      AND PHONE2.PHONE_TYPE_CD = PHONE.PHONE_TYPE_CD)
UNION
SELECT PER.PER_ID, COUNTRY_CODE, PHONE, EXTENSION, PHONE_TYPE_CD
  FROM CI_PER PER
	   ,CI_PER_PHONE PHONE
 WHERE PHONE.PER_ID = PER.PER_ID
   AND PER.PER_OR_BUS_FLG = 'B'
   AND TRIM(PHONE_TYPE_CD)
  = (SELECT TRIM(WFO.WFM_OPT_VAL)
       FROM CI_WFM WFM,
      CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='BPHN')
   AND PHONE.SEQ_NUM
= (SELECT MIN(SEQ_NUM)
     FROM CI_PER_PHONE PHONE2
		    WHERE PHONE2.PER_ID = PER.PER_ID
		      AND PHONE2.PHONE_TYPE_CD = PHONE.PHONE_TYPE_CD)
UNION
SELECT PER.PER_ID, COUNTRY_CODE, PHONE, EXTENSION, PHONE_TYPE_CD
 FROM CI_PER PER
  ,CI_PER_PHONE PHONE
WHERE PHONE.PER_ID = PER.PER_ID
  AND PER.PER_OR_BUS_FLG = 'P'
  AND NOT EXISTS (SELECT 'X'
    FROM CI_PER_PHONE PHONE3
	 		   WHERE PHONE3.PER_ID = PER.PER_ID
			     AND TRIM(PHONE3.PHONE_TYPE_CD)
   = (SELECT TRIM(WFO.WFM_OPT_VAL)
       			    FROM CI_WFM WFM,
      			     CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='PPHN'))
  AND PHONE.SEQ_NUM = (SELECT MIN(SEQ_NUM)
 FROM CI_PER_PHONE PHONE2
		WHERE PHONE2.PER_ID = PER.PER_ID)
UNION
SELECT PER.PER_ID, COUNTRY_CODE, PHONE, EXTENSION, PHONE_TYPE_CD
  FROM CI_PER PER
   ,CI_PER_PHONE PHONE
 WHERE PHONE.PER_ID = PER.PER_ID
   AND PER.PER_OR_BUS_FLG = 'B'
   AND NOT EXISTS (SELECT 'X'
    FROM CI_PER_PHONE PHONE3
  	  	  	   WHERE PHONE3.PER_ID = PER.PER_ID
			     AND TRIM(PHONE3.PHONE_TYPE_CD)
= (SELECT TRIM(WFO.WFM_OPT_VAL)
       			     FROM CI_WFM WFM,
      				   CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='BPHN'))
   AND PHONE.SEQ_NUM = (SELECT MIN(SEQ_NUM)
  FROM CI_PER_PHONE PHONE2
  	  			 WHERE PHONE2.PER_ID = PER.PER_ID)
UNION
SELECT PER.PER_ID, NULL COUNTRY_CODE, NULL PHONE, NULL EXTENSION, NULL PHONE_TYPE_CD
  FROM CI_PER PER
 WHERE NOT EXISTS (SELECT 'X'
 FROM CI_PER_PHONE PHONE4
			   WHERE PHONE4.PER_ID = PER.PER_ID)
 ;

-- ----- CI_OMS_PRIC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_OMS_PRIC_VW" ("SP_ID", "C_PRIORITY") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SP_ID SP_ID,
       CHAR_VAL C_PRIORITY
  FROM CI_SP_CHAR SPC
 WHERE TRIM(SPC.CHAR_TYPE_CD)
        = (SELECT TRIM(WFO.WFM_OPT_VAL)
             FROM CI_WFM WFM,
                  CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='PRIC')
   AND SPC.EFFDT
= (SELECT MAX(SPC2.EFFDT)
               FROM CI_SP_CHAR SPC2
              WHERE SPC2.SP_ID = SPC.SP_ID
                AND SPC2.CHAR_TYPE_CD = SPC.CHAR_TYPE_CD
                AND SPC2.EFFDT <= CURRENT_DATE)
UNION
SELECT SP_ID SP_ID, '0' C_PRIORITY
  FROM CI_SP SP
 WHERE NOT EXISTS (SELECT 'X'
 FROM CI_SP_CHAR SPC
WHERE SPC.SP_ID = SP.SP_ID
    AND TRIM(SPC.CHAR_TYPE_CD)
 = (SELECT TRIM(WFO.WFM_OPT_VAL)
   FROM CI_WFM WFM,
        CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='PRIC'));

-- ----- CI_OMS_PRIK_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_OMS_PRIK_VW" ("SP_ID", "K_PRIORITY") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SP_ID SP_ID,
       CHAR_VAL K_PRIORITY
  FROM CI_SP_CHAR SPC
 WHERE TRIM(SPC.CHAR_TYPE_CD)
      = (SELECT TRIM(WFO.WFM_OPT_VAL)
FROM CI_WFM WFM,
                  CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='PRIK')
   AND SPC.EFFDT
= (SELECT MAX(SPC2.EFFDT)
               FROM CI_SP_CHAR SPC2
              WHERE SPC2.SP_ID = SPC.SP_ID
                AND SPC2.CHAR_TYPE_CD = SPC.CHAR_TYPE_CD
                AND SPC2.EFFDT <= CURRENT_DATE)
UNION
SELECT SP_ID SP_ID, '0' K_PRIORITY
  FROM CI_SP SP
 WHERE NOT EXISTS (SELECT 'X'
 FROM CI_SP_CHAR SPC
WHERE SPC.SP_ID = SP.SP_ID
                             AND TRIM(SPC.CHAR_TYPE_CD)
 = (SELECT TRIM(WFO.WFM_OPT_VAL)
   FROM CI_WFM WFM,
        CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='PRIK'));

-- ----- CI_OMS_PRIM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_OMS_PRIM_VW" ("SP_ID", "M_PRIORITY") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SP_ID SP_ID,
       CHAR_VAL M_PRIORITY
  FROM CI_SP_CHAR SPC
 WHERE TRIM(SPC.CHAR_TYPE_CD)
      = (SELECT TRIM(WFO.WFM_OPT_VAL)
               FROM CI_WFM WFM,
                    CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='PRIM')
   AND SPC.EFFDT
= (SELECT MAX(SPC2.EFFDT)
               FROM CI_SP_CHAR SPC2
              WHERE SPC2.SP_ID = SPC.SP_ID
                AND SPC2.CHAR_TYPE_CD = SPC.CHAR_TYPE_CD
                AND SPC2.EFFDT <= CURRENT_DATE)
UNION
SELECT SP_ID SP_ID, '0' M_PRIORITY
  FROM CI_SP SP
 WHERE NOT EXISTS (SELECT 'X'
 FROM CI_SP_CHAR SPC
WHERE SPC.SP_ID = SP.SP_ID
AND TRIM(SPC.CHAR_TYPE_CD)
 = (SELECT TRIM(WFO.WFM_OPT_VAL)
   FROM CI_WFM WFM,
        CI_WFM_OPT WFO
  WHERE WFM.EXT_SYS_TYP_FLG = 'OMS'
       AND WFM.WFM_NAME = WFO.WFM_NAME
       AND WFO.EXT_OPT_TYPE='PRIM'));

-- ----- CI_PAY_TND_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_PAY_TND_VW" ("PAY_EVENT_ID", "ACCT_ID", "PAY_OR_TNDR_AMT", "PAY_OR_TNDR_FLG", "PAY_OR_TNDR_ST_FLG") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT A.PAY_EVENT_ID, A.PAYOR_ACCT_ID, A.TENDER_AMT, 'TN', A.TNDR_STATUS_FLG
       FROM CI_PAY_TNDR A
 ;

-- ----- CI_PAY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_PAY_VW" ("PAY_EVENT_ID", "ACCT_ID", "PAY_OR_TNDR_AMT", "PAY_OR_TNDR_FLG", "PAY_OR_TNDR_ST_FLG") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT A.PAY_EVENT_ID, A.ACCT_ID, A.PAY_AMT, 'PY', A.PAY_STATUS_FLG    FROM CI_PAY A
 ;

-- ----- CI_PA_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_PA_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       SA.ACCT_ID
      ,LU.LANGUAGE_CD
      ,SA.SA_ID
      ,'          '
      ,SA.START_DT
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,TO_CHAR(SA.START_DT,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM CI_SA        SA
      ,CI_SA_TYPE   SAT
      ,CI_LOOKUP       LU
   WHERE SA.CIS_DIVISION = SAT.CIS_DIVISION
   AND SA.SA_TYPE_CD = SAT.SA_TYPE_CD
   AND SA.SA_STATUS_FLG < '70'
   AND SAT.SPECIAL_ROLE_FLG = 'PA'
   AND LU.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LU.FIELD_VALUE = 'PA'
WITH READ ONLY
 ;

-- ----- CI_PER_PRIM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_PER_PRIM_VW" ("PER_ID", "ENTITY_NAME") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT A.PER_ID, A.ENTITY_NAME
       FROM CI_PER_NAME A
       WHERE A.NAME_TYPE_FLG =  'PRIM'
 ;

-- ----- CI_PP_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_PP_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       PP.ACCT_ID
      ,LU.LANGUAGE_CD
      ,PP.PP_ID
      ,'          '
      ,PPS.PP_SCHED_DT
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,TO_CHAR(PPS.PP_SCHED_DT,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM CI_PP            PP
      ,CI_PP_SCHED_PAY  PPS
      ,CI_CURRENCY_CD   CR
      ,CI_LOOKUP        LU
   WHERE PP.PP_ID = PPS.PP_ID
   AND PP.PP_STAT_FLG <> '30'
   AND PPS.CURRENCY_CD = CR.CURRENCY_CD
   AND LU.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LU.FIELD_VALUE = 'PP'
WITH READ ONLY
 ;

-- ----- CI_RC_ACCT_HIS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_RC_ACCT_HIS_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       RC.ACCT_ID
      ,LU.LANGUAGE_CD
      ,RC.REBATE_CLAIM_ID
      ,'          '
      ,RCL.LOG_DTTM
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,TO_CHAR(RCL.LOG_DTTM,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM CI_REBATE_CLAIM  RC
      ,CI_REBATE_CLAIM_LOG RCL
      ,CI_LOOKUP        LU
   WHERE LU.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LU.FIELD_VALUE = 'RC'
   AND RC.ACCT_ID <> ' '
   AND RCL.REBATE_CLAIM_ID = RC.REBATE_CLAIM_ID
   AND RCL.LOG_ENTRY_TYPE_FLG = 'F1CR'
WITH READ ONLY
 ;

-- ----- CI_REGRD_SEL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_REGRD_SEL_VW" ("REVIEW_HILO_SW", "TRENDED_SW", "REG_READ_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_REG_READ.REVIEW_HILO_SW, CI_REG_READ.TRENDED_SW, CI_REG_READ.REG_READ_ID
       FROM CI_REG_READ
 ;

-- ----- CI_ROOT_OBJ_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_ROOT_OBJ_VW" ("ROOT_OBJ_ID", "ENV_REF_CD", "MAINT_OBJ_CD", "ROOT_ACTION_FLG", "ROOT_STATUS_FLG", "VERSION", "BATCH_CD", "BATCH_NBR", "FLD_VAL1", "FLD_VAL2", "FLD_VAL3", "FLD_VAL4", "FLD_VAL5", "FLD_VAL6", "FLD_VAL7", "FLD_VAL8", "FLD_VAL9", "FLD_VAL10") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
RO.ROOT_OBJ_ID,
RO.ENV_REF_CD,
RO.MAINT_OBJ_CD,
RO.ROOT_ACTION_FLG,
RO.ROOT_STATUS_FLG,
RO.VERSION,
RO.BATCH_CD,
RO.BATCH_NBR,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 1) as fld_val1,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 2) as  fld_val2,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 3)  as fld_val3,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 4)  as fld_val4,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 5)  as fld_val5,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 6)  as fld_val6,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 7)  as fld_val7,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 8)  as fld_val8,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 9)  as fld_val9,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 10)  as fld_val10
from ci_root_obj RO

 
 
 
 ;

-- ----- CI_RV_BF_RDR_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_RV_BF_RDR_VW" ("RS_CD", "EFFDT", "BF_CD", "DESCR", "LANGUAGE_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT RC.RS_CD, RC.EFFDT, RC.BF_CD, BFL.DESCR, BFL.LANGUAGE_CD
       FROM CI_BF BF, CI_BF_L BFL, CI_RC RC, CI_RV RV
       WHERE RC.BF_CD=BF.BF_CD AND
BF.APPL_IN_CONT_SW='Y' AND
RC.RS_CD=RV.RS_CD AND
RC.EFFDT=RV.EFFDT AND
RV.RV_STATUS_FLG= 'F' AND
BFL.BF_CD=BF.BF_CD
 ;

-- ----- CI_RV_BF_TXE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_RV_BF_TXE_VW" ("RS_CD", "EFFDT", "BF_CD", "DESCR", "LANGUAGE_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT RC.RS_CD, RC.EFFDT, RC.BF_CD, BFL.DESCR, BFL.LANGUAGE_CD
       FROM CI_BF_L BFL, CI_BF BF, CI_RC RC, CI_RV RV
       WHERE RC.BF_CD=BF.BF_CD AND
BF.EXEMPT_IN_CONT_SW='Y' AND
RC.RS_CD=RV.RS_CD AND
RC.EFFDT=RV.EFFDT AND
RV.RV_STATUS_FLG='F' AND
BF.BF_CD = BFL.BF_CD
 ;

-- ----- CI_RV_BF_VAL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_RV_BF_VAL_VW" ("RS_CD", "EFFDT", "BF_CD", "DESCR", "LANGUAGE_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT RC.RS_CD, RC.EFFDT, RC.BF_CD, BFL.DESCR, BFL.LANGUAGE_CD
       FROM CI_BF BF, CI_BF_L BFL, CI_RC RC, CI_RV RV
       WHERE RC.BF_CD=BF.BF_CD AND
BF.VAL_IN_CONT_SW='Y' AND
RC.RS_CD=RV.RS_CD AND
RC.EFFDT=RV.EFFDT AND
RV.RV_STATUS_FLG='F' AND
BF.BF_CD = BFL.BF_CD
 ;

-- ----- CI_SA_IREG_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_SA_IREG_VW" ("SA_ID", "SP_ID", "SA_SP_ID", "START_MR_ID", "STOP_MR_ID", "USAGE_FLG", "START_DTTM", "STOP_DTTM", "SP_MTR_HIST_ID", "MTR_CONFIG_ID", "INSTALL_DTTM", "REMOVAL_DTTM", "MTR_ID", "EFF_DTTM", "REG_ID", "HOW_TO_USE_FLG", "UOM_CD", "INTV_MINUTE", "SQI_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT A.SA_ID, A.SP_ID, A.SA_SP_ID, A.START_MR_ID, A.STOP_MR_ID, A.USAGE_FLG, A.START_DTTM, A.STOP_DTTM, B.SP_MTR_HIST_ID, B.MTR_CONFIG_ID, B.INSTALL_DTTM, B.REMOVAL_DTTM, C.MTR_ID, C.EFF_DTTM, D.REG_ID, D.HOW_TO_USE_FLG, E.UOM_CD, E.INTV_MINUTE, E.SQI_CD
FROM CI_SA_SP A, CI_CFG_SPMR_VW B, CI_MTR_CONFIG C, CI_INTV_REG_TYP E, CI_REG D
WHERE B.SP_ID = A.SP_ID AND
(B.REMOVAL_DTTM IS NULL OR
 B.REMOVAL_DTTM >= A.START_DTTM) AND
(A.STOP_DTTM IS NULL OR
 B.INSTALL_DTTM <= A.STOP_DTTM) AND
C.MTR_CONFIG_ID = B.MTR_CONFIG_ID AND
D.MTR_ID = C.MTR_ID AND
D.EFF_DTTM = C.EFF_DTTM AND
D.INTV_REG_TYPE_CD = E.INTV_REG_TYPE_CD
 ;

-- ----- CI_SA_RDR_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_SA_RDR_VW" ("SA_ID", "CONTERM_TYPE_FLG", "BF_CD", "START_DT", "END_DT", "PCT_EXEMPT", "TAX_CERT", "TAX_EX_TYPE_CD", "VAL") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_SA_CONTERM.SA_ID, CI_SA_CONTERM.CONTERM_TYPE_FLG, CI_SA_CONTERM.BF_CD, CI_SA_CONTERM.START_DT, CI_SA_CONTERM.END_DT, CI_SA_CONTERM.PCT_EXEMPT, CI_SA_CONTERM.TAX_CERT, CI_SA_CONTERM.TAX_EX_TYPE_CD, CI_SA_CONTERM.VAL
       FROM CI_SA_CONTERM
       WHERE CONTERM_TYPE_FLG =  'R'
 ;

-- ----- CI_SA_SP_DT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_SA_SP_DT_VW" ("SP_ID", "SA_SP_ID", "SA_ID", "START_DTTM", "START_DT", "START_TM", "START_MR_ID", "STOP_DTTM", "STOP_DT", "STOP_TM", "USAGE_FLG", "STOP_MR_ID", "USE_PCT", "VERSION") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
              SP_ID,
              SA_SP_ID,
              SA_ID,
              START_DTTM,
              TO_CHAR(START_DTTM,'YYYY-MM-DD'),
              TO_CHAR(START_DTTM,'HH24.MI.SS."000000"'),
              START_MR_ID,
              STOP_DTTM,
              TO_CHAR(STOP_DTTM,'YYYY-MM-DD'),
              TO_CHAR(STOP_DTTM,'HH24.MI.SS."000000"'),
              USAGE_FLG,
              STOP_MR_ID,
              USE_PCT,
              VERSION
         FROM
              CI_SA_SP
 ;

-- ----- CI_SA_TXE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_SA_TXE_VW" ("SA_ID", "CONTERM_TYPE_FLG", "BF_CD", "START_DT", "END_DT", "PCT_EXEMPT", "TAX_CERT", "TAX_EX_TYPE_CD", "VAL") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_SA_CONTERM.SA_ID, CI_SA_CONTERM.CONTERM_TYPE_FLG, CI_SA_CONTERM.BF_CD, CI_SA_CONTERM.START_DT, CI_SA_CONTERM.END_DT, CI_SA_CONTERM.PCT_EXEMPT, CI_SA_CONTERM.TAX_CERT, CI_SA_CONTERM.TAX_EX_TYPE_CD, CI_SA_CONTERM.VAL
       FROM CI_SA_CONTERM
       WHERE CONTERM_TYPE_FLG =  'T'
 ;

-- ----- CI_SA_VAL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_SA_VAL_VW" ("SA_ID", "CONTERM_TYPE_FLG", "BF_CD", "TOU_GRP_CD", "START_DT", "END_DT", "PCT_EXEMPT", "TAX_CERT", "TAX_EX_TYPE_CD", "VAL") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT CI_SA_CONTERM.SA_ID, CI_SA_CONTERM.CONTERM_TYPE_FLG, CI_SA_CONTERM.BF_CD,
CI_SA_CONTERM.TOU_GRP_CD, CI_SA_CONTERM.START_DT, CI_SA_CONTERM.END_DT,       CI_SA_CONTERM.PCT_EXEMPT, CI_SA_CONTERM.TAX_CERT, CI_SA_CONTERM.TAX_EX_TYPE_CD,        CI_SA_CONTERM.VAL
FROM CI_SA_CONTERM
WHERE CONTERM_TYPE_FLG =  'V'
 ;

-- ----- CI_SCTY_VAL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_SCTY_VAL_VW" ("LANGUAGE_CD", "SC_TYPE_CD", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT DISTINCT L.LANGUAGE_CD, S.SC_TYPE_CD, L.DESCR
   FROM CI_APP_SVC_SCTY S, CI_SC_TYPE_L L, SC_USR_GRP_PROF U
   WHERE S.APP_SVC_ID =  U.APP_SVC_ID AND
         L.SC_TYPE_CD = S.SC_TYPE_CD

 
 
 
 ;

-- ----- CI_SED_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_SED_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       SA.ACCT_ID
      ,LU.LANGUAGE_CD
      ,SEVP.SEV_PROC_ID
      ,RPAD(LPAD(TO_CHAR(SE.EVT_SEQ), 3, '0'),10,' ')
      ,SE.TRIGGER_DT
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,'4712-12-31-00.00.00.000000'
  FROM CI_SEV_PROC    SEVP
      ,CI_SA          SA
      ,CI_SEV_EVT     SE
      ,CI_SEV_EVT_DEP SED
      ,CI_LOOKUP       LU
   WHERE SEVP.SA_ID = SA.SA_ID
   AND SA.SA_STATUS_FLG < '70'
   AND SE.SEV_PROC_ID = SEVP.SEV_PROC_ID
   AND SE.TRIGGER_DT IS NULL
   AND SED.SEV_PROC_ID = SE.SEV_PROC_ID
   AND SED.EVT_SEQ = SE.EVT_SEQ
   AND SE.SEV_EVT_STAT_FLG IN ('10', '20')
   AND LU.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LU.FIELD_VALUE = 'SE'
WITH READ ONLY
 ;

-- ----- CI_SE_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_SE_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       SA.ACCT_ID
      ,LU.LANGUAGE_CD
      ,SEVP.SEV_PROC_ID
      ,RPAD(LPAD(TO_CHAR(SE.EVT_SEQ), 3, '0'),10,' ')
      ,SE.TRIGGER_DT
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,TO_CHAR(SE.TRIGGER_DT,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM CI_SEV_PROC    SEVP
      ,CI_SA          SA
      ,CI_SEV_EVT     SE
      ,CI_LOOKUP       LU
   WHERE SEVP.SA_ID = SA.SA_ID
   AND SA.SA_STATUS_FLG < '70'
   AND SE.SEV_PROC_ID = SEVP.SEV_PROC_ID
   AND SE.TRIGGER_DT IS NOT NULL
   AND SE.SEV_EVT_STAT_FLG IN ('10', '20')
   AND LU.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LU.FIELD_VALUE = 'SE'
WITH READ ONLY
 ;

-- ----- CI_SP_CHTY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_SP_CHTY_VW" ("LANGUAGE_CD", "SP_TYPE_CD", "CHAR_TYPE_CD", "DESCR", "REQUIRED_SW") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT L.LANGUAGE_CD, C.SP_TYPE_CD, C.CHAR_TYPE_CD, L.DESCR, C.REQUIRED_SW
       FROM CI_CHTY_SPTY C, CI_CHAR_ENTITY E, CI_CHAR_TYPE_L L
       WHERE E.CHAR_ENTITY_FLG =  'SP' AND
C.CHAR_TYPE_CD = L.CHAR_TYPE_CD AND
C.CHAR_TYPE_CD = E.CHAR_TYPE_CD
ORDER BY LANGUAGE_CD
 ;

-- ----- CI_SP_IT_EV_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_SP_IT_EV_VW" ("SP_ITEM_HIST_ID", "SP_ID", "ITEM_ID", "EVENT_DTTM", "SP_ITEM_EVT_FLG", "ITEM_ON_OFF_FLG") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT A.SP_ITEM_HIST_ID, A.SP_ID, A.ITEM_ID, B.EVENT_DTTM, B.SP_ITEM_EVT_FLG, B.ITEM_ON_OFF_FLG
       FROM CI_SP_ITEM_HIST A, CI_SP_ITEM_EVT B
       WHERE A.SP_ITEM_HIST_ID =  B.SP_ITEM_HIST_ID
 ;

-- ----- CI_SP_MTR_EV_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_SP_MTR_EV_VW" ("SP_MTR_HIST_ID", "SP_ID", "MTR_CONFIG_ID", "MR_ID", "SP_MTR_EVT_FLG", "MTR_ON_OFF_FLG", "READ_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT A.SP_MTR_HIST_ID, A.SP_ID, A.MTR_CONFIG_ID, B.MR_ID, B.SP_MTR_EVT_FLG, B.MTR_ON_OFF_FLG, C.READ_DTTM
       FROM CI_SP_MTR_HIST A, CI_SP_MTR_EVT B, CI_MR C
       WHERE B.MR_ID =  C.MR_ID AND A.SP_MTR_HIST_ID =  B.SP_MTR_HIST_ID
 ;

-- ----- CI_SV_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_SV_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       SA.ACCT_ID
      ,LU.LANGUAGE_CD
      ,SEVP.SEV_PROC_ID
      ,'          '
      ,SEVP.CRE_DTTM
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,TO_CHAR(SEVP.CRE_DTTM,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM CI_SEV_PROC   SEVP
      ,CI_SA         SA
      ,CI_LOOKUP       LU
   WHERE SEVP.SA_ID = SA.SA_ID
   AND LU.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LU.FIELD_VALUE = 'SV'
   AND SEVP.SEV_STATUS_FLG = '20'
WITH READ ONLY
 ;

-- ----- CI_TD_ENTRY_OPEN_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_TD_ENTRY_OPEN_VW" ("TD_ENTRY_ID", "BATCH_CD", "BATCH_NBR", "MESSAGE_CAT_NBR", "MESSAGE_NBR", "ASSIGNED_TO", "TD_TYPE_CD", "ROLE_ID", "ENTRY_STATUS_FLG", "VERSION", "CRE_DTTM", "ASSIGNED_DTTM", "COMPLETE_DTTM", "COMPLETE_USER_ID", "COMMENTS", "ASSIGNED_USER_ID", "TD_PRIORITY_FLG", "ILM_DT", "ILM_ARCH_SW", "PARMS_TLBL", "DKEY1", "DKEY2", "DKEY3", "DKEY4", "DKEY5", "SKEY1", "SKEY2", "SKEY3", "SKEY4", "SKEY5", "DAYS_OLD", "COMMENTS_LOGS", "RELATED_TODO_CNT", "DKSQ1", "DKSQ2", "DKSQ3", "DKSQ4", "DKSQ5", "SKSQ1", "SKSQ2", "SKSQ3", "SKSQ4", "SKSQ5") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT A."TD_ENTRY_ID",A."BATCH_CD",A."BATCH_NBR",A."MESSAGE_CAT_NBR",A."MESSAGE_NBR",A."ASSIGNED_TO",A."TD_TYPE_CD",A."ROLE_ID",A."ENTRY_STATUS_FLG",A."VERSION",A."CRE_DTTM",A."ASSIGNED_DTTM",A."COMPLETE_DTTM",A."COMPLETE_USER_ID",A."COMMENTS",A."ASSIGNED_USER_ID",A."TD_PRIORITY_FLG",A."ILM_DT",A."ILM_ARCH_SW",
(SELECT LISTAGG(msg_parm_val, '#') WITHIN GROUP (ORDER BY seq_num) FROM (select * from ci_td_msg_parm z where z.td_entry_id = a.td_entry_id))||'#' as PARMS_TLBL,
nvl((select key_value from ci_td_drlkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.dksq1),' ') as DKey1,
nvl((select key_value from ci_td_drlkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.dksq2),' ') as DKey2,
nvl((select key_value from ci_td_drlkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.dksq3),' ') as DKey3,
nvl((select key_value from ci_td_drlkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.dksq4),' ') as DKey4,
nvl((select key_value from ci_td_drlkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.dksq5),' ') as DKey5,
nvl((select key_value from ci_td_srtkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.sksq1),' ') as SKey1,
nvl((select key_value from ci_td_srtkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.sksq2),' ') as SKey2,
nvl((select key_value from ci_td_srtkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.sksq3),' ') as SKey3,
nvl((select key_value from ci_td_srtkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.sksq4),' ') as SKey4,
nvl((select key_value from ci_td_srtkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.sksq5),' ') as SKey5,
round((current_date - A.cre_dttm),0) as DAYS_OLD,
decode(a.comments,' ', nvl((select 'F1CMNT' from dual where exists (select 'x' from ci_td_log z where z.td_entry_id = a.td_entry_id and z.log_type_flg IN ('UDET','FWDD','SBCK'))),' '),'F1CMNT') COMMENTS_LOGS,
(
select decode(count(distinct TDC2.TD_ENTRY_ID),0,' ', count(distinct TDC2.TD_ENTRY_ID))
FROM
(select z.TD_ENTRY_ID, z.CHAR_TYPE_CD, z.SRCH_CHAR_VAL
from CI_TD_ENTRY_CHA z,
(select CT.CHAR_TYPE_CD
from CI_CHAR_TYPE CT,CI_FK_REF FKR,CI_MD_TBL TBL
where CT.CHAR_TYPE_FLG = 'FKV' AND
CT.FK_REF_CD = FKR.FK_REF_CD AND
FKR.TBL_NAME = TBL.TBL_NAME AND
TBL.TBL_CLASSIFICATION_FLG in ( 'F1MT','F1TT')
) fkrefs
where z.TD_ENTRY_ID = A.TD_ENTRY_ID
AND z.CHAR_TYPE_CD = fkrefs.CHAR_TYPE_CD
) TDC1,
CI_TD_ENTRY_CHA TDC2
WHERE TDC1.SRCH_CHAR_VAL = TDC2.SRCH_CHAR_VAL
AND TDC1.CHAR_TYPE_CD = TDC2.CHAR_TYPE_CD
AND TDC2.TD_ENTRY_ID <> A.TD_ENTRY_ID
and exists (select /*+ no_unnest */ 'x' from ci_td_entry q where TDC2.TD_ENTRY_ID = q.TD_ENTRY_ID and q.ENTRY_STATUS_FLG in ( 'O','W'))
) as RELATED_TODO_CNT,
ttyvw.dksq1, ttyvw.dksq2, ttyvw.dksq3, ttyvw.dksq4, ttyvw.dksq5,
ttyvw.sksq1, ttyvw.sksq2, ttyvw.sksq3, ttyvw.sksq4, ttyvw.sksq5
FROM CI_TD_ENTRY A,
(
select tdtyp.td_type_cd,
(select dkty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_DRLKEY_TY) dkty where dkty.td_type_cd = tdtyp.td_type_cd and dkty.seqno = 1) dksq1,
(select dkty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_DRLKEY_TY) dkty where dkty.td_type_cd = tdtyp.td_type_cd and dkty.seqno = 2) dksq2,
(select dkty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_DRLKEY_TY) dkty where dkty.td_type_cd = tdtyp.td_type_cd and dkty.seqno = 3) dksq3,
(select dkty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_DRLKEY_TY) dkty where dkty.td_type_cd = tdtyp.td_type_cd and dkty.seqno = 4) dksq4,
(select dkty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_DRLKEY_TY) dkty where dkty.td_type_cd = tdtyp.td_type_cd and dkty.seqno = 5) dksq5,
(select skty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_SRTKEY_TY) skty where skty.td_type_cd = tdtyp.td_type_cd and skty.seqno = 1) sksq1,
(select skty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_SRTKEY_TY) skty where skty.td_type_cd = tdtyp.td_type_cd and skty.seqno = 2) sksq2,
(select skty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_SRTKEY_TY) skty where skty.td_type_cd = tdtyp.td_type_cd and skty.seqno = 3) sksq3,
(select skty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_SRTKEY_TY) skty where skty.td_type_cd = tdtyp.td_type_cd and skty.seqno = 4) sksq4,
(select skty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_SRTKEY_TY) skty where skty.td_type_cd = tdtyp.td_type_cd and skty.seqno = 5) sksq5
from ci_td_type tdtyp
) ttyvw
WHERE A.ENTRY_STATUS_FLG in ( 'O','W')
and a.td_type_cd = ttyvw.td_type_cd;

-- ----- CI_USR_ACC_GRP_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_USR_ACC_GRP_VW" ("USER_ID", "ACCESS_GRP_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT A.USER_ID, B.ACCESS_GRP_CD
FROM CI_DAR_USR A, CI_ACC_GRP_DAR B
WHERE A.DAR_CD = B.DAR_CD
AND A.EXPIRE_DT >= CURRENT_TIMESTAMP;

-- ----- CI_WE_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_WE_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       WO.ACCT_ID
      ,LU.LANGUAGE_CD
      ,WE.WO_PROC_ID
      ,RPAD(LPAD(TO_CHAR(WE.EVT_SEQ), 3, '0'),10,' ')
      ,WE.TRIGGER_DT
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,TO_CHAR(WE.TRIGGER_DT,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM CI_WO_PROC    WO
      ,CI_WO_EVT     WE
      ,CI_LOOKUP     LU
   WHERE WO.WO_PROC_ID = WE.WO_PROC_ID
   AND WE.WO_EVT_STAT_FLG = '10'
   AND LU.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LU.FIELD_VALUE = 'WE'
WITH READ ONLY
 ;

-- ----- CI_WO_ACCT_HST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CI_WO_ACCT_HST_VW" ("ACCT_ID", "LANGUAGE_CD", "ACTIVITY_ID", "ACTIVITY_ID2", "ACTIVITY_DTTM", "ACT_TYPE_FLG", "ACT_DESCR", "SORT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       WO.ACCT_ID
      ,LU.LANGUAGE_CD
      ,WO.WO_PROC_ID
      ,'          '
      ,WO.CRE_DTTM
      ,LU.FIELD_VALUE
      ,LU.DESCR
      ,TO_CHAR(WO.CRE_DTTM,'YYYY-MM-DD-HH24.MI.SS') ||'.000000'
  FROM CI_WO_PROC     WO
      ,CI_LOOKUP       LU
   WHERE
       LU.FIELD_NAME = 'ACT_TYPE_FLG'
   AND LU.FIELD_VALUE = 'WO'
   AND WO.WO_STATUS_FLG = '20'
WITH READ ONLY
 ;

-- ----- CMS_ADMIN_CONFIG_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_ADMIN_CONFIG_VW" ("TBL_NAME", "TBL_DESCR", "LANG_TBL_NAME", "OWNER_FLG", "MAINT_OBJ_CD", "ENVIRONMENT", "KEY", "DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT 'CI_APREQ_TYPE' AS TBL_NAME, 'A/P Request Type' AS TBL_DESCR, 'CI_APREQ_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'A/P REQ TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, AP_REQ_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_APREQ_TYPE_L  UNION 
SELECT 'CI_ACC_GRP' AS TBL_NAME, 'Access Group' AS TBL_DESCR, 'CI_ACC_GRP_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'ACCT GROUP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ACCESS_GRP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_ACC_GRP_L  UNION 
SELECT 'CI_ACCT_MGMT_GR' AS TBL_NAME, 'Account Management Group' AS TBL_DESCR, 'CI_ACCT_MGMT_GR_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'ACCT MGMT GR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ACCT_MGMT_GRP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_ACCT_MGMT_GR_L  UNION 
SELECT 'CI_ACCT_REL_TYP' AS TBL_NAME, 'Account Relationship Type' AS TBL_DESCR, 'CI_ACCT_REL_TYP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'ACCT REL TYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ACCT_REL_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_ACCT_REL_TYP_L  UNION 
SELECT 'CI_CAL_GL' AS TBL_NAME, 'Accounting Calendar' AS TBL_DESCR, 'CI_CAL_GL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'GL CALENDAR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CALENDAR_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_CAL_GL_L  UNION 
SELECT 'W1_CALENDAR' AS TBL_NAME, 'Accounting Calendar' AS TBL_DESCR, 'W1_CALENDAR_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-ACTCAL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, W1_CALENDAR_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CALENDAR_L  UNION 
SELECT 'F1_ACTION_METHOD' AS TBL_NAME, 'Action Method' AS TBL_DESCR, 'F1_ACTION_METHOD_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-ACTNMETHD' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ACTION_METHOD_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_ACTION_METHOD_L  UNION 
SELECT 'CI_AM_ACTIVITY_TYPE' AS TBL_NAME, 'Activity Request Type' AS TBL_DESCR, 'CI_AM_ACTIVITY_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-ACM-ACTTY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, AM_ACTIVITY_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_AM_ACTIVITY_TYPE_L  UNION 
SELECT 'W1_ACTIVITY_TYPE' AS TBL_NAME, 'Activity Type' AS TBL_DESCR, 'W1_ACTIVITY_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-ACTTY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ACT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_ACTIVITY_TYPE_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'D1_ACTIVITY_TYPE' AS TBL_NAME, 'Activity Type' AS TBL_DESCR, 'D1_ACTIVITY_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-ACTTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ACTIVITY_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_ACTIVITY_TYPE_L  UNION 
SELECT 'CI_ADJ_CAN_RSN' AS TBL_NAME, 'Adjustment Cancel Reason' AS TBL_DESCR, 'CI_ADJ_CAN_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'ADJ CAN RSN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CAN_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_ADJ_CAN_RSN_L  UNION 
SELECT 'CI_ADJ_TYPE' AS TBL_NAME, 'Adjustment Type' AS TBL_DESCR, 'CI_ADJ_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'ADJ TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ADJ_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_ADJ_TYPE_L  UNION 
SELECT 'CI_ADJ_TYP_PROF' AS TBL_NAME, 'Adjustment Type Profile' AS TBL_DESCR, 'CI_ADJ_TYP_PROF_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'ADJ TYPE PRF' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ADJ_TYPE_PROF_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_ADJ_TYP_PROF_L  UNION 
SELECT 'D1_AGG_GROUP' AS TBL_NAME, 'Aggregation Group' AS TBL_DESCR, 'D1_AGG_GROUP_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-AGGGROUP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_AGG_GROUP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_AGG_GROUP_L  UNION 
SELECT 'CI_ALERT_TYPE' AS TBL_NAME, 'Alert Type' AS TBL_DESCR, 'CI_ALERT_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'ALERT TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ALERT_TYPE_CD AS KEY, DESCR80 AS DESCR  FROM CISADM.CI_ALERT_TYPE_L  UNION 
SELECT 'CI_ALG' AS TBL_NAME, 'Algorithm' AS TBL_DESCR, 'CI_ALG_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'ALGORITHM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ALG_CD AS KEY, DESCR50 AS DESCR  FROM CISADM.CI_ALG_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_ALG_TYPE' AS TBL_NAME, 'Algorithm Type' AS TBL_DESCR, 'CI_ALG_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'ALG TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ALG_TYPE_CD AS KEY, DESCR50 AS DESCR  FROM CISADM.CI_ALG_TYPE_L WHERE OWNER_FLG = 'CM' UNION 

SELECT 'F1_MD_BI_TBL' AS TBL_NAME, 'Analytics Table' AS TBL_DESCR, 'F1_MD_BI_TBL_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-ANALYTICS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, F1_BI_TBL_NAME AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_MD_BI_TBL_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'SC_APP_SERVICE' AS TBL_NAME, 'Application Service' AS TBL_DESCR, 'SC_APP_SERVICE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'APP SERVICE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, APP_SVC_ID AS KEY, DESCR AS DESCR  FROM CISADM.SC_APP_SERVICE_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'W1_APPROVAL_PROF' AS TBL_NAME, 'Approval Profile' AS TBL_DESCR, 'W1_APPROVAL_PROF_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-APVLPROF' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, APPROVAL_PROF_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_APPROVAL_PROF_L  UNION 
SELECT 'CI_APPR_PROF' AS TBL_NAME, 'Approval Profile' AS TBL_DESCR, 'CI_APPR_PROF_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-APPR PROF' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, APPR_PROF_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_APPR_PROF_L  UNION 
SELECT 'W1_ASSESS_CLASS' AS TBL_NAME, 'Assessment Class' AS TBL_DESCR, 'W1_ASSESS_CLASS_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-ASSESSCLS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ASSESSMENT_CLASS_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_ASSESS_CLASS_L  UNION 
SELECT 'W1_ASSESS_GRP' AS TBL_NAME, 'Assessment Group' AS TBL_DESCR, 'W1_ASSESS_GRP_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-ASSESSGRP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ASSESSMENT_GROUP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_ASSESS_GRP_L  UNION 
SELECT 'W1_ASSET_TYPE' AS TBL_NAME, 'Asset Type' AS TBL_DESCR, 'W1_ASSET_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-ASSETTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ASSET_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_ASSET_TYPE_L  UNION 
SELECT 'D1_ADS_TYPE' AS TBL_NAME, 'Attribute Data Snapshot Type' AS TBL_DESCR, 'D1_ADS_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-ADSTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ADS_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_ADS_TYPE_L  UNION 
SELECT 'D1_ATTR_GRP' AS TBL_NAME, 'Attribute Group' AS TBL_DESCR, 'D1_ATTR_GRP_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-ATTRGRP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ATTR_GRP_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_ATTR_GRP_L  UNION 
SELECT 'CI_APAY_RT_TYPE' AS TBL_NAME, 'Auto Pay Route Type' AS TBL_DESCR, 'CI_APAY_RT_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'APAY RT TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, APAY_RTE_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_APAY_RT_TYPE_L  UNION 
SELECT 'CI_APAY_SRC' AS TBL_NAME, 'Auto Pay Source' AS TBL_DESCR, 'CI_APAY_SRC_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'AUTOPAY SRC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, APAY_SRC_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_APAY_SRC_L  UNION 
SELECT 'CI_BANK' AS TBL_NAME, 'Bank' AS TBL_DESCR, 'CI_BANK_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'BANK' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BANK_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_BANK_L  UNION 
SELECT 'CI_BATCH_CTRL' AS TBL_NAME, 'Batch Control' AS TBL_DESCR, 'CI_BATCH_CTRL_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'BATCH CNTL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BATCH_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_BATCH_CTRL_L WHERE OWNER_FLG = 'CM' UNION 

SELECT 'CI_BILL_CAN_RSN' AS TBL_NAME, 'Bill Cancel Reason' AS TBL_DESCR, 'CI_BILL_CAN_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'BILL CAN RSN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CAN_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_BILL_CAN_RSN_L  UNION 
SELECT 'CI_BILL_CYC' AS TBL_NAME, 'Bill Cycle - CCB' AS TBL_DESCR, 'CI_BILL_CYC_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'BILL CYCLE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BILL_CYC_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_BILL_CYC_L  UNION 
SELECT 'D1_BILL_CYC' AS TBL_NAME, 'Bill Cycle - MDM' AS TBL_DESCR, 'D1_BILL_CYC_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-BILLCYCLE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_BILL_CYC_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_BILL_CYC_L  UNION 

SELECT 'CI_BF' AS TBL_NAME, 'Bill Factor' AS TBL_DESCR, 'CI_BF_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'BILL FACTOR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BF_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_BF_L  UNION 


SELECT 'CI_BILL_MSG' AS TBL_NAME, 'Bill Message Codes (Admin)' AS TBL_DESCR, 'CI_BILL_MSG_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'BILL MESSAGE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BILL_MSG_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_BILL_MSG_L  UNION 
SELECT 'CI_BILL_PERIOD' AS TBL_NAME, 'Bill Period' AS TBL_DESCR, 'CI_BILL_PERIOD_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'BILL PERIOD' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BILL_PERIOD_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_BILL_PERIOD_L  UNION 
SELECT 'CI_BILL_RT_TYPE' AS TBL_NAME, 'Bill Route Type' AS TBL_DESCR, 'CI_BILL_RT_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'BILL RT TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BILL_RTE_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_BILL_RT_TYPE_L  UNION 
SELECT 'CI_BILL_SEG_TYP' AS TBL_NAME, 'Bill Segment Type' AS TBL_DESCR, 'CI_BILL_SEG_TYP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'BILL SEG TYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BILL_SEG_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_BILL_SEG_TYP_L  UNION 
SELECT 'CI_B_CHG_TMPLT' AS TBL_NAME, 'Billable Charge Template' AS TBL_DESCR, 'CI_B_CHG_TMPLT_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'BILL CH TMPL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BILL_CHG_TMPLT_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_B_CHG_TMPLT_L  UNION 
SELECT 'CI_BCHG_UP_XTYP' AS TBL_NAME, 'Billable Charge Upload Line Type' AS TBL_DESCR, 'CI_BCHG_UP_XTYP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'BCHG UP TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BCHG_UP_XTYPE AS KEY, DESCR50 AS DESCR  FROM CISADM.CI_BCHG_UP_XTYP_L  UNION 
SELECT 'W1_BC_ACCESS_LIST' AS TBL_NAME, 'Blanket Contract Access List' AS TBL_DESCR, 'W1_BC_ACCESS_LIST_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-BCACSLIST' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BC_ACCESS_LIST_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_BC_ACCESS_LIST_L  UNION 
SELECT 'W1_BKT_CONFIG' AS TBL_NAME, 'Bucket Configuration' AS TBL_DESCR, 'W1_BKT_CONFIG_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-BKTCONFIG' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BKT_CONFIG_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_BKT_CONFIG_L  UNION 
SELECT 'F1_BKT_CONFIG' AS TBL_NAME, 'Bucket Configuration' AS TBL_DESCR, 'F1_BKT_CONFIG_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-BKTCONFIG' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BKT_CONFIG_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_BKT_CONFIG_L  UNION 
SELECT 'CI_BUD_PLAN' AS TBL_NAME, 'Budget Plan' AS TBL_DESCR, 'CI_BUD_PLAN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'BUDGET PLAN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BUD_PLAN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_BUD_PLAN_L  UNION 
SELECT 'F1_BUS_FLG_TYPE' AS TBL_NAME, 'Business Flag Type' AS TBL_DESCR, 'F1_BUS_FLG_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-BUSFLGTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BUS_FLG_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_BUS_FLG_TYPE_L  UNION 
SELECT 'F1_BUS_OBJ' AS TBL_NAME, 'Business Object' AS TBL_DESCR, 'F1_BUS_OBJ_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-BUS OBJ' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BUS_OBJ_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_BUS_OBJ_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'F1_BUS_SVC' AS TBL_NAME, 'Business Service' AS TBL_DESCR, 'F1_BUS_SVC_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-BUS SVC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BUS_SVC_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_BUS_SVC_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'W1_BUSINESS_UNIT' AS TBL_NAME, 'Business Unit' AS TBL_DESCR, 'W1_BUSINESS_UNIT_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-BUSUNIT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BUSINESS_UNIT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_BUSINESS_UNIT_L  UNION 
SELECT 'W1_BUYER' AS TBL_NAME, 'Buyer' AS TBL_DESCR, 'W1_BUYER_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-BUYER' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BUYER_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_BUYER_L  UNION 
SELECT 'CI_CIS_DIVISION' AS TBL_NAME, 'CIS Division' AS TBL_DESCR, 'CI_CIS_DIVISION_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'CIS DIVISION' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CIS_DIVISION AS KEY, DESCR AS DESCR  FROM CISADM.CI_CIS_DIVISION_L  UNION 


SELECT 'C1_CS_REQ_TYPE_SVC_CRIT' AS TBL_NAME, 'CS Request Type Svc Criteria' AS TBL_DESCR, 'C1_CS_REQ_TYPE_SVC_CRIT_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CSRTSELCR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CS_REQ_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_CS_REQ_TYPE_SVC_CRIT_L  UNION 
SELECT 'W1_CU_CATEGORY' AS TBL_NAME, 'CU Category' AS TBL_DESCR, 'W1_CU_CATEGORY_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CUCATEG' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CU_CATEGORY_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CU_CATEGORY_L  UNION 
SELECT 'W1_CU_USAGE' AS TBL_NAME, 'CU Usage' AS TBL_DESCR, 'W1_CU_USAGE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CUUSAGE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CU_USAGE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CU_USAGE_L  UNION 
SELECT 'C1_CL_CAT_TYPE' AS TBL_NAME, 'Calc Line Category Type' AS TBL_DESCR, 'C1_CL_CAT_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CL-CAT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CL_CAT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_CL_CAT_TYPE_L  UNION 
SELECT 'C1_CALC_RULE_CRT' AS TBL_NAME, 'Calc Rule Eligibility Criteria' AS TBL_DESCR, 'C1_CALC_RULE_CRT_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CALC-R-EL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CALC_GRP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_CALC_RULE_CRT_L  UNION 
SELECT 'C1_CALC_GRP' AS TBL_NAME, 'Calculation Group' AS TBL_DESCR, 'C1_CALC_GRP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CALC-GRP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CALC_GRP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_CALC_GRP_L  UNION 
SELECT 'C1_CALC_RULE' AS TBL_NAME, 'Calculation Rule' AS TBL_DESCR, 'C1_CALC_RULE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CALC-RULE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CALC_GRP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_CALC_RULE_L  UNION 
SELECT 'CI_CAMPAIGN' AS TBL_NAME, 'Campaign' AS TBL_DESCR, 'CI_CAMPAIGN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'CAMPAIGN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CAMPAIGN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CAMPAIGN_L  UNION 
SELECT 'W1_CAPABILITY_TYPE' AS TBL_NAME, 'Capability Type' AS TBL_DESCR, 'W1_CAPABILITY_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CPBLTYTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CAPABILITY_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CAPABILITY_TYPE_L  UNION 
SELECT 'CI_CASE_TYPE' AS TBL_NAME, 'Case Type' AS TBL_DESCR, 'CI_CASE_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'CASE TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CASE_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CASE_TYPE_L  UNION 
SELECT 'W1_CHANGE_REQ_TYPE' AS TBL_NAME, 'Change Request Type' AS TBL_DESCR, 'W1_CHANGE_REQ_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CHNGRQTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CHANGE_REQ_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CHANGE_REQ_TYPE_L  UNION 
SELECT 'CI_CHAR_TYPE' AS TBL_NAME, 'Characteristic Type' AS TBL_DESCR, 'CI_CHAR_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'CHAR TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CHAR_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CHAR_TYPE_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'W1_CHKLST_TYP' AS TBL_NAME, 'Checklist Type' AS TBL_DESCR, 'W1_CHKLST_TYP_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CHKLSTTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CHECKLIST_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CHKLST_TYP_L  UNION 
SELECT 'W1_CHILD_SPEC' AS TBL_NAME, 'Child Specification' AS TBL_DESCR, 'W1_CHILD_SPEC_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CHILDSPEC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CHILD_SPEC_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CHILD_SPEC_L  UNION 
SELECT 'CI_COLL_AGY' AS TBL_NAME, 'Collection Agency' AS TBL_DESCR, 'CI_COLL_AGY_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'COLL AGENCY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COLL_AGY_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_COLL_AGY_L  UNION 
SELECT 'CI_COLL_CL' AS TBL_NAME, 'Collection Class' AS TBL_DESCR, 'CI_COLL_CL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'COLL CLASS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COLL_CL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_COLL_CL_L  UNION 
SELECT 'CI_COLL_CL_CNTL' AS TBL_NAME, 'Collection Class Control' AS TBL_DESCR, 'CI_COLL_CL_CNTL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'COLL CL CNTL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COLL_CL_CNTL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_COLL_CL_CNTL_L  UNION 

SELECT 'CI_COLL_EVT_TYP' AS TBL_NAME, 'Collection Event Type' AS TBL_DESCR, 'CI_COLL_EVT_TYP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'COLL EVT TYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COLL_EVT_TYP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_COLL_EVT_TYP_L  UNION 
SELECT 'CI_COLL_PROC_TM' AS TBL_NAME, 'Collection Process Template' AS TBL_DESCR, 'CI_COLL_PROC_TM_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'COLL PROC TM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COLL_PROC_TMPL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_COLL_PROC_TM_L  UNION 
SELECT 'W1_COLOR' AS TBL_NAME, 'Color' AS TBL_DESCR, 'W1_COLOR_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-COLOR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COLOR_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_COLOR_L  UNION 
SELECT 'F1_COLOR_OPT' AS TBL_NAME, 'Color Option' AS TBL_DESCR, 'F1_COLOR_OPT_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-COLOROPT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COLOR_OPT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_COLOR_OPT_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_COL_REF' AS TBL_NAME, 'Column Reference' AS TBL_DESCR, 'CI_COL_REF_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'COLUMN REF' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COL_REF_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_COL_REF_L  UNION 
SELECT 'D1_COMMAND_SET' AS TBL_NAME, 'Command Set' AS TBL_DESCR, 'D1_COMMAND_SET_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-CMDSET' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_CMD_SET_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_COMMAND_SET_L  UNION 
SELECT 'W1_CMDTY_CAT' AS TBL_NAME, 'Commodity Category' AS TBL_DESCR, 'W1_CMDTY_CAT_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CDTCTG' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CMDTY_CAT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CMDTY_CAT_L  UNION 
SELECT 'W1_CMDTY_NAME' AS TBL_NAME, 'Commodity Name' AS TBL_DESCR, 'W1_CMDTY_NAME_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CDTNAME' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CMDTY_NAME_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CMDTY_NAME_L  UNION 
SELECT 'W1_CMDTY_TYPE' AS TBL_NAME, 'Commodity Type' AS TBL_DESCR, 'W1_CMDTY_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CDTTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CMDTY_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CMDTY_TYPE_L  UNION 
SELECT 'W1_COMM_TYPE' AS TBL_NAME, 'Communication Type' AS TBL_DESCR, 'W1_COMM_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-COMTY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COMM_TYP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_COMM_TYPE_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'D1_COMM_TYPE' AS TBL_NAME, 'Communication Type' AS TBL_DESCR, 'D1_COMM_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-COMMTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COMM_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_COMM_TYPE_L  UNION 
SELECT 'W1_CU_SET' AS TBL_NAME, 'Compatible Unit Set' AS TBL_DESCR, 'W1_CU_SET_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CUSET' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CU_SET_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CU_SET_L  UNION 
SELECT 'W1_CMPL_EVT_TYPE' AS TBL_NAME, 'Completion Event Type' AS TBL_DESCR, 'W1_CMPL_EVT_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CEVTT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CMPL_EVT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CMPL_EVT_TYPE_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'W1_COMPLIANCE_CAT' AS TBL_NAME, 'Compliance Category' AS TBL_DESCR, 'W1_COMPLIANCE_CAT_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CMPLNCAT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COMPLIANCE_CAT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_COMPLIANCE_CAT_L  UNION 
SELECT 'W1_COMPLIANCE_TYPE' AS TBL_NAME, 'Compliance Type' AS TBL_DESCR, 'W1_COMPLIANCE_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CMPLNTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COMPLIANCE_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_COMPLIANCE_TYPE_L  UNION 
SELECT 'W1_CONFIG_TYPE' AS TBL_NAME, 'Configuration Type' AS TBL_DESCR, 'W1_CONFIG_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CONFIGTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CONFIG_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CONFIG_TYPE_L  UNION 
SELECT 'CI_CONSV_PROG' AS TBL_NAME, 'Conservation Program' AS TBL_DESCR, 'CI_CONSV_PROG_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CPROG' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CONSV_PROG_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CONSV_PROG_L  UNION 
SELECT 'C1_CONT_MS_TYPE' AS TBL_NAME, 'Consumer Contract Milestone Type' AS TBL_DESCR, 'C1_CONT_MS_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CNSCNMTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CONT_MS_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_CONT_MS_TYPE_L  UNION 
SELECT 'C1_CONT_RULE' AS TBL_NAME, 'Consumer Contract Rule' AS TBL_DESCR, 'C1_CONT_RULE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CONTRULE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CONT_RULE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_CONT_RULE_L  UNION 
SELECT 'C1_CONT_TYPE' AS TBL_NAME, 'Consumer Contract Type' AS TBL_DESCR, 'C1_CONT_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CNSCONTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CONT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_CONT_TYPE_L  UNION 
SELECT 'C1_PROD' AS TBL_NAME, 'Consumer Product' AS TBL_DESCR, 'C1_PROD_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-PROD' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROD_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_PROD_L  UNION 
SELECT 'C1_PROD_COMP' AS TBL_NAME, 'Consumer Product Component' AS TBL_DESCR, 'C1_PROD_COMP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-PRODCOMP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROD_COMP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_PROD_COMP_L  UNION 
SELECT 'C1_PROD_COMP_ELIG_CRIT' AS TBL_NAME, 'Consumer Product Component Criteria' AS TBL_DESCR, 'C1_PROD_COMP_ELIG_CRIT_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-PRODCOMPC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROD_COMP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_PROD_COMP_ELIG_CRIT_L  UNION 
SELECT 'C1_PROD_ELIG_CRIT' AS TBL_NAME, 'Consumer Product Eligibility Criteria' AS TBL_DESCR, 'C1_PROD_ELIG_CRIT_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-PRODELIGC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROD_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_PROD_ELIG_CRIT_L  UNION 
SELECT 'C1_PROD_RULE' AS TBL_NAME, 'Consumer Product Rule' AS TBL_DESCR, 'C1_PROD_RULE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-PRODRULE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROD_RULE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_PROD_RULE_L  UNION 
SELECT 'C1_PROD_VER' AS TBL_NAME, 'Consumer Product Version' AS TBL_DESCR, 'C1_PROD_VER_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-PRODVER' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROD_VER_ID AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_PROD_VER_L  UNION 
SELECT 'D1_CONS_EXT_TYPE' AS TBL_NAME, 'Consumption Extract Type' AS TBL_DESCR, 'D1_CONS_EXT_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-CET' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CONS_EXT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_CONS_EXT_TYPE_L  UNION 
SELECT 'D1_CONTACT_TYPE' AS TBL_NAME, 'Contact Type' AS TBL_DESCR, 'D1_CONTACT_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-CONTTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CONTACT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_CONTACT_TYPE_L  UNION 
SELECT 'W1_CONTACT_TYPE' AS TBL_NAME, 'Contact Type' AS TBL_DESCR, 'W1_CONTACT_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CONTTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, W1_CONTACT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CONTACT_TYPE_L  UNION 


SELECT 'CI_COP_EVT_TYPE' AS TBL_NAME, 'Contract Option Event Type' AS TBL_DESCR, 'CI_COP_EVT_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'COP EVT TYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CONT_OPT_EVT_TY_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_COP_EVT_TYPE_L  UNION 
SELECT 'CI_COP_TYPE' AS TBL_NAME, 'Contract Option Type' AS TBL_DESCR, 'CI_COP_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'COP TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CONT_OPT_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_COP_TYPE_L  UNION 
SELECT 'CI_CONT_QTY_TYP' AS TBL_NAME, 'Contract Quantity Type' AS TBL_DESCR, 'CI_CONT_QTY_TYP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'CONT QTY TYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CONT_QTY_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CONT_QTY_TYP_L  UNION 
SELECT 'W1_ADJUSTMENT_TYPE' AS TBL_NAME, 'Cost Adjustment Type' AS TBL_DESCR, 'W1_ADJUSTMENT_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-ADJMTTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ADJUSTMENT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_ADJUSTMENT_TYPE_L  UNION 
SELECT 'W1_COST_CATEGORY' AS TBL_NAME, 'Cost Category' AS TBL_DESCR, 'W1_COST_CATEGORY_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-COSTCAT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COST_CATEGORY_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_COST_CATEGORY_L  UNION 
SELECT 'W1_COST_CENTER' AS TBL_NAME, 'Cost Center' AS TBL_DESCR, 'W1_COST_CENTER_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-COSTCTR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COST_CENTER_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_COST_CENTER_L  UNION 
SELECT 'CI_COUNTRY' AS TBL_NAME, 'Country' AS TBL_DESCR, 'CI_COUNTRY_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'COUNTRY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COUNTRY AS KEY, DESCR AS DESCR  FROM CISADM.CI_COUNTRY_L  UNION 
SELECT 'CI_CR_UNIT' AS TBL_NAME, 'Credit Unit' AS TBL_DESCR, 'CI_CR_UNIT_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'CREDIT UNIT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CR_UNIT_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CR_UNIT_L  UNION 
SELECT 'W1_CREW_SHIFT_TYPE' AS TBL_NAME, 'Crew Shift Type' AS TBL_DESCR, 'W1_CREW_SHIFT_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CREWSHFTY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CREW_SHIFT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CREW_SHIFT_TYPE_L  UNION 
SELECT 'W1_CREW_TYPE' AS TBL_NAME, 'Crew Type' AS TBL_DESCR, 'W1_CREW_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-CREWTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CREW_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_CREW_TYPE_L  UNION 
SELECT 'F1_CUBE_TYPE' AS TBL_NAME, 'Cube Type' AS TBL_DESCR, 'F1_CUBE_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-CUBETYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CUBE_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_CUBE_TYPE_L  UNION 
SELECT 'CI_CURRENCY_CD' AS TBL_NAME, 'Currency Code' AS TBL_DESCR, 'CI_CURRENCY_CD_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'CURR CODE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CURRENCY_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CURRENCY_CD_L  UNION 
SELECT 'CI_CUST_CL' AS TBL_NAME, 'Customer Class' AS TBL_DESCR, 'CI_CUST_CL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'CUST CLASS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CUST_CL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CUST_CL_L  UNION 
SELECT 'CI_CC_CL' AS TBL_NAME, 'Customer Contact Class' AS TBL_DESCR, 'CI_CC_CL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'CUST CONT CL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CC_CL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CC_CL_L  UNION 
SELECT 'CI_CC_TYPE' AS TBL_NAME, 'Customer Contact Type' AS TBL_DESCR, 'CI_CC_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'CUST CNT TYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CC_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CC_TYPE_L  UNION 
SELECT 'C1_QUESTION' AS TBL_NAME, 'Customer Question' AS TBL_DESCR, 'C1_QUESTION_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-QSTN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, C1_QUESTION_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_QUESTION_L  UNION 
SELECT 'C1_CUST_REL_REQ_TYPE' AS TBL_NAME, 'Customer Relationship Request Type' AS TBL_DESCR, 'C1_CUST_REL_REQ_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CUSTRRTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CUST_REL_REQ_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_CUST_REL_REQ_TYPE_L  UNION 
SELECT 'C1_CS_REQ_TYPE' AS TBL_NAME, 'Customer Service Request Type' AS TBL_DESCR, 'C1_CS_REQ_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CSREQTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CS_REQ_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_CS_REQ_TYPE_L  UNION 
SELECT 'CI_CEVT_CAN_RSN' AS TBL_NAME, 'Cut Event Cancel Reason' AS TBL_DESCR, 'CI_CEVT_CAN_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CE-CNREAS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CEVT_CAN_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CEVT_CAN_RSN_L  UNION 
SELECT 'CI_CUT_EVT_TYPE' AS TBL_NAME, 'Cut Event Type' AS TBL_DESCR, 'CI_CUT_EVT_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CUT-EVTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CUT_EVT_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CUT_EVT_TYPE_L  UNION 
SELECT 'CI_CUT_PROC_TMP' AS TBL_NAME, 'Cut Process Template' AS TBL_DESCR, 'CI_CUT_PROC_TMP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-CUTPROCTM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CUT_PROC_TMP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CUT_PROC_TMP_L  UNION 
SELECT 'CI_DAR' AS TBL_NAME, 'Data Access Role' AS TBL_DESCR, 'CI_DAR_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'DATA ACS-SC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DAR_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_DAR_L  UNION 
SELECT 'CI_DAR' AS TBL_NAME, 'Data Access Role' AS TBL_DESCR, 'CI_DAR_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'DATA ACCESS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DAR_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_DAR_L  UNION 
SELECT 'F1_DATA_AREA' AS TBL_NAME, 'Data Area' AS TBL_DESCR, 'F1_DATA_AREA_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-DATA AREA' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DATA_AREA_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_DATA_AREA_L WHERE OWNER_FLG = 'CM' UNION 

SELECT 'D1_DATA_SRC' AS TBL_NAME, 'Data Source' AS TBL_DESCR, 'D1_DATA_SRC_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-DATASRC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DATA_SRC_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_DATA_SRC_L  UNION 
SELECT 'CI_DEBT_CL' AS TBL_NAME, 'Debt Class' AS TBL_DESCR, 'CI_DEBT_CL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'DEBT CLASS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DEBT_CL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_DEBT_CL_L  UNION 

SELECT 'F1_DEPLOYMENT_PART' AS TBL_NAME, 'Deployment Part' AS TBL_DESCR, 'F1_DEPLOYMENT_PART_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-DEPLOYPRT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, F1_DEPLOYMENT_PART_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_DEPLOYMENT_PART_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'F1_DEPLOYMENT_TYPE' AS TBL_NAME, 'Deployment Type' AS TBL_DESCR, 'F1_DEPLOYMENT_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-DEPLOYTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, F1_DEPLOYMENT_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_DEPLOYMENT_TYPE_L  UNION 
SELECT 'CI_DEP_CL' AS TBL_NAME, 'Deposit Class' AS TBL_DESCR, 'CI_DEP_CL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'DEPOSIT CL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DEP_CL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_DEP_CL_L  UNION 
SELECT 'D1_DVC_CFG_TYPE' AS TBL_NAME, 'Device Configuration Type' AS TBL_DESCR, 'D1_DVC_CFG_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-DVCCONTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DEVICE_CONFIG_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_DVC_CFG_TYPE_L  UNION 
SELECT 'D1_DVC_EVT_TYPE' AS TBL_NAME, 'Device Event Type' AS TBL_DESCR, 'D1_DVC_EVT_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-DVCEVTTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DVC_EVT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_DVC_EVT_TYPE_L  UNION 
SELECT 'CI_TST_COMP_TYP' AS TBL_NAME, 'Device Test Component Type' AS TBL_DESCR, 'CI_TST_COMP_TYP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TST COMP TYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TST_COMP_TYP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TST_COMP_TYP_L  UNION 
SELECT 'CI_DV_TEST_TYPE' AS TBL_NAME, 'Device Test Type' AS TBL_DESCR, 'CI_DV_TEST_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'DEV TST TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DV_TEST_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_DV_TEST_TYPE_L  UNION 
SELECT 'D1_DVC_TYPE' AS TBL_NAME, 'Device Type' AS TBL_DESCR, 'D1_DVC_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-DEVICETYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DEVICE_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_DVC_TYPE_L  UNION 


SELECT 'CI_DISCON_LOC' AS TBL_NAME, 'Disconnect Location' AS TBL_DESCR, 'CI_DISCON_LOC_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'DICSON LOC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DISCON_LOC_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_DISCON_LOC_L  UNION 
SELECT 'CI_DISP_GRP' AS TBL_NAME, 'Dispatch Group' AS TBL_DESCR, 'CI_DISP_GRP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'DISP GROUP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DISP_GRP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_DISP_GRP_L  UNION 

SELECT 'CI_DISP_ICON' AS TBL_NAME, 'Display Icon' AS TBL_DESCR, 'CI_DISP_ICON_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'DISP ICON' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DISP_ICON_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_DISP_ICON_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_DISP_PROF' AS TBL_NAME, 'Display Profile' AS TBL_DESCR, 'CI_DISP_PROF_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'DISP PROF' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DISP_PROF_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_DISP_PROF_L  UNION 
SELECT 'CI_DST_CODE' AS TBL_NAME, 'Distribution Code' AS TBL_DESCR, 'CI_DST_CODE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'DISTR CODE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DST_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_DST_CODE_L  UNION 
SELECT 'W1_DIST_CODE' AS TBL_NAME, 'Distribution Code' AS TBL_DESCR, 'W1_DIST_CODE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-DISTCD' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DISTRIBUTION_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_DIST_CODE_L  UNION 
SELECT 'CI_DST_RULE' AS TBL_NAME, 'Distribution Rule' AS TBL_DESCR, 'CI_DST_RULE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-DST RULE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DST_RULE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_DST_RULE_L  UNION 
SELECT 'D1_DIVISION' AS TBL_NAME, 'Division' AS TBL_DESCR, 'D1_DIVISION_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-DIV' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DIVISION_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_DIVISION_L  UNION 
SELECT 'W1_DOCUMENT_TYPE' AS TBL_NAME, 'Document Type' AS TBL_DESCR, 'W1_DOCUMENT_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-DOCTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DOCUMENT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_DOCUMENT_TYPE_L  UNION 
SELECT 'D1_DYN_OPT_TYPE' AS TBL_NAME, 'Dynamic Option Type' AS TBL_DESCR, 'D1_DYN_OPT_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-DOPTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, DYN_OPT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_DYN_OPT_TYPE_L  UNION 
SELECT 'W1_EMPLOYEE_TYPE' AS TBL_NAME, 'Employee Type' AS TBL_DESCR, 'W1_EMPLOYEE_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-EMPTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, EMPLOYEE_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_EMPLOYEE_TYPE_L  UNION 
SELECT 'W1_EU_TYPE' AS TBL_NAME, 'Employee Unavailability Type' AS TBL_DESCR, 'W1_EU_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-EUTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, EU_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_EU_TYPE_L  UNION 

SELECT 'F1_TAG' AS TBL_NAME, 'Entity Tag' AS TBL_DESCR, 'F1_TAG_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-ENTYTAG' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ENTITY_TAG AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_TAG_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'W1_EQUIP_GROUP' AS TBL_NAME, 'Equipment Group' AS TBL_DESCR, 'W1_EQUIP_GROUP_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-EQUIPGRP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, EQUIP_GROUP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_EQUIP_GROUP_L  UNION 
SELECT 'D1_EXCP_TYPE' AS TBL_NAME, 'Exception Type' AS TBL_DESCR, 'D1_EXCP_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-EXCPTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, EXCP_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_EXCP_TYPE_L  UNION 
SELECT 'W1_EXPENSE_CD' AS TBL_NAME, 'Expense Code' AS TBL_DESCR, 'W1_EXPENSE_CD_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-EXPCODE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, EXPENSE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_EXPENSE_CD_L  UNION 
SELECT 'F1_EXT_LOOKUP_VAL' AS TBL_NAME, 'Extendable Lookup' AS TBL_DESCR, 'F1_EXT_LOOKUP_VAL_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-EXT LKUP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, F1_EXT_LOOKUP_VALUE AS KEY, DESCR AS DESCR  FROM CISADM.F1_EXT_LOOKUP_VAL_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_NT_XID' AS TBL_NAME, 'External System' AS TBL_DESCR, 'CI_NT_XID_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'NT XID' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, NT_XID_CD AS KEY, DESCR50 AS DESCR  FROM CISADM.CI_NT_XID_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_FA_CAN_RSN' AS TBL_NAME, 'FA Cancel Reason' AS TBL_DESCR, 'CI_FA_CAN_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'FA CAN RSN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FA_CAN_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_FA_CAN_RSN_L  UNION 
SELECT 'CI_FA_TYPE' AS TBL_NAME, 'FA Type' AS TBL_DESCR, 'CI_FA_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'FA TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FA_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_FA_TYPE_L  UNION 
SELECT 'CI_FA_TYPE_PROF' AS TBL_NAME, 'FA Type Profile' AS TBL_DESCR, 'CI_FA_TYPE_PROF_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'FA TYPE PROF' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FA_TYPE_PROF_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_FA_TYPE_PROF_L  UNION 


SELECT 'D1_FACTOR' AS TBL_NAME, 'Factor' AS TBL_DESCR, 'D1_FACTOR_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-FACTOR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FACTOR_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_FACTOR_L  UNION 
SELECT 'W1_FACTOR' AS TBL_NAME, 'Factor' AS TBL_DESCR, 'W1_FACTOR_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-FACTOR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, W1_FACTOR_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_FACTOR_L  UNION 


SELECT 'W1_FAILURE_TYPE' AS TBL_NAME, 'Failure Cause' AS TBL_DESCR, 'W1_FAILURE_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-FAILTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FAILURE_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_FAILURE_TYPE_L  UNION 
SELECT 'W1_FAILURE_COMP' AS TBL_NAME, 'Failure Component' AS TBL_DESCR, 'W1_FAILURE_COMP_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-FAILCOMP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FAILURE_COMP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_FAILURE_COMP_L  UNION 
SELECT 'W1_FAILURE_MODE' AS TBL_NAME, 'Failure Mode' AS TBL_DESCR, 'W1_FAILURE_MODE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-FAILMODE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FAILURE_MODE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_FAILURE_MODE_L  UNION 
SELECT 'W1_FAILURE_PROF' AS TBL_NAME, 'Failure Profile' AS TBL_DESCR, 'W1_FAILURE_PROF_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-FAILPROF' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FAILURE_PROFILE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_FAILURE_PROF_L  UNION 
SELECT 'W1_FAILURE_REPAIR' AS TBL_NAME, 'Failure Repair' AS TBL_DESCR, 'W1_FAILURE_REPAIR_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-FAILREPR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FAILURE_REPAIR_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_FAILURE_REPAIR_L  UNION 
SELECT 'CI_WFM' AS TBL_NAME, 'Feature Configuration' AS TBL_DESCR, 'CI_WFM_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'WFM SYSTEM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WFM_NAME AS KEY, DESCR AS DESCR  FROM CISADM.CI_WFM_L  UNION 
SELECT 'CI_MD_FLD' AS TBL_NAME, 'Field' AS TBL_DESCR, 'CI_MD_FLD_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'FIELD' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FLD_NAME AS KEY, LABEL_LONG AS DESCR  FROM CISADM.CI_MD_FLD_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_FA_REM_CD' AS TBL_NAME, 'Field Activity Remark Code' AS TBL_DESCR, 'CI_FA_REM_CD_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'FA REMARK' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FA_REM_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_FA_REM_CD_L  UNION 
SELECT 'CI_FS_CL' AS TBL_NAME, 'Field Service Class' AS TBL_DESCR, 'CI_FS_CL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'FEILD SRV CL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FS_CL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_FS_CL_L  UNION 

SELECT 'CI_FA_RESCHED_RSN' AS TBL_NAME, 'Fieldwork Reschedule Reason' AS TBL_DESCR, 'CI_FA_RESCHED_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-FW RSREAS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FA_RESCHED_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_FA_RESCHED_RSN_L  UNION 
SELECT 'F1_FILE_INT_REC' AS TBL_NAME, 'File Integration Record' AS TBL_DESCR, 'F1_FILE_INT_REC_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-FLINREC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FILE_INT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_FILE_INT_REC_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'F1_FILE_INT_TYPE' AS TBL_NAME, 'File Integration Type' AS TBL_DESCR, 'F1_FILE_INT_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-FILEINT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FILE_INT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_FILE_INT_TYPE_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_FK_REF' AS TBL_NAME, 'Foreign Key Reference' AS TBL_DESCR, 'CI_FK_REF_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'FK REF' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FK_REF_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_FK_REF_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'W1_FOB' AS TBL_NAME, 'Free On Board' AS TBL_DESCR, 'W1_FOB_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-FOB' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FOB_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_FOB_L  UNION 
SELECT 'CI_FREQ' AS TBL_NAME, 'Frequency' AS TBL_DESCR, 'CI_FREQ_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'FREQUENCY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FREQ_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_FREQ_L  UNION 
SELECT 'CI_FUNC' AS TBL_NAME, 'Function' AS TBL_DESCR, 'CI_FUNC_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'FUNCTION' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FUNC_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_FUNC_L  UNION 
SELECT 'W1_PROCESS_TYPE' AS TBL_NAME, 'Functional Process Type' AS TBL_DESCR, 'W1_PROCESS_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-PROCESTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROCESS_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_PROCESS_TYPE_L  UNION 
SELECT 'CI_FUND' AS TBL_NAME, 'Fund' AS TBL_DESCR, 'CI_FUND_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'FUND' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FUND_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_FUND_L  UNION 
SELECT 'CI_GL_DIVISION' AS TBL_NAME, 'GL Division' AS TBL_DESCR, 'CI_GL_DIVISION_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'GL DIVISION' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, GL_DIVISION AS KEY, DESCR AS DESCR  FROM CISADM.CI_GL_DIVISION_L  UNION 
SELECT 'CI_MD_CTL' AS TBL_NAME, 'Generator Control' AS TBL_DESCR, 'CI_MD_CTL_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'MD CNTR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PLUG_IN_NAME AS KEY, DESCR AS DESCR  FROM CISADM.CI_MD_CTL_L  UNION 
SELECT 'CI_GEO_TYPE' AS TBL_NAME, 'Geographic Type' AS TBL_DESCR, 'CI_GEO_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'GEO TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, GEO_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_GEO_TYPE_L  UNION 

SELECT 'CI_ID_TYPE' AS TBL_NAME, 'Identifier Type' AS TBL_DESCR, 'CI_ID_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'ID TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ID_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_ID_TYPE_L  UNION 
SELECT 'F1_IWS_SVC' AS TBL_NAME, 'Inbound Web Service' AS TBL_DESCR, 'F1_IWS_SVC_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-IWSSVC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, IN_SVC_NAME AS KEY, DESCR AS DESCR  FROM CISADM.F1_IWS_SVC_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'F1_IWS_SVC_OPER' AS TBL_NAME, 'Inbound Web Service Operations' AS TBL_DESCR, 'F1_IWS_SVC_OPER_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-IWSSVCOPR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, OPERATION_NAME AS KEY, DESCR AS DESCR  FROM CISADM.F1_IWS_SVC_OPER_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'C1_INITIATIVE' AS TBL_NAME, 'Initiative' AS TBL_DESCR, 'C1_INITIATIVE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-INITIATIV' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, C1_INITIATIVE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_INITIATIVE_L  UNION 
SELECT 'C1_INITIATIVE_CRITERIA' AS TBL_NAME, 'Initiative Criteria' AS TBL_DESCR, 'C1_INITIATIVE_CRITERIA_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-INTV-CR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, C1_INITIATIVE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_INITIATIVE_CRITERIA_L  UNION 
SELECT 'F1_INSIGHT_GRP' AS TBL_NAME, 'Insight Group' AS TBL_DESCR, 'F1_INSIGHT_GRP_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-INSIGHGRP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, INSIGHT_GRP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_INSIGHT_GRP_L  UNION 
SELECT 'F1_INSIGHT_TYPE' AS TBL_NAME, 'Insight Type' AS TBL_DESCR, 'F1_INSIGHT_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-INSIGHTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, INSIGHT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_INSIGHT_TYPE_L WHERE OWNER_FLG = 'CM' UNION 



SELECT 'CI_INTV_PFRELTY' AS TBL_NAME, 'Interval Profile Relationship Type' AS TBL_DESCR, 'CI_INTV_PFRELTY_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'INT PF REL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, INTV_PF_REL_TYP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_INTV_PFRELTY_L  UNION 
SELECT 'CI_INTV_PF_TYP' AS TBL_NAME, 'Interval Profile Type' AS TBL_DESCR, 'CI_INTV_PF_TYP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'INT PF TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, INTV_PF_TYP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_INTV_PF_TYP_L  UNION 
SELECT 'CI_INTV_REG_TYP' AS TBL_NAME, 'Interval Register Type' AS TBL_DESCR, 'CI_INTV_REG_TYP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'INT REG TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, INTV_REG_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_INTV_REG_TYP_L  UNION 
SELECT 'C1_ISS_CTR' AS TBL_NAME, 'Issuing Center' AS TBL_DESCR, 'C1_ISS_CTR_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-ISSCTR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ISS_CTR_CD AS KEY, DESCR AS DESCR  FROM CISADM.C1_ISS_CTR_L  UNION 
SELECT 'CI_ITEM_TYPE' AS TBL_NAME, 'Item Type' AS TBL_DESCR, 'CI_ITEM_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'ITEM TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ITEM_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_ITEM_TYPE_L  UNION 
SELECT 'CI_XAI_JMS_CON' AS TBL_NAME, 'JMS Connection' AS TBL_DESCR, 'CI_XAI_JMS_CON_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'JMS CONNECT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_JMS_CON_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_JMS_CON_L  UNION 
SELECT 'CI_XAI_JMS_Q' AS TBL_NAME, 'JMS Queue' AS TBL_DESCR, 'CI_XAI_JMS_Q_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'XAI JMS Q' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_JMS_QUEUE_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_JMS_Q_L  UNION 
SELECT 'CI_XAI_JMS_TPC' AS TBL_NAME, 'JMS Topic' AS TBL_DESCR, 'CI_XAI_JMS_TPC_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'XAI JMS TPC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_JMS_TOPIC_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_JMS_TPC_L  UNION 
SELECT 'CI_XAI_JNDI_SVR' AS TBL_NAME, 'JNDI Server' AS TBL_DESCR, 'CI_XAI_JNDI_SVR_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'XAI JNDI SVR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_JNDI_SVR_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_JNDI_SVR_L  UNION 
SELECT 'F1_CRYPTO_KEY_RING' AS TBL_NAME, 'Key Ring' AS TBL_DESCR, 'F1_CRYPTO_KEY_RING_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-CRYPTRING' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, KEY_RING_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_CRYPTO_KEY_RING_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'W1_LABOR_EARNING_TYPE' AS TBL_NAME, 'Labor Earning Type' AS TBL_DESCR, 'W1_LABOR_EARNING_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-LBRERNTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, LABOR_EARNING_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_LABOR_EARNING_TYPE_L  UNION 

SELECT 'C1_LEAD_EVT_TYPE' AS TBL_NAME, 'Lead Event Type' AS TBL_DESCR, 'C1_LEAD_EVT_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-LEAD-EVTY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, C1_LEAD_EVT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_LEAD_EVT_TYPE_L  UNION 
SELECT 'CI_LETTER_TMPL' AS TBL_NAME, 'Letter Template' AS TBL_DESCR, 'CI_LETTER_TMPL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'LETTER TMPL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, LTR_TMPL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_LETTER_TMPL_L  UNION 
SELECT 'C1_LTR_TMPL_REC' AS TBL_NAME, 'Letter Template Record' AS TBL_DESCR, 'C1_LTR_TMPL_REC_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-LTRTMPREC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, LTR_TMPL_CD AS KEY, DESCR AS DESCR  FROM CISADM.C1_LTR_TMPL_REC_L  UNION 
SELECT 'W1_NODE_TYPE' AS TBL_NAME, 'Location/Organization Type' AS TBL_DESCR, 'W1_NODE_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-NODETYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, NODE_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_NODE_TYPE_L  UNION 

SELECT 'CI_LOOKUP_VAL' AS TBL_NAME, 'Lookup Field Value' AS TBL_DESCR, 'CI_LOOKUP_VAL_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-LOOKUPVAL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, FIELD_VALUE AS KEY, DESCR AS DESCR  FROM CISADM.CI_LOOKUP_VAL_L WHERE OWNER_FLG = 'CM' UNION 

SELECT 'CI_MD_ELTY' AS TBL_NAME, 'MD Element Type' AS TBL_DESCR, 'CI_MD_ELTY_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'ELEM TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ELEM_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MD_ELTY_L  UNION 
SELECT 'CI_MD_SVC' AS TBL_NAME, 'MD Service' AS TBL_DESCR, 'CI_MD_SVC_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'SERVICE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SVC_NAME AS KEY, DESCR AS DESCR  FROM CISADM.CI_MD_SVC_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'W1_MAINTMGR' AS TBL_NAME, 'Maintenance Manager' AS TBL_DESCR, 'W1_MAINTMGR_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-MAINTMGR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MAINTMGR_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_MAINTMGR_L  UNION 
SELECT 'CI_MD_MO' AS TBL_NAME, 'Maintenance Object' AS TBL_DESCR, 'CI_MD_MO_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'MAIN OBJ' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MAINT_OBJ_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MD_MO_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'F1_MANAG_CONTENT' AS TBL_NAME, 'Managed Content' AS TBL_DESCR, 'F1_MANAG_CONTENT_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-MAN CONT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MANAG_CONTENT_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_MANAG_CONTENT_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'W1_MANUFACTURER' AS TBL_NAME, 'Manufacturer' AS TBL_DESCR, 'W1_MANUFACTURER_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-MANUF' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, W1_MANUFACTURER_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_MANUFACTURER_L  UNION 
SELECT 'CI_MFG' AS TBL_NAME, 'Manufacturer - CCB' AS TBL_DESCR, 'CI_MFG_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'MANUFACT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MFG_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MFG_L  UNION 
SELECT 'D1_MANUFACTURER' AS TBL_NAME, 'Manufacturer - MDM' AS TBL_DESCR, 'D1_MANUFACTURER_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-MANUF' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MANUFACTURER_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_MANUFACTURER_L  UNION 
SELECT 'C1_MKT' AS TBL_NAME, 'Market' AS TBL_DESCR, 'C1_MKT_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-MKT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, C1_MKT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_MKT_L  UNION 
SELECT 'D1_MKT' AS TBL_NAME, 'Market' AS TBL_DESCR, 'D1_MKT_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-MARKET' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MKT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_MKT_L  UNION 
SELECT 'F1_MKTCFG' AS TBL_NAME, 'Market Configuration' AS TBL_DESCR, 'F1_MKTCFG_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-MKTCFG' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, F1_MKTCFG_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_MKTCFG_L  UNION 
SELECT 'D1_MKT_CONTRACT_TYPE' AS TBL_NAME, 'Market Contract Type' AS TBL_DESCR, 'D1_MKT_CONTRACT_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-MKTCNTTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MKT_CONTRACT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_MKT_CONTRACT_TYPE_L  UNION 
SELECT 'F1_MKTMSG_TYPE' AS TBL_NAME, 'Market Message Type' AS TBL_DESCR, 'F1_MKTMSG_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-MKTMSGTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, F1_MKTMSG_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_MKTMSG_TYPE_L  UNION 
SELECT 'CI_MKTMSG_TYPE' AS TBL_NAME, 'Market Message Type' AS TBL_DESCR, 'CI_MKTMSG_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-MKTMSGTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MKTMSG_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MKTMSG_TYPE_L  UNION 
SELECT 'F1_MKTPROC_TYPE' AS TBL_NAME, 'Market Process Type' AS TBL_DESCR, 'F1_MKTPROC_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-MKTPRCTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MKTPROC_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_MKTPROC_TYPE_L  UNION 
SELECT 'D1_MKT_PRODUCT_SET' AS TBL_NAME, 'Market Product Set' AS TBL_DESCR, 'D1_MKT_PRODUCT_SET_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-MKTPROSET' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MKT_PRODUCT_SET_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_MKT_PRODUCT_SET_L  UNION 
SELECT 'D1_MKT_PRODUCT_TYPE' AS TBL_NAME, 'Market Product Type' AS TBL_DESCR, 'D1_MKT_PRODUCT_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-MKTPROTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MKT_PRODUCT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_MKT_PRODUCT_TYPE_L  UNION 
SELECT 'C1_MKT_PROV_CONFIG_OPT' AS TBL_NAME, 'Market Provider Configuration Option' AS TBL_DESCR, 'C1_MKT_PROV_CONFIG_OPT_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-MKTPRVCFG' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROV_CONFIG_OPT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_MKT_PROV_CONFIG_OPT_L  UNION 

SELECT 'CI_MEVT_CAN_RSN' AS TBL_NAME, 'Match Event Cancel Reason' AS TBL_DESCR, 'CI_MEVT_CAN_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'M EVT CAN RS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MEVT_CAN_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MEVT_CAN_RSN_L  UNION 
SELECT 'CI_MATCH_TYPE' AS TBL_NAME, 'Match Type' AS TBL_DESCR, 'CI_MATCH_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'MATCH TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MATCH_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MATCH_TYPE_L  UNION 
SELECT 'D1_MSRMT_CYC' AS TBL_NAME, 'Measurement Cycle' AS TBL_DESCR, 'D1_MSRMT_CYC_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-MSRMTCYC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MSRMT_CYC_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_MSRMT_CYC_L  UNION 
SELECT 'D1_MSRMT_CYC_RTE' AS TBL_NAME, 'Measurement Cycle Route' AS TBL_DESCR, 'D1_MSRMT_CYC_RTE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-MSRMTCYCR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MSRMT_CYC_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_MSRMT_CYC_RTE_L  UNION 

SELECT 'D1_MSRMT_DATA_SNAP_TYPE' AS TBL_NAME, 'Measurement Data Snapshot Type' AS TBL_DESCR, 'D1_MSRMT_DATA_SNAP_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-MSRTDSTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MSRMT_DATA_SNAP_TYPE_CD AS KEY, DESCR_SHORT AS DESCR  FROM CISADM.D1_MSRMT_DATA_SNAP_TYPE_L  UNION 
SELECT 'W1_MEASUREMENT_UOM' AS TBL_NAME, 'Measurement Identifier' AS TBL_DESCR, 'W1_MEASUREMENT_UOM_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-MSRMTUOM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MEASUREMENT_UOM_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_MEASUREMENT_UOM_L  UNION 
SELECT 'W1_MEASUREMENT_TYPE' AS TBL_NAME, 'Measurement Type' AS TBL_DESCR, 'W1_MEASUREMENT_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-MSRMTTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MEASUREMENT_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_MEASUREMENT_TYPE_L  UNION 
SELECT 'D1_MC_COMPAR_TYPE' AS TBL_NAME, 'Measuring Component Comparison Type' AS TBL_DESCR, 'D1_MC_COMPAR_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-MCCMPTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COMPAR_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_MC_COMPAR_TYPE_L  UNION 
SELECT 'D1_MEASR_COMP_SET' AS TBL_NAME, 'Measuring Component Set' AS TBL_DESCR, 'D1_MEASR_COMP_SET_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-MCSET' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MEASR_COMP_SET_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_MEASR_COMP_SET_L  UNION 
SELECT 'D1_MEASR_COMP_TYPE' AS TBL_NAME, 'Measuring Component Type' AS TBL_DESCR, 'D1_MEASR_COMP_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-MCTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MEASR_COMP_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_MEASR_COMP_TYPE_L  UNION 
SELECT 'CI_MD_MENU' AS TBL_NAME, 'Menu Information' AS TBL_DESCR, 'CI_MD_MENU_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'MENU' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MENU_NAME AS KEY, DESCR50 AS DESCR  FROM CISADM.CI_MD_MENU_L WHERE OWNER_FLG = 'CM' UNION 



SELECT 'CI_XAI_CLASS' AS TBL_NAME, 'Message Class' AS TBL_DESCR, 'CI_XAI_CLASS_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'XAI CLASS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_CLASS_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_CLASS_L WHERE OWNER_FLG = 'CM' UNION 

SELECT 'CI_XAI_SENDER' AS TBL_NAME, 'Message Sender' AS TBL_DESCR, 'CI_XAI_SENDER_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'XAI SENDER' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_SENDER_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_SENDER_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_MTR_CONFIG_TY' AS TBL_NAME, 'Meter Configuration Type' AS TBL_DESCR, 'CI_MTR_CONFIG_TY_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'MTR CONF TYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MTR_CONFIG_TY_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MTR_CONFIG_TY_L  UNION 
SELECT 'CI_MTR_ID_TYPE' AS TBL_NAME, 'Meter ID Type' AS TBL_DESCR, 'CI_MTR_ID_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'MR ID TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MTR_ID_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MTR_ID_TYPE_L  UNION 
SELECT 'CI_MTR_LOC' AS TBL_NAME, 'Meter Location' AS TBL_DESCR, 'CI_MTR_LOC_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'MTR LOC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MTR_LOC_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MTR_LOC_L  UNION 
SELECT 'CI_MR_CYC' AS TBL_NAME, 'Meter Read Cycle' AS TBL_DESCR, 'CI_MR_CYC_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'MR CYCLE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MR_CYC_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MR_CYC_L  UNION 
SELECT 'CI_MR_INSTR' AS TBL_NAME, 'Meter Read Instruction' AS TBL_DESCR, 'CI_MR_INSTR_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'MR INSTR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MR_INSTR_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MR_INSTR_L  UNION 

SELECT 'CI_MR_SOURCE' AS TBL_NAME, 'Meter Read Source' AS TBL_DESCR, 'CI_MR_SOURCE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'MR SOURCE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MR_SOURCE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MR_SOURCE_L  UNION 
SELECT 'CI_MR_WARN' AS TBL_NAME, 'Meter Read Warning' AS TBL_DESCR, 'CI_MR_WARN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'MR WARN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MR_WARN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MR_WARN_L  UNION 
SELECT 'CI_READER_REM' AS TBL_NAME, 'Meter Reader Remark' AS TBL_DESCR, 'CI_READER_REM_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'MR RDR REM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, READER_REM_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_READER_REM_L  UNION 
SELECT 'CI_MTR_TYPE' AS TBL_NAME, 'Meter Type' AS TBL_DESCR, 'CI_MTR_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'METER TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MTR_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MTR_TYPE_L  UNION 
SELECT 'F1_MIGR_PLAN' AS TBL_NAME, 'Migration Plan' AS TBL_DESCR, 'F1_MIGR_PLAN_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-MIGRPLAN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MIGR_PLAN_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_MIGR_PLAN_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'F1_MIGR_REQ' AS TBL_NAME, 'Migration Request' AS TBL_DESCR, 'F1_MIGR_REQ_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-MIGRREQ' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MIGR_REQ_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_MIGR_REQ_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'F1_MOBILE_COMPONENT' AS TBL_NAME, 'Mobile Component' AS TBL_DESCR, 'F1_MOBILE_COMPONENT_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-MOBCOMP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, F1_COMPONENT_NAME_CD AS KEY, DESCR254 AS DESCR  FROM CISADM.F1_MOBILE_COMPONENT_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'D1_MULTI_VAR_FACTOR' AS TBL_NAME, 'Multi Variable Factor' AS TBL_DESCR, 'D1_MULTI_VAR_FACTOR_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-MLVARFACT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MULTI_VAR_FACTOR_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_MULTI_VAR_FACTOR_L  UNION 


SELECT 'CI_NAV_OPT' AS TBL_NAME, 'Navigation Option' AS TBL_DESCR, 'CI_NAV_OPT_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'NAV OPT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, NAV_OPT_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_NAV_OPT_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_NCD_TYPE' AS TBL_NAME, 'Non Cash Deposit Type' AS TBL_DESCR, 'CI_NCD_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'NCD TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, NCD_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_NCD_TYPE_L  UNION 
SELECT 'CI_NB_RULE' AS TBL_NAME, 'Non-billed Budget Rule' AS TBL_DESCR, 'CI_NB_RULE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'NB RULE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, NB_RULE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_NB_RULE_L  UNION 
SELECT 'CI_NT_DWN_PROF' AS TBL_NAME, 'Notification Download Profile' AS TBL_DESCR, 'CI_NT_DWN_PROF_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'NT DWN PROF' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, NT_DWN_PROF_CD AS KEY, DESCR50 AS DESCR  FROM CISADM.CI_NT_DWN_PROF_L  UNION 
SELECT 'CI_NT_DWN_TYPE' AS TBL_NAME, 'Notification Download Type' AS TBL_DESCR, 'CI_NT_DWN_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'NT DWN TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, NT_DWN_TYPE_CD AS KEY, DESCR50 AS DESCR  FROM CISADM.CI_NT_DWN_TYPE_L  UNION 

SELECT 'C1_NTF_TYPE' AS TBL_NAME, 'Notification Type' AS TBL_DESCR, 'C1_NTF_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-NTF-TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, NTF_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_NTF_TYPE_L  UNION 
SELECT 'CI_NT_UP_XTYPE' AS TBL_NAME, 'Notification Upload Type' AS TBL_DESCR, 'CI_NT_UP_XTYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'NT UPL TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, NT_UP_XTYPE_CD AS KEY, DESCR50 AS DESCR  FROM CISADM.CI_NT_UP_XTYPE_L  UNION 
SELECT 'CI_OP_AREA' AS TBL_NAME, 'Operational Area' AS TBL_DESCR, 'CI_OP_AREA_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'OP AREA' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, OP_AREA_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_OP_AREA_L  UNION 
SELECT 'CI_ENRL_CAN_RSN' AS TBL_NAME, 'Order Cancel Reason' AS TBL_DESCR, 'CI_ENRL_CAN_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'ENRL CAN RSN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ENRL_CAN_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_ENRL_CAN_RSN_L  UNION 
SELECT 'CI_ENRL_CBK_RSN' AS TBL_NAME, 'Order Hold Reason' AS TBL_DESCR, 'CI_ENRL_CBK_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'ENRL CBK RSN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ENRL_CALLBK_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_ENRL_CBK_RSN_L  UNION 
SELECT 'F1_OUTMSG_TYPE' AS TBL_NAME, 'Outbound Message Type' AS TBL_DESCR, 'F1_OUTMSG_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-OUTMSGTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, OUTMSG_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_OUTMSG_TYPE_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_OEVT_CAN_RSN' AS TBL_NAME, 'Overdue Event Cancel Reason' AS TBL_DESCR, 'CI_OEVT_CAN_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-OE-CNREAS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, OEVT_CAN_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_OEVT_CAN_RSN_L  UNION 
SELECT 'CI_OD_EVT_TYPE' AS TBL_NAME, 'Overdue Event Type' AS TBL_DESCR, 'CI_OD_EVT_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-OD-EVTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, OD_EVT_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_OD_EVT_TYPE_L  UNION 
SELECT 'CI_OD_PROC_TMP' AS TBL_NAME, 'Overdue Process Template' AS TBL_DESCR, 'CI_OD_PROC_TMP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-ODPROC-TM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, OD_PROC_TMP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_OD_PROC_TMP_L  UNION 
SELECT 'W1_OVERHEAD' AS TBL_NAME, 'Overhead' AS TBL_DESCR, 'W1_OVERHEAD_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-OVRHD' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, OVERHEAD_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_OVERHEAD_L  UNION 
SELECT 'W1_OVERTIME_TYPE' AS TBL_NAME, 'Overtime Type' AS TBL_DESCR, 'W1_OVERTIME_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-OVRTIMTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, OVERTIME_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_OVERTIME_TYPE_L  UNION 
SELECT 'CI_PKG' AS TBL_NAME, 'Package' AS TBL_DESCR, 'CI_PKG_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'PACKAGE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PACKAGE_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_PKG_L  UNION 
SELECT 'CI_PP_TYPE' AS TBL_NAME, 'Pay Plan Type' AS TBL_DESCR, 'CI_PP_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'PP TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PP_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_PP_TYPE_L  UNION 
SELECT 'C1_PA_RQST_TYPE' AS TBL_NAME, 'Payment Arrangement Request Type' AS TBL_DESCR, 'C1_PA_RQST_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-PARQSTTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PA_RQST_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_PA_RQST_TYPE_L  UNION 
SELECT 'CI_PAY_CAN_RSN' AS TBL_NAME, 'Payment Cancel Reason' AS TBL_DESCR, 'CI_PAY_CAN_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'PAY CAN RSN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CAN_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_PAY_CAN_RSN_L  UNION 
SELECT 'CI_PAY_METH' AS TBL_NAME, 'Payment Method' AS TBL_DESCR, 'CI_PAY_METH_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'PAY METHOD' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PAY_METH_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_PAY_METH_L  UNION 
SELECT 'CI_PAY_SEG_TYPE' AS TBL_NAME, 'Payment Segment Type' AS TBL_DESCR, 'CI_PAY_SEG_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'PAY SEG TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PAY_SEG_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_PAY_SEG_TYPE_L  UNION 
SELECT 'CI_PAY_TMPL' AS TBL_NAME, 'Payment Template' AS TBL_DESCR, 'CI_PAY_TMPL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-PAY TMPL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PAY_TMPL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_PAY_TMPL_L  UNION 
SELECT 'W1_PAYMENT_TERM' AS TBL_NAME, 'Payment Term' AS TBL_DESCR, 'W1_PAYMENT_TERM_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-PAYMNTERM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PAYMENT_TERM_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_PAYMENT_TERM_L  UNION 
SELECT 'F1_PERF_TGT' AS TBL_NAME, 'Performance Target' AS TBL_DESCR, 'F1_PERF_TGT_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-PERFTGT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PERF_TARGET_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_PERF_TGT_L  UNION 
SELECT 'F1_PERF_TGT_TYPE' AS TBL_NAME, 'Performance Target Type' AS TBL_DESCR, 'F1_PERF_TGT_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-PERFTGTTY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PERF_TARGET_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_PERF_TGT_TYPE_L  UNION 
SELECT 'W1_PERMIT_CLASS' AS TBL_NAME, 'Permit Class' AS TBL_DESCR, 'W1_PERMIT_CLASS_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-PERMITCLS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PERMIT_CLASS_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_PERMIT_CLASS_L  UNION 
SELECT 'W1_PERMIT_TMPL' AS TBL_NAME, 'Permit Template' AS TBL_DESCR, 'W1_PERMIT_TMPL_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-PRMTTMPL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PERMIT_TMPL_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_PERMIT_TMPL_L  UNION 
SELECT 'C1_COMM_RTE_TYPE' AS TBL_NAME, 'Person Contact Type' AS TBL_DESCR, 'C1_COMM_RTE_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-PERCNT-TY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, COMM_RTE_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_COMM_RTE_TYPE_L  UNION 
SELECT 'CI_PER_REL_TYPE' AS TBL_NAME, 'Person Relationship Type' AS TBL_DESCR, 'CI_PER_REL_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'PER REL TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PER_REL_TYPE_CD AS KEY, DESCR12 AS DESCR  FROM CISADM.CI_PER_REL_TYPE_L  UNION 
SELECT 'CI_PHONE_TYPE' AS TBL_NAME, 'Phone Type' AS TBL_DESCR, 'CI_PHONE_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'PHONE TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PHONE_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_PHONE_TYPE_L  UNION 
SELECT 'W1_PLANNER' AS TBL_NAME, 'Planner' AS TBL_DESCR, 'W1_PLANNER_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-PLANNER' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PLANNER_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_PLANNER_L  UNION 
SELECT 'CI_PORTAL' AS TBL_NAME, 'Portal' AS TBL_DESCR, 'CI_PORTAL_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'PORTAL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PORTAL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_PORTAL_L WHERE OWNER_FLG = 'CM' UNION 


SELECT 'CI_PREM_TYPE' AS TBL_NAME, 'Premise Type' AS TBL_DESCR, 'CI_PREM_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'PREM TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PREM_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_PREM_TYPE_L  UNION 
SELECT 'F1_PROC_DEFN' AS TBL_NAME, 'Process Flow Type' AS TBL_DESCR, 'F1_PROC_DEFN_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-PROCDEFN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROCESS_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_PROC_DEFN_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'D1_PROC_MTHD' AS TBL_NAME, 'Processing Method' AS TBL_DESCR, 'D1_PROC_MTHD_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-PROCMETHD' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROC_ROLE_FLG AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_PROC_MTHD_L  UNION 
SELECT 'D1_PROC_TIMETABLE_TYPE' AS TBL_NAME, 'Processing Timetable Type' AS TBL_DESCR, 'D1_PROC_TIMETABLE_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-PRCTTBTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROC_TIMETABLE_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_PROC_TIMETABLE_TYPE_L  UNION 




SELECT 'W1_PROJECT_CATEGORY' AS TBL_NAME, 'Project Category' AS TBL_DESCR, 'W1_PROJECT_CATEGORY_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-PRJCAT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PRJ_CAT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_PROJECT_CATEGORY_L  UNION 
SELECT 'W1_PROPERTY_UNIT' AS TBL_NAME, 'Property Unit' AS TBL_DESCR, 'W1_PROPERTY_UNIT_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-PROPUNIT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROPERTY_UNIT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_PROPERTY_UNIT_L  UNION 
SELECT 'CI_PROP_DCL_RSN' AS TBL_NAME, 'Proposal SA Decline Reason' AS TBL_DESCR, 'CI_PROP_DCL_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'PROP DCL RSN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROP_DCL_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_PROP_DCL_RSN_L  UNION 
SELECT 'CI_PROTOCOL' AS TBL_NAME, 'Protocol' AS TBL_DESCR, 'CI_PROTOCOL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'PROTOCOL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROTOCOL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_PROTOCOL_L  UNION 
SELECT 'C1_PROV_CONFIG_OPT' AS TBL_NAME, 'Provider Configuration Option' AS TBL_DESCR, 'C1_PROV_CONFIG_OPT_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-PROVCNFG' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PROV_CONFIG_OPT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_PROV_CONFIG_OPT_L  UNION 
SELECT 'W1_PURCHASE_CMDTY' AS TBL_NAME, 'Purchase Commodity' AS TBL_DESCR, 'W1_PURCHASE_CMDTY_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-PRCHSCOM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, PURCHASE_CMDTY_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_PURCHASE_CMDTY_L  UNION 
SELECT 'W1_QUESTION' AS TBL_NAME, 'Question' AS TBL_DESCR, 'W1_QUESTION_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-QUESTION' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, QUESTION_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_QUESTION_L  UNION 
SELECT 'CI_QTE_RTE_TYPE' AS TBL_NAME, 'Quote Route Type' AS TBL_DESCR, 'CI_QTE_RTE_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'QTE RTE TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, QTE_RTE_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_QTE_RTE_TYPE_L  UNION 
SELECT 'CI_RC' AS TBL_NAME, 'Rate Component' AS TBL_DESCR, 'CI_RC_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'RATE COMP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, RS_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_RC_L  UNION 
SELECT 'CI_RS' AS TBL_NAME, 'Rate Schedule' AS TBL_DESCR, 'CI_RS_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'RATE SCHED' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, RS_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_RS_L  UNION 
SELECT 'CI_RS' AS TBL_NAME, 'Rate Schedule' AS TBL_DESCR, 'CI_RS_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'RS CMA' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, RS_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_RS_L  UNION 
SELECT 'CI_RV' AS TBL_NAME, 'Rate Version' AS TBL_DESCR, 'CI_RV_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'RATE VERSION' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, RS_CD AS KEY, DESCR_TMPLT AS DESCR  FROM CISADM.CI_RV_L  UNION 
SELECT 'CI_READ_OUT_TYP' AS TBL_NAME, 'Read Out Type' AS TBL_DESCR, 'CI_READ_OUT_TYP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'READ OUT TYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, READ_OUT_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_READ_OUT_TYP_L  UNION 
SELECT 'CI_REBATE_DEFN' AS TBL_NAME, 'Rebate Definition' AS TBL_DESCR, 'CI_REBATE_DEFN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-RDEF' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CONSV_PROG_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_REBATE_DEFN_L  UNION 
SELECT 'F1_REDACTION_RULE' AS TBL_NAME, 'Redaction Rule' AS TBL_DESCR, 'F1_REDACTION_RULE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-RDCTRULE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, REDACT_RULE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_REDACTION_RULE_L  UNION 
SELECT 'CI_REG_RULE' AS TBL_NAME, 'Register Rule' AS TBL_DESCR, 'CI_REG_RULE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'REG RULE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, REG_RULE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_REG_RULE_L  UNION 
SELECT 'CI_MD_RPT' AS TBL_NAME, 'Report Definition' AS TBL_DESCR, 'CI_MD_RPT_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'REPORT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, REPORT_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MD_RPT_L  UNION 

SELECT 'CI_REP' AS TBL_NAME, 'Representative' AS TBL_DESCR, 'CI_REP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'REPREST' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, REP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_REP_L  UNION 
SELECT 'F1_REQ_TYPE' AS TBL_NAME, 'Request Type' AS TBL_DESCR, 'F1_REQ_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-REQ-TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, REQ_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_REQ_TYPE_L  UNION 
SELECT 'W1_RESRC_UOM' AS TBL_NAME, 'Resource UOM' AS TBL_DESCR, 'W1_RESRC_UOM_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-RESRCUOM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, RESRC_UOM_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_RESRC_UOM_L  UNION 
SELECT 'CI_RETIRE_RSN' AS TBL_NAME, 'Retirement Reason' AS TBL_DESCR, 'CI_RETIRE_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'RETIRE RSN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, RETIRE_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_RETIRE_RSN_L  UNION 
SELECT 'CI_REV_CL' AS TBL_NAME, 'Revenue Class' AS TBL_DESCR, 'CI_REV_CL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'REV GL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, REV_CL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_REV_CL_L  UNION 
SELECT 'CI_ROLE' AS TBL_NAME, 'Role' AS TBL_DESCR, 'CI_ROLE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'TO DO RL SC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ROLE_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_ROLE_L  UNION 
SELECT 'CI_ROLE' AS TBL_NAME, 'Role' AS TBL_DESCR, 'CI_ROLE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'TO DO ROLE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ROLE_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_ROLE_L  UNION 
SELECT 'D1_RULE' AS TBL_NAME, 'Rule' AS TBL_DESCR, 'D1_RULE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-RULE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, RULE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_RULE_L  UNION 
SELECT 'CI_SA_REL_TYPE' AS TBL_NAME, 'SA Relationship Type' AS TBL_DESCR, 'CI_SA_REL_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SA REL TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SA_REL_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SA_REL_TYPE_L  UNION 
SELECT 'CI_SA_TYPE' AS TBL_NAME, 'SA Type' AS TBL_DESCR, 'CI_SA_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SA TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SA_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SA_TYPE_L  UNION 

SELECT 'CI_SCM_NCTV_RSN' AS TBL_NAME, 'SC Membership Inactive Reason' AS TBL_DESCR, 'CI_SCM_NCTV_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SCM INCTV RS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SCM_INACTV_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SCM_NCTV_RSN_L  UNION 
SELECT 'CI_SCM_TYPE' AS TBL_NAME, 'SC Membership Type' AS TBL_DESCR, 'CI_SCM_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SCM TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SCM_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SCM_TYPE_L  UNION 
SELECT 'CI_SIC' AS TBL_NAME, 'SIC Code' AS TBL_DESCR, 'CI_SIC_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SIC CODE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SIC_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SIC_L  UNION 
SELECT 'CI_SP_TYPE' AS TBL_NAME, 'SP Type' AS TBL_DESCR, 'CI_SP_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SPTYPE CMA' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SP_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SP_TYPE_L  UNION 
SELECT 'CI_SP_TYPE' AS TBL_NAME, 'SP Type' AS TBL_DESCR, 'CI_SP_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SP TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SP_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SP_TYPE_L  UNION 
SELECT 'C1_REPRESENTATIVE' AS TBL_NAME, 'Sales Representative' AS TBL_DESCR, 'C1_REPRESENTATIVE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-SALESREP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, C1_REPRESENTATIVE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_REPRESENTATIVE_L  UNION 


SELECT 'CI_SCR' AS TBL_NAME, 'Script' AS TBL_DESCR, 'CI_SCR_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'SCRIPT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SCR_CD AS KEY, DESCR254 AS DESCR  FROM CISADM.CI_SCR_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_MD_SO' AS TBL_NAME, 'Search Object' AS TBL_DESCR, 'CI_MD_SO_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'MD SRCH OBJ' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SO_CD AS KEY, TTL AS DESCR  FROM CISADM.CI_MD_SO_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_SEAS_TM_SHIFT' AS TBL_NAME, 'Seasonal Time Shift' AS TBL_DESCR, 'CI_SEAS_TM_SHIFT_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'SEAS TM SHFT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SEASON_TM_SHIFT_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SEAS_TM_SHIFT_L  UNION 
SELECT 'CI_SC_TYPE' AS TBL_NAME, 'Security Type' AS TBL_DESCR, 'CI_SC_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'SEC TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SC_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SC_TYPE_L  UNION 
SELECT 'W1_SERVICE_AREA' AS TBL_NAME, 'Service Area' AS TBL_DESCR, 'W1_SERVICE_AREA_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-SVCAREA' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SERVICE_AREA_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_SERVICE_AREA_L  UNION 
SELECT 'C1_SERVICE_CAT' AS TBL_NAME, 'Service Category - CCB' AS TBL_DESCR, 'C1_SERVICE_CAT_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-SVCCAT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, C1_SERVICE_CAT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_SERVICE_CAT_L  UNION 
SELECT 'W1_SERVICE_CLASS' AS TBL_NAME, 'Service Class' AS TBL_DESCR, 'W1_SERVICE_CLASS_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-SVCCLASS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SERVICE_CLASS_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_SERVICE_CLASS_L  UNION 
SELECT 'W1_SERVICE_CODE' AS TBL_NAME, 'Service Code' AS TBL_DESCR, 'W1_SERVICE_CODE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-SVCCODE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SERVICE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_SERVICE_CODE_L  UNION 
SELECT 'C1_SERVICE_CODE' AS TBL_NAME, 'Service Code - CCB' AS TBL_DESCR, 'C1_SERVICE_CODE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-SVCCODE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, C1_SERVICE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_SERVICE_CODE_L  UNION 
SELECT 'CI_SC_EVT_TYPE' AS TBL_NAME, 'Service Credit Event Type' AS TBL_DESCR, 'CI_SC_EVT_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SC EVT TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SC_EVT_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SC_EVT_TYPE_L  UNION 
SELECT 'W1_SVC_HIST_TYPE' AS TBL_NAME, 'Service History Type' AS TBL_DESCR, 'W1_SVC_HIST_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-SVCHSTTY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SVC_HIST_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_SVC_HIST_TYPE_L  UNION 
SELECT 'D1_SP_QTY_TYPE' AS TBL_NAME, 'Service Point Quantity Type' AS TBL_DESCR, 'D1_SP_QTY_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-SPQTYTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_SP_QTY_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_SP_QTY_TYPE_L  UNION 
SELECT 'D1_SP_TYPE' AS TBL_NAME, 'Service Point Type' AS TBL_DESCR, 'D1_SP_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-SPTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_SP_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_SP_TYPE_L  UNION 
SELECT 'D1_SPR' AS TBL_NAME, 'Service Provider - MDM' AS TBL_DESCR, 'D1_SPR_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-SVCPROVDR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_SPR_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_SPR_L  UNION 

SELECT 'CI_SQI' AS TBL_NAME, 'Service Quantity Identifier - CCB' AS TBL_DESCR, 'CI_SQI_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SQI' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SQI_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SQI_L  UNION 
SELECT 'D1_SQI' AS TBL_NAME, 'Service Quantity Identifier - MDM' AS TBL_DESCR, 'D1_SQI_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-SQI' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_SQI_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_SQI_L  UNION 
SELECT 'CI_SQ_RULE' AS TBL_NAME, 'Service Quantity Rule' AS TBL_DESCR, 'CI_SQ_RULE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SQ RULE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SQ_RULE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SQ_RULE_L  UNION 
SELECT 'CI_MR_RTE_TYPE' AS TBL_NAME, 'Service Route Type' AS TBL_DESCR, 'CI_MR_RTE_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'MR RTE TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MR_RTE_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MR_RTE_TYPE_L  UNION 
SELECT 'F1_SVC_TASK_TYPE' AS TBL_NAME, 'Service Task Type' AS TBL_DESCR, 'F1_SVC_TASK_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-STASKTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, F1_STASK_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_SVC_TASK_TYPE_L  UNION 
SELECT 'CI_SVC_TYPE' AS TBL_NAME, 'Service Type - CCB' AS TBL_DESCR, 'CI_SVC_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SERVICE TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SVC_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SVC_TYPE_L  UNION 
SELECT 'D1_SVC_TYPE' AS TBL_NAME, 'Service Type - MDM' AS TBL_DESCR, 'D1_SVC_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-SVCTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_SVC_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_SVC_TYPE_L  UNION 
SELECT 'W1_SERVICE_CALL_CATEGORY' AS TBL_NAME, 'Service call category' AS TBL_DESCR, 'W1_SERVICE_CALL_CATEGORY_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-SVCCALCAT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SERVICE_CAT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_SERVICE_CALL_CATEGORY_L  UNION 
SELECT 'D1_SETT_UNIT' AS TBL_NAME, 'Settlement Unit' AS TBL_DESCR, 'D1_SETT_UNIT_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-SETTUNIT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SETT_UNIT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_SETT_UNIT_L  UNION 
SELECT 'CI_SEV_EVT_TYPE' AS TBL_NAME, 'Severance Event Type' AS TBL_DESCR, 'CI_SEV_EVT_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SEV EVT TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SEV_EVT_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SEV_EVT_TYPE_L  UNION 
SELECT 'CI_SEV_PROC_TMP' AS TBL_NAME, 'Severance Process Template' AS TBL_DESCR, 'CI_SEV_PROC_TMP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SEV PROC TMP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SEV_PROC_TMPL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_SEV_PROC_TMP_L  UNION 
SELECT 'W1_SHAPE' AS TBL_NAME, 'Shape' AS TBL_DESCR, 'W1_SHAPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-SHAPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SHAPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_SHAPE_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'W1_SHIP_DEFICIENCY_TYPE' AS TBL_NAME, 'Shipment Deficiency Type' AS TBL_DESCR, 'W1_SHIP_DEFICIENCY_TYPE_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-SHIPDEFCY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SHIPMENT_DEFICIENCY_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_SHIP_DEFICIENCY_TYPE_L  UNION 
SELECT 'CI_MD_SRC_TYPE' AS TBL_NAME, 'Source Type' AS TBL_DESCR, 'CI_MD_SRC_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'MD SRC TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SRC_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MD_SRC_TYPE_L  UNION 
SELECT 'W1_SPECIFICATION' AS TBL_NAME, 'Specification' AS TBL_DESCR, 'W1_SPECIFICATION_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-SPEC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, SPECIFICATION_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_SPECIFICATION_L  UNION 
SELECT 'CI_SS_OPT' AS TBL_NAME, 'Start Option' AS TBL_DESCR, 'CI_SS_OPT_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'SA START OPT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, START_OPT_CD AS KEY, DESCR90 AS DESCR  FROM CISADM.CI_SS_OPT_L  UNION 
SELECT 'CI_STM_CYC' AS TBL_NAME, 'Statement Cycle' AS TBL_DESCR, 'CI_STM_CYC_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'STM CYCLE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, STM_CYC_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_STM_CYC_L  UNION 
SELECT 'CI_STM_RTE_TY' AS TBL_NAME, 'Statement Route Type' AS TBL_DESCR, 'CI_STM_RTE_TY_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'STM RTE TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, STM_RTE_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_STM_RTE_TY_L  UNION 

SELECT 'F1_STATS' AS TBL_NAME, 'Statistics Control' AS TBL_DESCR, 'F1_STATS_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-STATS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, F1_STATISTIC_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_STATS_L  UNION 
SELECT 'F1_BUS_OBJ_STATUS_RSN' AS TBL_NAME, 'Status Reason' AS TBL_DESCR, 'F1_BUS_OBJ_STATUS_RSN_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-STSREASON' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, BO_STATUS_REASON_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_BUS_OBJ_STATUS_RSN_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_TMAP_RELTY' AS TBL_NAME, 'TOU Map Relationship Type' AS TBL_DESCR, 'CI_TMAP_RELTY_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TOU MAP REL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TMAP_REL_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TMAP_RELTY_L  UNION 
SELECT 'CI_MD_TBL' AS TBL_NAME, 'Table' AS TBL_DESCR, 'CI_MD_TBL_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'TABLE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TBL_NAME AS KEY, DESCR AS DESCR  FROM CISADM.CI_MD_TBL_L WHERE OWNER_FLG = 'CM' UNION 

SELECT 'CI_TAX_EX_TYPE' AS TBL_NAME, 'Tax Exemption Type' AS TBL_DESCR, 'CI_TAX_EX_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TAX EX TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TAX_EX_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TAX_EX_TYPE_L  UNION 
SELECT 'W1_TAX_RATE_SCHED' AS TBL_NAME, 'Tax Rate Schedule' AS TBL_DESCR, 'W1_TAX_RATE_SCHED_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-TAXRATSCH' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TAX_RATE_SCHED_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_TAX_RATE_SCHED_L  UNION 
SELECT 'CI_MD_TMPL' AS TBL_NAME, 'Template' AS TBL_DESCR, 'CI_MD_TMPL_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'TEMPLATE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TMPL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_MD_TMPL_L  UNION 
SELECT 'CI_TNDR_SRCE' AS TBL_NAME, 'Tender Source' AS TBL_DESCR, 'CI_TNDR_SRCE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TENDER SRC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TNDR_SOURCE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TNDR_SRCE_L  UNION 
SELECT 'CI_TENDER_TYPE' AS TBL_NAME, 'Tender Type' AS TBL_DESCR, 'CI_TENDER_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TENDER TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TENDER_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TENDER_TYPE_L  UNION 
SELECT 'CI_TC' AS TBL_NAME, 'Terms and Conditions' AS TBL_DESCR, 'CI_TC_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TERM COND' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TC_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TC_L  UNION 
SELECT 'CI_TOS_CAN_RSN' AS TBL_NAME, 'Terms of Service Cancel Reason' AS TBL_DESCR, 'CI_TOS_CAN_RSN_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TOS CAN RSN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TOS_CAN_RSN_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TOS_CAN_RSN_L  UNION 
SELECT 'CI_TOS_TYPE' AS TBL_NAME, 'Terms of Service Type' AS TBL_DESCR, 'CI_TOS_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TOS TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TOS_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TOS_TYPE_L  UNION 
SELECT 'CI_THRD_PTY' AS TBL_NAME, 'Third Party' AS TBL_DESCR, 'CI_THRD_PTY_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'THIRD PRTY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, THRD_PTY_PAYOR_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_THRD_PTY_L  UNION 
SELECT 'CI_TOU' AS TBL_NAME, 'Time Of Use - CCB' AS TBL_DESCR, 'CI_TOU_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TOU' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TOU_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TOU_L  UNION 
SELECT 'D1_TOU' AS TBL_NAME, 'Time Of Use - MDM' AS TBL_DESCR, 'D1_TOU_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-TOU' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_TOU_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_TOU_L  UNION 
SELECT 'CI_TOU_GRP' AS TBL_NAME, 'Time Of Use Group - CCB' AS TBL_DESCR, 'CI_TOU_GRP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TOU GROUP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TOU_GRP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TOU_GRP_L  UNION 
SELECT 'D1_TOU_GRP' AS TBL_NAME, 'Time Of Use Group - MDM' AS TBL_DESCR, 'D1_TOU_GRP_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-TOUGROUP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_TOU_GRP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_TOU_GRP_L  UNION 
SELECT 'C1_TOU_MAP' AS TBL_NAME, 'Time Of Use Map - CCB' AS TBL_DESCR, 'C1_TOU_MAP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-TOUMAP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, C1_TOU_MAP_ID AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_TOU_MAP_L  UNION 
SELECT 'D1_TOU_MAP' AS TBL_NAME, 'Time Of Use Map - MDM' AS TBL_DESCR, 'D1_TOU_MAP_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-TOUMAP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_TOU_MAP_ID AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_TOU_MAP_L  UNION 


SELECT 'C1_TOU_MAP_TMPLT' AS TBL_NAME, 'Time Of Use Map Template - CCB' AS TBL_DESCR, 'C1_TOU_MAP_TMPLT_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-TOUMAPTM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, C1_TOU_MAP_TMPLT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_TOU_MAP_TMPLT_L  UNION 
SELECT 'D1_TOU_MAP_TMPLT' AS TBL_NAME, 'Time Of Use Map Template - MDM' AS TBL_DESCR, 'D1_TOU_MAP_TMPLT_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-TOUMAPTM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TOU_MAP_TMPLT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_TOU_MAP_TMPLT_L  UNION 
SELECT 'CI_TMAP_TMPL' AS TBL_NAME, 'Time Of Use Map Template Classic' AS TBL_DESCR, 'CI_TMAP_TMPL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TOU MAP TMPL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TMAP_TMPL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TMAP_TMPL_L  UNION 
SELECT 'C1_TOU_MAP_TYPE' AS TBL_NAME, 'Time Of Use Map Type - CCB' AS TBL_DESCR, 'C1_TOU_MAP_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'C1-TOUMAPTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, C1_TOU_MAP_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.C1_TOU_MAP_TYPE_L  UNION 
SELECT 'D1_TOU_MAP_TYPE' AS TBL_NAME, 'Time Of Use Map Type - MDM' AS TBL_DESCR, 'D1_TOU_MAP_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-TOUMAPTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_TOU_MAP_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_TOU_MAP_TYPE_L  UNION 
SELECT 'CI_TMAP_TYPE' AS TBL_NAME, 'Time Of Use Map Type Classic' AS TBL_DESCR, 'CI_TMAP_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TOU MAP TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TOU_MAP_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TMAP_TYPE_L  UNION 
SELECT 'W1_TIME_PERIOD' AS TBL_NAME, 'Time Period' AS TBL_DESCR, 'W1_TIME_PERIOD_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-TIMEPRD' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TIME_PERIOD_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_TIME_PERIOD_L  UNION 
SELECT 'CI_TIME_ZONE' AS TBL_NAME, 'Time Zone' AS TBL_DESCR, 'CI_TIME_ZONE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'TIME ZONE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TIME_ZONE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TIME_ZONE_L  UNION 
SELECT 'W1_TIMEKEEPER' AS TBL_NAME, 'Timekeeper' AS TBL_DESCR, 'W1_TIMEKEEPER_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-TIMEKPR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TIMEKEEPER_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_TIMEKEEPER_L  UNION 
SELECT 'CI_TD_TYPE' AS TBL_NAME, 'To Do Type' AS TBL_DESCR, 'CI_TD_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'TO DO TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TD_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TD_TYPE_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'F1_TREE' AS TBL_NAME, 'Tree' AS TBL_DESCR, 'F1_TREE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-TREE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TREE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_TREE_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_TREND_AREA' AS TBL_NAME, 'Trend Area' AS TBL_DESCR, 'CI_TREND_AREA_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TREND AREA' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TREND_AREA_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TREND_AREA_L  UNION 
SELECT 'CI_TREND_CL' AS TBL_NAME, 'Trend Class' AS TBL_DESCR, 'CI_TREND_CL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'TREND CL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, TREND_CL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_TREND_CL_L  UNION 
SELECT 'CI_UA_TYPE' AS TBL_NAME, 'UA Type' AS TBL_DESCR, 'CI_UA_TYPE_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'UA TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, UA_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_UA_TYPE_L  UNION 
SELECT 'F1_MAP' AS TBL_NAME, 'UI Map' AS TBL_DESCR, 'F1_MAP_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-UI MAP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, MAP_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_MAP_L WHERE OWNER_FLG = 'CM' UNION 

SELECT 'CI_UOM' AS TBL_NAME, 'Unit Of Measure - CCB' AS TBL_DESCR, 'CI_UOM_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'UOM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, UOM_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_UOM_L  UNION 
SELECT 'D1_UOM' AS TBL_NAME, 'Unit Of Measure - MDM' AS TBL_DESCR, 'D1_UOM_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-UOM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_UOM_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_UOM_L  UNION 

SELECT 'D1_USG_CAL_TYPE' AS TBL_NAME, 'Usage Calculation Type' AS TBL_DESCR, 'D1_USG_CAL_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-USGCALTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_USG_CAL_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_USG_CAL_TYPE_L  UNION 
SELECT 'D1_USG_GRP' AS TBL_NAME, 'Usage Group' AS TBL_DESCR, 'D1_USG_GRP_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-USGGRP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, USG_GRP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_USG_GRP_L  UNION 
SELECT 'D1_USG_RULE' AS TBL_NAME, 'Usage Rule' AS TBL_DESCR, 'D1_USG_RULE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-USGRULE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, USG_RULE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_USG_RULE_L  UNION 
SELECT 'D1_USG_RULE_ELIG_CRIT' AS TBL_NAME, 'Usage Rule Eligibility Criteria' AS TBL_DESCR, 'D1_USG_RULE_ELIG_CRIT_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-USGRLELIG' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, USG_RULE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_USG_RULE_ELIG_CRIT_L  UNION 
SELECT 'D1_US_QTY_TYPE' AS TBL_NAME, 'Usage Subscription Quantity Type' AS TBL_DESCR, 'D1_US_QTY_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-USQTYTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, D1_US_QTY_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_US_QTY_TYPE_L  UNION 
SELECT 'D1_US_TYPE' AS TBL_NAME, 'Usage Subscription Type' AS TBL_DESCR, 'D1_US_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-USTYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, US_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_US_TYPE_L  UNION 
SELECT 'D1_USAGE_EXCP_TYPE' AS TBL_NAME, 'Usage Transaction Exception Type' AS TBL_DESCR, 'D1_USAGE_EXCP_TYPE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-UTEXCPTY' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, USAGE_EXCP_TYPE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_USAGE_EXCP_TYPE_L  UNION 




SELECT 'SC_USER_GROUP' AS TBL_NAME, 'User Group' AS TBL_DESCR, 'SC_USER_GROUP_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-USRGRP-SC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, USR_GRP_ID AS KEY, DESCR AS DESCR  FROM CISADM.SC_USER_GROUP_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'SC_USER_GROUP' AS TBL_NAME, 'User Group' AS TBL_DESCR, 'SC_USER_GROUP_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'USER GROUP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, USR_GRP_ID AS KEY, DESCR AS DESCR  FROM CISADM.SC_USER_GROUP_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'D1_VEE_ELIG_CRIT' AS TBL_NAME, 'VEE Eligibility Criteria' AS TBL_DESCR, 'D1_VEE_ELIG_CRIT_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-VEEELIGCR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, VEE_RULE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_VEE_ELIG_CRIT_L  UNION 
SELECT 'D1_VEE_GRP' AS TBL_NAME, 'VEE Group' AS TBL_DESCR, 'D1_VEE_GRP_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-VEEGROUP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, VEE_GRP_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_VEE_GRP_L  UNION 
SELECT 'D1_VEE_RULE' AS TBL_NAME, 'VEE Rule' AS TBL_DESCR, 'D1_VEE_RULE_L' AS LANG_TBL_NAME, 'D1' AS OWNER_FLG, 'D1-VEERULE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, VEE_RULE_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.D1_VEE_RULE_L  UNION 

SELECT 'CI_WF_EVT_TYPE' AS TBL_NAME, 'WF Event Type' AS TBL_DESCR, 'CI_WF_EVT_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'WF EVT TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WF_EVT_TYPE_CD AS KEY, DESCR50 AS DESCR  FROM CISADM.CI_WF_EVT_TYPE_L  UNION 

SELECT 'CI_WF_PP' AS TBL_NAME, 'WF Process Profile' AS TBL_DESCR, 'CI_WF_PP_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'WF PROFILE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WF_PP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_WF_PP_L  UNION 
SELECT 'CI_WF_PROC_TMPL' AS TBL_NAME, 'WF Process Template' AS TBL_DESCR, 'CI_WF_PROC_TMPL_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'WF PROC TMPL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WF_PROC_TMPL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_WF_PROC_TMPL_L  UNION 
SELECT 'W1_WARRANTY_TERM' AS TBL_NAME, 'Warranty Term' AS TBL_DESCR, 'W1_WARRANTY_TERM_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-WRNTYTERM' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WARRANTY_TERM_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_WARRANTY_TERM_L  UNION 
SELECT 'F1_WEB_SVC' AS TBL_NAME, 'Web Service Adapter' AS TBL_DESCR, 'F1_WEB_SVC_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-WEBSVC' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WEB_SVC_NAME AS KEY, DESCR AS DESCR  FROM CISADM.F1_WEB_SVC_L  UNION 
SELECT 'F1_IWS_ANN' AS TBL_NAME, 'Web Service Annotation' AS TBL_DESCR, 'F1_IWS_ANN_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-IWSANN' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ANN_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_IWS_ANN_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'F1_IWS_ANN_TYPE' AS TBL_NAME, 'Web Service Annotation Type' AS TBL_DESCR, 'F1_IWS_ANN_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-IWSANNTYP' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ANN_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.F1_IWS_ANN_TYPE_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'F1_WEB_CAT' AS TBL_NAME, 'Web Service Category' AS TBL_DESCR, 'F1_WEB_CAT_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'F1-WEBSVCCAT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WEB_SVC_CAT_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.F1_WEB_CAT_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'W1_WORK_CAL' AS TBL_NAME, 'Work Calendar' AS TBL_DESCR, 'W1_WORK_CAL_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-WORKCAL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WORK_CALENDAR_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_WORK_CAL_L  UNION 
SELECT 'CI_CAL_WORK' AS TBL_NAME, 'Work Calendar' AS TBL_DESCR, 'CI_CAL_WORK_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'WORK CAL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, CALENDAR_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_CAL_WORK_L  UNION 
SELECT 'W1_WORK_CATEGORY' AS TBL_NAME, 'Work Category' AS TBL_DESCR, 'W1_WORK_CATEGORY_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-WORKCAT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WORK_CATEGORY_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_WORK_CATEGORY_L  UNION 
SELECT 'W1_WORK_CLASS' AS TBL_NAME, 'Work Class' AS TBL_DESCR, 'W1_WORK_CLASS_L' AS LANG_TBL_NAME, 'W1' AS OWNER_FLG, 'W1-WORKCLASS' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WORK_CLASS_CD AS KEY, DESCR100 AS DESCR  FROM CISADM.W1_WORK_CLASS_L  UNION 
SELECT 'CI_MD_WRK_TBL' AS TBL_NAME, 'Work Table' AS TBL_DESCR, 'CI_MD_WRK_TBL_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'MD WORK TBL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WRK_TBL_NAME AS KEY, DESCR AS DESCR  FROM CISADM.CI_MD_WRK_TBL_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_WO_CNTL' AS TBL_NAME, 'Write Off Control' AS TBL_DESCR, 'CI_WO_CNTL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'WO CNTL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WO_CNTL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_WO_CNTL_L  UNION 
SELECT 'CI_WO_DEBT_CL' AS TBL_NAME, 'Write Off Debt Class' AS TBL_DESCR, 'CI_WO_DEBT_CL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'WO DEBT CL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WO_DEBT_CL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_WO_DEBT_CL_L  UNION 
SELECT 'CI_WO_EVT_TYP' AS TBL_NAME, 'Write Off Event Type' AS TBL_DESCR, 'CI_WO_EVT_TYP_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'WO EVT TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WO_EVT_TYP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_WO_EVT_TYP_L  UNION 
SELECT 'CI_WO_PROC_TMPL' AS TBL_NAME, 'Write Off Process Template' AS TBL_DESCR, 'CI_WO_PROC_TMPL_L' AS LANG_TBL_NAME, 'C1' AS OWNER_FLG, 'WO PROC TMPL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, WO_PROC_TMPL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_WO_PROC_TMPL_L  UNION 
SELECT 'CI_XAI_ADAPTER' AS TBL_NAME, 'XAI Adapter' AS TBL_DESCR, 'CI_XAI_ADAPTER_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'XAI ADAPTER' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_ADAPTER_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_ADAPTER_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_XAI_ENV_HNDL' AS TBL_NAME, 'XAI Envelope Handler' AS TBL_DESCR, 'CI_XAI_ENV_HNDL_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'ENV HNDLR' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_ENV_HNDL_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_ENV_HNDL_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_XAI_EXECUTER' AS TBL_NAME, 'XAI Executer' AS TBL_DESCR, 'CI_XAI_EXECUTER_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'XAI EXECUTER' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_EXECUTER_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_EXECUTER_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_XAI_FORMAT' AS TBL_NAME, 'XAI Format' AS TBL_DESCR, 'CI_XAI_FORMAT_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'XAI FORMAT' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_FORMAT_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_FORMAT_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_XAI_IN_SVC' AS TBL_NAME, 'XAI Inbound Service' AS TBL_DESCR, 'CI_XAI_IN_SVC_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'XAI SERVICE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_IN_SVC_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_IN_SVC_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_XAI_JDBC_CON' AS TBL_NAME, 'XAI JDBC Connection' AS TBL_DESCR, 'CI_XAI_JDBC_CON_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'XAI JDBC CON' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_JDBC_CON_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_JDBC_CON_L  UNION 
SELECT 'CI_XAI_RCVR' AS TBL_NAME, 'XAI Receiver' AS TBL_DESCR, 'CI_XAI_RCVR_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'XAI RECEIVER' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_RCVR_ID AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_RCVR_L  UNION 
SELECT 'CI_XAI_RT_TYPE' AS TBL_NAME, 'XAI Route Type' AS TBL_DESCR, 'CI_XAI_RT_TYPE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'XAI RT TYPE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_RT_TYPE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_RT_TYPE_L  UNION 
SELECT 'CI_XAI_RGRP' AS TBL_NAME, 'XAI Rule Group' AS TBL_DESCR, 'CI_XAI_RGRP_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'XAI RULE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, XAI_RGRP_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_XAI_RGRP_L  UNION 
SELECT 'CI_ZONE' AS TBL_NAME, 'Zone' AS TBL_DESCR, 'CI_ZONE_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'CONTENT ZONE' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ZONE_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_ZONE_L WHERE OWNER_FLG = 'CM' UNION 
SELECT 'CI_ZONE_HDL' AS TBL_NAME, 'Zone Type' AS TBL_DESCR, 'CI_ZONE_HDL_L' AS LANG_TBL_NAME, 'F1' AS OWNER_FLG, 'ZONE HDL' AS MAINT_OBJ_CD, 'Internal' AS ENVIRONMENT, ZONE_HDL_CD AS KEY, DESCR AS DESCR  FROM CISADM.CI_ZONE_HDL_L WHERE OWNER_FLG = 'CM';

-- ----- CMS_C1_PA_RQST_BODA_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_C1_PA_RQST_BODA_VW" ("PA_RQST_ID", "SA_ID", "PA_RQST_DOWN_PAY_PAYMENT", "PA_REMAINING_AMOUNT", "PA_RQST_NBR_INSTALLMENT", "PA_RQST_INSTALLMENT_AMT", "PA_PAYMENT_TERMS", "PA_RQST_CUR_BAL", "PA_RQST_SA_AMT", "PA_RQST_SA_AMT_RECALC") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
          PA.PA_RQST_ID
        , RELOBJ.PK_VALUE1                                                                                                                           AS SA_ID
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', PA.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/paymentAmount'))                          AS PA_RQST_DOWN_PAY_PAYMENT
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', PA.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/recalculated/remainingAmount'))           AS PA_REMAINING_AMOUNT
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', PA.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/recalculated/numberOfInstallments'))      AS PA_RQST_NBR_INSTALLMENT
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', PA.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/recalculated/installmentAmount'))         AS PA_RQST_INSTALLMENT_AMT
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', PA.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/recalculated/termsSummary') AS VARCHAR2(4000)) AS PA_PAYMENT_TERMS
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', RELOBJ.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/currentBalance'))                     AS PA_RQST_CUR_BAL
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', RELOBJ.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/amount'))                             AS PA_RQST_SA_AMT
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', RELOBJ.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/recalculated/amount'))                AS PA_RQST_SA_AMT_RECALC
FROM
          CISADM.C1_PA_RQST PA
        , CISADM.C1_PA_RQST_REL_OBJ RELOBJ
WHERE
          PA.PA_RQST_ID                       = RELOBJ.PA_RQST_ID (+)
          AND RELOBJ.PA_RQST_REL_OBJ_TYPE_FLG(+) = 'C1SA'
          AND RELOBJ.MAINT_OBJ_CD(+)             = 'SA';

-- ----- CMS_C1_REPRESENTATIVE_BODA_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_C1_REPRESENTATIVE_BODA_VW" ("C1_REPRESENTATIVE_CD", "CM_ML_SVC_AREA", "CM_ML_WORKER_CAPABILITY") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
          REP.C1_REPRESENTATIVE_CD
        , CAST(SVC_AREA.CM_ML_SVC_AREA AS VARCHAR2(30))                 AS CM_ML_SVC_AREA
        , CAST(WORK_CAPABILITY.CM_ML_WORKER_CAPABILITY AS VARCHAR2(16)) AS CM_ML_WORKER_CAPABILITY
FROM
          CISADM.C1_REPRESENTATIVE REP
          LEFT JOIN
                    XMLTABLE( '/root/cmMobileLiteDetails/serviceAreas/serviceAreaList' PASSING XMLTYPE(CONCAT(CONCAT('<root>', REP.BO_DATA_AREA), '</root>')) COLUMNS CM_ML_SVC_AREA VARCHAR2(50) PATH 'serviceArea' ) SVC_AREA
                    ON
                              1=1
          LEFT JOIN
                    XMLTABLE( '/root/cmMobileLiteDetails/workerCapability/capabilities' PASSING XMLTYPE(CONCAT(CONCAT('<root>', REP.BO_DATA_AREA), '</root>')) COLUMNS CM_ML_WORKER_CAPABILITY VARCHAR2(50) PATH 'capability' ) WORK_CAPABILITY
                    ON
                              1=1;

-- ----- CMS_CI_APPR_REQ_BODA_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_CI_APPR_REQ_BODA_VW" ("APPR_REQ_ID", "ADJ_ID", "ACCOUNTING_DT", "TD_ENTRY_ID", "C1_AREQ_REJECT_RSN_FLG") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       APREQ.APPR_REQ_ID
    , CAST(COALESCE(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', APREQ.BO_DATA_AREA), '</root>')),'root/adjustmentId'), RPAD(' ', 12)) AS CHAR(12))                       AS ADJ_ID
    , TO_DATE(NULLIF(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', APREQ.BO_DATA_AREA), '</root>')),'root/approvalInfo/accountingDate'), ''), 'YYYY-MM-DD')             AS ACCOUNTING_DT
    , CAST(COALESCE(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', APREQ.BO_DATA_AREA), '</root>')),'root/approvalInfo/currentApprovalToDoId'), RPAD(' ', 14)) AS CHAR(14)) AS TD_ENTRY_ID
    , CAST(COALESCE(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', APREQ.BO_DATA_AREA), '</root>')),'root/rejectInfo/rejectReason'), RPAD(' ', 4)) AS CHAR(4))             AS C1_AREQ_REJECT_RSN_FLG
FROM
       CISADM.CI_APPR_REQ APREQ;

-- ----- CMS_CI_CASE_LOG_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_CI_CASE_LOG_VW" ("CASE_ID", "SEQ_NUM", "CASE_LOG_TYPE_FLG", "CASE_TYPE_CD", "CASE_STATUS_CD", "ACCT_ID", "PER_ID", "PREM_ID", "USER_ID", "LOG_DTTM", "PREV_LOG_DTTM", "PREV_CASE_STATUS_CD", "PREV_STATE_DUR", "CURR_STATE_DUR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  select
               clog.case_id
             , clog.seq_num
             , clog.case_log_type_flg
             , ca.case_type_cd
             , clog.case_status_cd
             , ca.acct_id
             , ca.per_id
             , ca.prem_id
             , ca.user_id
             , clog.log_dttm
             , LAG(clog.log_dttm) OVER (PARTITION BY clog.case_id ORDER BY
                                        clog.log_dttm,clog.seq_num) AS prev_log_dttm
             , LAG(clog.case_status_cd) OVER (PARTITION BY clog.case_id ORDER BY
                                              clog.log_dttm,clog.seq_num) AS prev_case_status
             , decode(clog.case_log_type_flg, 'CASC',0, round((log_dttm - LAG(clog.log_dttm) OVER (PARTITION BY clog.case_id ORDER BY
                                                                                                   clog.log_dttm,clog.seq_num))*24*60 , 2)) as prev_state_dur
             , CASE
                            when st.status_cond_flg <> 'FINL'
                                         and LEAD(clog.log_dttm) OVER( PARTITION BY clog.case_id ORDER BY
                                                                      clog.log_dttm,clog.seq_num) is null
                                         then round((current_date - clog.log_dttm)*24*60,2)
                            when st.status_cond_flg <> 'FINL'
                                       AND NOT(LEAD(CLOG.LOG_DTTM) OVER(PARTITION BY CLOG.CASE_ID ORDER BY
                                                                        CLOG.LOG_DTTM,CLOG.SEQ_NUM) IS NULL)
                                         then round((LEAD(clog.log_dttm) OVER (PARTITION BY clog.case_id ORDER BY
                                                                               clog.log_dttm,clog.seq_num) - clog.log_dttm)*24*60,2)
                                         else 0
               END as curr_state_dur
  from
               ci_case_log    clog
             , ci_case        ca
             , ci_case_status st
  WHERE
               clog.case_log_type_flg IN ( 'CASC'
                                        , 'STAT' )
               AND ca.case_id        = clog.case_id
               AND st.case_type_cd   = ca.case_type_cd
               AND st.case_status_cd = clog.case_status_cd
  ORDER BY
               clog.case_id
             , clog.seq_num;

-- ----- CMS_CI_CASE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_CI_CASE_VW" ("CASE_ID", "CASE_TYPE_CD", "CASE_STATUS_CD", "ACCT_ID", "PER_ID", "PREM_ID", "USER_ID", "CASE_CRE_DTTM", "CASE_COND_FLG", "CLOSED_DTTM", "ILM_DT", "ILM_ARCH_SW", "CASE_DUR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  select
           CA.CASE_ID
         , CA.CASE_TYPE_CD
         , CA.CASE_STATUS_CD
         , ACCT_ID
         , PER_ID
         , PREM_ID
         , CA.USER_ID
         , CRE_DTTM AS CASE_CRE_DTTM
         , CASE_COND_FLG
         , CLOSED_DTTM
         , CA.ILM_DT
         , CA.ILM_ARCH_SW
         , CASE
                      when CLOSED_DTTM is null
                                 then round((current_date - cre_dttm)*24*60,2)
                                 else round((closed_dttm  - cre_dttm)*24*60,2)
           END as CASE_DUR
from
           CI_CASE CA
           inner join
                      (
                                 select
                                            C1.CASE_ID
                                          , max(CL.LOG_DTTM) CRE_DTTM
                                          , max(CR.LOG_DTTM) CLOSED_DTTM
                                 from
                                            CI_CASE C1
                                            inner join
                                                       CI_CASE_LOG CL
                                                       on
                                                                  CL.CASE_ID               = C1.CASE_ID
                                                                  and CL.CASE_LOG_TYPE_FLG = 'CASC'
                                            left join
                                                       CI_CASE_LOG CR
                                                       on
                                                                  C1.CASE_COND_FLG         = 'CLSD'
                                                                  and CR.CASE_ID           = C1.CASE_ID
                                                                  and CR.CASE_LOG_TYPE_FLG = 'STAT'
                                 group by
                                            C1.CASE_ID
                      )
                      C2
                      on
                                 C2.CASE_ID = CA.CASE_ID
order by
           CA.CASE_ID;

-- ----- CMS_CI_TD_ENTRY_CHAR_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_CI_TD_ENTRY_CHAR_VW" ("TD_ENTRY_ID", "SA_ID", "ACCT_ID", "PER_ID", "PREM_ID", "D1_SP_ID", "D1_DEVICE_ID", "MEASR_COMP_ID", "CONTACT_ID", "US_ID", "ASSET_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT   td_entry_id ,
         MIN(sa_id) sa_id ,
         MIN(acct_id) acct_id ,
         MIN(per_id) per_id ,
         MIN(prem_id) prem_id ,
         MIN(d1_sp_id) d1_sp_id ,
         MIN(d1_device_id) d1_device_id ,
         MIN(measr_comp_id) measr_comp_id ,
         MIN(contact_id) contact_id ,
         MIN(us_id) us_id ,
         MIN(asset_id) asset_id
FROM     ( SELECT  td.td_entry_id ,
                  DECODE(TRIM(fkr.tbl_name) ,
                                  'CI_SA', tdc.srch_char_val ,
                                  NULL) AS sa_id ,
                  DECODE(TRIM(fkr.tbl_name) ,
                                  'CI_ACCT', tdc.srch_char_val ,
                                  NULL) AS acct_id ,
                  DECODE(TRIM(fkr.tbl_name) ,
                                  'CI_PER', tdc.srch_char_val ,
                                  NULL) AS per_id ,
                  DECODE(TRIM(fkr.tbl_name) ,
                                  'CI_PREM', tdc.srch_char_val ,
                                  NULL) AS prem_id ,
                  DECODE(TRIM(fkr.tbl_name) ,
                                  'D1_SP', tdc.srch_char_val ,
                                  NULL) AS d1_sp_id ,
                  DECODE(TRIM(fkr.tbl_name) ,
                                  'D1_DVC', tdc.srch_char_val ,
                                  NULL) AS d1_device_id ,
                  DECODE(TRIM(fkr.tbl_name) ,
                                  'D1_MEASR_COMP', tdc.srch_char_val ,
                                  NULL) AS measr_comp_id ,
                  DECODE(TRIM(fkr.tbl_name) ,
                                  'D1_CONTACT', tdc.srch_char_val ,
                                  NULL) AS contact_id ,
                  DECODE(TRIM(fkr.tbl_name) ,
                                  'D1_US', tdc.srch_char_val ,
                                  NULL) AS us_id ,
                  DECODE(TRIM(fkr.tbl_name) ,
                                  'W1_ASSET', tdc.srch_char_val ,
                                  NULL) AS asset_id
         FROM     CISADM.ci_td_entry td ,
                  CISADM.ci_td_entry_cha tdc ,
                  CISADM.ci_char_type ct ,
                  CISADM.ci_fk_ref fkr
         WHERE    tdc.td_entry_id = td.td_entry_id
                  AND ct.char_type_cd = tdc.char_type_cd
                  AND ct.char_type_flg = 'FKV'
                  AND fkr.fk_ref_cd = ct.fk_ref_cd
                  AND TRIM(fkr.tbl_name) IN ( 'CI_SA' ,
                                             'CI_ACCT' ,
                                             'CI_PER' ,
                                             'CI_PREM' ,
                                             'D1_SP' ,
                                             'D1_DVC' ,
                                             'D1_MEASR_COMP' ,
                                             'D1_CONTACT' ,
                                             'D1_US' ,
                                             'W1_ASSET' ) )
GROUP BY td_entry_id;

-- ----- CMS_D1_ACTIVITY_CHAR_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_D1_ACTIVITY_CHAR_VW" ("D1_ACTIVITY_ID", "FA_INT_STATUS_FLG", "FA_PRIORITY_FLG", "THRD_PTY_REP_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT   D1_ACTIVITY_ID,
         MIN(FA_INT_STATUS_FLG) AS FA_INT_STATUS_FLG,
         MIN(FA_PRIORITY_FLG) AS FA_PRIORITY_FLG,
         MIN(THRD_PTY_REP_CD) AS THRD_PTY_REP_CD
FROM    ( SELECT  AC.D1_ACTIVITY_ID,
                  DECODE(trim(AC.CHAR_TYPE_CD),
                                  'CMFAINST', ac.srch_char_val,
                                  NULL) AS FA_INT_STATUS_FLG,
                  DECODE(trim(AC.CHAR_TYPE_CD),
                                  'CMFAPRIO', ac.srch_char_val,
                                  NULL) AS FA_PRIORITY_FLG,
                  DECODE(trim(AC.CHAR_TYPE_CD),
                                  'CMFAREP', ac.srch_char_val,
                                  NULL) || '  ' AS THRD_PTY_REP_CD
         FROM     CISADM.D1_ACTIVITY_CHAR AC )
GROUP BY D1_ACTIVITY_ID;

-- ----- CMS_D1_ACTIVITY_D1FA_BODA_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_D1_ACTIVITY_D1FA_BODA_VW" ("D1_ACTIVITY_ID", "COMMENTS", "D1_INSTRUCTIONS", "APPOINTMENT_FLG", "APPOINTMENT_WINDOW_START_DTTM", "APPOINTMENT_WINDOW_END_DTTM", "APPOINTMENT_TAKEN_BY", "APPOINTMENT_TAKEN_DATE", "APPOINTMENT_COMMENTS", "EXPIRATION_DTTM", "CR_REQUESTER_USER", "EXT_REFERENCE_ID", "D1_CONT_EXTERNAL_ID", "D1_CUSTOMERNAME", "D1_CONTACTNAME", "D1_MAINPHONE", "D1_CELLPHONE", "EMAIL_VALUE", "EXTERNAL_ACCT_ID", "CM_ML_IS_PICKUP_FLG") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
       ACT.D1_ACTIVITY_ID
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/comments') AS VARCHAR2(254))                        AS COMMENTS
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/instructions') AS VARCHAR2(4000))                   AS D1_INSTRUCTIONS
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/isAppointmentNecessary') AS VARCHAR2(1))            AS D1_APPOINTMENT_FLG
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/appointmentWindow/startDateTime') AS VARCHAR2(26))  AS APPOINTMENT_WINDOW_START_DTTM
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/appointmentWindow/endDateTime') AS VARCHAR2(26))    AS APPOINTMENT_WINDOW_END_DTTM
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/appointmentInformation/takenBy') AS VARCHAR2(32))   AS D1_TAKEN_BY
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/appointmentInformation/takenDate') AS VARCHAR2(32)) AS D1_TAKEN_DATE
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/appointmentInformation/comments') AS VARCHAR2(254)) AS D1_COMMENT
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/expirationDateTime') AS VARCHAR2(26))               AS EXPIRATION_DTTM
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/requesterUserId') AS VARCHAR2(8))                   AS CR_REQUESTER_USER
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/externalReferenceId') AS VARCHAR2(36))              AS EXT_REFERENCE_ID
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/contactDetails/personId') AS VARCHAR2(60))          AS D1_CONT_EXTERNAL_ID
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/contactDetails/customerName') AS VARCHAR2(50))      AS D1_CUSTOMERNAME
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/contactDetails/contactName') AS VARCHAR2(50))       AS D1_CONTACTNAME
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/contactDetails/mainPhone') AS VARCHAR2(24))         AS D1_MAINPHONE
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/contactDetails/cellPhone') AS VARCHAR2(24))         AS D1_CELLPHONE
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/contactDetails/email') AS VARCHAR2(254))            AS EMAIL_VALUE
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/contactDetails/accountId') AS VARCHAR2(30))         AS EXTERNAL_ACCT_ID
     , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', ACT.BO_DATA_AREA), '</root>')),'root/cmMobileLiteDetails/isPickupOrder') AS VARCHAR2(1)) AS CM_ML_IS_PICKUP_FLG
FROM
       CISADM.D1_ACTIVITY      ACT
     , CISADM.D1_ACTIVITY_TYPE ACTTY
WHERE
       ACTTY.ACTIVITY_TYPE_CD          = ACT.ACTIVITY_TYPE_CD
       AND ACTTY.ACTIVITY_TYPE_CAT_FLG = 'D1FA';

-- ----- CMS_D1_DVC_BODA_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_D1_DVC_BODA_VW" ("D1_DEVICE_ID", "BUS_OBJ_CD", "STATUS", "RETIREMENT_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
         DVC.D1_DEVICE_ID
       , MIN(DVC.BUS_OBJ_CD)
       , CAST(MIN(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', DVC.BO_DATA_AREA), '</root>')),'root/latestBoStatus')) AS CHAR(12))     AS STATUS
       , MIN(TO_DATE(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', DVC.BO_DATA_AREA), '</root>')),'root/retirementDateTime'), 'YYYY-MM-DD-HH24.MI.SS')) AS RETIREMENT_DTTM
FROM
         CISADM.D1_DVC DVC
WHERE
         DVC.BO_DATA_AREA IS NOT NULL
GROUP BY
         DVC.D1_DEVICE_ID;

-- ----- CMS_D1_DVC_CHAR_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_D1_DVC_CHAR_VW" ("D1_DEVICE_ID", "MXU_TYPE") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
         D1_DEVICE_ID
       , CAST(MIN(MXU_TYPE) AS CHAR(16))     AS MXU_TYPE
FROM
         (
                SELECT
                       D1_DEVICE_ID
                     , DECODE(trim(CHAR_TYPE_CD), 'CMCMXUTY', TRIM(SRCH_CHAR_VAL), NULL) AS MXU_TYPE
                FROM
                       CISADM.D1_DVC_CHAR
         )
WHERE
         MXU_TYPE IS NOT NULL
GROUP BY
         D1_DEVICE_ID;

-- ----- CMS_D1_DVC_IDENTIFIER_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_D1_DVC_IDENTIFIER_VW" ("D1_DEVICE_ID", "ASSET_ID", "BADGE_NUMBER", "CONFIGURATION", "EXTERNAL_ID", "INTERNAL_METER_NUMBER", "MDM_EXTERNAL_ID", "NIC_ID", "PALLET_NUMBER", "SERIAL_NUMBER", "SPECIFICATION", "NEURON_ID", "NAME", "NIC_SERIAL_NUMBER", "UTILITY_DEVICE_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
         D1_DEVICE_ID
       , CAST(MIN(ASSET_ID) AS VARCHAR2(60))                                                                                               AS ASSET_ID
       , CAST(MIN(BADGE_NUMBER) AS VARCHAR2(60))                                                                                           AS BADGE_NUMBER
       , CAST(MIN(CONFIGURATION) AS VARCHAR2(60))                                                                                          AS CONFIGURATION
       , CAST(MIN(EXTERNAL_ID) AS VARCHAR2(60))                                                                                            AS EXTERNAL_ID
       , CAST(MIN(INTERNAL_METER_NUMBER) AS VARCHAR2(60))                                                                                  AS INTERNAL_METER_NUMBER
       , CAST(MIN(MDM_EXTERNAL_ID) AS VARCHAR2(14))                                                                                        AS MDM_EXTERNAL_ID
       , CAST(MIN(NIC_ID) AS VARCHAR2(120))                                                                                                AS NIC_ID
       , CAST(MIN(PALLET_NUMBER) AS VARCHAR2(14))                                                                                          AS PALLET_NUMBER
       , CAST(MIN(SERIAL_NUMBER) AS VARCHAR2(60))                                                                                          AS SERIAL_NUMBER
       , CAST(MIN(SPECIFICATION) AS VARCHAR2(60))                                                                                          AS SPECIFICATION
       , CAST(MIN(NEURON_ID) AS VARCHAR2(60))                                                                                              AS NEURON_ID
       , CAST(MIN(NAME) AS VARCHAR2(60))                                                                                                   AS NAME
       , CAST(MIN(NIC_SERIAL_NUMBER) AS VARCHAR2(60))                                                                                      AS NIC_SERIAL_NUMBER
       , CAST(MIN(UTILITY_DEVICE_ID) AS VARCHAR2(60))                                                                                      AS UTILITY_DEVICE_ID
FROM
         (
                SELECT
                       D1_DEVICE_ID
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1AS', TRIM(ID_VALUE), NULL) AS ASSET_ID
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1BN', TRIM(ID_VALUE), NULL) AS BADGE_NUMBER
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1CO', TRIM(ID_VALUE), NULL) AS CONFIGURATION
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1EI', TRIM(ID_VALUE), NULL) AS EXTERNAL_ID
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1IN', TRIM(ID_VALUE), NULL) AS INTERNAL_METER_NUMBER
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1MI', TRIM(ID_VALUE), NULL) AS MDM_EXTERNAL_ID
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1NI', TRIM(ID_VALUE), NULL) AS NIC_ID
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1PN', TRIM(ID_VALUE), NULL) AS PALLET_NUMBER
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1SN', TRIM(ID_VALUE), NULL) AS SERIAL_NUMBER
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1SP', TRIM(ID_VALUE), NULL) AS SPECIFICATION
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D4NR', TRIM(ID_VALUE), NULL) AS NEURON_ID
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D7NA', TRIM(ID_VALUE), NULL) AS NAME
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D7NS', TRIM(ID_VALUE), NULL) AS NIC_SERIAL_NUMBER
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D7UD', TRIM(ID_VALUE), NULL) AS UTILITY_DEVICE_ID
                FROM
                       CISADM.D1_DVC_IDENTIFIER
         )
GROUP BY
         D1_DEVICE_ID;

-- ----- CMS_D1_SP_BODA_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_D1_SP_BODA_VW" ("D1_SP_ID", "PERIODIC_EST_ELIGIBILITY_FLG", "OK_TO_ETR_LBL", "SP_WARN_LBL", "SP_INSTR_LBL", "SP_INSTR_DTS_LBL", "KEY_LBL", "D1_KEY_ID_LBL", "DEVICE_LOC_LBL", "DEVICE_LOC_DTS_LBL") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
          SP.D1_SP_ID
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/periodicEstimationEligibility') AS VARCHAR2(4)) AS PERIODIC_EST_ELIGIBILITY_FLG
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/okToEnter') AS VARCHAR2(30))                    AS OK_TO_ETR_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/spWarning') AS VARCHAR2(30))                    AS SP_WARN_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/spInstruction') AS VARCHAR2(30))                AS SP_INSTR_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/spInstructionDetails') AS VARCHAR2(250))        AS SP_INSTR_DTS_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/key') AS VARCHAR2(30))                          AS KEY_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/keyId') AS VARCHAR2(30))                        AS D1_KEY_ID_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/deviceLocation') AS VARCHAR2(30))               AS DEVICE_LOC_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/deviceLocationDetails') AS VARCHAR2(250))       AS DEVICE_LOC_DTS_LBL
FROM
          CISADM.D1_SP SP;

-- ----- CMS_NON_INVOICED_USAGE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_NON_INVOICED_USAGE_VW" ("MEASR_COMP_ID", "DEVICE_CONFIG_ID", "D1_DEVICE_ID", "BADGE_NBR", "SERIAL_NBR", "MSRMT_DTTM", "READING_VAL") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT  MC.MEASR_COMP_ID    AS "MEASR_COMP_ID",
        DC.DEVICE_CONFIG_ID AS "DEVICE_CONFIG_ID",
        DC.D1_DEVICE_ID     AS "D1_DEVICE_ID",
        DVCBN.ID_VALUE      AS "BADGE_NBR",
        DVCSN.ID_VALUE      AS "SERIAL_NBR",
        M.MSRMT_DTTM        AS "MSRMT_DTTM",
        M.READING_VAL       AS "READING_VAL"
FROM    CISADM.D1_MSRMT M
        JOIN CISADM.D1_MEASR_COMP MC
          ON M.MEASR_COMP_ID = MC.MEASR_COMP_ID
        LEFT JOIN CISADM.D1_DVC_CFG DC
          ON MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
        JOIN CISADM.D1_DVC_IDENTIFIER DVCBN
          ON DC.D1_DEVICE_ID = DVCBN.D1_DEVICE_ID
          AND DVCBN.DVC_ID_TYPE_FLG = 'D1BN'
        JOIN CISADM.D1_DVC_IDENTIFIER DVCSN
          ON DC.D1_DEVICE_ID = DVCSN.D1_DEVICE_ID
          AND DVCSN.DVC_ID_TYPE_FLG = 'D1SN'
WHERE   M.MSRMT_USE_FLG <> 'D101'
        AND NOT EXISTS (SELECT 1 
              FROM (SELECT BADGE_NBR, SERIAL_NBR, 
                        START_READ_DTTM AS READ_DTTM,
                        START_READING AS READING_VAL
                    FROM CISADM.CMS_C1_USAGE_BODA_VW
                    WHERE READ_SEQ = 1
                    UNION ALL
                    SELECT BADGE_NBR, SERIAL_NBR,
                          END_READ_DTTM AS READ_DTTM,
                          END_READING AS READING_VAL
                    FROM CISADM.CMS_C1_USAGE_BODA_VW) X
              WHERE DVCBN.ID_VALUE = X.BADGE_NBR
                    AND DVCSN.ID_VALUE = X.SERIAL_NBR
                    AND X.READ_DTTM = M.MSRMT_DTTM
                    AND X.READING_VAL = M.READING_VAL
        );

-- ----- CMS_W1_ASSET_IDENTIFIER_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_W1_ASSET_IDENTIFIER_VW" ("ASSET_ID", "EXTERNAL_ID", "PALLET_NUMBER", "SERIAL_NUMBER", "BADGE_NUMBER", "PURCHASE_ORDER", "METROLOGY_FIRMWARE_VERSION", "NIC_FIRMWARE_VERSION") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
         ASSET_ID
       , CAST(MIN(EXTERNAL_ID) AS VARCHAR2(60))                AS EXTERNAL_ID
       , CAST(MIN(PALLET_NUMBER) AS VARCHAR2(60))              AS PALLET_NUMBER
       , CAST(MIN(SERIAL_NUMBER) AS VARCHAR2(14))              AS SERIAL_NUMBER
       , CAST(MIN(BADGE_NUMBER) AS VARCHAR2(120))              AS BADGE_NUMBER
       , CAST(MIN(PURCHASE_ORDER) AS VARCHAR2(14))             AS PURCHASE_ORDER
       , CAST(MIN(METROLOGY_FIRMWARE_VERSION) AS VARCHAR2(60)) AS METROLOGY_FIRMWARE_VERSION
       , CAST(MIN(NIC_FIRMWARE_VERSION) AS VARCHAR2(60))       AS NIC_FIRMWARE_VERSION
FROM
         (
                SELECT
                       AC.ASSET_ID
                     , DECODE(trim(AC.ASSET_ID_TYPE_FLG), 'W1EI', TRIM(AC.W1_ID_VALUE), NULL) AS EXTERNAL_ID
                     , DECODE(trim(AC.ASSET_ID_TYPE_FLG), 'W1PN', TRIM(AC.W1_ID_VALUE), NULL) AS PALLET_NUMBER
                     , DECODE(trim(AC.ASSET_ID_TYPE_FLG), 'W1SN', TRIM(AC.W1_ID_VALUE), NULL) AS SERIAL_NUMBER
                     , DECODE(trim(AC.ASSET_ID_TYPE_FLG), 'W1BN', TRIM(AC.W1_ID_VALUE), NULL) AS BADGE_NUMBER
                     , DECODE(trim(AC.ASSET_ID_TYPE_FLG), 'W2PO', TRIM(AC.W1_ID_VALUE), NULL) AS PURCHASE_ORDER
                     , DECODE(trim(AC.ASSET_ID_TYPE_FLG), 'W2MF', TRIM(AC.W1_ID_VALUE), NULL) AS METROLOGY_FIRMWARE_VERSION
                     , DECODE(trim(AC.ASSET_ID_TYPE_FLG), 'W2NF', TRIM(AC.W1_ID_VALUE), NULL) AS NIC_FIRMWARE_VERSION
                FROM
                       CISADM.W1_ASSET_IDENTIFIER AC
         )
GROUP BY
         ASSET_ID;

-- ----- D1_ACT_DVC_SP_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_ACT_DVC_SP_VW" ("D1_PK_VALUE", "D1_ACTIVITY_ID", "MAINT_OBJ_CD", "ACCESS_GRP_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT RO.PK_VALUE1 AS D1_PK_VALUE, RO.D1_ACTIVITY_ID, MAINT_OBJ_CD, ACCESS_GRP_CD
from D1_DVC_SP_VW VW JOIN D1_ACTIVITY_REL_OBJ RO ON VW.D1_DEVICE_ID = RO.PK_VALUE1
WHERE RO.MAINT_OBJ_CD = 'D1-DEVICE' AND RO.ACTIVITY_REL_OBJ_TYPE_FLG='D1RO'
UNION
SELECT RO.PK_VALUE1 AS D1_PK_VALUE, RO.D1_ACTIVITY_ID, MAINT_OBJ_CD, ACCESS_GRP_CD
from D1_DVC_SP_VW VW JOIN D1_ACTIVITY_REL_OBJ RO ON VW.D1_SP_ID = RO.PK_VALUE1
WHERE RO.MAINT_OBJ_CD = 'D1-SP';

-- ----- D1_BI_DYN_AGG_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_BI_DYN_AGG_VW" ("MEASR_COMP_SET_CD", "AGG_MEASR_COMP_ID", "AGG_ATTR1", "AGG_ATTR2", "AGG_ATTR3", "AGG_ATTR4", "AGG_ATTR5", "AGG_ATTR6", "AGG_ATTR7", "AGG_ATTR8", "AGG_ATTR9", "AGG_ATTR10", "AGG_ATTR11", "AGG_ATTR12", "AGG_ATTR13", "AGG_ATTR14", "AGG_ATTR15", "AGG_ATTR16", "AGG_ATTR17", "AGG_ATTR18", "AGG_ATTR19", "AGG_ATTR20", "MSRMT_DTTM", "AGG_VAL", "AGG_VAL1", "AGG_VAL2", "AGG_VAL3", "AGG_VAL4", "AGG_VAL5", "AGG_VAL6", "AGG_VAL7", "AGG_VAL8", "AGG_VAL9", "AGG_VAL10") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  with MC_SET_RANK as (
    select distinct MCSP.MEASR_COMP_SET_CD,
                    MCA.MEASR_COMP_ID,
                    dense_rank () over (
                      partition by MCSP.MEASR_COMP_SET_CD, MCA.MEASR_COMP_ID
                          order by MCA.SEQNO)   as ENTITY_RANK,
                    MCA.TBL_NAME                as ENTITY,
                    nvl2(MCA.FLD_VALUE2, MCA.FLD_VALUE1, MCA.FLD_NAME1) as ENTITY_FIELD,
                    nvl(MCA.FLD_VALUE2, MCA.FLD_VALUE1) as ENTITY_FIELD_VALUE
        from D1_MEASR_COMP_ATTRIBUTES        MCA
  inner join D1_MEASR_COMP_SET_PARTICIPANT   MCSP on MCSP.MEASR_COMP_ID    = MCA.MEASR_COMP_ID
),
MC_SET_ATTRS as (
    select * from (select MEASR_COMP_SET_CD, MEASR_COMP_ID as AGG_MEASR_COMP_ID, ENTITY_RANK, ENTITY_FIELD_VALUE
                     from MC_SET_RANK)
      pivot (max(ENTITY_FIELD_VALUE) for ENTITY_RANK
         in ( 1 as AGG_ATTR1,   2 as AGG_ATTR2,   3 as AGG_ATTR3,   4 as AGG_ATTR4,   5 as AGG_ATTR5,
              6 as AGG_ATTR6,   7 as AGG_ATTR7,   8 as AGG_ATTR8,   9 as AGG_ATTR9,  10 as AGG_ATTR10,
             11 as AGG_ATTR11, 12 as AGG_ATTR12, 13 as AGG_ATTR13, 14 as AGG_ATTR14, 15 as AGG_ATTR15,
             16 as AGG_ATTR16, 17 as AGG_ATTR17, 18 as AGG_ATTR18, 19 as AGG_ATTR19, 20 as AGG_ATTR20))
)
select  A.MEASR_COMP_SET_CD, A.AGG_MEASR_COMP_ID,
        A.AGG_ATTR1,  A.AGG_ATTR2,  A.AGG_ATTR3,  A.AGG_ATTR4,  A.AGG_ATTR5,
        A.AGG_ATTR6,  A.AGG_ATTR7,  A.AGG_ATTR8,  A.AGG_ATTR9,  A.AGG_ATTR10,
        A.AGG_ATTR11, A.AGG_ATTR12, A.AGG_ATTR13, A.AGG_ATTR14, A.AGG_ATTR15,
        A.AGG_ATTR16, A.AGG_ATTR17, A.AGG_ATTR18, A.AGG_ATTR19, A.AGG_ATTR20,
        nvl2(AM.MEASR_COMP_ID,  AM.MSRMT_DTTM, M.MSRMT_DTTM) as MSRMT_DTTM,
        nvl2(AM.MEASR_COMP_ID, AM.MSRMT_VAL,  M.MSRMT_VAL)   as AGG_VAL,
        nvl2(AM.MEASR_COMP_ID, AM.MSRMT_VAL1, M.MSRMT_VAL1)  as AGG_VAL1,
        nvl2(AM.MEASR_COMP_ID, AM.MSRMT_VAL2, M.MSRMT_VAL2)  as AGG_VAL2,
        nvl2(AM.MEASR_COMP_ID, AM.MSRMT_VAL3, M.MSRMT_VAL3)  as AGG_VAL3,
        nvl2(AM.MEASR_COMP_ID, AM.MSRMT_VAL4, M.MSRMT_VAL4)  as AGG_VAL4,
        nvl2(AM.MEASR_COMP_ID, AM.MSRMT_VAL5, M.MSRMT_VAL5)  as AGG_VAL5,
        nvl2(AM.MEASR_COMP_ID, AM.MSRMT_VAL6, M.MSRMT_VAL6)  as AGG_VAL6,
        nvl2(AM.MEASR_COMP_ID, AM.MSRMT_VAL7, M.MSRMT_VAL7)  as AGG_VAL7,
        nvl2(AM.MEASR_COMP_ID, AM.MSRMT_VAL8, M.MSRMT_VAL8)  as AGG_VAL8,
        nvl2(AM.MEASR_COMP_ID, AM.MSRMT_VAL9, M.MSRMT_VAL9)  as AGG_VAL9,
        nvl2(AM.MEASR_COMP_ID, AM.MSRMT_VAL10,M.MSRMT_VAL10) as AGG_VAL10
  from MC_SET_ATTRS      A
  left join D1_AGG_MSRMT   AM on AM.MEASR_COMP_ID = A.AGG_MEASR_COMP_ID
  left join D1_MSRMT        M on M.MEASR_COMP_ID  = A.AGG_MEASR_COMP_ID;

-- ----- D1_CONTACT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_CONTACT_VW" ("NAME_VALUE_UPPER", "CONTACT_ID", "US_ID", "D1_SP_ID", "D1_DEVICE_ID", "MEASR_COMP_ID", "US_TYPE_CD", "D1_SP_TYPE_CD", "DEVICE_TYPE_CD", "D1_SPR_CD", "MEASR_COMP_TYPE_CD", "D1_UOM_CD", "ACCESS_GRP_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
  /* ... */
  CN.NAME_VALUE_UPPER      ,
  USC.CONTACT_ID           ,
  US.US_ID                 ,
  ' ' AS D1_SP_ID          ,
  ' ' AS D1_DEVICE_ID      ,
  ' ' AS MEASR_COMP_ID     ,
  US.US_TYPE_CD            ,
  ' ' AS D1_SP_TYPE_CD     ,
  ' ' AS DEVICE_TYPE_CD    ,
  ' ' AS D1_SPR_CD         ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  ' ' AS ACCESS_GRP_CD
   FROM D1_CONTACT_NAME CN,
  D1_US_CONTACT USC       ,
  D1_US US
  WHERE USC.US_ID       = US.US_ID
AND US.US_STAT_COND_FLG = 'D1AC'
AND CN.CONTACT_ID       = USC.CONTACT_ID
AND NOT EXISTS
  (SELECT 'x' FROM D1_US_SP USSP WHERE USSP.US_ID = USC.US_ID
  )

UNION ALL
 
 SELECT CN.NAME_VALUE_UPPER,
  USC.CONTACT_ID           ,
  USSP.US_ID               ,
  USSP.D1_SP_ID            ,
  ' ' AS D1_DEVICE_ID      ,
  ' ' AS MEASR_COMP_ID     ,
  US.US_TYPE_CD            ,
  SP.D1_SP_TYPE_CD         ,
  ' ' AS DEVICE_TYPE_CD    ,
  ' ' AS D1_SPR_CD         ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_CONTACT_NAME CN,
  D1_US_CONTACT USC       ,
  D1_US_SP USSP           ,
  D1_US US                ,
  D1_SP SP
  WHERE USC.US_ID       = USSP.US_ID
AND SP.D1_SP_ID         = USSP.D1_SP_ID
AND US.US_ID            = USC.US_ID
AND US.US_STAT_COND_FLG = 'D1AC'
AND CN.CONTACT_ID       = USC.CONTACT_ID
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_INSTALL_EVT IE
    WHERE IE.D1_SP_ID      = USSP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM IS NULL
  OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL) )
  )

UNION ALL
 
 SELECT CN.NAME_VALUE_UPPER,
  USC.CONTACT_ID           ,
  USSP.US_ID               ,
  USSP.D1_SP_ID            ,
  D.D1_DEVICE_ID           ,
  ' ' AS MEASR_COMP_ID     ,
  US.US_TYPE_CD            ,
  SP.D1_SP_TYPE_CD         ,
  DVC.DEVICE_TYPE_CD       ,
  DVC.D1_SPR_CD            ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_CONTACT_NAME CN,
  D1_US_CONTACT USC       ,
  D1_US_SP USSP           ,
  D1_INSTALL_EVT IE       ,
  D1_DVC_CFG D            ,
  D1_US US                ,
  D1_SP SP                ,
  D1_DVC DVC
  WHERE US.US_ID         = USC.US_ID
AND USC.US_ID            = USSP.US_ID
AND US.US_STAT_COND_FLG  = 'D1AC'
AND CN.CONTACT_ID        = USC.CONTACT_ID
AND SP.D1_SP_ID          = USSP.D1_SP_ID
AND IE.D1_SP_ID          = USSP.D1_SP_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
AND DVC.D1_SPR_CD       <> ' '
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_MEASR_COMP MC
    WHERE MC.DEVICE_CONFIG_ID = D.DEVICE_CONFIG_ID
  )

UNION ALL
 
 SELECT CN.NAME_VALUE_UPPER,
  USC.CONTACT_ID           ,
  USSP.US_ID               ,
  USSP.D1_SP_ID            ,
  D.D1_DEVICE_ID           ,
  ' ' AS MEASR_COMP_ID     ,
  US.US_TYPE_CD            ,
  SP.D1_SP_TYPE_CD         ,
  DVC.DEVICE_TYPE_CD       ,
  DT.D1_SPR_CD             ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_CONTACT_NAME CN,
  D1_US_CONTACT USC       ,
  D1_US_SP USSP           ,
  D1_INSTALL_EVT IE       ,
  D1_DVC_CFG D            ,
  D1_US US                ,
  D1_SP SP                ,
  D1_DVC DVC              ,
  D1_DVC_TYPE DT
  WHERE USC.US_ID        = USSP.US_ID
AND US.US_ID             = USC.US_ID
AND US.US_STAT_COND_FLG  = 'D1AC'
AND CN.CONTACT_ID        = USC.CONTACT_ID
AND SP.D1_SP_ID          = USSP.D1_SP_ID
AND IE.D1_SP_ID          = USSP.D1_SP_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
AND DVC.D1_SPR_CD        = ' '
AND DT.DEVICE_TYPE_CD    = DVC.DEVICE_TYPE_CD
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_MEASR_COMP MC
    WHERE MC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
  )

UNION ALL
 
 SELECT CN.NAME_VALUE_UPPER,
  USC.CONTACT_ID           ,
  USSP.US_ID               ,
  USSP.D1_SP_ID            ,
  D.D1_DEVICE_ID           ,
  MC.MEASR_COMP_ID         ,
  US.US_TYPE_CD            ,
  SP.D1_SP_TYPE_CD         ,
  DVC.DEVICE_TYPE_CD       ,
  DVC.D1_SPR_CD            ,
  MC.MEASR_COMP_TYPE_CD    ,
  ' ' AS D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_CONTACT_NAME CN,
  D1_US_CONTACT USC       ,
  D1_US_SP USSP           ,
  D1_INSTALL_EVT IE       ,
  D1_DVC_CFG D            ,
  D1_MEASR_COMP MC        ,
  D1_US US                ,
  D1_SP SP                ,
  D1_DVC DVC
  WHERE USC.US_ID        = USSP.US_ID
AND US.US_ID             = USC.US_ID
AND US.US_STAT_COND_FLG  = 'D1AC'
AND CN.CONTACT_ID        = USC.CONTACT_ID
AND SP.D1_SP_ID          = USSP.D1_SP_ID
AND IE.D1_SP_ID          = USSP.D1_SP_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
AND DVC.D1_SPR_CD       <> ' '
AND MC.DEVICE_CONFIG_ID  = IE.DEVICE_CONFIG_ID
AND NOT EXISTS
  (SELECT 'X'
     FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
  )

UNION ALL
 
 SELECT CN.NAME_VALUE_UPPER,
  USC.CONTACT_ID           ,
  USSP.US_ID               ,
  USSP.D1_SP_ID            ,
  D.D1_DEVICE_ID           ,
  MC.MEASR_COMP_ID         ,
  US.US_TYPE_CD            ,
  SP.D1_SP_TYPE_CD         ,
  DVC.DEVICE_TYPE_CD       ,
  DVC.D1_SPR_CD            ,
  MC.MEASR_COMP_TYPE_CD    ,
  VI.D1_UOM_CD             ,
  SP.ACCESS_GRP_CD
   FROM D1_CONTACT_NAME CN,
  D1_US_CONTACT USC       ,
  D1_US_SP USSP           ,
  D1_INSTALL_EVT IE       ,
  D1_DVC_CFG D            ,
  D1_MEASR_COMP MC        ,
  D1_US US                ,
  D1_SP SP                ,
  D1_DVC DVC              ,
  D1_MC_TYPE_VALUE_IDENTIFIER VI
  WHERE USC.US_ID         = USSP.US_ID
AND US.US_ID              = USC.US_ID
AND US.US_STAT_COND_FLG   = 'D1AC'
AND CN.CONTACT_ID         = USC.CONTACT_ID
AND SP.D1_SP_ID           = USSP.D1_SP_ID
AND IE.D1_SP_ID           = USSP.D1_SP_ID
AND IE.D1_INSTALL_DTTM   <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM  IS NULL
OR IE.D1_REMOVAL_DTTM     > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND D.DEVICE_CONFIG_ID    = IE.DEVICE_CONFIG_ID
AND DVC.D1_DEVICE_ID      = D.D1_DEVICE_ID
AND DVC.D1_SPR_CD        <> ' '
AND MC.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'

UNION ALL
 
 SELECT CN.NAME_VALUE_UPPER,
  USC.CONTACT_ID           ,
  USSP.US_ID               ,
  USSP.D1_SP_ID            ,
  D.D1_DEVICE_ID           ,
  MC.MEASR_COMP_ID         ,
  US.US_TYPE_CD            ,
  SP.D1_SP_TYPE_CD         ,
  DVC.DEVICE_TYPE_CD       ,
  DT.D1_SPR_CD             ,
  MC.MEASR_COMP_TYPE_CD    ,
  ' ' AS D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_CONTACT_NAME CN,
  D1_US_CONTACT USC       ,
  D1_US_SP USSP           ,
  D1_INSTALL_EVT IE       ,
  D1_DVC_CFG D            ,
  D1_MEASR_COMP MC        ,
  D1_US US                ,
  D1_SP SP                ,
  D1_DVC DVC              ,
  D1_DVC_TYPE DT
  WHERE USC.US_ID        = USSP.US_ID
AND US.US_ID             = USC.US_ID
AND US.US_STAT_COND_FLG  = 'D1AC'
AND CN.CONTACT_ID        = USC.CONTACT_ID
AND SP.D1_SP_ID          = USSP.D1_SP_ID
AND IE.D1_SP_ID          = USSP.D1_SP_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
AND DVC.D1_SPR_CD        = ' '
AND DT.DEVICE_TYPE_CD    = DVC.DEVICE_TYPE_CD
AND MC.DEVICE_CONFIG_ID  = IE.DEVICE_CONFIG_ID
AND NOT EXISTS
  (SELECT 'X'
     FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
  )

UNION ALL
 
 SELECT CN.NAME_VALUE_UPPER,
  USC.CONTACT_ID           ,
  USSP.US_ID               ,
  USSP.D1_SP_ID            ,
  D.D1_DEVICE_ID           ,
  MC.MEASR_COMP_ID         ,
  US.US_TYPE_CD            ,
  SP.D1_SP_TYPE_CD         ,
  DVC.DEVICE_TYPE_CD       ,
  DT.D1_SPR_CD             ,
  MC.MEASR_COMP_TYPE_CD    ,
  VI.D1_UOM_CD             ,
  SP.ACCESS_GRP_CD
   FROM D1_CONTACT_NAME CN,
  D1_US_CONTACT USC       ,
  D1_US_SP USSP           ,
  D1_INSTALL_EVT IE       ,
  D1_DVC_CFG D            ,
  D1_MEASR_COMP MC        ,
  D1_US US                ,
  D1_SP SP                ,
  D1_DVC DVC              ,
  D1_DVC_TYPE DT          ,
  D1_MC_TYPE_VALUE_IDENTIFIER VI
  WHERE USC.US_ID         = USSP.US_ID
AND US.US_ID              = USC.US_ID
AND US.US_STAT_COND_FLG   = 'D1AC'
AND SP.D1_SP_ID           = USSP.D1_SP_ID
AND CN.CONTACT_ID         = USC.CONTACT_ID
AND IE.D1_SP_ID           = USSP.D1_SP_ID
AND IE.D1_INSTALL_DTTM   <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM  IS NULL
OR IE.D1_REMOVAL_DTTM     > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND D.DEVICE_CONFIG_ID    = IE.DEVICE_CONFIG_ID
AND DVC.D1_DEVICE_ID      = D.D1_DEVICE_ID
AND DVC.D1_SPR_CD         = ' '
AND DT.DEVICE_TYPE_CD     = DVC.DEVICE_TYPE_CD
AND MC.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD 
AND VI.VALUE_ID_TYPE_FLG  = 'D1MS';

-- ----- D1_DEVICE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_DEVICE_VW" ("D1_DEVICE_ID", "MEASR_COMP_ID", "D1_SP_ID", "US_ID", "US_TYPE_CD", "D1_SP_TYPE_CD", "DEVICE_TYPE_CD", "D1_SPR_CD", "MEASR_COMP_TYPE_CD", "D1_UOM_CD", "ACCESS_GRP_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT D.D1_DEVICE_ID     ,
  ' ' AS MEASR_COMP_ID     ,
  ' ' AS D1_SP_ID          ,
  ' ' AS US_ID             ,
  ' ' AS US_TYPE_CD        ,
  ' ' AS D1_SP_TYPE_CD     ,
  D.DEVICE_TYPE_CD         ,
  D.D1_SPR_CD              ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  ' ' AS ACCESS_GRP_CD
   FROM D1_DVC D
  WHERE NOT EXISTS
  (SELECT 'x'
     FROM D1_INSTALL_EVT IE,
    D1_DVC_CFG DC
    WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND DC.EFF_DTTM        <=
    (SELECT MAX(EFF_DTTM)
       FROM D1_DVC_CFG DC2
      WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
    AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
    )
  AND IE.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM IS NULL
  OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  )
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_DVC_CFG DC,
    D1_MEASR_COMP MC
    WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
  )
AND D.D1_SPR_CD <> ' '
  
  UNION
 
 SELECT D.D1_DEVICE_ID     ,
  ' ' AS MEASR_COMP_ID     ,
  ' ' AS D1_SP_ID          ,
  ' ' AS US_ID             ,
  ' ' AS US_TYPE_CD        ,
  ' ' AS D1_SP_TYPE_CD     ,
  D.DEVICE_TYPE_CD         ,
  DT.D1_SPR_CD             ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  ' ' AS ACCESS_GRP_CD
   FROM D1_DVC D,
  D1_DVC_TYPE DT
  WHERE NOT EXISTS
  (SELECT 'x'
     FROM D1_INSTALL_EVT IE,
    D1_DVC_CFG DC
    WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND DC.EFF_DTTM        <=
    (SELECT MAX(EFF_DTTM)
       FROM D1_DVC_CFG DC2
      WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
    AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
    )
  AND IE.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM IS NULL
  OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  )
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_DVC_CFG DC,
    D1_MEASR_COMP MC
    WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
  )
AND D.D1_SPR_CD       = ' '
AND DT.DEVICE_TYPE_CD = D.DEVICE_TYPE_CD
  
  UNION
 
 SELECT D.D1_DEVICE_ID ,
  MC.MEASR_COMP_ID     ,
  ' ' AS D1_SP_ID      ,
  ' ' AS US_ID         ,
  ' ' AS US_TYPE_CD    ,
  ' ' AS D1_SP_TYPE_CD ,
  D.DEVICE_TYPE_CD     ,
  D.D1_SPR_CD          ,
  MC.MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD     ,
  ' ' AS ACCESS_GRP_CD
   FROM D1_DVC D,
  D1_DVC_CFG DC ,
  D1_MEASR_COMP MC
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD        <> ' '
AND MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_INSTALL_EVT IE
    WHERE IE.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM    IS NULL
  OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  )
AND NOT EXISTS
  (SELECT 'X'
     FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
  )
  
  UNION
 
 SELECT D.D1_DEVICE_ID ,
  MC.MEASR_COMP_ID     ,
  ' ' AS D1_SP_ID      ,
  ' ' AS US_ID         ,
  ' ' AS US_TYPE_CD    ,
  ' ' AS D1_SP_TYPE_CD ,
  D.DEVICE_TYPE_CD     ,
  D.D1_SPR_CD          ,
  MC.MEASR_COMP_TYPE_CD,
  VI.D1_UOM_CD         ,
  ' ' AS ACCESS_GRP_CD
   FROM D1_DVC D  ,
  D1_DVC_CFG DC   ,
  D1_MEASR_COMP MC,
  D1_MC_TYPE_VALUE_IDENTIFIER VI
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD        <> ' '
AND MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_INSTALL_EVT IE
    WHERE IE.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM    IS NULL
  OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  )
AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'
  
  UNION
 
 SELECT D.D1_DEVICE_ID ,
  MC.MEASR_COMP_ID     ,
  ' ' AS D1_SP_ID      ,
  ' ' AS US_ID         ,
  ' ' AS US_TYPE_CD    ,
  ' ' AS D1_SP_TYPE_CD ,
  D.DEVICE_TYPE_CD     ,
  DT.D1_SPR_CD         ,
  MC.MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD     ,
  ' ' AS ACCESS_GRP_CD
   FROM D1_DVC D  ,
  D1_DVC_CFG DC   ,
  D1_MEASR_COMP MC,
  D1_DVC_TYPE DT
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD         = ' '
AND DT.DEVICE_TYPE_CD   = D.DEVICE_TYPE_CD
AND MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_INSTALL_EVT IE
    WHERE IE.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM    IS NULL
  OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  )
AND NOT EXISTS
  (SELECT 'X'
     FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
  )
  
  UNION
 
 SELECT D.D1_DEVICE_ID ,
  MC.MEASR_COMP_ID     ,
  ' ' AS D1_SP_ID      ,
  ' ' AS US_ID         ,
  ' ' AS US_TYPE_CD    ,
  ' ' AS D1_SP_TYPE_CD ,
  D.DEVICE_TYPE_CD     ,
  DT.D1_SPR_CD         ,
  MC.MEASR_COMP_TYPE_CD,
  VI.D1_UOM_CD         ,
  ' ' AS ACCESS_GRP_CD
   FROM D1_DVC D  ,
  D1_DVC_CFG DC   ,
  D1_MEASR_COMP MC,
  D1_DVC_TYPE DT  ,
  D1_MC_TYPE_VALUE_IDENTIFIER VI
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD         = ' '
AND DT.DEVICE_TYPE_CD   = D.DEVICE_TYPE_CD
AND MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_INSTALL_EVT IE
    WHERE IE.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM    IS NULL
  OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  )
AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'
  
  UNION
 
 SELECT D.D1_DEVICE_ID     ,
  ' ' AS MEASR_COMP_ID     ,
  IE.D1_SP_ID              ,
  ' ' AS US_ID             ,
  ' ' AS US_TYPE_CD        ,
  SP.D1_SP_TYPE_CD         ,
  D.DEVICE_TYPE_CD         ,
  D.D1_SPR_CD              ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_DVC D   ,
  D1_DVC_CFG DC    ,
  D1_INSTALL_EVT IE,
  D1_SP SP
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD        <> ' '
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND IE.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND SP.D1_SP_ID          = IE.D1_SP_ID
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_MEASR_COMP MC
    WHERE MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
  )
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_US_SP USSP,
    D1_US US
    WHERE USSP.D1_SP_ID   = IE.D1_SP_ID
  AND US.US_ID            = USSP.US_ID
  AND US.US_STAT_COND_FLG = 'D1AC'
  )
  
  UNION
 
 SELECT D.D1_DEVICE_ID     ,
  ' ' AS MEASR_COMP_ID     ,
  IE.D1_SP_ID              ,
  ' ' AS US_ID             ,
  ' ' AS US_TYPE_CD        ,
  SP.D1_SP_TYPE_CD         ,
  D.DEVICE_TYPE_CD         ,
  DT.D1_SPR_CD             ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_DVC D   ,
  D1_DVC_CFG DC    ,
  D1_INSTALL_EVT IE,
  D1_SP SP         ,
  D1_DVC_TYPE DT
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD         = ' '
AND DT.DEVICE_TYPE_CD   = D.DEVICE_TYPE_CD
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND IE.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND SP.D1_SP_ID          = IE.D1_SP_ID
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_MEASR_COMP MC
    WHERE MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
  )
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_US_SP USSP,
    D1_US US
    WHERE USSP.D1_SP_ID   = IE.D1_SP_ID
  AND US.US_ID            = USSP.US_ID
  AND US.US_STAT_COND_FLG = 'D1AC'
  )
  
  UNION
 
 SELECT D.D1_DEVICE_ID     ,
  ' ' AS MEASR_COMP_ID     ,
  IE.D1_SP_ID              ,
  USSP.US_ID               ,
  US.US_TYPE_CD            ,
  SP.D1_SP_TYPE_CD         ,
  D.DEVICE_TYPE_CD         ,
  D.D1_SPR_CD              ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_DVC D   ,
  D1_DVC_CFG DC    ,
  D1_INSTALL_EVT IE,
  D1_US_SP USSP    ,
  D1_US US         ,
  D1_SP SP
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD        <> ' '
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND IE.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_MEASR_COMP MC
    WHERE MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
  )
AND USSP.D1_SP_ID       = IE.D1_SP_ID
AND US.US_ID            = USSP.US_ID
AND US.US_STAT_COND_FLG = 'D1AC'
AND SP.D1_SP_ID         = USSP.D1_SP_ID
  
  UNION
 
 SELECT D.D1_DEVICE_ID     ,
  ' ' AS MEASR_COMP_ID     ,
  IE.D1_SP_ID              ,
  USSP.US_ID               ,
  US.US_TYPE_CD            ,
  SP.D1_SP_TYPE_CD         ,
  D.DEVICE_TYPE_CD         ,
  DT.D1_SPR_CD             ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_DVC D   ,
  D1_DVC_CFG DC    ,
  D1_INSTALL_EVT IE,
  D1_US_SP USSP    ,
  D1_US US         ,
  D1_SP SP         ,
  D1_DVC_TYPE DT
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD         = ' '
AND DT.DEVICE_TYPE_CD   = D.DEVICE_TYPE_CD
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND IE.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_MEASR_COMP MC
    WHERE MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
  )
AND USSP.D1_SP_ID       = IE.D1_SP_ID
AND US.US_ID            = USSP.US_ID
AND US.US_STAT_COND_FLG = 'D1AC'
AND SP.D1_SP_ID         = USSP.D1_SP_ID
  
  UNION
 
 SELECT D.D1_DEVICE_ID ,
  MC.MEASR_COMP_ID     ,
  IE.D1_SP_ID          ,
  ' ' AS US_ID         ,
  ' ' AS US_TYPE_CD    ,
  SP.D1_SP_TYPE_CD     ,
  D.DEVICE_TYPE_CD     ,
  D.D1_SPR_CD          ,
  MC.MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD     ,
  SP.ACCESS_GRP_CD
   FROM D1_DVC D   ,
  D1_DVC_CFG DC    ,
  D1_INSTALL_EVT IE,
  D1_MEASR_COMP MC ,
  D1_SP SP
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD        <> ' '
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND IE.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND MC.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND SP.D1_SP_ID          = IE.D1_SP_ID
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_US_SP USSP,
    D1_US US
    WHERE USSP.D1_SP_ID   = IE.D1_SP_ID
  AND US.US_ID            = USSP.US_ID
  AND US.US_STAT_COND_FLG = 'D1AC'
  )
  
  UNION
 
 SELECT D.D1_DEVICE_ID ,
  MC.MEASR_COMP_ID     ,
  IE.D1_SP_ID          ,
  ' ' AS US_ID         ,
  ' ' AS US_TYPE_CD    ,
  SP.D1_SP_TYPE_CD     ,
  D.DEVICE_TYPE_CD     ,
  D.D1_SPR_CD          ,
  MC.MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD     ,
  SP.ACCESS_GRP_CD
   FROM D1_DVC D   ,
  D1_DVC_CFG DC    ,
  D1_INSTALL_EVT IE,
  D1_MEASR_COMP MC ,
  D1_SP SP
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD        <> ' '
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND IE.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND MC.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND SP.D1_SP_ID          = IE.D1_SP_ID
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_US_SP USSP,
    D1_US US
    WHERE USSP.D1_SP_ID   = IE.D1_SP_ID
  AND US.US_ID            = USSP.US_ID
  AND US.US_STAT_COND_FLG = 'D1AC'
  )
  
  UNION
 
 SELECT D.D1_DEVICE_ID ,
  MC.MEASR_COMP_ID     ,
  IE.D1_SP_ID          ,
  ' ' AS US_ID         ,
  ' ' AS US_TYPE_CD    ,
  SP.D1_SP_TYPE_CD     ,
  D.DEVICE_TYPE_CD     ,
  DT.D1_SPR_CD         ,
  MC.MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD     ,
  SP.ACCESS_GRP_CD
   FROM D1_DVC D   ,
  D1_DVC_CFG DC    ,
  D1_INSTALL_EVT IE,
  D1_MEASR_COMP MC ,
  D1_SP SP         ,
  D1_DVC_TYPE DT
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD         = ' '
AND DT.DEVICE_TYPE_CD   = D.DEVICE_TYPE_CD
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND IE.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND MC.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND SP.D1_SP_ID          = IE.D1_SP_ID
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_US_SP USSP,
    D1_US US
    WHERE USSP.D1_SP_ID   = IE.D1_SP_ID
  AND US.US_ID            = USSP.US_ID
  AND US.US_STAT_COND_FLG = 'D1AC'
  )
AND NOT EXISTS
  (SELECT 'X'
     FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
  )
  
  UNION
 
 SELECT D.D1_DEVICE_ID ,
  MC.MEASR_COMP_ID     ,
  IE.D1_SP_ID          ,
  ' ' AS US_ID         ,
  ' ' AS US_TYPE_CD    ,
  SP.D1_SP_TYPE_CD     ,
  D.DEVICE_TYPE_CD     ,
  DT.D1_SPR_CD         ,
  MC.MEASR_COMP_TYPE_CD,
  VI.D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_DVC D   ,
  D1_DVC_CFG DC    ,
  D1_INSTALL_EVT IE,
  D1_MEASR_COMP MC ,
  D1_SP SP         ,
  D1_DVC_TYPE DT   ,
  D1_MC_TYPE_VALUE_IDENTIFIER VI
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD         = ' '
AND DT.DEVICE_TYPE_CD   = D.DEVICE_TYPE_CD
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND IE.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND MC.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND SP.D1_SP_ID          = IE.D1_SP_ID
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_US_SP USSP,
    D1_US US
    WHERE USSP.D1_SP_ID   = IE.D1_SP_ID
  AND US.US_ID            = USSP.US_ID
  AND US.US_STAT_COND_FLG = 'D1AC'
  )
AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'
  
  UNION
 
 SELECT D.D1_DEVICE_ID ,
  MC.MEASR_COMP_ID     ,
  IE.D1_SP_ID          ,
  USSP.US_ID           ,
  US.US_TYPE_CD        ,
  SP.D1_SP_TYPE_CD     ,
  D.DEVICE_TYPE_CD     ,
  D.D1_SPR_CD          ,
  MC.MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD     ,
  SP.ACCESS_GRP_CD
   FROM D1_DVC D   ,
  D1_DVC_CFG DC    ,
  D1_INSTALL_EVT IE,
  D1_MEASR_COMP MC ,
  D1_US_SP USSP    ,
  D1_US US         ,
  D1_SP SP
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD        <> ' '
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND IE.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND MC.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND USSP.D1_SP_ID        = IE.D1_SP_ID
AND US.US_ID             = USSP.US_ID
AND US.US_STAT_COND_FLG  = 'D1AC'
AND SP.D1_SP_ID          = USSP.D1_SP_ID
AND NOT EXISTS
  (SELECT 'X'
     FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
  )
  
  UNION
 
 SELECT D.D1_DEVICE_ID ,
  MC.MEASR_COMP_ID     ,
  IE.D1_SP_ID          ,
  USSP.US_ID           ,
  US.US_TYPE_CD        ,
  SP.D1_SP_TYPE_CD     ,
  D.DEVICE_TYPE_CD     ,
  D.D1_SPR_CD          ,
  MC.MEASR_COMP_TYPE_CD,
  VI.D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_DVC D   ,
  D1_DVC_CFG DC    ,
  D1_INSTALL_EVT IE,
  D1_MEASR_COMP MC ,
  D1_US_SP USSP    ,
  D1_US US         ,
  D1_SP SP         ,
  D1_MC_TYPE_VALUE_IDENTIFIER VI
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD        <> ' '
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND IE.DEVICE_CONFIG_ID   = DC.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM   <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM  IS NULL
OR IE.D1_REMOVAL_DTTM     > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND MC.DEVICE_CONFIG_ID   = DC.DEVICE_CONFIG_ID
AND USSP.D1_SP_ID         = IE.D1_SP_ID
AND US.US_ID              = USSP.US_ID
AND US.US_STAT_COND_FLG   = 'D1AC'
AND SP.D1_SP_ID           = USSP.D1_SP_ID
AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'
  
  UNION
 
 SELECT D.D1_DEVICE_ID ,
  MC.MEASR_COMP_ID     ,
  IE.D1_SP_ID          ,
  USSP.US_ID           ,
  US.US_TYPE_CD        ,
  SP.D1_SP_TYPE_CD     ,
  D.DEVICE_TYPE_CD     ,
  DT.D1_SPR_CD         ,
  MC.MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD     ,
  SP.ACCESS_GRP_CD
   FROM D1_DVC D   ,
  D1_DVC_CFG DC    ,
  D1_INSTALL_EVT IE,
  D1_MEASR_COMP MC ,
  D1_US_SP USSP    ,
  D1_US US         ,
  D1_SP SP         ,
  D1_DVC_TYPE DT
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD         = ' '
AND DT.DEVICE_TYPE_CD   = D.DEVICE_TYPE_CD
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND IE.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND MC.DEVICE_CONFIG_ID  = DC.DEVICE_CONFIG_ID
AND USSP.D1_SP_ID        = IE.D1_SP_ID
AND US.US_ID             = USSP.US_ID
AND US.US_STAT_COND_FLG  = 'D1AC'
AND SP.D1_SP_ID          = USSP.D1_SP_ID
AND NOT EXISTS
  (SELECT 'X'
     FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
  )
  
  UNION
 
 SELECT D.D1_DEVICE_ID ,
  MC.MEASR_COMP_ID     ,
  IE.D1_SP_ID          ,
  USSP.US_ID           ,
  US.US_TYPE_CD        ,
  SP.D1_SP_TYPE_CD     ,
  D.DEVICE_TYPE_CD     ,
  DT.D1_SPR_CD         ,
  MC.MEASR_COMP_TYPE_CD,
  VI.D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_DVC D   ,
  D1_DVC_CFG DC    ,
  D1_INSTALL_EVT IE,
  D1_MEASR_COMP MC ,
  D1_US_SP USSP    ,
  D1_US US         ,
  D1_SP SP         ,
  D1_DVC_TYPE DT   ,
  D1_MC_TYPE_VALUE_IDENTIFIER VI
  WHERE DC.D1_DEVICE_ID = D.D1_DEVICE_ID
AND D.D1_SPR_CD         = ' '
AND DT.DEVICE_TYPE_CD   = D.DEVICE_TYPE_CD
AND DC.EFF_DTTM        <=
  (SELECT MAX(EFF_DTTM)
     FROM D1_DVC_CFG DC2
    WHERE DC2.D1_DEVICE_ID = D.D1_DEVICE_ID
  AND EFF_DTTM            <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  )
AND IE.DEVICE_CONFIG_ID   = DC.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM   <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM  IS NULL
OR IE.D1_REMOVAL_DTTM     > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND MC.DEVICE_CONFIG_ID   = DC.DEVICE_CONFIG_ID
AND USSP.D1_SP_ID         = IE.D1_SP_ID
AND US.US_ID              = USSP.US_ID
AND US.US_STAT_COND_FLG   = 'D1AC'
AND SP.D1_SP_ID           = USSP.D1_SP_ID
AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
AND VI.VALUE_ID_TYPE_FLG  = 'D1MS';

-- ----- D1_DVC_SP_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_DVC_SP_VW" ("D1_DEVICE_ID", "MEASR_COMP_ID", "D1_SP_ID", "ACCESS_GRP_CD", "DIVISION_CD", "DEVICE_CONFIG_ID", "INSTALL_EVT_ID", "D1_INSTALL_DTTM", "D1_REMOVAL_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
  DVC.D1_DEVICE_ID,
  MC.MEASR_COMP_ID,
  SP.D1_SP_ID,
  SP.ACCESS_GRP_CD,
  SP.DIVISION_CD,
  DC.DEVICE_CONFIG_ID,
  IE.INSTALL_EVT_ID,
  IE.D1_INSTALL_DTTM,
  IE.D1_REMOVAL_DTTM
FROM
  D1_INSTALL_EVT IE,
  D1_DVC_CFG DC,
  D1_MEASR_COMP MC,
  D1_DVC DVC,
  D1_SP SP
WHERE IE.D1_INSTALL_DTTM <= CAST(CURRENT_TIMESTAMP AS DATE)
AND (IE.D1_REMOVAL_DTTM IS NULL OR IE.D1_REMOVAL_DTTM > CAST(CURRENT_TIMESTAMP AS DATE))
AND SP.D1_SP_ID = IE.D1_SP_ID
AND DC.DEVICE_CONFIG_ID= IE.DEVICE_CONFIG_ID
AND DVC.D1_DEVICE_ID = DC.D1_DEVICE_ID
AND MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID;

-- ----- D1_EXT_US_INT_MDS_CONST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_EXT_US_INT_MDS_CONST_VW" ("US_ID", "MEASR_COMP_ID", "INSTALL_EVT_ID", "VALUE_ID_TYPE_FLG", "SEC_PER_INTRVL", "MSRMT_DATA_SNAP_TYPE_CD", "MSR_PEAK_QTY_FLG", "CONS_EXT_TYPE_CD", "EXT_TO_SI", "SOURCE_ID_TYPE_CD", "TARGET_ID_TYPE_CD", "USE_PERCENT", "D1_USAGE_FLG", "MEASR_COMP_USAGE_FLG", "USE_MULT", "UOM_CONV_MULT", "START_DTTM", "END_DTTM", "US_TZ_NAME", "US_STD_OFFSET", "SYS_STD_OFFSET") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  WITH STD_OFFSET as (
 select case
        when diff > 0
          then to_char(to_date(abs(round(diff*24*60*60,0)),'sssss'),'HH24:MI')
        else   '-'||to_char(to_date(abs(round(diff*24*60*60,0)),'sssss'),'HH24:MI')
      end utc_offset
      , F1_TIMEZONE_NAME
      , TIME_ZONE_CD
from (select min(all_days.dt - to_date(to_char(from_tz(CAST(all_days.dt AS TIMESTAMP),tz.f1_timezone_name)
                                 at time zone 'UTC', 'YYYY-MM-DD HH24:MI:SS'), 'YYYY-MM-DD HH24:MI:SS')) diff
      , TZ.F1_TIMEZONE_NAME
      , TZ.TIME_ZONE_CD
      from (select trunc(CURRENT_DATE-rownum) dt
            from dual connect by rownum < 366) all_days
      ,     ci_time_zone tz
      where tz.F1_TIMEZONE_NAME <> ' '
      group by TZ.F1_TIMEZONE_NAME, TZ.TIME_ZONE_CD) minDiff
), MCTVI as (
    SELECT MCTVI.MEASR_COMP_TYPE_CD
    ,      MCTVI.VALUE_ID_TYPE_FLG
    ,      MCT.SEC_PER_INTRVL
    ,      MDST.MSRMT_DATA_SNAP_TYPE_CD
    ,      MCUOM.MSR_PEAK_QTY_FLG
    ,      MCUOM.MAGNITUDE / MDSUOM.MAGNITUDE UOM_CONV_MULT
    FROM   D1_MC_TYPE_VALUE_IDENTIFIER MCTVI
    INNER JOIN D1_UOM MCUOM ON MCTVI.D1_UOM_CD = MCUOM.D1_UOM_CD
    INNER JOIN D1_MEASR_COMP_TYPE MCT ON MCT.MEASR_COMP_TYPE_CD = MCTVI.MEASR_COMP_TYPE_CD AND MCT.INTERVAL_SCALAR_FLG = 'D1IN'
    INNER JOIN D1_DVC_CFG_TYPE_MC_TYPE DCMC ON DCMC.MEASR_COMP_TYPE_CD = MCT.MEASR_COMP_TYPE_CD
    INNER JOIN D1_DVC_TYPE_CFG_TYPE DTCT ON DTCT.DEVICE_CONFIG_TYPE_CD = DCMC.DEVICE_CONFIG_TYPE_CD
    INNER JOIN D1_SP_TYPE_DEVICE_TYPE STDT ON STDT.DEVICE_TYPE_CD = DTCT.DEVICE_TYPE_CD
    INNER JOIN D1_US_TYPE_VAL_SP_TYPE UTST ON UTST.D1_SP_TYPE_CD = STDT.D1_SP_TYPE_CD
    INNER JOIN D1_CONS_EXT_TYPE_US_TYPE CETUT ON CETUT.US_TYPE_CD = UTST.US_TYPE_CD AND CETUT.D1_UOM_CD = MCTVI.D1_UOM_CD
    AND
   (((CETUT.D1_TOU_CD IS NULL OR CETUT.D1_TOU_CD = ' ') AND (MCTVI.D1_TOU_CD IS NULL OR MCTVI.D1_TOU_CD = ' ')) OR CETUT.D1_TOU_CD = MCTVI.D1_TOU_CD) AND
   (((CETUT.D1_SQI_CD IS NULL OR CETUT.D1_SQI_CD = ' ') AND (MCTVI.D1_SQI_CD IS NULL OR MCTVI.D1_SQI_CD = ' ')) OR CETUT.D1_SQI_CD = MCTVI.D1_SQI_CD)
    INNER JOIN D1_CONS_EXT_TYPE_MDS_TYPE CETST ON CETST.CONS_EXT_TYPE_CD = CETUT.CONS_EXT_TYPE_CD
    INNER JOIN D1_MSRMT_DATA_SNAP_TYPE MDST ON MDST.MSRMT_DATA_SNAP_TYPE_CD = CETST.MSRMT_DATA_SNAP_TYPE_CD AND MDST.SEC_PER_INTRVL = MCT.SEC_PER_INTRVL
    INNER JOIN D1_UOM MDSUOM ON MDST.D1_UOM_CD = MDSUOM.D1_UOM_CD
)
    SELECT US.US_ID
    ,      MC.MEASR_COMP_ID
    ,      IE.INSTALL_EVT_ID
    ,      MCTVI.VALUE_ID_TYPE_FLG
    ,      MCTVI.SEC_PER_INTRVL
    ,      MCTVI.MSRMT_DATA_SNAP_TYPE_CD
    ,      MCTVI.MSR_PEAK_QTY_FLG
    ,      CETUT.CONS_EXT_TYPE_CD
    ,      extractvalue(XMLPARSE(CONTENT CET.BO_DATA_AREA),'extractToDifferentUsageSubscription') EXT_TO_SI
    ,      extractvalue(XMLPARSE(CONTENT CET.BO_DATA_AREA),'sourceIdentifierType') SOURCE_ID_TYPE_CD
    ,      extractvalue(XMLPARSE(CONTENT CET.BO_DATA_AREA),'targetIdentifierType') TARGET_ID_TYPE_CD
    ,      USSP.USE_PERCENT
    ,      USSP.D1_USAGE_FLG
    ,      MC.MEASR_COMP_USAGE_FLG
    , CASE
        WHEN (MC.MEASR_COMP_USAGE_FLG = 'P   ' OR MCTVI.MSR_PEAK_QTY_FLG = 'D1MP') AND USSP.D1_USAGE_FLG = 'D1ST'
            THEN -1
        WHEN (MC.MEASR_COMP_USAGE_FLG <> 'P   ' AND MCTVI.MSR_PEAK_QTY_FLG <> 'D1MP') AND (DECODE(USSP.D1_USAGE_FLG,'D1AD','+   ','-   ') <> MC.MEASR_COMP_USAGE_FLG)
            THEN -1
        ELSE 1
      END USE_MULT
    , MCTVI.UOM_CONV_MULT
    , from_tz(CAST(to_date(greatest(nvl(IE.D1_INSTALL_DTTM,date'1900-01-01')
        , nvl(US.START_DTTM,date'1900-01-01')
        , nvl(USSP.START_DTTM,date'1900-01-01'))) AS TIMESTAMP), INTZ.F1_TIMEZONE_NAME) AT TIME ZONE (INTZOFFSET.UTC_OFFSET)
        START_DTTM
     , from_tz(CAST(to_date(least(nvl(IE.D1_REMOVAL_DTTM,date'9999-01-01')
        , nvl(US.END_DTTM,date'9999-01-01')
        , nvl(USSP.D1_STOP_DTTM,date'9999-01-01')))AS TIMESTAMP), INTZ.F1_TIMEZONE_NAME ) AT TIME ZONE (INTZOFFSET.UTC_OFFSET)
    END_DTTM
    , CTZ.F1_TIMEZONE_NAME US_TZ_NAME
    , USOFFSET.UTC_OFFSET US_STD_OFFSET
    , INTZOFFSET.UTC_OFFSET SYS_STD_OFFSET
    FROM D1_US US
    INNER JOIN D1_US_SP USSP ON US.US_ID = USSP.US_ID AND USSP.D1_USAGE_FLG <> 'D1CK'
    INNER JOIN D1_INSTALL_EVT IE ON USSP.D1_SP_ID = IE.D1_SP_ID
    INNER JOIN D1_DVC_CFG DC ON IE.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
    INNER JOIN D1_MEASR_COMP MC ON MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID AND MC.MEASR_COMP_USAGE_FLG <> 'C   '
    INNER JOIN F1_INSTALLATION INSTLL ON 1 = 1
    INNER JOIN CI_TIME_ZONE INTZ on INSTLL.TIME_ZONE_CD = INTZ.TIME_ZONE_CD
    INNER JOIN STD_OFFSET INTZOFFSET on INTZ.TIME_ZONE_CD = INTZOFFSET.TIME_ZONE_CD
    INNER JOIN CI_TIME_ZONE CTZ ON US.TIME_ZONE_CD = CTZ.TIME_ZONE_CD
    INNER JOIN STD_OFFSET USOFFSET on CTZ.TIME_ZONE_CD = USOFFSET.TIME_ZONE_CD
    INNER JOIN MCTVI on MC.MEASR_COMP_TYPE_CD = MCTVI.MEASR_COMP_TYPE_CD
    INNER JOIN D1_CONS_EXT_TYPE_US_TYPE CETUT on US.US_TYPE_CD = CETUT.US_TYPE_CD
    INNER JOIN D1_CONS_EXT_TYPE CET on CET.CONS_EXT_TYPE_CD = CETUT.CONS_EXT_TYPE_CD;

-- ----- D1_EXT_US_INT_MDS_MSRMTS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_EXT_US_INT_MDS_MSRMTS_VW" ("SETT_US_ID", "MSRMT_DATA_SNAP_TYPE_CD", "CONS_EXT_TYPE_CD", "US_ID", "EXT_TO_SI", "SOURCE_ID_TYPE_CD", "TARGET_ID_TYPE_CD", "D1_SP_ID", "MEASR_COMP_ID", "TRANS_ID", "START_DTTM", "D1_LOCAL_DT", "INTERVALS_PER_DAY", "INT_FOUND", "MSRMT_COND_FLG", "LAST_UPD_DTTM", "ILM_DT", "ILM_ARCH_SW", "MSRMT_VAL1", "MSRMT_VAL2", "MSRMT_VAL3", "MSRMT_VAL4", "MSRMT_VAL5", "MSRMT_VAL6", "MSRMT_VAL7", "MSRMT_VAL8", "MSRMT_VAL9", "MSRMT_VAL10", "MSRMT_VAL11", "MSRMT_VAL12", "MSRMT_VAL13", "MSRMT_VAL14", "MSRMT_VAL15", "MSRMT_VAL16", "MSRMT_VAL17", "MSRMT_VAL18", "MSRMT_VAL19", "MSRMT_VAL20", "MSRMT_VAL21", "MSRMT_VAL22", "MSRMT_VAL23", "MSRMT_VAL24", "MSRMT_VAL25", "MSRMT_VAL26", "MSRMT_VAL27", "MSRMT_VAL28", "MSRMT_VAL29", "MSRMT_VAL30", "MSRMT_VAL31", "MSRMT_VAL32", "MSRMT_VAL33", "MSRMT_VAL34", "MSRMT_VAL35", "MSRMT_VAL36", "MSRMT_VAL37", "MSRMT_VAL38", "MSRMT_VAL39", "MSRMT_VAL40", "MSRMT_VAL41", "MSRMT_VAL42", "MSRMT_VAL43", "MSRMT_VAL44", "MSRMT_VAL45", "MSRMT_VAL46", "MSRMT_VAL47", "MSRMT_VAL48", "MSRMT_VAL49", "MSRMT_VAL50", "MSRMT_VAL51", "MSRMT_VAL52", "MSRMT_VAL53", "MSRMT_VAL54", "MSRMT_VAL55", "MSRMT_VAL56", "MSRMT_VAL57", "MSRMT_VAL58", "MSRMT_VAL59", "MSRMT_VAL60", "MSRMT_VAL61", "MSRMT_VAL62", "MSRMT_VAL63", "MSRMT_VAL64", "MSRMT_VAL65", "MSRMT_VAL66", "MSRMT_VAL67", "MSRMT_VAL68", "MSRMT_VAL69", "MSRMT_VAL70", "MSRMT_VAL71", "MSRMT_VAL72", "MSRMT_VAL73", "MSRMT_VAL74", "MSRMT_VAL75", "MSRMT_VAL76", "MSRMT_VAL77", "MSRMT_VAL78", "MSRMT_VAL79", "MSRMT_VAL80", "MSRMT_VAL81", "MSRMT_VAL82", "MSRMT_VAL83", "MSRMT_VAL84", "MSRMT_VAL85", "MSRMT_VAL86", "MSRMT_VAL87", "MSRMT_VAL88", "MSRMT_VAL89", "MSRMT_VAL90", "MSRMT_VAL91", "MSRMT_VAL92", "MSRMT_VAL93", "MSRMT_VAL94", "MSRMT_VAL95", "MSRMT_VAL96", "MSRMT_VAL97", "MSRMT_VAL98", "MSRMT_VAL99", "MSRMT_VAL100") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  WITH INTS as (
    SELECT CONST.US_ID
    ,      CONST.MSRMT_DATA_SNAP_TYPE_CD
    ,      CONST.SEC_PER_INTRVL
    ,      CONST.US_TZ_NAME
    ,      CONST.SYS_STD_OFFSET
    ,      CONST.MSR_PEAK_QTY_FLG
    ,      CONST.CONS_EXT_TYPE_CD
    ,      EXT_TO_SI
    ,      SOURCE_ID_TYPE_CD
    ,      TARGET_ID_TYPE_CD
    ,      MSR.MSRMT_DTTM
    ,      MIN(MSR.MSRMT_COND_FLG) MSRMT_COND_FLG
    ,      to_date(to_char(from_tz(CAST(MSR.MSRMT_DTTM AS TIMESTAMP),CONST.SYS_STD_OFFSET)
       at time zone CONST.US_STD_OFFSET, 'YYYY-MM-DD HH24:MI:SS'), 'YYYY-MM-DD HH24:MI:SS')
       MSRMT_US_DTTM
    ,      MAX(decode(CONST.VALUE_ID_TYPE_FLG, 'D1V1', MSRMT_VAL1, 'D1V2', MSRMT_VAL2, 'D1V3', MSRMT_VAL3, 'D1V4', MSRMT_VAL4, 'D1V5', MSRMT_VAL5,
                         'D1V6', MSRMT_VAL6, 'D1V7', MSRMT_VAL7, 'D1V8', MSRMT_VAL8, 'D1V9', MSRMT_VAL9, 'D1V0', MSRMT_VAL10, MSRMT_VAL)
                        * (CONST.USE_PERCENT/100) * USE_MULT * UOM_CONV_MULT)
           MSRMT_VAL_MAX
    ,      SUM(decode(CONST.VALUE_ID_TYPE_FLG, 'D1V1', MSRMT_VAL1, 'D1V2', MSRMT_VAL2, 'D1V3', MSRMT_VAL3, 'D1V4', MSRMT_VAL4, 'D1V5', MSRMT_VAL5,
                     'D1V6', MSRMT_VAL6, 'D1V7', MSRMT_VAL7, 'D1V8', MSRMT_VAL8, 'D1V9', MSRMT_VAL9, 'D1V0', MSRMT_VAL10, MSRMT_VAL)
                     * (CONST.USE_PERCENT/100) * USE_MULT * UOM_CONV_MULT)
           MSRMT_VAL_SUM
    FROM   D1_EXT_US_INT_MDS_CONST_VW CONST
    INNER JOIN D1_MSRMT MSR on CONST.MEASR_COMP_ID = MSR.MEASR_COMP_ID AND MSR.MSRMT_DTTM > CAST(CONST.START_DTTM as DATE) AND MSR.MSRMT_DTTM <= CAST(CONST.END_DTTM as DATE)
    group by CONST.US_ID
    ,        CONST.MSRMT_DATA_SNAP_TYPE_CD
    ,        EXT_TO_SI
    ,        SOURCE_ID_TYPE_CD
    ,        TARGET_ID_TYPE_CD
    ,        CONST.SEC_PER_INTRVL
    ,        CONST.US_TZ_NAME
    ,        CONST.SYS_STD_OFFSET
    ,        CONST.MSR_PEAK_QTY_FLG
    ,        CONST.CONS_EXT_TYPE_CD
    ,        MSR.MSRMT_DTTM
    ,        to_date(to_char(from_tz(CAST(MSR.MSRMT_DTTM AS TIMESTAMP),CONST.SYS_STD_OFFSET)
       at time zone CONST.US_STD_OFFSET, 'YYYY-MM-DD HH24:MI:SS'), 'YYYY-MM-DD HH24:MI:SS')
)
, SNAPS as (
    SELECT INTS.MSRMT_DATA_SNAP_TYPE_CD
    ,      INTS.CONS_EXT_TYPE_CD
    ,      INTS.US_ID
    ,      INTS.EXT_TO_SI
    ,      INTS.SOURCE_ID_TYPE_CD
    ,      INTS.TARGET_ID_TYPE_CD
    ,      NULL D1_SP_ID
    ,      NULL MEASR_COMP_ID
    ,      NULL TRANS_ID
    ,      to_date(to_char(from_tz(CAST(ISM.D1_LOCAL_DT AS TIMESTAMP),INTS.US_TZ_NAME)
           at time zone INTS.SYS_STD_OFFSET, 'YYYY-MM-DD HH24:MI:SS'), 'YYYY-MM-DD HH24:MI:SS') START_DTTM
    ,      ISM.D1_LOCAL_DT D1_LOCAL_DT
    ,      ISM.INTERVALS_PER_DAY
    ,      COUNT(MSRMT_VAL_MAX) INT_FOUND
    ,      MIN(INTS.MSRMT_COND_FLG) MSRMT_COND_FLG
    ,      CURRENT_DATE LAST_UPD_DTTM
    ,      TRUNC(CURRENT_DATE) ILM_DT
    ,      'Y' ILM_ARCH_SW
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'1',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL1
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'2',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL2
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'3',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL3
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'4',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL4
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'5',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL5
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'6',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL6
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'7',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL7
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'8',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL8
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'9',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL9
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'10',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL10
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'11',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL11
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'12',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL12
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'13',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL13
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'14',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL14
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'15',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL15
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'16',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL16
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'17',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL17
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'18',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL18
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'19',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL19
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'20',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL20
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'21',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL21
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'22',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL22
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'23',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL23
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'24',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL24
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'25',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL25
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'26',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL26
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'27',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL27
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'28',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL28
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'29',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL29
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'30',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL30
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'31',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL31
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'32',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL32
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'33',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL33
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'34',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL34
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'35',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL35
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'36',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL36
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'37',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL37
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'38',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL38
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'39',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL39
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'40',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL40
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'41',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL41
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'42',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL42
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'43',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL43
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'44',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL44
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'45',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL45
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'46',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL46
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'47',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL47
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'48',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL48
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'49',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL49
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'50',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL50
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'51',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL51
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'52',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL52
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'53',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL53
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'54',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL54
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'55',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL55
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'56',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL56
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'57',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL57
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'58',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL58
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'59',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL59
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'60',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL60
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'61',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL61
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'62',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL62
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'63',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL63
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'64',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL64
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'65',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL65
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'66',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL66
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'67',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL67
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'68',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL68
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'69',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL69
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'70',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL70
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'71',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL71
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'72',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL72
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'73',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL73
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'74',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL74
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'75',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL75
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'76',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL76
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'77',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL77
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'78',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL78
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'79',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL79
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'80',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL80
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'81',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL81
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'82',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL82
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'83',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL83
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'84',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL84
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'85',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL85
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'86',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL86
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'87',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL87
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'88',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL88
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'89',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL89
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'90',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL90
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'91',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL91
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'92',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL92
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'93',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL93
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'94',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL94
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'95',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL95
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'96',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL96
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'97',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL97
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'98',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL98
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'99',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL99
    ,      sum(DECODE(ISM.INTERVAL_NUMBER,'100',DECODE(INTS.MSR_PEAK_QTY_FLG,'D1MP',INTS.MSRMT_VAL_MAX,INTS.MSRMT_VAL_SUM),null)) MSRMT_VAL100
    FROM   D1_INT_SNAP_MAP ISM
    INNER JOIN INTS on INTS.SEC_PER_INTRVL = ISM.SEC_PER_INTRVL AND INTS.MSRMT_US_DTTM = ISM.MSRMT_DTTM
    group by INTS.MSRMT_DATA_SNAP_TYPE_CD
    ,      INTS.CONS_EXT_TYPE_CD
    ,      INTS.US_ID
    ,      INTS.EXT_TO_SI
    ,      INTS.SOURCE_ID_TYPE_CD
    ,      INTS.TARGET_ID_TYPE_CD
    ,      to_date(to_char(from_tz(CAST(ISM.D1_LOCAL_DT AS TIMESTAMP),INTS.US_TZ_NAME)
           at time zone INTS.SYS_STD_OFFSET, 'YYYY-MM-DD HH24:MI:SS'), 'YYYY-MM-DD HH24:MI:SS')
    ,      ISM.D1_LOCAL_DT
    ,      ISM.INTERVALS_PER_DAY
    ,      TRUNC(CURRENT_DATE)
    ,      'Y'
) select CASE
            WHEN SNAPS.EXT_TO_SI = 'D1YS' AND SNAPS.SOURCE_ID_TYPE_CD <> 'D1US'
                THEN (SELECT max(TRGT.US_ID)
                      FROM   D1_US_IDENTIFIER SRC
                      INNER JOIN D1_US_IDENTIFIER TRGT
                        ON TRGT.ID_VALUE = SRC.ID_VALUE
                        AND TRGT.US_ID_TYPE_FLG = SNAPS.TARGET_ID_TYPE_CD
                        AND TRGT.US_ID <> SRC.US_ID
                      WHERE SRC.US_ID_TYPE_FLG = SNAPS.SOURCE_ID_TYPE_CD
                      AND   SRC.US_ID = SNAPS.US_ID
                      having count(*) = 1)
            WHEN SNAPS.EXT_TO_SI = 'D1YS' AND SNAPS.SOURCE_ID_TYPE_CD = 'D1US'
                THEN (SELECT max(TRGT.US_ID)
                      FROM  D1_US_IDENTIFIER TRGT
                     WHERE  TRGT.ID_VALUE = SNAPS.US_ID
                        AND TRGT.US_ID_TYPE_FLG = SNAPS.TARGET_ID_TYPE_CD
                        AND TRGT.US_ID <> SNAPS.US_ID
                     having count(*) = 1)
            ELSE null
     end SETT_US_ID
,    SNAPS."MSRMT_DATA_SNAP_TYPE_CD",SNAPS."CONS_EXT_TYPE_CD",SNAPS."US_ID",SNAPS."EXT_TO_SI",SNAPS."SOURCE_ID_TYPE_CD",SNAPS."TARGET_ID_TYPE_CD",SNAPS."D1_SP_ID",SNAPS."MEASR_COMP_ID",SNAPS."TRANS_ID",SNAPS."START_DTTM",SNAPS."D1_LOCAL_DT",SNAPS."INTERVALS_PER_DAY",SNAPS."INT_FOUND",SNAPS."MSRMT_COND_FLG",SNAPS."LAST_UPD_DTTM",SNAPS."ILM_DT",SNAPS."ILM_ARCH_SW",SNAPS."MSRMT_VAL1",SNAPS."MSRMT_VAL2",SNAPS."MSRMT_VAL3",SNAPS."MSRMT_VAL4",SNAPS."MSRMT_VAL5",SNAPS."MSRMT_VAL6",SNAPS."MSRMT_VAL7",SNAPS."MSRMT_VAL8",SNAPS."MSRMT_VAL9",SNAPS."MSRMT_VAL10",SNAPS."MSRMT_VAL11",SNAPS."MSRMT_VAL12",SNAPS."MSRMT_VAL13",SNAPS."MSRMT_VAL14",SNAPS."MSRMT_VAL15",SNAPS."MSRMT_VAL16",SNAPS."MSRMT_VAL17",SNAPS."MSRMT_VAL18",SNAPS."MSRMT_VAL19",SNAPS."MSRMT_VAL20",SNAPS."MSRMT_VAL21",SNAPS."MSRMT_VAL22",SNAPS."MSRMT_VAL23",SNAPS."MSRMT_VAL24",SNAPS."MSRMT_VAL25",SNAPS."MSRMT_VAL26",SNAPS."MSRMT_VAL27",SNAPS."MSRMT_VAL28",SNAPS."MSRMT_VAL29",SNAPS."MSRMT_VAL30",SNAPS."MSRMT_VAL31",SNAPS."MSRMT_VAL32",SNAPS."MSRMT_VAL33",SNAPS."MSRMT_VAL34",SNAPS."MSRMT_VAL35",SNAPS."MSRMT_VAL36",SNAPS."MSRMT_VAL37",SNAPS."MSRMT_VAL38",SNAPS."MSRMT_VAL39",SNAPS."MSRMT_VAL40",SNAPS."MSRMT_VAL41",SNAPS."MSRMT_VAL42",SNAPS."MSRMT_VAL43",SNAPS."MSRMT_VAL44",SNAPS."MSRMT_VAL45",SNAPS."MSRMT_VAL46",SNAPS."MSRMT_VAL47",SNAPS."MSRMT_VAL48",SNAPS."MSRMT_VAL49",SNAPS."MSRMT_VAL50",SNAPS."MSRMT_VAL51",SNAPS."MSRMT_VAL52",SNAPS."MSRMT_VAL53",SNAPS."MSRMT_VAL54",SNAPS."MSRMT_VAL55",SNAPS."MSRMT_VAL56",SNAPS."MSRMT_VAL57",SNAPS."MSRMT_VAL58",SNAPS."MSRMT_VAL59",SNAPS."MSRMT_VAL60",SNAPS."MSRMT_VAL61",SNAPS."MSRMT_VAL62",SNAPS."MSRMT_VAL63",SNAPS."MSRMT_VAL64",SNAPS."MSRMT_VAL65",SNAPS."MSRMT_VAL66",SNAPS."MSRMT_VAL67",SNAPS."MSRMT_VAL68",SNAPS."MSRMT_VAL69",SNAPS."MSRMT_VAL70",SNAPS."MSRMT_VAL71",SNAPS."MSRMT_VAL72",SNAPS."MSRMT_VAL73",SNAPS."MSRMT_VAL74",SNAPS."MSRMT_VAL75",SNAPS."MSRMT_VAL76",SNAPS."MSRMT_VAL77",SNAPS."MSRMT_VAL78",SNAPS."MSRMT_VAL79",SNAPS."MSRMT_VAL80",SNAPS."MSRMT_VAL81",SNAPS."MSRMT_VAL82",SNAPS."MSRMT_VAL83",SNAPS."MSRMT_VAL84",SNAPS."MSRMT_VAL85",SNAPS."MSRMT_VAL86",SNAPS."MSRMT_VAL87",SNAPS."MSRMT_VAL88",SNAPS."MSRMT_VAL89",SNAPS."MSRMT_VAL90",SNAPS."MSRMT_VAL91",SNAPS."MSRMT_VAL92",SNAPS."MSRMT_VAL93",SNAPS."MSRMT_VAL94",SNAPS."MSRMT_VAL95",SNAPS."MSRMT_VAL96",SNAPS."MSRMT_VAL97",SNAPS."MSRMT_VAL98",SNAPS."MSRMT_VAL99",SNAPS."MSRMT_VAL100"
from SNAPS;

-- ----- D1_EXT_US_SCLR_MDS_CONST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_EXT_US_SCLR_MDS_CONST_VW" ("US_ID", "MEASR_COMP_ID", "INSTALL_EVT_ID", "VALUE_ID_TYPE_FLG", "MSRMT_DATA_SNAP_TYPE_CD", "MSR_PEAK_QTY_FLG", "D1_UOM_CD", "D1_TOU_CD", "D1_SQI_CD", "CONS_EXT_TYPE_CD", "EXT_TO_SI", "SOURCE_ID_TYPE_CD", "TARGET_ID_TYPE_CD", "D1_USAGE_FLG", "MEASR_COMP_USAGE_FLG", "US_TZ_NAME", "US_STD_OFFSET", "SYS_STD_OFFSET", "USAGE_MULT", "START_DTTM", "END_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  WITH STD_OFFSET as (
 select case
        when diff > 0
          then to_char(to_date(abs(round(diff*24*60*60,0)),'sssss'),'HH24:MI')
        else   '-'||to_char(to_date(abs(round(diff*24*60*60,0)),'sssss'),'HH24:MI')
      end utc_offset
      , F1_TIMEZONE_NAME
      , TIME_ZONE_CD
from (select min(all_days.dt - to_date(to_char(from_tz(CAST(all_days.dt AS TIMESTAMP),tz.f1_timezone_name)
                                 at time zone 'UTC', 'YYYY-MM-DD HH24:MI:SS'), 'YYYY-MM-DD HH24:MI:SS')) diff
      , TZ.F1_TIMEZONE_NAME
      , TZ.TIME_ZONE_CD
      from (select trunc(CURRENT_DATE-rownum) dt
            from dual connect by rownum < 366) all_days
      ,     ci_time_zone tz
      where tz.F1_TIMEZONE_NAME <> ' '
      group by TZ.F1_TIMEZONE_NAME, TZ.TIME_ZONE_CD) minDiff
), MCTVI as (
    SELECT DISTINCT MCTVI.MEASR_COMP_TYPE_CD
    ,      MCTVI.VALUE_ID_TYPE_FLG
    ,      MCUOM.MSR_PEAK_QTY_FLG
    ,      CETST.MSRMT_DATA_SNAP_TYPE_CD
    ,      MCTVI.D1_UOM_CD
    ,      MCTVI.D1_TOU_CD
    ,      MCTVI.D1_SQI_CD
    FROM   D1_MC_TYPE_VALUE_IDENTIFIER MCTVI
    INNER JOIN D1_UOM MCUOM ON MCTVI.D1_UOM_CD = MCUOM.D1_UOM_CD
    INNER JOIN D1_MEASR_COMP_TYPE MCT ON MCT.MEASR_COMP_TYPE_CD = MCTVI.MEASR_COMP_TYPE_CD AND MCT.INTERVAL_SCALAR_FLG = 'D1SC'
    INNER JOIN D1_DVC_CFG_TYPE_MC_TYPE DCMC ON DCMC.MEASR_COMP_TYPE_CD = MCT.MEASR_COMP_TYPE_CD
    INNER JOIN D1_DVC_TYPE_CFG_TYPE DTCT ON DTCT.DEVICE_CONFIG_TYPE_CD = DCMC.DEVICE_CONFIG_TYPE_CD
    INNER JOIN D1_SP_TYPE_DEVICE_TYPE STDT ON STDT.DEVICE_TYPE_CD = DTCT.DEVICE_TYPE_CD
    INNER JOIN D1_US_TYPE_VAL_SP_TYPE UTST ON UTST.D1_SP_TYPE_CD = STDT.D1_SP_TYPE_CD
    INNER JOIN D1_CONS_EXT_TYPE_US_TYPE CETUT ON CETUT.US_TYPE_CD = UTST.US_TYPE_CD AND CETUT.D1_UOM_CD = MCTVI.D1_UOM_CD
AND
   (((CETUT.D1_TOU_CD IS NULL OR CETUT.D1_TOU_CD = ' ') AND (MCTVI.D1_TOU_CD IS NULL OR MCTVI.D1_TOU_CD = ' ')) OR CETUT.D1_TOU_CD = MCTVI.D1_TOU_CD) AND
   (((CETUT.D1_SQI_CD IS NULL OR CETUT.D1_SQI_CD = ' ') AND (MCTVI.D1_SQI_CD IS NULL OR MCTVI.D1_SQI_CD = ' ')) OR CETUT.D1_SQI_CD = MCTVI.D1_SQI_CD)
    INNER JOIN D1_CONS_EXT_TYPE_MDS_TYPE CETST ON CETST.CONS_EXT_TYPE_CD = CETUT.CONS_EXT_TYPE_CD
)
    SELECT US.US_ID
    ,      MC.MEASR_COMP_ID
    ,      IE.INSTALL_EVT_ID
    ,      MCTVI.VALUE_ID_TYPE_FLG
    ,      MCTVI.MSRMT_DATA_SNAP_TYPE_CD
    ,      MCTVI.MSR_PEAK_QTY_FLG
    ,      MCTVI.D1_UOM_CD
    ,      MCTVI.D1_TOU_CD
    ,      MCTVI.D1_SQI_CD
    ,      CETUT.CONS_EXT_TYPE_CD
    ,      extractvalue(XMLPARSE(CONTENT CET.BO_DATA_AREA),'extractToDifferentUsageSubscription') EXT_TO_SI
    ,      extractvalue(XMLPARSE(CONTENT CET.BO_DATA_AREA),'sourceIdentifierType') SOURCE_ID_TYPE_CD
    ,      extractvalue(XMLPARSE(CONTENT CET.BO_DATA_AREA),'targetIdentifierType') TARGET_ID_TYPE_CD
    ,      USSP.D1_USAGE_FLG
    ,      MC.MEASR_COMP_USAGE_FLG
    ,      CTZ.F1_TIMEZONE_NAME US_TZ_NAME
    ,      USOFFSET.UTC_OFFSET US_STD_OFFSET
    ,      INTZOFFSET.UTC_OFFSET SYS_STD_OFFSET
    , CASE
        WHEN (MC.MEASR_COMP_USAGE_FLG = 'P   ' OR MCTVI.MSR_PEAK_QTY_FLG = 'D1MP') AND USSP.D1_USAGE_FLG = 'D1ST'
            THEN -1 * (USE_PERCENT / 100)
        WHEN (MC.MEASR_COMP_USAGE_FLG <> 'P   ' AND MCTVI.MSR_PEAK_QTY_FLG <> 'D1MP') AND (DECODE(USSP.D1_USAGE_FLG,'D1AD','+   ','-   ') <> MC.MEASR_COMP_USAGE_FLG)
            THEN -1 * (USE_PERCENT / 100)
        ELSE 1 * (USE_PERCENT / 100)
      END USAGE_MULT
    , cast(from_tz(CAST(to_date(greatest(nvl(IE.D1_INSTALL_DTTM,date'1900-01-01')
        , nvl(US.START_DTTM,date'1900-01-01')
        , nvl(USSP.START_DTTM,date'1900-01-01'))) AS TIMESTAMP), INTZ.F1_TIMEZONE_NAME) AT TIME ZONE (INTZOFFSET.UTC_OFFSET) as date)
        START_DTTM
     , cast(from_tz(CAST(to_date(least(nvl(IE.D1_REMOVAL_DTTM,date'9999-01-01')
        , nvl(US.END_DTTM,date'9999-01-01')
        , nvl(USSP.D1_STOP_DTTM,date'9999-01-01')))AS TIMESTAMP), INTZ.F1_TIMEZONE_NAME ) AT TIME ZONE (INTZOFFSET.UTC_OFFSET) as date)
    END_DTTM
    FROM D1_US US
    INNER JOIN D1_US_SP USSP ON US.US_ID = USSP.US_ID AND USSP.D1_USAGE_FLG <> 'D1CK'
    INNER JOIN D1_INSTALL_EVT IE ON USSP.D1_SP_ID = IE.D1_SP_ID AND (USSP.D1_STOP_DTTM is null or IE.D1_INSTALL_DTTM < USSP.D1_STOP_DTTM) AND (IE.D1_REMOVAL_DTTM is null or IE.D1_REMOVAL_DTTM >= USSP.START_DTTM)
    INNER JOIN D1_DVC_CFG DC ON IE.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
    INNER JOIN D1_MEASR_COMP MC ON MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID AND MC.MEASR_COMP_USAGE_FLG <> 'C   '
    INNER JOIN F1_INSTALLATION INSTLL ON 1 = 1
    INNER JOIN CI_TIME_ZONE INTZ on INSTLL.TIME_ZONE_CD = INTZ.TIME_ZONE_CD
    INNER JOIN STD_OFFSET INTZOFFSET on INTZ.TIME_ZONE_CD = INTZOFFSET.TIME_ZONE_CD
    INNER JOIN CI_TIME_ZONE CTZ ON US.TIME_ZONE_CD = CTZ.TIME_ZONE_CD
    INNER JOIN STD_OFFSET USOFFSET on CTZ.TIME_ZONE_CD = USOFFSET.TIME_ZONE_CD
    INNER JOIN MCTVI on MC.MEASR_COMP_TYPE_CD = MCTVI.MEASR_COMP_TYPE_CD
    INNER JOIN D1_CONS_EXT_TYPE_US_TYPE CETUT on US.US_TYPE_CD = CETUT.US_TYPE_CD
    INNER JOIN D1_CONS_EXT_TYPE CET on CET.CONS_EXT_TYPE_CD = CETUT.CONS_EXT_TYPE_CD;

-- ----- D1_EXT_US_SCLR_MDS_MSRMTS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_EXT_US_SCLR_MDS_MSRMTS_VW" ("US_ID", "SI_US", "MC_ID", "E_SI", "SI_CD", "TI_CD", "P_DTTM", "M_DTTM", "MUSE_FLG", "MCOND_FLG", "MSRMT_VAL") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  select C.US_ID
	  ,CASE
          WHEN C.EXT_TO_SI = 'D1YS' AND C.SOURCE_ID_TYPE_CD <> 'D1US'
              THEN (SELECT max(TRGT.US_ID)
                    FROM   D1_US_IDENTIFIER SRC
                    INNER JOIN D1_US_IDENTIFIER TRGT
                      ON TRGT.ID_VALUE = SRC.ID_VALUE
                      AND TRGT.US_ID_TYPE_FLG = C.TARGET_ID_TYPE_CD
                      AND TRGT.US_ID <> SRC.US_ID
                    WHERE SRC.US_ID_TYPE_FLG = C.SOURCE_ID_TYPE_CD
                    AND   SRC.US_ID = C.US_ID
                    having count(*) = 1)
          WHEN C.EXT_TO_SI = 'D1YS' AND C.SOURCE_ID_TYPE_CD = 'D1US'
              THEN (SELECT max(TRGT.US_ID)
                    FROM  D1_US_IDENTIFIER TRGT
                   WHERE  TRGT.ID_VALUE = C.US_ID
                      AND TRGT.US_ID_TYPE_FLG = C.TARGET_ID_TYPE_CD
                      AND TRGT.US_ID <> C.US_ID
                   having count(*) = 1)
          ELSE null
     end SI_US
    ,C.MEASR_COMP_ID MC_ID
	,C.EXT_TO_SI E_SI
    ,C.SOURCE_ID_TYPE_CD SI_CD
    ,C.TARGET_ID_TYPE_CD TI_CD
    ,nvl(m.prev_msrmt_dttm,m.msrmt_dttm) P_DTTM
    ,m.msrmt_dttm M_DTTM
    ,m.MSRMT_USE_FLG MUSE_FLG
    ,m.MSRMT_COND_FLG MCOND_FLG
    , DECODE(C.VALUE_ID_TYPE_FLG,'1',m.MSRMT_VAL1,'2',m.MSRMT_VAL2,'3',m.MSRMT_VAL3,'4',m.MSRMT_VAL4
       ,'5',m.MSRMT_VAL5,'6',m.MSRMT_VAL6,'7',m.MSRMT_VAL7,'8',m.MSRMT_VAL8,'9',m.MSRMT_VAL9,'10'
       ,m.MSRMT_VAL10,m.MSRMT_VAL) * USAGE_MULT
       MSRMT_VAL
    from D1_EXT_US_SCLR_MDS_CONST_VW C
    INNER JOIN D1_MSRMT M on M.MEASR_COMP_ID = C.MEASR_COMP_ID
        AND M.MSRMT_DTTM > c.START_DTTM
        AND ( m.PREV_MSRMT_DTTM < c.END_DTTM or m.PREV_MSRMT_DTTM is null )
        AND m.MSRMT_DTTM in (
            SELECT MA.MSRMT_DTTM
            FROM D1_MSRMT MA
            WHERE MA.MEASR_COMP_ID = m.MEASR_COMP_ID
            AND MA.MSRMT_DTTM >= c.START_DTTM
            AND MA.MSRMT_DTTM <= c.END_DTTM
            AND MA.MSRMT_USE_FLG <> 'D101'
            UNION
            SELECT
            MIN(MB.MSRMT_DTTM)
            FROM D1_MSRMT MB
            WHERE MB.MEASR_COMP_ID = m.MEASR_COMP_ID
            AND MB.MSRMT_DTTM > c.END_DTTM
            AND MB.MSRMT_USE_FLG <> 'D101'
         );

-- ----- D1_INBOUND_COMM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_INBOUND_COMM_VW" ("D1_COMM_ID", "COMM_TYPE_CD", "CRE_DTTM", "D1_SP_ID", "ADDRESS", "CITY", "POSTAL", "ACCESS_GRP_CD", "DIVISION_CD", "NAME_VALUE_UPPER") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
	COMMIN.D1_COMM_ID AS D1_COMM_ID,
	COMMIN.COMM_TYPE_CD AS COMM_TYPE_CD,
	COMMIN.CRE_DTTM AS CRE_DTTM,
    SP.D1_SP_ID AS D1_SP_ID,
	SP.ADDRESS1_UPPER AS ADDRESS,
	SP.CITY_UPPER AS CITY,
	SP.POSTAL AS POSTAL,
	SP.ACCESS_GRP_CD AS ACCESS_GRP_CD,
	SP.DIVISION_CD AS DIVISION_CD,
    CNN.NAME_VALUE_UPPER AS NAME_VALUE_UPPER
FROM
	D1_COMM_IN COMMIN,
	D1_COMM_IN_REL_OBJ COMMOBJ,
	D1_SP SP,
	D1_SP_CONTACT SPC,
	D1_CONTACT CN,
	D1_CONTACT_NAME CNN
WHERE
	COMMOBJ.D1_COMM_ID = COMMIN.D1_COMM_ID
AND COMMOBJ.MAINT_OBJ_CD = 'D1-SP'
AND SP.D1_SP_ID = RTRIM(COMMOBJ.PK_VALUE1)
AND SPC.D1_SP_ID = SP.D1_SP_ID
AND SPC.SP_CNTCT_REL_FLG = 'D1MC'
AND CN.CONTACT_ID = SPC.CONTACT_ID
AND CNN.CONTACT_ID = CN.CONTACT_ID
AND CNN.D1_NAME_TYPE_FLG = 'D1PR'
UNION
SELECT
	COMMIN.D1_COMM_ID AS D1_COMM_ID,
	COMMIN.COMM_TYPE_CD AS COMM_TYPE_CD,
	COMMIN.CRE_DTTM AS CRE_DTTM,
    SP.D1_SP_ID AS D1_SP_ID,
	SP.ADDRESS1_UPPER AS ADDRESS,
	SP.CITY_UPPER AS CITY,
	SP.POSTAL AS POSTAL,
	SP.ACCESS_GRP_CD AS ACCESS_GRP_CD,
	SP.DIVISION_CD AS DIVISION_CD,
    CNN.NAME_VALUE_UPPER AS NAME_VALUE_UPPER
FROM
	D1_COMM_IN COMMIN,
	D1_COMM_IN_REL_OBJ COMMOBJ,
	D1_SP SP,
	D1_US_SP USSP,
	D1_US_CONTACT USC,
	D1_CONTACT CN,
	D1_CONTACT_NAME CNN
WHERE
	COMMOBJ.D1_COMM_ID = COMMIN.D1_COMM_ID
AND COMMOBJ.MAINT_OBJ_CD = 'D1-SP'
AND SP.D1_SP_ID = RTRIM(COMMOBJ.PK_VALUE1)
AND USSP.D1_SP_ID = SP.D1_SP_ID
AND USC.US_ID = USSP.US_ID
AND USC.US_CNTCT_REL_FLG = 'D1MC'
AND CN.CONTACT_ID = USC.CONTACT_ID
AND CNN.CONTACT_ID = CN.CONTACT_ID
AND CNN.D1_NAME_TYPE_FLG = 'D1PR'
UNION
SELECT
	COMMIN.D1_COMM_ID AS D1_COMM_ID,
	COMMIN.COMM_TYPE_CD AS COMM_TYPE_CD,
	COMMIN.CRE_DTTM AS CRE_DTTM,
    SP.D1_SP_ID AS D1_SP_ID,
	SP.ADDRESS1_UPPER AS ADDRESS,
	SP.CITY_UPPER AS CITY,
	SP.POSTAL AS POSTAL,
	SP.ACCESS_GRP_CD AS ACCESS_GRP_CD,
	SP.DIVISION_CD AS DIVISION_CD,
    ' ' as NAME_VALUE_UPPER
FROM
	D1_COMM_IN COMMIN,
	D1_COMM_IN_REL_OBJ COMMOBJ,
	D1_SP SP
WHERE
	COMMOBJ.D1_COMM_ID = COMMIN.D1_COMM_ID
AND COMMOBJ.MAINT_OBJ_CD = 'D1-SP'
AND SP.D1_SP_ID = RTRIM(COMMOBJ.PK_VALUE1)
AND NOT EXISTS (SELECT 'X' FROM D1_SP_CONTACT SPC WHERE SPC.D1_SP_ID = SP.D1_SP_ID)
AND NOT EXISTS (SELECT 'X' FROM D1_US_SP USSP WHERE USSP.D1_SP_ID = SP.D1_SP_ID)
UNION
SELECT
	COMMIN.D1_COMM_ID AS D1_COMM_ID,
	COMMIN.COMM_TYPE_CD AS COMM_TYPE_CD,
	COMMIN.CRE_DTTM AS CRE_DTTM,
    SP.D1_SP_ID AS D1_SP_ID,
	SP.ADDRESS1_UPPER AS ADDRESS,
	SP.CITY_UPPER AS CITY,
	SP.POSTAL AS POSTAL,
	SP.ACCESS_GRP_CD AS ACCESS_GRP_CD,
	SP.DIVISION_CD AS DIVISION_CD,
    CNN.NAME_VALUE_UPPER AS NAME_VALUE_UPPER
FROM
	D1_COMM_IN COMMIN,
	D1_COMM_IN_REL_OBJ COMMOBJ,
	D1_SP SP,
	D1_SP_CONTACT SPC,
	D1_CONTACT CN,
	D1_CONTACT_NAME CNN,
	D1_DVC DVC,
	D1_INSTALL_EVT IE,
	D1_DVC_CFG DC
WHERE
	COMMOBJ.D1_COMM_ID = COMMIN.D1_COMM_ID
AND COMMOBJ.MAINT_OBJ_CD = 'D1-DEVICE'
AND DVC.D1_DEVICE_ID = RTRIM(COMMOBJ.PK_VALUE1)
AND DC.D1_DEVICE_ID = DVC.D1_DEVICE_ID
AND SP.D1_SP_ID = IE.D1_SP_ID
AND DC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM <= CAST(CURRENT_TIMESTAMP AS DATE)
AND (IE.D1_REMOVAL_DTTM IS NULL OR IE.D1_REMOVAL_DTTM > CAST(CURRENT_TIMESTAMP AS DATE))
AND SPC.D1_SP_ID = SP.D1_SP_ID
AND SPC.SP_CNTCT_REL_FLG = 'D1MC'
AND CN.CONTACT_ID = SPC.CONTACT_ID
AND CNN.CONTACT_ID = CN.CONTACT_ID
AND CNN.D1_NAME_TYPE_FLG = 'D1PR'
UNION
SELECT
	COMMIN.D1_COMM_ID AS D1_COMM_ID,
	COMMIN.COMM_TYPE_CD AS COMM_TYPE_CD,
	COMMIN.CRE_DTTM AS CRE_DTTM,
    SP.D1_SP_ID AS D1_SP_ID,
	SP.ADDRESS1_UPPER AS ADDRESS,
	SP.CITY_UPPER AS CITY,
	SP.POSTAL AS POSTAL,
	SP.ACCESS_GRP_CD AS ACCESS_GRP_CD,
	SP.DIVISION_CD AS DIVISION_CD,
    CNN.NAME_VALUE_UPPER AS NAME_VALUE_UPPER
FROM
	D1_COMM_IN COMMIN,
	D1_COMM_IN_REL_OBJ COMMOBJ,
	D1_SP SP,
	D1_US_SP USSP,
	D1_US_CONTACT USC,
	D1_CONTACT CN,
	D1_CONTACT_NAME CNN,
	D1_DVC DVC,
	D1_INSTALL_EVT IE,
	D1_DVC_CFG DC
WHERE
	COMMOBJ.D1_COMM_ID = COMMIN.D1_COMM_ID
AND COMMOBJ.MAINT_OBJ_CD = 'D1-DEVICE'
AND DVC.D1_DEVICE_ID = RTRIM(COMMOBJ.PK_VALUE1)
AND DC.D1_DEVICE_ID = DVC.D1_DEVICE_ID
AND SP.D1_SP_ID = IE.D1_SP_ID
AND DC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM <= CAST(CURRENT_TIMESTAMP AS DATE)
AND (IE.D1_REMOVAL_DTTM IS NULL OR IE.D1_REMOVAL_DTTM > CAST(CURRENT_TIMESTAMP AS DATE))
AND USSP.D1_SP_ID = SP.D1_SP_ID
AND USC.US_ID = USSP.US_ID
AND USC.US_CNTCT_REL_FLG = 'D1MC'
AND CN.CONTACT_ID = USC.CONTACT_ID
AND CNN.CONTACT_ID = CN.CONTACT_ID
AND CNN.D1_NAME_TYPE_FLG = 'D1PR'
UNION
SELECT
	COMMIN.D1_COMM_ID AS D1_COMM_ID,
	COMMIN.COMM_TYPE_CD AS COMM_TYPE_CD,
	COMMIN.CRE_DTTM AS CRE_DTTM,
    SP.D1_SP_ID AS D1_SP_ID,
	SP.ADDRESS1_UPPER AS ADDRESS,
	SP.CITY_UPPER AS CITY,
	SP.POSTAL AS POSTAL,
	SP.ACCESS_GRP_CD AS ACCESS_GRP_CD,
	SP.DIVISION_CD AS DIVISION_CD,
    ' ' as NAME_VALUE_UPPER
FROM
	D1_COMM_IN COMMIN,
	D1_COMM_IN_REL_OBJ COMMOBJ,
	D1_DVC DVC,
	D1_SP SP,
	D1_INSTALL_EVT IE,
	D1_DVC_CFG DC
WHERE
	COMMOBJ.D1_COMM_ID = COMMIN.D1_COMM_ID
AND COMMOBJ.MAINT_OBJ_CD = 'D1-DEVICE'
AND DVC.D1_DEVICE_ID = RTRIM(COMMOBJ.PK_VALUE1)
AND DC.D1_DEVICE_ID = DVC.D1_DEVICE_ID
AND SP.D1_SP_ID = IE.D1_SP_ID
AND DC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM <= CAST(CURRENT_TIMESTAMP AS DATE)
AND (IE.D1_REMOVAL_DTTM IS NULL OR IE.D1_REMOVAL_DTTM > CAST(CURRENT_TIMESTAMP AS DATE))
AND NOT EXISTS (SELECT 'X' FROM D1_SP_CONTACT SPC WHERE SPC.D1_SP_ID = SP.D1_SP_ID)
AND NOT EXISTS (SELECT 'X' FROM D1_US_SP USSP WHERE USSP.D1_SP_ID = SP.D1_SP_ID);

-- ----- D1_INI_CONTACT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_INI_CONTACT_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
NT_XID_CD,
EXT_PK_VALUE1,
PK_VALUE1
FROM
F1_SYNC_REQ_IN
WHERE MAINT_OBJ_CD = 'D1-CONTACT'
              AND F1_COMPOSITE_SYNC_FLG = 'F1SS'
 
 
 
 
 ;

-- ----- D1_INI_DOE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_INI_DOE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,EXT_PK_VALUE1,PK_VALUE1 FROM F1_SYNC_REQ_IN WHERE MAINT_OBJ_CD = 'D1-DOPEVT' AND F1_COMPOSITE_SYNC_FLG = 'F1SS';

-- ----- D1_INI_DO_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_INI_DO_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,EXT_PK_VALUE1,PK_VALUE1 FROM F1_SYNC_REQ_IN WHERE MAINT_OBJ_CD = 'D1-DOP' AND F1_COMPOSITE_SYNC_FLG = 'F1SS';

-- ----- D1_INI_DVC_CFG_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_INI_DVC_CFG_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
NT_XID_CD,
EXT_PK_VALUE1,
PK_VALUE1
FROM
F1_SYNC_REQ_IN
WHERE MAINT_OBJ_CD = 'D1-DVCCONFIG'
       AND F1_COMPOSITE_SYNC_FLG = 'F1SS'
 
 
 
 
 ;

-- ----- D1_INI_DVC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_INI_DVC_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
NT_XID_CD,
EXT_PK_VALUE1,
PK_VALUE1
FROM
F1_SYNC_REQ_IN
WHERE MAINT_OBJ_CD = 'D1-DEVICE'
      AND F1_COMPOSITE_SYNC_FLG = 'F1SS'
 
 
 
 
 ;

-- ----- D1_INI_IE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_INI_IE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
NT_XID_CD,
EXT_PK_VALUE1,
PK_VALUE1
FROM
F1_SYNC_REQ_IN
WHERE MAINT_OBJ_CD = 'D1-INSTLEVT'
      AND F1_COMPOSITE_SYNC_FLG = 'F1SS'
 
 
 
 
 ;

-- ----- D1_INI_MC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_INI_MC_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
NT_XID_CD,
EXT_PK_VALUE1,
PK_VALUE1
FROM
F1_SYNC_REQ_IN
WHERE MAINT_OBJ_CD = 'D1-MEASRCOMP'
      AND F1_COMPOSITE_SYNC_FLG = 'F1SS'
 
 
 
 
 ;

-- ----- D1_INI_SP_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_INI_SP_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
NT_XID_CD,
EXT_PK_VALUE1,
PK_VALUE1
FROM
F1_SYNC_REQ_IN
WHERE MAINT_OBJ_CD = 'D1-SP'
      AND F1_COMPOSITE_SYNC_FLG = 'F1SS'
 
 
 
 
 ;

-- ----- D1_INI_US_MKT_PART_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_INI_US_MKT_PART_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
NT_XID_CD,
EXT_PK_VALUE1,
PK_VALUE1
FROM F1_SYNC_REQ_IN
WHERE MAINT_OBJ_CD = 'D1-USMKPT'
  AND F1_COMPOSITE_SYNC_FLG = 'F1SS';

-- ----- D1_INI_US_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_INI_US_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
NT_XID_CD,
EXT_PK_VALUE1,
PK_VALUE1
FROM
F1_SYNC_REQ_IN
WHERE MAINT_OBJ_CD = 'D1-US'
      AND F1_COMPOSITE_SYNC_FLG = 'F1SS'
 
 
 
 
 ;

-- ----- D1_MEASR_COMP_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_MEASR_COMP_VW" ("MEASR_COMP_ID", "D1_DEVICE_ID", "D1_SP_ID", "US_ID", "US_TYPE_CD", "D1_SP_TYPE_CD", "DEVICE_TYPE_CD", "D1_SPR_CD", "MEASR_COMP_TYPE_CD", "D1_UOM_CD", "ACCESS_GRP_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT MC.MEASR_COMP_ID,
    ' ' AS D1_DEVICE_ID   ,
    ' ' AS D1_SP_ID       ,
    ' ' AS US_ID          ,
    ' ' AS US_TYPE_CD     ,
    ' ' AS D1_SP_TYPE_CD  ,
    ' ' AS DEVICE_TYPE_CD ,
    ' ' AS D1_SPR_CD      ,
    MC.MEASR_COMP_TYPE_CD ,
    ' ' AS D1_UOM_CD      ,
    ' ' AS ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC
    WHERE MC.DEVICE_CONFIG_ID = ' '
  AND NOT EXISTS
    (SELECT 'X'
       FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
      WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
    AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
    )
    
    UNION SELECT MC.MEASR_COMP_ID,
    DC.D1_DEVICE_ID       ,
    ' ' AS D1_SP_ID       ,
    ' ' AS US_ID          ,
    ' ' AS US_TYPE_CD     ,
    ' ' AS D1_SP_TYPE_CD  ,
    DVC.DEVICE_TYPE_CD    ,
    DVC.D1_SPR_CD         ,
    MC.MEASR_COMP_TYPE_CD ,
    ' ' AS D1_UOM_CD      ,
    ' ' AS ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC,
    D1_DVC_CFG DC         ,
    D1_DVC DVC
    WHERE DC.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID        = DC.D1_DEVICE_ID
  AND DVC.D1_SPR_CD          <> ' '
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_INSTALL_EVT IE
      WHERE IE.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
    AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
    AND (IE.D1_REMOVAL_DTTM    IS NULL
    OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
    )
  AND NOT EXISTS
    (SELECT 'X'
       FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
      WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
    AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
    )
    
    UNION SELECT MC.MEASR_COMP_ID,
    DC.D1_DEVICE_ID       ,
    ' ' AS D1_SP_ID       ,
    ' ' AS US_ID          ,
    ' ' AS US_TYPE_CD     ,
    ' ' AS D1_SP_TYPE_CD  ,
    DVC.DEVICE_TYPE_CD    ,
    DT.D1_SPR_CD          ,
    MC.MEASR_COMP_TYPE_CD ,
    ' ' AS D1_UOM_CD      ,
    ' ' AS ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC,
    D1_DVC_CFG DC         ,
    D1_DVC DVC            ,
    D1_DVC_TYPE DT
    WHERE DC.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID        = DC.D1_DEVICE_ID
  AND DVC.D1_SPR_CD           = ' '
  AND DT.DEVICE_TYPE_CD       = DVC.DEVICE_TYPE_CD
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_INSTALL_EVT IE
      WHERE IE.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
    AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
    AND (IE.D1_REMOVAL_DTTM    IS NULL
    OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
    )
  AND NOT EXISTS
    (SELECT 'X'
       FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
      WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
    AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
    )
    
    UNION SELECT MC.MEASR_COMP_ID,
    DC.D1_DEVICE_ID       ,
    IE.D1_SP_ID           ,
    ' ' AS US_ID          ,
    ' ' AS US_TYPE_CD     ,
    SP.D1_SP_TYPE_CD      ,
    DVC.DEVICE_TYPE_CD    ,
    DVC.D1_SPR_CD         ,
    MC.MEASR_COMP_TYPE_CD ,
    ' ' AS D1_UOM_CD      ,
    SP.ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC,
    D1_DVC_CFG DC         ,
    D1_INSTALL_EVT IE     ,
    D1_SP SP              ,
    D1_DVC DVC
    WHERE DC.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID        = DC.D1_DEVICE_ID
  AND DVC.D1_SPR_CD          <> ' '
  AND IE.DEVICE_CONFIG_ID     = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM    IS NULL
  OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND SP.D1_SP_ID             = IE.D1_SP_ID
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_US_SP USSP,
      D1_US US
      WHERE USSP.D1_SP_ID   = IE.D1_SP_ID
    AND US.US_ID            = USSP.US_ID
    AND US.US_STAT_COND_FLG = 'D1AC'
    )
  AND NOT EXISTS
    (SELECT 'X'
       FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
      WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
    AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
    )
    
    UNION SELECT MC.MEASR_COMP_ID,
    DC.D1_DEVICE_ID       ,
    IE.D1_SP_ID           ,
    ' ' AS US_ID          ,
    ' ' AS US_TYPE_CD     ,
    SP.D1_SP_TYPE_CD      ,
    DVC.DEVICE_TYPE_CD    ,
    DT.D1_SPR_CD          ,
    MC.MEASR_COMP_TYPE_CD ,
    ' ' AS D1_UOM_CD      ,
    SP.ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC,
    D1_DVC_CFG DC         ,
    D1_INSTALL_EVT IE     ,
    D1_SP SP              ,
    D1_DVC DVC            ,
    D1_DVC_TYPE DT
    WHERE DC.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID        = DC.D1_DEVICE_ID
  AND DVC.D1_SPR_CD           = ' '
  AND DT.DEVICE_TYPE_CD       = DVC.DEVICE_TYPE_CD
  AND IE.DEVICE_CONFIG_ID     = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM    IS NULL
  OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND SP.D1_SP_ID             = IE.D1_SP_ID
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_US_SP USSP,
      D1_US US
      WHERE USSP.D1_SP_ID   = IE.D1_SP_ID
    AND US.US_ID            = USSP.US_ID
    AND US.US_STAT_COND_FLG = 'D1AC'
    )
  AND NOT EXISTS
    (SELECT 'X'
       FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
      WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
    AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
    )
    
    UNION SELECT MC.MEASR_COMP_ID,
    DC.D1_DEVICE_ID       ,
    IE.D1_SP_ID           ,
    USSP.US_ID            ,
    US.US_TYPE_CD         ,
    SP.D1_SP_TYPE_CD      ,
    DVC.DEVICE_TYPE_CD    ,
    DVC.D1_SPR_CD         ,
    MC.MEASR_COMP_TYPE_CD ,
    ' ' AS D1_UOM_CD      ,
    SP.ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC,
    D1_DVC_CFG DC         ,
    D1_INSTALL_EVT IE     ,
    D1_US_SP USSP         ,
    D1_US US              ,
    D1_SP SP              ,
    D1_DVC DVC
    WHERE DC.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID        = DC.D1_DEVICE_ID
  AND DVC.D1_SPR_CD          <> ' '
  AND IE.DEVICE_CONFIG_ID     = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM    IS NULL
  OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND USSP.D1_SP_ID           = IE.D1_SP_ID
  AND SP.D1_SP_ID             = USSP.D1_SP_ID
  AND US.US_ID                = USSP.US_ID
  AND US.US_STAT_COND_FLG     = 'D1AC'
  AND NOT EXISTS
    (SELECT 'X'
       FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
      WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
    AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
    )
    
    UNION SELECT MC.MEASR_COMP_ID,
    DC.D1_DEVICE_ID       ,
    IE.D1_SP_ID           ,
    USSP.US_ID            ,
    US.US_TYPE_CD         ,
    SP.D1_SP_TYPE_CD      ,
    DVC.DEVICE_TYPE_CD    ,
    DT.D1_SPR_CD          ,
    MC.MEASR_COMP_TYPE_CD ,
    ' ' AS D1_UOM_CD      ,
    SP.ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC,
    D1_DVC_CFG DC         ,
    D1_INSTALL_EVT IE     ,
    D1_US_SP USSP         ,
    D1_US US              ,
    D1_SP SP              ,
    D1_DVC DVC            ,
    D1_DVC_TYPE DT
    WHERE DC.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID        = DC.D1_DEVICE_ID
  AND DVC.D1_SPR_CD           = ' '
  AND DT.DEVICE_TYPE_CD       = DVC.DEVICE_TYPE_CD
  AND IE.DEVICE_CONFIG_ID     = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM    IS NULL
  OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND USSP.D1_SP_ID           = IE.D1_SP_ID
  AND SP.D1_SP_ID             = USSP.D1_SP_ID
  AND US.US_ID                = USSP.US_ID
  AND US.US_STAT_COND_FLG     = 'D1AC'
  AND NOT EXISTS
    (SELECT 'X'
       FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
      WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
    AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
    )
    
    UNION SELECT MC.MEASR_COMP_ID,
    ' ' AS D1_DEVICE_ID   ,
    ' ' AS D1_SP_ID       ,
    ' ' AS US_ID          ,
    ' ' AS US_TYPE_CD     ,
    ' ' AS D1_SP_TYPE_CD  ,
    ' ' AS DEVICE_TYPE_CD ,
    ' ' AS D1_SPR_CD      ,
    MC.MEASR_COMP_TYPE_CD ,
    VI.D1_UOM_CD          ,
    ' ' AS ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC,
    D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE MC.DEVICE_CONFIG_ID = ' '
  AND VI.MEASR_COMP_TYPE_CD   = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG    = 'D1MS'
    
    UNION SELECT MC.MEASR_COMP_ID,
    DC.D1_DEVICE_ID       ,
    ' ' AS D1_SP_ID       ,
    ' ' AS US_ID          ,
    ' ' AS US_TYPE_CD     ,
    ' ' AS D1_SP_TYPE_CD  ,
    DVC.DEVICE_TYPE_CD    ,
    DVC.D1_SPR_CD         ,
    MC.MEASR_COMP_TYPE_CD ,
    VI.D1_UOM_CD          ,
    ' ' AS ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC,
    D1_DVC_CFG DC         ,
    D1_DVC DVC            ,
    D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE DC.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID        = DC.D1_DEVICE_ID
  AND DVC.D1_SPR_CD          <> ' '
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_INSTALL_EVT IE
      WHERE IE.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
    AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
    AND (IE.D1_REMOVAL_DTTM    IS NULL
    OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
    )
  AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'
    
    UNION SELECT MC.MEASR_COMP_ID,
    DC.D1_DEVICE_ID       ,
    ' ' AS D1_SP_ID       ,
    ' ' AS US_ID          ,
    ' ' AS US_TYPE_CD     ,
    ' ' AS D1_SP_TYPE_CD  ,
    DVC.DEVICE_TYPE_CD    ,
    DT.D1_SPR_CD          ,
    MC.MEASR_COMP_TYPE_CD ,
    VI.D1_UOM_CD          ,
    ' ' AS ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC,
    D1_DVC_CFG DC         ,
    D1_DVC DVC            ,
    D1_DVC_TYPE DT        ,
    D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE DC.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID        = DC.D1_DEVICE_ID
  AND DVC.D1_SPR_CD           = ' '
  AND DT.DEVICE_TYPE_CD       = DVC.DEVICE_TYPE_CD
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_INSTALL_EVT IE
      WHERE IE.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
    AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
    AND (IE.D1_REMOVAL_DTTM    IS NULL
    OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
    )
  AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'
    
    UNION SELECT MC.MEASR_COMP_ID,
    DC.D1_DEVICE_ID       ,
    IE.D1_SP_ID           ,
    ' ' AS US_ID          ,
    ' ' AS US_TYPE_CD     ,
    SP.D1_SP_TYPE_CD      ,
    DVC.DEVICE_TYPE_CD    ,
    DVC.D1_SPR_CD         ,
    MC.MEASR_COMP_TYPE_CD ,
    VI.D1_UOM_CD          ,
    SP.ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC,
    D1_DVC_CFG DC         ,
    D1_INSTALL_EVT IE     ,
    D1_SP SP              ,
    D1_DVC DVC            ,
    D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE DC.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID        = DC.D1_DEVICE_ID
  AND DVC.D1_SPR_CD          <> ' '
  AND IE.DEVICE_CONFIG_ID     = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM    IS NULL
  OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND SP.D1_SP_ID             = IE.D1_SP_ID
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_US_SP USSP,
      D1_US US
      WHERE USSP.D1_SP_ID   = IE.D1_SP_ID
    AND US.US_ID            = USSP.US_ID
    AND US.US_STAT_COND_FLG = 'D1AC'
    )
  AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'
    
    UNION SELECT MC.MEASR_COMP_ID,
    DC.D1_DEVICE_ID       ,
    IE.D1_SP_ID           ,
    ' ' AS US_ID          ,
    ' ' AS US_TYPE_CD     ,
    SP.D1_SP_TYPE_CD      ,
    DVC.DEVICE_TYPE_CD    ,
    DT.D1_SPR_CD          ,
    MC.MEASR_COMP_TYPE_CD ,
    VI.D1_UOM_CD          ,
    SP.ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC,
    D1_DVC_CFG DC         ,
    D1_INSTALL_EVT IE     ,
    D1_SP SP              ,
    D1_DVC DVC            ,
    D1_DVC_TYPE DT        ,
    D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE DC.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID        = DC.D1_DEVICE_ID
  AND DVC.D1_SPR_CD           = ' '
  AND DT.DEVICE_TYPE_CD       = DVC.DEVICE_TYPE_CD
  AND IE.DEVICE_CONFIG_ID     = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM    IS NULL
  OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND SP.D1_SP_ID             = IE.D1_SP_ID
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_US_SP USSP,
      D1_US US
      WHERE USSP.D1_SP_ID   = IE.D1_SP_ID
    AND US.US_ID            = USSP.US_ID
    AND US.US_STAT_COND_FLG = 'D1AC'
    )
  AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'
    
    UNION SELECT MC.MEASR_COMP_ID,
    DC.D1_DEVICE_ID       ,
    IE.D1_SP_ID           ,
    USSP.US_ID            ,
    US.US_TYPE_CD         ,
    SP.D1_SP_TYPE_CD      ,
    DVC.DEVICE_TYPE_CD    ,
    DVC.D1_SPR_CD         ,
    MC.MEASR_COMP_TYPE_CD ,
    VI.D1_UOM_CD          ,
    SP.ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC,
    D1_DVC_CFG DC         ,
    D1_INSTALL_EVT IE     ,
    D1_US_SP USSP         ,
    D1_US US              ,
    D1_SP SP              ,
    D1_DVC DVC            ,
    D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE DC.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID        = DC.D1_DEVICE_ID
  AND DVC.D1_SPR_CD          <> ' '
  AND IE.DEVICE_CONFIG_ID     = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM    IS NULL
  OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND USSP.D1_SP_ID           = IE.D1_SP_ID
  AND SP.D1_SP_ID             = USSP.D1_SP_ID
  AND US.US_ID                = USSP.US_ID
  AND US.US_STAT_COND_FLG     = 'D1AC'
  AND VI.MEASR_COMP_TYPE_CD   = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG    = 'D1MS'
    
    UNION SELECT MC.MEASR_COMP_ID,
    DC.D1_DEVICE_ID       ,
    IE.D1_SP_ID           ,
    USSP.US_ID            ,
    US.US_TYPE_CD         ,
    SP.D1_SP_TYPE_CD      ,
    DVC.DEVICE_TYPE_CD    ,
    DT.D1_SPR_CD          ,
    MC.MEASR_COMP_TYPE_CD ,
    VI.D1_UOM_CD          ,
    SP.ACCESS_GRP_CD
     FROM D1_MEASR_COMP MC,
    D1_DVC_CFG DC         ,
    D1_INSTALL_EVT IE     ,
    D1_US_SP USSP         ,
    D1_US US              ,
    D1_SP SP              ,
    D1_DVC DVC            ,
    D1_DVC_TYPE DT        ,
    D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE DC.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID        = DC.D1_DEVICE_ID
  AND DVC.D1_SPR_CD           = ' '
  AND DT.DEVICE_TYPE_CD       = DVC.DEVICE_TYPE_CD
  AND IE.DEVICE_CONFIG_ID     = DC.DEVICE_CONFIG_ID
  AND IE.D1_INSTALL_DTTM     <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM    IS NULL
  OR IE.D1_REMOVAL_DTTM       > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND USSP.D1_SP_ID           = IE.D1_SP_ID
  AND SP.D1_SP_ID             = USSP.D1_SP_ID
  AND US.US_ID                = USSP.US_ID
  AND US.US_STAT_COND_FLG     = 'D1AC'
  AND VI.MEASR_COMP_TYPE_CD   = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG    = 'D1MS';

-- ----- D1_ON_CONTACT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_ON_CONTACT_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT 
CONTACT_ID_TYPE_FLG as NT_XID_CD,
ID_VALUE as EXT_PK_VALUE1,
CONTACT_ID as PK_VALUE1
FROM 
D1_CONTACT_IDENTIFIER
 
 
 
 
 ;

-- ----- D1_ON_DOE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_ON_DOE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "ADHOC_CHAR_VAL", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
CHAR_TYPE_CD AS NT_XID_CD,
SRCH_CHAR_VAL AS EXT_PK_VALUE1,
ADHOC_CHAR_VAL AS ADHOC_CHAR_VAL,
DYN_OPT_EVENT_ID AS PK_VALUE1
FROM D1_DYN_OPT_EVENT_CHAR;

-- ----- D1_ON_DO_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_ON_DO_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "ADHOC_CHAR_VAL", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
CHAR_TYPE_CD AS NT_XID_CD,
SRCH_CHAR_VAL AS EXT_PK_VALUE1,
ADHOC_CHAR_VAL AS ADHOC_CHAR_VAL,
DYN_OPT_ID AS PK_VALUE1
FROM D1_DYN_OPT_CHAR;

-- ----- D1_ON_DVC_CFG_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_ON_DVC_CFG_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "ADHOC_CHAR_VAL", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
char_type_cd AS nt_xid_cd,
srch_char_val AS ext_pk_value1,
adhoc_char_val as adhoc_char_val,
device_config_id AS pk_value1
FROM D1_DVC_CFG_CHAR;

-- ----- D1_ON_DVC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_ON_DVC_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT 
DVC_ID_TYPE_FLG as NT_XID_CD,
ID_VALUE as EXT_PK_VALUE1,
D1_DEVICE_ID as PK_VALUE1
FROM 
D1_DVC_IDENTIFIER
 
 
 
 
 ;

-- ----- D1_ON_IE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_ON_IE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "ADHOC_CHAR_VAL", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
char_type_cd AS nt_xid_cd,
srch_char_val AS ext_pk_value1,
adhoc_char_val as adhoc_char_val,
install_evt_id AS pk_value1
FROM D1_INSTALL_EVT_CHAR;

-- ----- D1_ON_MC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_ON_MC_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT 
MC_ID_TYPE_FLG as NT_XID_CD,
ID_VALUE as EXT_PK_VALUE1,
MEASR_COMP_ID as PK_VALUE1
FROM 
D1_MEASR_COMP_IDENTIFIER
 
 
 
 
 ;

-- ----- D1_ON_SP_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_ON_SP_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT 
SP_ID_TYPE_FLG as NT_XID_CD,
ID_VALUE as EXT_PK_VALUE1,
D1_SP_ID as PK_VALUE1
FROM 
D1_SP_IDENTIFIER
 
 
 
 
 ;

-- ----- D1_ON_US_MKT_PART_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_ON_US_MKT_PART_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
US_MP_ID_TYPE_FLG as NT_XID_CD,
ID_VALUE as EXT_PK_VALUE1,
US_MP_ID as PK_VALUE1
FROM D1_US_MKT_PART_IDENTIFIER;

-- ----- D1_ON_US_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_ON_US_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT 
US_ID_TYPE_FLG as NT_XID_CD,
ID_VALUE as EXT_PK_VALUE1,
US_ID as PK_VALUE1
FROM 
D1_US_IDENTIFIER
 
 
 
 
 ;

-- ----- D1_OUTBOUND_COMM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_OUTBOUND_COMM_VW" ("D1_COMM_ID", "COMM_TYPE_CD", "CRE_DTTM", "D1_SP_ID", "ADDRESS", "CITY", "POSTAL", "ACCESS_GRP_CD", "DIVISION_CD", "NAME_VALUE_UPPER") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
	COMMOUT.D1_COMM_ID AS D1_COMM_ID,
	COMMOUT.COMM_TYPE_CD AS COMM_TYPE_CD,
	COMMOUT.CRE_DTTM AS CRE_DTTM,
    SP.D1_SP_ID AS D1_SP_ID,
	SP.ADDRESS1_UPPER AS ADDRESS,
	SP.CITY_UPPER AS CITY,
	SP.POSTAL AS POSTAL,
	SP.ACCESS_GRP_CD AS ACCESS_GRP_CD,
	SP.DIVISION_CD AS DIVISION_CD,
    CNN.NAME_VALUE_UPPER AS NAME_VALUE_UPPER
FROM
	D1_COMM_OUT COMMOUT,
	D1_COMM_OUT_REL_OBJ COMMOBJ,
	D1_ACTIVITY_REL_OBJ ACTOBJ,
	D1_SP SP,
	D1_SP_CONTACT SPC,
	D1_CONTACT CN,
	D1_CONTACT_NAME CNN
WHERE
	COMMOBJ.D1_COMM_ID = COMMOUT.D1_COMM_ID
AND COMMOBJ.MAINT_OBJ_CD = 'D1-ACTIVITY'
AND ACTOBJ.D1_ACTIVITY_ID = RTRIM(COMMOBJ.PK_VALUE1)
AND ACTOBJ.MAINT_OBJ_CD = 'D1-SP'
AND SP.D1_SP_ID = RTRIM(ACTOBJ.PK_VALUE1)
AND SPC.D1_SP_ID = SP.D1_SP_ID
AND SPC.SP_CNTCT_REL_FLG = 'D1MC'
AND CN.CONTACT_ID = SPC.CONTACT_ID
AND CNN.CONTACT_ID = CN.CONTACT_ID
AND CNN.D1_NAME_TYPE_FLG = 'D1PR'
UNION
SELECT
	COMMOUT.D1_COMM_ID AS D1_COMM_ID,
	COMMOUT.COMM_TYPE_CD AS COMM_TYPE_CD,
	COMMOUT.CRE_DTTM AS CRE_DTTM,
    SP.D1_SP_ID AS D1_SP_ID,
	SP.ADDRESS1_UPPER AS ADDRESS,
	SP.CITY_UPPER AS CITY,
	SP.POSTAL AS POSTAL,
	SP.ACCESS_GRP_CD AS ACCESS_GRP_CD,
	SP.DIVISION_CD AS DIVISION_CD,
    CNN.NAME_VALUE_UPPER AS NAME_VALUE_UPPER
FROM
	D1_COMM_OUT COMMOUT,
	D1_COMM_OUT_REL_OBJ COMMOBJ,
	D1_ACTIVITY_REL_OBJ ACTOBJ,
	D1_SP SP,
	D1_US_SP USSP,
	D1_US_CONTACT USC,
	D1_CONTACT CN,
	D1_CONTACT_NAME CNN
WHERE
	COMMOBJ.D1_COMM_ID = COMMOUT.D1_COMM_ID
AND COMMOBJ.MAINT_OBJ_CD = 'D1-ACTIVITY'
AND ACTOBJ.D1_ACTIVITY_ID = RTRIM(COMMOBJ.PK_VALUE1)
AND ACTOBJ.MAINT_OBJ_CD = 'D1-SP'
AND SP.D1_SP_ID = RTRIM(ACTOBJ.PK_VALUE1)
AND USSP.D1_SP_ID = SP.D1_SP_ID
AND USC.US_ID = USSP.US_ID
AND USC.US_CNTCT_REL_FLG = 'D1MC'
AND CN.CONTACT_ID = USC.CONTACT_ID
AND CNN.CONTACT_ID = CN.CONTACT_ID
AND CNN.D1_NAME_TYPE_FLG = 'D1PR'
UNION
SELECT
	COMMOUT.D1_COMM_ID AS D1_COMM_ID,
	COMMOUT.COMM_TYPE_CD AS COMM_TYPE_CD,
	COMMOUT.CRE_DTTM AS CRE_DTTM,
    SP.D1_SP_ID AS D1_SP_ID,
	SP.ADDRESS1_UPPER AS ADDRESS,
	SP.CITY_UPPER AS CITY,
	SP.POSTAL AS POSTAL,
	SP.ACCESS_GRP_CD AS ACCESS_GRP_CD,
	SP.DIVISION_CD AS DIVISION_CD,
    ' ' AS NAME_VALUE_UPPER
FROM
	D1_COMM_OUT COMMOUT,
	D1_COMM_OUT_REL_OBJ COMMOBJ,
	D1_ACTIVITY_REL_OBJ ACTOBJ,
	D1_SP SP
WHERE
	COMMOBJ.D1_COMM_ID = COMMOUT.D1_COMM_ID
AND COMMOBJ.MAINT_OBJ_CD = 'D1-ACTIVITY'
AND ACTOBJ.D1_ACTIVITY_ID = RTRIM(COMMOBJ.PK_VALUE1)
AND ACTOBJ.MAINT_OBJ_CD = 'D1-SP'
AND SP.D1_SP_ID = RTRIM(ACTOBJ.PK_VALUE1)
AND NOT EXISTS (SELECT 'X' FROM D1_SP_CONTACT SPC WHERE SPC.D1_SP_ID = SP.D1_SP_ID)
AND NOT EXISTS (SELECT 'X' FROM D1_US_SP USSP WHERE USSP.D1_SP_ID = SP.D1_SP_ID)
UNION
SELECT
	COMMOUT.D1_COMM_ID AS D1_COMM_ID,
	COMMOUT.COMM_TYPE_CD AS COMM_TYPE_CD,
	COMMOUT.CRE_DTTM AS CRE_DTTM,
    SP.D1_SP_ID AS D1_SP_ID,
	SP.ADDRESS1_UPPER AS ADDRESS,
	SP.CITY_UPPER AS CITY,
	SP.POSTAL AS POSTAL,
	SP.ACCESS_GRP_CD AS ACCESS_GRP_CD,
	SP.DIVISION_CD AS DIVISION_CD,
    CNN.NAME_VALUE_UPPER AS NAME_VALUE_UPPER
FROM
	D1_COMM_OUT COMMOUT,
	D1_COMM_OUT_REL_OBJ COMMOBJ,
	D1_SP SP,
	D1_SP_CONTACT SPC,
	D1_CONTACT CN,
	D1_CONTACT_NAME CNN,
	D1_DVC DVC,
	D1_INSTALL_EVT IE,
	D1_DVC_CFG DC
WHERE
	COMMOBJ.D1_COMM_ID = COMMOUT.D1_COMM_ID
AND COMMOBJ.MAINT_OBJ_CD = 'D1-DEVICE'
AND DVC.D1_DEVICE_ID = RTRIM(COMMOBJ.PK_VALUE1)
AND DC.D1_DEVICE_ID = DVC.D1_DEVICE_ID
AND SP.D1_SP_ID = IE.D1_SP_ID
AND DC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM <= CAST(CURRENT_TIMESTAMP AS DATE)
AND (IE.D1_REMOVAL_DTTM IS NULL OR IE.D1_REMOVAL_DTTM > CAST(CURRENT_TIMESTAMP AS DATE))
AND SPC.D1_SP_ID = SP.D1_SP_ID
AND SPC.SP_CNTCT_REL_FLG = 'D1MC'
AND CN.CONTACT_ID = SPC.CONTACT_ID
AND CNN.CONTACT_ID = CN.CONTACT_ID
AND CNN.D1_NAME_TYPE_FLG = 'D1PR'
UNION
SELECT
	COMMOUT.D1_COMM_ID AS D1_COMM_ID,
	COMMOUT.COMM_TYPE_CD AS COMM_TYPE_CD,
	COMMOUT.CRE_DTTM AS CRE_DTTM,
    SP.D1_SP_ID AS D1_SP_ID,
	SP.ADDRESS1_UPPER AS ADDRESS,
	SP.CITY_UPPER AS CITY,
	SP.POSTAL AS POSTAL,
	SP.ACCESS_GRP_CD AS ACCESS_GRP_CD,
	SP.DIVISION_CD AS DIVISION_CD,
    CNN.NAME_VALUE_UPPER AS NAME_VALUE_UPPER
FROM
	D1_COMM_OUT COMMOUT,
	D1_COMM_OUT_REL_OBJ COMMOBJ,
	D1_SP SP,
	D1_US_SP USSP,
	D1_US_CONTACT USC,
	D1_CONTACT CN,
	D1_CONTACT_NAME CNN,
	D1_DVC DVC,
	D1_INSTALL_EVT IE,
	D1_DVC_CFG DC
WHERE
	COMMOBJ.D1_COMM_ID = COMMOUT.D1_COMM_ID
AND COMMOBJ.MAINT_OBJ_CD = 'D1-DEVICE'
AND DVC.D1_DEVICE_ID = RTRIM(COMMOBJ.PK_VALUE1)
AND DC.D1_DEVICE_ID = DVC.D1_DEVICE_ID
AND SP.D1_SP_ID = IE.D1_SP_ID
AND DC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM <= CAST(CURRENT_TIMESTAMP AS DATE)
AND (IE.D1_REMOVAL_DTTM IS NULL OR IE.D1_REMOVAL_DTTM > CAST(CURRENT_TIMESTAMP AS DATE))
AND USSP.D1_SP_ID = SP.D1_SP_ID
AND USC.US_ID = USSP.US_ID
AND USC.US_CNTCT_REL_FLG = 'D1MC'
AND CN.CONTACT_ID = USC.CONTACT_ID
AND CNN.CONTACT_ID = CN.CONTACT_ID
AND CNN.D1_NAME_TYPE_FLG = 'D1PR'
UNION
SELECT
	COMMOUT.D1_COMM_ID AS D1_COMM_ID,
	COMMOUT.COMM_TYPE_CD AS COMM_TYPE_CD,
	COMMOUT.CRE_DTTM AS CRE_DTTM,
    SP.D1_SP_ID AS D1_SP_ID,
	SP.ADDRESS1_UPPER AS ADDRESS,
	SP.CITY_UPPER AS CITY,
	SP.POSTAL AS POSTAL,
	SP.ACCESS_GRP_CD AS ACCESS_GRP_CD,
	SP.DIVISION_CD AS DIVISION_CD,
    ' ' AS NAME_VALUE_UPPER
FROM
	D1_COMM_OUT COMMOUT,
	D1_COMM_OUT_REL_OBJ COMMOBJ,
	D1_DVC DVC,
	D1_SP SP,
	D1_INSTALL_EVT IE,
	D1_DVC_CFG DC
WHERE
	COMMOBJ.D1_COMM_ID = COMMOUT.D1_COMM_ID
AND COMMOBJ.MAINT_OBJ_CD = 'D1-DEVICE'
AND DVC.D1_DEVICE_ID = RTRIM(COMMOBJ.PK_VALUE1)
AND DC.D1_DEVICE_ID = DVC.D1_DEVICE_ID
AND SP.D1_SP_ID = IE.D1_SP_ID
AND DC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
AND IE.D1_INSTALL_DTTM <= CAST(CURRENT_TIMESTAMP AS DATE)
AND (IE.D1_REMOVAL_DTTM IS NULL OR IE.D1_REMOVAL_DTTM > CAST(CURRENT_TIMESTAMP AS DATE))
AND NOT EXISTS (SELECT 'X' FROM D1_SP_CONTACT SPC WHERE SPC.D1_SP_ID = SP.D1_SP_ID)
AND NOT EXISTS (SELECT 'X' FROM D1_US_SP USSP WHERE USSP.D1_SP_ID = SP.D1_SP_ID);

-- ----- D1_SP_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_SP_VW" ("D1_SP_ID", "US_ID", "D1_DEVICE_ID", "MEASR_COMP_ID", "D1_SP_TYPE_CD", "US_TYPE_CD", "DEVICE_TYPE_CD", "D1_SPR_CD", "MEASR_COMP_TYPE_CD", "D1_UOM_CD", "ACCESS_GRP_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT SP.D1_SP_ID        ,
    ' ' AS US_ID             ,
    ' ' AS D1_DEVICE_ID      ,
    ' ' AS MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD         ,
    ' ' AS US_TYPE_CD        ,
    ' ' AS DEVICE_TYPE_CD    ,
    ' ' AS D1_SPR_CD         ,
    ' ' AS MEASR_COMP_TYPE_CD,
    ' ' AS D1_UOM_CD         ,
    SP.ACCESS_GRP_CD
     FROM D1_SP SP
    WHERE NOT EXISTS
    (SELECT 'x'
       FROM D1_US_SP USSP,
      D1_US US
      WHERE USSP.D1_SP_ID   = SP.D1_SP_ID
    AND US.US_ID            = USSP.US_ID
    AND US.US_STAT_COND_FLG = 'D1AC'
    )
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_INSTALL_EVT IE
      WHERE IE.D1_SP_ID      = SP.D1_SP_ID
    AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
    AND (IE.D1_REMOVAL_DTTM IS NULL
    OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
    )
    
    UNION
   
   SELECT USSP.D1_SP_ID      ,
    USSP.US_ID               ,
    ' ' AS D1_DEVICE_ID      ,
    ' ' AS MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD         ,
    US.US_TYPE_CD            ,
    ' ' AS DEVICE_TYPE_CD    ,
    ' ' AS D1_SPR_CD         ,
    ' ' AS MEASR_COMP_TYPE_CD,
    ' ' AS D1_UOM_CD         ,
    SP.ACCESS_GRP_CD
     FROM D1_US_SP USSP,
    D1_US US           ,
    D1_SP SP
    WHERE US.US_ID        = USSP.US_ID
  AND US.US_STAT_COND_FLG = 'D1AC'
  AND SP.D1_SP_ID         = USSP.D1_SP_ID
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_INSTALL_EVT IE
      WHERE IE.D1_SP_ID      = USSP.D1_SP_ID
    AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
    AND (IE.D1_REMOVAL_DTTM IS NULL
    OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
    )
    
    UNION
   
   SELECT USSP.D1_SP_ID      ,
    USSP.US_ID               ,
    D.D1_DEVICE_ID           ,
    ' ' AS MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD         ,
    US.US_TYPE_CD            ,
    DVC.DEVICE_TYPE_CD       ,
    DVC.D1_SPR_CD            ,
    ' ' AS MEASR_COMP_TYPE_CD,
    ' ' AS D1_UOM_CD         ,
    SP.ACCESS_GRP_CD
     FROM D1_US_SP USSP,
    D1_INSTALL_EVT IE  ,
    D1_DVC_CFG D       ,
    D1_US US           ,
    D1_DVC DVC         ,
    D1_SP SP
    WHERE US.US_ID         = USSP.US_ID
  AND US.US_STAT_COND_FLG  = 'D1AC'
  AND SP.D1_SP_ID          = USSP.D1_SP_ID
  AND IE.D1_SP_ID          = USSP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM IS NULL
  OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
  AND DVC.D1_SPR_CD       <> ' '
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_MEASR_COMP MC
      WHERE MC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
    )
    
    UNION
   
   SELECT USSP.D1_SP_ID      ,
    USSP.US_ID               ,
    D.D1_DEVICE_ID           ,
    ' ' AS MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD         ,
    US.US_TYPE_CD            ,
    DVC.DEVICE_TYPE_CD       ,
    DT.D1_SPR_CD             ,
    ' ' AS MEASR_COMP_TYPE_CD,
    ' ' AS D1_UOM_CD         ,
    SP.ACCESS_GRP_CD
     FROM D1_US_SP USSP,
    D1_INSTALL_EVT IE  ,
    D1_DVC_CFG D       ,
    D1_US US           ,
    D1_DVC DVC         ,
    D1_SP SP           ,
    D1_DVC_TYPE DT
    WHERE US.US_ID         = USSP.US_ID
  AND US.US_STAT_COND_FLG  = 'D1AC'
  AND SP.D1_SP_ID          = USSP.D1_SP_ID
  AND IE.D1_SP_ID          = USSP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM IS NULL
  OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
  AND DVC.D1_SPR_CD        = ' '
  AND DT.DEVICE_TYPE_CD    = DVC.DEVICE_TYPE_CD
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_MEASR_COMP MC
      WHERE MC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
    )
    
    UNION
   
   SELECT USSP.D1_SP_ID  ,
    USSP.US_ID           ,
    D.D1_DEVICE_ID       ,
    MC.MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD     ,
    US.US_TYPE_CD        ,
    DVC.DEVICE_TYPE_CD   ,
    DVC.D1_SPR_CD        ,
    MC.MEASR_COMP_TYPE_CD,
    ' ' AS D1_D1_UOM_CD  ,
    SP.ACCESS_GRP_CD
     FROM D1_US_SP USSP,
    D1_INSTALL_EVT IE  ,
    D1_DVC_CFG D       ,
    D1_MEASR_COMP MC   ,
    D1_US US           ,
    D1_DVC DVC         ,
    D1_SP SP
    WHERE US.US_ID         = USSP.US_ID
  AND US.US_STAT_COND_FLG  = 'D1AC'
  AND SP.D1_SP_ID          = USSP.D1_SP_ID
  AND IE.D1_SP_ID          = USSP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM IS NULL
  OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
  AND DVC.D1_SPR_CD       <> ' '
  AND MC.DEVICE_CONFIG_ID  = IE.DEVICE_CONFIG_ID
  AND NOT EXISTS
    (SELECT 'X'
       FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
      WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
    AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
    )
    
    UNION
   
   SELECT USSP.D1_SP_ID  ,
    USSP.US_ID           ,
    D.D1_DEVICE_ID       ,
    MC.MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD     ,
    US.US_TYPE_CD        ,
    DVC.DEVICE_TYPE_CD   ,
    DVC.D1_SPR_CD        ,
    MC.MEASR_COMP_TYPE_CD,
    VI.D1_UOM_CD         ,
    SP.ACCESS_GRP_CD
     FROM D1_US_SP USSP,
    D1_INSTALL_EVT IE  ,
    D1_DVC_CFG D       ,
    D1_MEASR_COMP MC   ,
    D1_US US           ,
    D1_DVC DVC         ,
    D1_SP SP           ,
    D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE US.US_ID          = USSP.US_ID
  AND US.US_STAT_COND_FLG   = 'D1AC'
  AND SP.D1_SP_ID           = USSP.D1_SP_ID
  AND IE.D1_SP_ID           = USSP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM   <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM  IS NULL
  OR IE.D1_REMOVAL_DTTM     > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND D.DEVICE_CONFIG_ID    = IE.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID      = D.D1_DEVICE_ID
  AND DVC.D1_SPR_CD        <> ' '
  AND MC.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
  AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'
    
    UNION
   
   SELECT USSP.D1_SP_ID  ,
    USSP.US_ID           ,
    D.D1_DEVICE_ID       ,
    MC.MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD     ,
    US.US_TYPE_CD        ,
    DVC.DEVICE_TYPE_CD   ,
    DT.D1_SPR_CD         ,
    MC.MEASR_COMP_TYPE_CD,
    ' ' AS D1_UOM_CD     ,
    SP.ACCESS_GRP_CD
     FROM D1_US_SP USSP,
    D1_INSTALL_EVT IE  ,
    D1_DVC_CFG D       ,
    D1_MEASR_COMP MC   ,
    D1_US US           ,
    D1_DVC DVC         ,
    D1_SP SP           ,
    D1_DVC_TYPE DT
    WHERE US.US_ID         = USSP.US_ID
  AND US.US_STAT_COND_FLG  = 'D1AC'
  AND SP.D1_SP_ID          = USSP.D1_SP_ID
  AND IE.D1_SP_ID          = USSP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM IS NULL
  OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
  AND DVC.D1_SPR_CD        = ' '
  AND DT.DEVICE_TYPE_CD    = DVC.DEVICE_TYPE_CD
  AND MC.DEVICE_CONFIG_ID  = IE.DEVICE_CONFIG_ID
  AND NOT EXISTS
    (SELECT 'X'
       FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
      WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
    AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
    )
    
    UNION
   
   SELECT USSP.D1_SP_ID  ,
    USSP.US_ID           ,
    D.D1_DEVICE_ID       ,
    MC.MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD     ,
    US.US_TYPE_CD        ,
    DVC.DEVICE_TYPE_CD   ,
    DT.D1_SPR_CD         ,
    MC.MEASR_COMP_TYPE_CD,
    VI.D1_UOM_CD         ,
    SP.ACCESS_GRP_CD
     FROM D1_US_SP USSP,
    D1_INSTALL_EVT IE  ,
    D1_DVC_CFG D       ,
    D1_MEASR_COMP MC   ,
    D1_US US           ,
    D1_DVC DVC         ,
    D1_SP SP           ,
    D1_DVC_TYPE DT     ,
    D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE US.US_ID          = USSP.US_ID
  AND US.US_STAT_COND_FLG   = 'D1AC'
  AND SP.D1_SP_ID           = USSP.D1_SP_ID
  AND IE.D1_SP_ID           = USSP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM   <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM  IS NULL
  OR IE.D1_REMOVAL_DTTM     > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND D.DEVICE_CONFIG_ID    = IE.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID      = D.D1_DEVICE_ID
  AND DVC.D1_SPR_CD         = ' '
  AND DT.DEVICE_TYPE_CD     = DVC.DEVICE_TYPE_CD
  AND MC.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
  AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'
    
    UNION
   
   SELECT SP.D1_SP_ID        ,
    ' ' AS US_ID             ,
    D.D1_DEVICE_ID           ,
    ' ' AS MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD         ,
    ' ' AS US_TYPE_CD        ,
    DVC.DEVICE_TYPE_CD       ,
    DVC.D1_SPR_CD            ,
    ' ' AS MEASR_COMP_TYPE_CD,
    ' ' AS D1_UOM_CD         ,
    SP.ACCESS_GRP_CD
     FROM D1_SP SP   ,
    D1_INSTALL_EVT IE,
    D1_DVC_CFG D     ,
    D1_DVC DVC
    WHERE IE.D1_SP_ID      = SP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM IS NULL
  OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
  AND DVC.D1_SPR_CD       <> ' '
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_MEASR_COMP MC
      WHERE MC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
    )
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_US_SP USSP,
      D1_US US
      WHERE USSP.D1_SP_ID   = SP.D1_SP_ID
    AND US.US_ID            = USSP.US_ID
    AND US.US_STAT_COND_FLG = 'D1AC'
    )
    
    UNION
   
   SELECT SP.D1_SP_ID        ,
    ' ' AS US_ID             ,
    D.D1_DEVICE_ID           ,
    ' ' AS MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD         ,
    ' ' AS US_TYPE_CD        ,
    DVC.DEVICE_TYPE_CD       ,
    DT.D1_SPR_CD             ,
    ' ' AS MEASR_COMP_TYPE_CD,
    ' ' AS D1_UOM_CD         ,
    SP.ACCESS_GRP_CD
     FROM D1_SP SP   ,
    D1_INSTALL_EVT IE,
    D1_DVC_CFG D     ,
    D1_DVC DVC       ,
    D1_DVC_TYPE DT
    WHERE IE.D1_SP_ID      = SP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM IS NULL
  OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
  AND DVC.D1_SPR_CD        = ' '
  AND DT.DEVICE_TYPE_CD    = DVC.DEVICE_TYPE_CD
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_MEASR_COMP MC
      WHERE MC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
    )
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_US_SP USSP,
      D1_US US
      WHERE USSP.D1_SP_ID   = SP.D1_SP_ID
    AND US.US_ID            = USSP.US_ID
    AND US.US_STAT_COND_FLG = 'D1AC'
    )
    
    UNION
   
   SELECT SP.D1_SP_ID    ,
    ' ' AS US_ID         ,
    D.D1_DEVICE_ID       ,
    MC.MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD     ,
    ' ' AS US_TYPE_CD    ,
    DVC.DEVICE_TYPE_CD   ,
    DVC.D1_SPR_CD        ,
    MC.MEASR_COMP_TYPE_CD,
    ' ' AS D1_UOM_CD     ,
    SP.ACCESS_GRP_CD
     FROM D1_SP SP   ,
    D1_INSTALL_EVT IE,
    D1_DVC_CFG D     ,
    D1_MEASR_COMP MC ,
    D1_DVC DVC
    WHERE IE.D1_SP_ID      = SP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM IS NULL
  OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
  AND MC.DEVICE_CONFIG_ID  = IE.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
  AND DVC.D1_SPR_CD       <> ' '
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_US_SP USSP,
      D1_US US
      WHERE USSP.D1_SP_ID   = SP.D1_SP_ID
    AND US.US_ID            = USSP.US_ID
    AND US.US_STAT_COND_FLG = 'D1AC'
    )
  AND NOT EXISTS
    (SELECT 'X'
       FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
      WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
    AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
    )
    
    UNION
   
   SELECT SP.D1_SP_ID    ,
    ' ' AS US_ID         ,
    D.D1_DEVICE_ID       ,
    MC.MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD     ,
    ' ' AS US_TYPE_CD    ,
    DVC.DEVICE_TYPE_CD   ,
    DVC.D1_SPR_CD        ,
    MC.MEASR_COMP_TYPE_CD,
    VI.D1_UOM_CD         ,
    SP.ACCESS_GRP_CD
     FROM D1_SP SP   ,
    D1_INSTALL_EVT IE,
    D1_DVC_CFG D     ,
    D1_MEASR_COMP MC ,
    D1_DVC DVC       ,
    D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE IE.D1_SP_ID       = SP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM   <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM  IS NULL
  OR IE.D1_REMOVAL_DTTM     > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND D.DEVICE_CONFIG_ID    = IE.DEVICE_CONFIG_ID
  AND MC.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID      = D.D1_DEVICE_ID
  AND DVC.D1_SPR_CD        <> ' '
  AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_US_SP USSP,
      D1_US US
      WHERE USSP.D1_SP_ID   = SP.D1_SP_ID
    AND US.US_ID            = USSP.US_ID
    AND US.US_STAT_COND_FLG = 'D1AC'
    )
    
    UNION
   
   SELECT SP.D1_SP_ID    ,
    ' ' AS US_ID         ,
    D.D1_DEVICE_ID       ,
    MC.MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD     ,
    ' ' AS US_TYPE_CD    ,
    DVC.DEVICE_TYPE_CD   ,
    DT.D1_SPR_CD         ,
    MC.MEASR_COMP_TYPE_CD,
    ' ' AS D1_UOM_CD     ,
    SP.ACCESS_GRP_CD
     FROM D1_SP SP   ,
    D1_INSTALL_EVT IE,
    D1_DVC_CFG D     ,
    D1_MEASR_COMP MC ,
    D1_DVC DVC       ,
    D1_DVC_TYPE DT
    WHERE IE.D1_SP_ID      = SP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM IS NULL
  OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
  AND MC.DEVICE_CONFIG_ID  = IE.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
  AND DVC.D1_SPR_CD        = ' '
  AND DT.DEVICE_TYPE_CD    = DVC.DEVICE_TYPE_CD
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_US_SP USSP,
      D1_US US
      WHERE USSP.D1_SP_ID   = SP.D1_SP_ID
    AND US.US_ID            = USSP.US_ID
    AND US.US_STAT_COND_FLG = 'D1AC'
    )
  AND NOT EXISTS
    (SELECT 'X'
       FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
      WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
    AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
    )
    
    UNION
   
   SELECT SP.D1_SP_ID    ,
    ' ' AS US_ID         ,
    D.D1_DEVICE_ID       ,
    MC.MEASR_COMP_ID     ,
    SP.D1_SP_TYPE_CD     ,
    ' ' AS US_TYPE_CD    ,
    DVC.DEVICE_TYPE_CD   ,
    DT.D1_SPR_CD         ,
    MC.MEASR_COMP_TYPE_CD,
    VI.D1_UOM_CD         ,
    SP.ACCESS_GRP_CD
     FROM D1_SP SP   ,
    D1_INSTALL_EVT IE,
    D1_DVC_CFG D     ,
    D1_MEASR_COMP MC ,
    D1_DVC DVC       ,
    D1_DVC_TYPE DT   ,
    D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE IE.D1_SP_ID       = SP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM   <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND (IE.D1_REMOVAL_DTTM  IS NULL
  OR IE.D1_REMOVAL_DTTM     > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  AND D.DEVICE_CONFIG_ID    = IE.DEVICE_CONFIG_ID
  AND MC.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
  AND DVC.D1_DEVICE_ID      = D.D1_DEVICE_ID
  AND DVC.D1_SPR_CD         = ' '
  AND DT.DEVICE_TYPE_CD     = DVC.DEVICE_TYPE_CD
  AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'
  AND NOT EXISTS
    (SELECT 'x'
       FROM D1_US_SP USSP,
      D1_US US
      WHERE USSP.D1_SP_ID   = SP.D1_SP_ID
    AND US.US_ID            = USSP.US_ID
    AND US.US_STAT_COND_FLG = 'D1AC'
    );

-- ----- D1_US_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_US_VW" ("US_ID", "D1_SP_ID", "D1_DEVICE_ID", "MEASR_COMP_ID", "US_TYPE_CD", "D1_SP_TYPE_CD", "DEVICE_TYPE_CD", "D1_SPR_CD", "MEASR_COMP_TYPE_CD", "D1_UOM_CD", "ACCESS_GRP_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT US.US_ID           ,
  ' ' AS D1_SP_ID          ,
  ' ' AS D1_DEVICE_ID      ,
  ' ' AS MEASR_COMP_ID     ,
  US.US_TYPE_CD            ,
  ' ' AS D1_SP_TYPE_CD     ,
  ' ' AS DEVICE_TYPE_CD    ,
  ' ' AS D1_SPR_CD         ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  ' ' AS ACCESS_GRP_CD
   FROM D1_US US
  WHERE US.US_STAT_COND_FLG = 'D1AC'
AND NOT EXISTS
  (SELECT 'x' FROM D1_US_SP USSP WHERE USSP.US_ID = US.US_ID
  )
  
  UNION
 
 SELECT USSP.US_ID         ,
  USSP.D1_SP_ID            ,
  ' ' AS D1_DEVICE_ID      ,
  ' ' AS MEASR_COMP_ID     ,
  US.US_TYPE_CD            ,
  SP.D1_SP_TYPE_CD         ,
  ' ' AS DEVICE_TYPE_CD    ,
  ' ' AS D1_SPR_CD         ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_US_SP USSP,
  D1_US US           ,
  D1_SP SP
  WHERE US.US_ID        = USSP.US_ID
AND US.US_STAT_COND_FLG = 'D1AC'
AND SP.D1_SP_ID         = USSP.D1_SP_ID
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_INSTALL_EVT IE
    WHERE IE.D1_SP_ID       = USSP.D1_SP_ID
  AND IE.D1_INSTALL_DTTM   <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
  AND ( IE.D1_REMOVAL_DTTM IS NULL
  OR IE.D1_REMOVAL_DTTM     > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
  )
  
  UNION
 
 SELECT USSP.US_ID         ,
  USSP.D1_SP_ID            ,
  D.D1_DEVICE_ID           ,
  ' ' AS MEASR_COMP_ID     ,
  US.US_TYPE_CD            ,
  SP.D1_SP_TYPE_CD         ,
  DVC.DEVICE_TYPE_CD       ,
  DVC.D1_SPR_CD            ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_US_SP USSP,
  D1_INSTALL_EVT IE  ,
  D1_DVC_CFG D       ,
  D1_US US           ,
  D1_SP SP           ,
  D1_DVC DVC
  WHERE US.US_ID         = USSP.US_ID
AND US.US_STAT_COND_FLG  = 'D1AC'
AND IE.D1_SP_ID          = USSP.D1_SP_ID
AND SP.D1_SP_ID          = USSP.D1_SP_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
AND DVC.D1_SPR_CD       <> ' '
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_MEASR_COMP MC
    WHERE MC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
  )
  
  UNION
 
 SELECT USSP.US_ID         ,
  USSP.D1_SP_ID            ,
  D.D1_DEVICE_ID           ,
  ' ' AS MEASR_COMP_ID     ,
  US.US_TYPE_CD            ,
  SP.D1_SP_TYPE_CD         ,
  DVC.DEVICE_TYPE_CD       ,
  DT.D1_SPR_CD             ,
  ' ' AS MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_US_SP USSP,
  D1_INSTALL_EVT IE  ,
  D1_DVC_CFG D       ,
  D1_US US           ,
  D1_SP SP           ,
  D1_DVC DVC         ,
  D1_DVC_TYPE DT
  WHERE US.US_ID         = USSP.US_ID
AND US.US_STAT_COND_FLG  = 'D1AC'
AND IE.D1_SP_ID          = USSP.D1_SP_ID
AND SP.D1_SP_ID          = USSP.D1_SP_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
AND DVC.D1_SPR_CD        = ' '
AND DT.DEVICE_TYPE_CD    = DVC.DEVICE_TYPE_CD
AND NOT EXISTS
  (SELECT 'x'
     FROM D1_MEASR_COMP MC
    WHERE MC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
  )
  
  UNION
 
 SELECT USSP.US_ID     ,
  USSP.D1_SP_ID        ,
  D.D1_DEVICE_ID       ,
  MC.MEASR_COMP_ID     ,
  US.US_TYPE_CD        ,
  SP.D1_SP_TYPE_CD     ,
  DVC.DEVICE_TYPE_CD   ,
  DVC.D1_SPR_CD        ,
  MC.MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD     ,
  SP.ACCESS_GRP_CD
   FROM D1_US_SP USSP,
  D1_INSTALL_EVT IE  ,
  D1_DVC_CFG D       ,
  D1_MEASR_COMP MC   ,
  D1_US US           ,
  D1_SP SP           ,
  D1_DVC DVC
  WHERE US.US_ID         = USSP.US_ID
AND US.US_STAT_COND_FLG  = 'D1AC'
AND IE.D1_SP_ID          = USSP.D1_SP_ID
AND SP.D1_SP_ID          = USSP.D1_SP_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
AND MC.DEVICE_CONFIG_ID  = IE.DEVICE_CONFIG_ID
AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
AND DVC.D1_SPR_CD       <> ' '
AND NOT EXISTS
  (SELECT 'X'
     FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
  )
  
  UNION
 
 SELECT USSP.US_ID     ,
  USSP.D1_SP_ID        ,
  D.D1_DEVICE_ID       ,
  MC.MEASR_COMP_ID     ,
  US.US_TYPE_CD        ,
  SP.D1_SP_TYPE_CD     ,
  DVC.DEVICE_TYPE_CD   ,
  DT.D1_SPR_CD         ,
  MC.MEASR_COMP_TYPE_CD,
  ' ' AS D1_UOM_CD     ,
  SP.ACCESS_GRP_CD
   FROM D1_US_SP USSP,
  D1_INSTALL_EVT IE  ,
  D1_DVC_CFG D       ,
  D1_MEASR_COMP MC   ,
  D1_US US           ,
  D1_SP SP           ,
  D1_DVC DVC         ,
  D1_DVC_TYPE DT
  WHERE US.US_ID         = USSP.US_ID
AND US.US_STAT_COND_FLG  = 'D1AC'
AND IE.D1_SP_ID          = USSP.D1_SP_ID
AND SP.D1_SP_ID          = USSP.D1_SP_ID
AND IE.D1_INSTALL_DTTM  <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM IS NULL
OR IE.D1_REMOVAL_DTTM    > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND D.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
AND MC.DEVICE_CONFIG_ID  = IE.DEVICE_CONFIG_ID
AND DVC.D1_DEVICE_ID     = D.D1_DEVICE_ID
AND DVC.D1_SPR_CD        = ' '
AND DT.DEVICE_TYPE_CD    = DVC.DEVICE_TYPE_CD
AND NOT EXISTS
  (SELECT 'X'
     FROM D1_MC_TYPE_VALUE_IDENTIFIER VI
    WHERE VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
  AND VI.VALUE_ID_TYPE_FLG      = 'D1MS'
  )
  
  UNION
 
 SELECT USSP.US_ID     ,
  USSP.D1_SP_ID        ,
  D.D1_DEVICE_ID       ,
  MC.MEASR_COMP_ID     ,
  US.US_TYPE_CD        ,
  SP.D1_SP_TYPE_CD     ,
  DVC.DEVICE_TYPE_CD   ,
  DVC.D1_SPR_CD        ,
  MC.MEASR_COMP_TYPE_CD,
  VI.D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_US_SP USSP,
  D1_INSTALL_EVT IE  ,
  D1_DVC_CFG D       ,
  D1_MEASR_COMP MC   ,
  D1_US US           ,
  D1_SP SP           ,
  D1_DVC DVC         ,
  D1_MC_TYPE_VALUE_IDENTIFIER VI
  WHERE US.US_ID          = USSP.US_ID
AND US.US_STAT_COND_FLG   = 'D1AC'
AND IE.D1_SP_ID           = USSP.D1_SP_ID
AND SP.D1_SP_ID           = USSP.D1_SP_ID
AND IE.D1_INSTALL_DTTM   <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM  IS NULL
OR IE.D1_REMOVAL_DTTM     > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND D.DEVICE_CONFIG_ID    = IE.DEVICE_CONFIG_ID
AND MC.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
AND DVC.D1_DEVICE_ID      = D.D1_DEVICE_ID
AND DVC.D1_SPR_CD        <> ' '
AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
AND VI.VALUE_ID_TYPE_FLG  = 'D1MS'
  
  UNION
 
 SELECT USSP.US_ID     ,
  USSP.D1_SP_ID        ,
  D.D1_DEVICE_ID       ,
  MC.MEASR_COMP_ID     ,
  US.US_TYPE_CD        ,
  SP.D1_SP_TYPE_CD     ,
  DVC.DEVICE_TYPE_CD   ,
  DT.D1_SPR_CD         ,
  MC.MEASR_COMP_TYPE_CD,
  VI.D1_UOM_CD         ,
  SP.ACCESS_GRP_CD
   FROM D1_US_SP USSP,
  D1_INSTALL_EVT IE  ,
  D1_DVC_CFG D       ,
  D1_MEASR_COMP MC   ,
  D1_US US           ,
  D1_SP SP           ,
  D1_DVC DVC         ,
  D1_DVC_TYPE DT     ,
  D1_MC_TYPE_VALUE_IDENTIFIER VI
  WHERE US.US_ID          = USSP.US_ID
AND US.US_STAT_COND_FLG   = 'D1AC'
AND IE.D1_SP_ID           = USSP.D1_SP_ID
AND SP.D1_SP_ID           = USSP.D1_SP_ID
AND IE.D1_INSTALL_DTTM   <= (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL)
AND (IE.D1_REMOVAL_DTTM  IS NULL
OR IE.D1_REMOVAL_DTTM     > (SELECT from_tz(CAST(CURRENT_DATE AS TIMESTAMP), (SELECT TZ.F1_TIMEZONE_NAME FROM CI_TIME_ZONE TZ, F1_INSTALLATION INST WHERE INST.TIME_ZONE_CD = TZ.TIME_ZONE_CD)) DTTM FROM DUAL))
AND D.DEVICE_CONFIG_ID    = IE.DEVICE_CONFIG_ID
AND MC.DEVICE_CONFIG_ID   = IE.DEVICE_CONFIG_ID
AND DVC.D1_DEVICE_ID      = D.D1_DEVICE_ID
AND DVC.D1_SPR_CD         = ' '
AND DT.DEVICE_TYPE_CD     = DVC.DEVICE_TYPE_CD
AND VI.MEASR_COMP_TYPE_CD = MC.MEASR_COMP_TYPE_CD
AND VI.VALUE_ID_TYPE_FLG  = 'D1MS';

-- ----- D2_MEASR_QTY_AGR_MV -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D2_MEASR_QTY_AGR_MV" ("MEASR_COMP_ID", "MSRMT_DTTM", "MSRMT_DT", "MSRMT_LOCAL_DTTM", "LOCAL_DT", "MSRMT_VAL", "MSRMT_VAL1", "MSRMT_VAL2", "MSRMT_VAL3", "MSRMT_VAL4", "MSRMT_VAL5", "MSRMT_VAL6", "MSRMT_VAL7", "MSRMT_VAL8", "MSRMT_VAL9", "MSRMT_VAL10") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT MEASR_COMP_ID,
	   MSRMT_DTTM,
	   TRUNC(MSRMT_DTTM) AS MSRMT_DT,
	   MSRMT_LOCAL_DTTM,
	   TRUNC(MSRMT_LOCAL_DTTM) AS LOCAL_DT,
	   MSRMT_VAL,
	   MSRMT_VAL1,
	   MSRMT_VAL2,
	   MSRMT_VAL3,
	   MSRMT_VAL4,
	   MSRMT_VAL5,
	   MSRMT_VAL6,
	   MSRMT_VAL7,
	   MSRMT_VAL8,
	   MSRMT_VAL9,
	   MSRMT_VAL10
	FROM D1_AGG_MSRMT
	  WHERE BUS_OBJ_CD = 'D2-MeasuredQuantityMsrmt';

-- ----- D2_MEASR_QTY_MV -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D2_MEASR_QTY_MV" ("MEASR_COMP_ID", "MEASR_COMP_TYPE_CD", "POSTAL", "MC_TYPE_DESCR", "CITY", "DEVICE_TYPE_CD", "DEVICE_TYPE_DESCR", "HEAD_END_SYSTEM_CD", "HEAD_END_SYSTEM_DESCR", "USG_CALC_GRP_CD", "USG_CALC_GRP_DESCR", "MKT_CD", "MKT_DESCR", "D1_SPR_CD", "SPR_DESCR", "D1_SVC_TPE_CD", "SVC_TYPE_DESCR", "MKT_REL_TYPE_FLG", "MKT_REL_TYPE_DESCR", "MANUFACTURER_CD", "MANUFACTURER_DESCR", "D1_MODEL_CD", "MODEL_DESCR", "GEO_CODE") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT T1.MEASR_COMP_ID AS  MEASR_COMP_ID,
    T1.measr_comp_type_Cd as MEASR_COMP_TYPE_CD,
    T1.POSTAL AS POSTAL ,
    MCTYP.DESCR100 AS MC_TYPE_DESCR ,
    T1.CITY  AS CITY,
    T1.DEVICE_TYPE_CD AS  DEVICE_TYPE_CD,
    DVTL.DESCR100 AS DEVICE_TYPE_DESCR ,
    T1.HEAD_END_SYSTEM_CD AS HEAD_END_SYSTEM_CD ,
    SPRL.DESCR100 AS HEAD_END_SYSTEM_DESCR ,
    T1.USG_CALC_GRP_CD AS USG_CALC_GRP_CD,
    USGRL.DESCR100 AS USG_CALC_GRP_DESCR ,
    T1.MKT_CD AS MKT_CD,
    MKTL.DESCR100 AS MKT_DESCR ,
    T1.SPR_CD AS D1_SPR_CD ,
    SPRL1.DESCR100 AS SPR_DESCR ,
    T1.D1_SVC_TPE_CD  AS D1_SVC_TPE_CD,
    SVTL.DESCR100 AS SVC_TYPE_DESCR ,
    T1.MKT_REL_TYPE_FLG AS MKT_REL_TYPE_FLG ,
    LKPL.DESCR AS MKT_REL_TYPE_DESCR ,
    T1.MANUFACTURER_CD AS MANUFACTURER_CD,
    DMNL.DESCR100 AS MANUFACTURER_DESCR ,
    T1.D1_MODEL_CD AS D1_MODEL_CD,
    DMDL.DESCR100 AS MODEL_DESCR ,
    T1.GEO_CODE
  FROM
    (SELECT
      mc.measr_comp_id,
      mc.measr_comp_type_Cd,
      MAX(DECODE(m.char_type_cd ,'D2POSTCD',m.SRCH_CHAR_VAL,NULL))       AS postal,
      MAX(DECODE(trim(m.char_type_cd) ,'D2CITY',m.SRCH_CHAR_VAL,NULL))   AS city,
      MAX(DECODE(trim(m.char_type_cd) ,'D2DVCTYP',m.SRCH_CHAR_VAL,NULL)) AS DEVICE_TYPE_CD,
      MAX(DECODE(trim(m.char_type_cd) ,'D2HEADED',m.SRCH_CHAR_VAL,NULL)) AS head_end_system_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2USGGRP',m.SRCH_CHAR_VAL,NULL)) AS usg_calc_grp_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MARKET',m.SRCH_CHAR_VAL,NULL)) AS mkt_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2SPR',m.SRCH_CHAR_VAL,NULL))    AS spr_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2SVCTYP',m.SRCH_CHAR_VAL,NULL)) AS d1_svc_tpe_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MKRLTY',m.SRCH_CHAR_VAL,NULL)) AS mkt_rel_type_flg,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MANUF',m.SRCH_CHAR_VAL,NULL))  AS manufacturer_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MODEL',m.SRCH_CHAR_VAL,NULL))  AS d1_model_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2GEOCD',m.SRCH_CHAR_VAL,NULL))  AS geo_code,
      mc.bus_obj_cd,
      f1.language_cd
    FROM d1_measr_comp mc,
      d1_measr_comp_type mct,
      d1_measr_comp_char m,
      f1_installation f1
    WHERE mc.measr_comp_id    =m.measr_comp_id
    AND m.char_type_cd       IN ('D2POSTCD' ,'D2CITY','D2DVCTYP','D2HEADED','D2USGGRP','D2MARKET','D2SPR','D2SVCTYP','D2MKRLTY','D2MANUF','D2MODEL','D2GEOCD')
    AND mc.bus_obj_cd         = 'D2-MeasuredQuantityAggregator '
    AND mc.BO_STATUS_CD       = 'ACTIVE'
    AND mc.measr_comp_type_cd = mct.measr_comp_type_cd
    AND mct.mc_class_flg      = 'D1AG'
    AND m.effdt               =
      (SELECT MAX (a.effdt)
      FROM d1_measr_comp_char a
      WHERE a.measr_comp_id = m.measr_comp_id
      AND a.char_type_cd    = m.char_type_cd
      )
    GROUP BY mc.measr_comp_id,
      mc.measr_comp_type_Cd,
      mc.bus_obj_cd,
      f1.language_cd
    ) T1,
    d1_measr_comp_type_l mctyp,
    d1_dvc_type_l dvtl,
    d1_spr_l sprl,
    d1_usg_grp_l usgrl,
    d1_mkt_l mktl,
    d1_spr_l sprl1,
    d1_svc_type_l svtl,
    ci_lookup_val_l lkpl,
    d1_manufacturer_l dmnl,
    d1_model_l dmdl
  WHERE T1.measr_comp_type_cd=mctyp.measr_comp_type_cd
  AND mctyp.language_cd      = T1.language_cd
  AND T1.DEVICE_TYPE_CD      =dvtl.device_type_cd
  AND T1.language_cd         = dvtl.language_cd
  AND T1.head_end_system_cd  =sprl.d1_spr_cd(+)
  AND T1.language_cd         = sprl.language_cd(+)
  AND T1.usg_calc_grp_cd     =usgrl.usg_grp_cd(+)
  AND T1.language_cd         = usgrl.language_cd(+)
  AND T1.mkt_cd              =mktl.mkt_cd(+)
  AND T1.language_cd         = mktl.language_cd(+)
  AND T1.spr_cd              =sprl1.d1_spr_cd(+)
  AND T1.language_cd         = sprl1.language_cd(+)
  AND T1.d1_svc_tpe_cd       =svtl.d1_svc_type_cd(+)
  AND T1.language_cd         = svtl.language_cd(+)
  AND T1.mkt_rel_type_flg    =lkpl.field_value(+)
  AND T1.language_cd         = lkpl.language_cd(+)
  AND lkpl.field_name(+)     = 'MKT_REL_TYPE_FLG'
  AND T1.manufacturer_cd     =dmnl.manufacturer_cd(+)
  AND T1.manufacturer_cd    = dmdl.manufacturer_cd(+)
  AND T1.language_cd         = dmnl.language_cd(+)
  AND T1.d1_model_cd         =dmdl.d1_model_cd(+)
  AND T1.language_cd         = dmdl.language_cd(+);

-- ----- D2_QUALITY_CNT_AGR_MV -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D2_QUALITY_CNT_AGR_MV" ("MEASR_COMP_ID", "MSRMT_DTTM", "MSRMT_DT", "MSRMT_LOCAL_DTTM", "LOCAL_DT", "MSRMT_VAL", "MSRMT_VAL1", "MSRMT_VAL2", "MSRMT_VAL3", "MSRMT_VAL4", "MSRMT_VAL5", "MSRMT_VAL6", "MSRMT_VAL7", "MSRMT_VAL8", "MSRMT_VAL9", "MSRMT_VAL10") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT MEASR_COMP_ID,
       MSRMT_DTTM,
	   TRUNC(MSRMT_DTTM) AS MSRMT_DT,
	   MSRMT_LOCAL_DTTM,
	   TRUNC(MSRMT_LOCAL_DTTM) AS LOCAL_DT,
	   MSRMT_VAL,
	   MSRMT_VAL1,
	   MSRMT_VAL2,
	   MSRMT_VAL3,
	   MSRMT_VAL4,
	   MSRMT_VAL5,
	   MSRMT_VAL6,
	   MSRMT_VAL7,
	   MSRMT_VAL8,
	   MSRMT_VAL9,
	   MSRMT_VAL10 FROM D1_AGG_MSRMT
	   WHERE BUS_OBJ_CD = 'D2-QualityCountMsrmt';

-- ----- D2_QUALITY_CNT_MV -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D2_QUALITY_CNT_MV" ("MEASR_COMP_ID", "MEASR_COMP_TYPE_CD", "POSTAL", "MC_TYPE_DESCR", "CITY", "DEVICE_TYPE_CD", "DEVICE_TYPE_DESCR", "HEAD_END_SYSTEM_CD", "HEAD_END_SYSTEM_DESCR", "USG_CALC_GRP_CD", "USG_CALC_GRP_DESCR", "MKT_CD", "MKT_DESCR", "D1_SPR_CD", "SPR_DESCR", "D1_SVC_TPE_CD", "SVC_TYPE_DESCR", "MKT_REL_TYPE_FLG", "MKT_REL_TYPE_DESCR", "MANUFACTURER_CD", "MANUFACTURER_DESCR", "D1_MODEL_CD", "MODEL_DESCR", "GEO_CODE") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT T1.MEASR_COMP_ID AS  MEASR_COMP_ID,
    T1.measr_comp_type_Cd as MEASR_COMP_TYPE_CD,
    T1.POSTAL AS POSTAL ,
    MCTYP.DESCR100 AS MC_TYPE_DESCR ,
    T1.CITY  AS CITY,
    T1.DEVICE_TYPE_CD AS  DEVICE_TYPE_CD,
    DVTL.DESCR100 AS DEVICE_TYPE_DESCR ,
    T1.HEAD_END_SYSTEM_CD AS HEAD_END_SYSTEM_CD ,
    SPRL.DESCR100 AS HEAD_END_SYSTEM_DESCR ,
    T1.USG_CALC_GRP_CD AS USG_CALC_GRP_CD,
    USGRL.DESCR100 AS USG_CALC_GRP_DESCR ,
    T1.MKT_CD AS MKT_CD,
    MKTL.DESCR100 AS MKT_DESCR ,
    T1.SPR_CD AS D1_SPR_CD ,
    SPRL1.DESCR100 AS SPR_DESCR ,
    T1.D1_SVC_TPE_CD  AS D1_SVC_TPE_CD,
    SVTL.DESCR100 AS SVC_TYPE_DESCR ,
    T1.MKT_REL_TYPE_FLG AS MKT_REL_TYPE_FLG ,
    LKPL.DESCR AS MKT_REL_TYPE_DESCR ,
    T1.MANUFACTURER_CD AS MANUFACTURER_CD,
    DMNL.DESCR100 AS MANUFACTURER_DESCR ,
    T1.D1_MODEL_CD AS D1_MODEL_CD,
    DMDL.DESCR100 AS MODEL_DESCR ,
    T1.GEO_CODE AS GEO_CODE
  FROM
    (SELECT
      /*+ INDEX(mc,D1M252S2) */
      mc.measr_comp_id,
      mastermc.measr_comp_type_Cd,
      MAX(DECODE(m.char_type_cd ,'D2POSTCD',m.SRCH_CHAR_VAL,NULL))       AS postal,
      MAX(DECODE(trim(m.char_type_cd) ,'D2CITY',m.SRCH_CHAR_VAL,NULL))   AS city,
      MAX(DECODE(trim(m.char_type_cd) ,'D2DVCTYP',m.SRCH_CHAR_VAL,NULL)) AS DEVICE_TYPE_CD,
      MAX(DECODE(trim(m.char_type_cd) ,'D2HEADED',m.SRCH_CHAR_VAL,NULL)) AS head_end_system_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2USGGRP',m.SRCH_CHAR_VAL,NULL)) AS usg_calc_grp_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MARKET',m.SRCH_CHAR_VAL,NULL)) AS mkt_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2SPR',m.SRCH_CHAR_VAL,NULL))    AS spr_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2SVCTYP',m.SRCH_CHAR_VAL,NULL)) AS d1_svc_tpe_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MKRLTY',m.SRCH_CHAR_VAL,NULL)) AS mkt_rel_type_flg,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MANUF',m.SRCH_CHAR_VAL,NULL))  AS manufacturer_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MODEL',m.SRCH_CHAR_VAL,NULL))  AS d1_model_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2GEOCD',m.SRCH_CHAR_VAL,NULL))  AS geo_code,
      mc.bus_obj_cd,
      f1.language_cd
    FROM d1_measr_comp mc,
      d1_measr_comp_type mct,
      d1_measr_comp_char m,
      d1_measr_comp_rel mcrel,
      d1_measr_comp mastermc,
      f1_installation f1
    WHERE mc.measr_comp_id    =m.measr_comp_id
    AND m.char_type_cd       IN ('D2POSTCD' ,'D2CITY','D2DVCTYP','D2HEADED','D2USGGRP','D2MARKET','D2SPR','D2SVCTYP','D2MKRLTY','D2MANUF','D2MODEL','D2GEOCD')
    AND mc.bus_obj_cd         = 'D2-MsrmtQualityCountAggregator'
    AND mc.BO_STATUS_CD       = 'ACTIVE'
    AND mastermc.measr_comp_type_cd = mct.measr_comp_type_cd
    AND mct.mc_class_flg      = 'D1AG'
    AND mcrel.rel_measr_comp_id =mc.measr_comp_id
    AND mastermc.measr_comp_id = mcrel.measr_comp_id
    AND m.effdt               =
      (SELECT MAX (a.effdt)
      FROM d1_measr_comp_char a
      WHERE a.measr_comp_id = m.measr_comp_id
      AND a.char_type_cd    = m.char_type_cd
      )
    GROUP BY mc.measr_comp_id,
      mastermc.measr_comp_type_Cd,
      mc.bus_obj_cd,
      f1.language_cd
    ) T1,
    d1_measr_comp_type_l mctyp,
    d1_dvc_type_l dvtl,
    d1_spr_l sprl,
    d1_usg_grp_l usgrl,
    d1_mkt_l mktl,
    d1_spr_l sprl1,
    d1_svc_type_l svtl,
    ci_lookup_val_l lkpl,
    d1_manufacturer_l dmnl,
    d1_model_l dmdl
  WHERE T1.measr_comp_type_cd=mctyp.measr_comp_type_cd
  AND mctyp.language_cd      = T1.language_cd
  AND T1.DEVICE_TYPE_CD      =dvtl.device_type_cd
  AND T1.language_cd         = dvtl.language_cd
  AND T1.head_end_system_cd  =sprl.d1_spr_cd(+)
  AND T1.language_cd         = sprl.language_cd(+)
  AND T1.usg_calc_grp_cd     =usgrl.usg_grp_cd(+)
  AND T1.language_cd         = usgrl.language_cd(+)
  AND T1.mkt_cd              =mktl.mkt_cd(+)
  AND T1.language_cd         = mktl.language_cd(+)
  AND T1.spr_cd              =sprl1.d1_spr_cd(+)
  AND T1.language_cd         = sprl1.language_cd(+)
  AND T1.d1_svc_tpe_cd       =svtl.d1_svc_type_cd(+)
  AND T1.language_cd         = svtl.language_cd(+)
  AND T1.mkt_rel_type_flg    =lkpl.field_value(+)
  AND T1.language_cd         = lkpl.language_cd(+)
  AND lkpl.field_name(+)     = 'MKT_REL_TYPE_FLG'
  AND T1.manufacturer_cd     =dmnl.manufacturer_cd(+)
  AND T1.manufacturer_cd    = dmdl.manufacturer_cd(+)
  AND T1.language_cd         = dmnl.language_cd(+)
  AND T1.d1_model_cd         =dmdl.d1_model_cd(+)
  AND T1.language_cd         = dmdl.language_cd(+);

-- ----- D2_TIMELINESS_CNT_MV -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D2_TIMELINESS_CNT_MV" ("MEASR_COMP_ID", "MEASR_COMP_TYPE_CD", "POSTAL", "MC_TYPE_DESCR", "CITY", "DEVICE_TYPE_CD", "DEVICE_TYPE_DESCR", "HEAD_END_SYSTEM_CD", "HEAD_END_SYSTEM_DESCR", "USG_CALC_GRP_CD", "USG_CALC_GRP_DESCR", "MKT_CD", "MKT_DESCR", "D1_SPR_CD", "SPR_DESCR", "D1_SVC_TPE_CD", "SVC_TYPE_DESCR", "MKT_REL_TYPE_FLG", "MKT_REL_TYPE_DESCR", "MANUFACTURER_CD", "MANUFACTURER_DESCR", "D1_MODEL_CD", "MODEL_DESCR", "GEO_CODE") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT T1.MEASR_COMP_ID AS  MEASR_COMP_ID,
    T1.measr_comp_type_Cd as MEASR_COMP_TYPE_CD,
    T1.POSTAL AS POSTAL ,
    MCTYP.DESCR100 AS MC_TYPE_DESCR ,
    T1.CITY  AS CITY,
    T1.DEVICE_TYPE_CD AS  DEVICE_TYPE_CD,
    DVTL.DESCR100 AS DEVICE_TYPE_DESCR ,
    T1.HEAD_END_SYSTEM_CD AS HEAD_END_SYSTEM_CD ,
    SPRL.DESCR100 AS HEAD_END_SYSTEM_DESCR ,
    T1.USG_CALC_GRP_CD AS USG_CALC_GRP_CD,
    USGRL.DESCR100 AS USG_CALC_GRP_DESCR ,
    T1.MKT_CD AS MKT_CD,
    MKTL.DESCR100 AS MKT_DESCR ,
    T1.SPR_CD AS D1_SPR_CD ,
    SPRL1.DESCR100 AS SPR_DESCR ,
    T1.D1_SVC_TPE_CD  AS D1_SVC_TPE_CD,
    SVTL.DESCR100 AS SVC_TYPE_DESCR ,
    T1.MKT_REL_TYPE_FLG AS MKT_REL_TYPE_FLG ,
    LKPL.DESCR AS MKT_REL_TYPE_DESCR ,
    T1.MANUFACTURER_CD AS MANUFACTURER_CD,
    DMNL.DESCR100 AS MANUFACTURER_DESCR ,
    T1.D1_MODEL_CD AS D1_MODEL_CD,
    DMDL.DESCR100 AS MODEL_DESCR ,
    T1.GEO_CODE AS GEO_CODE
  FROM
    (SELECT
      /*+ INDEX(mc,D1M252S2) */
      mc.measr_comp_id,
      mastermc.measr_comp_type_Cd,
      MAX(DECODE(m.char_type_cd ,'D2POSTCD',m.SRCH_CHAR_VAL,NULL))       AS postal,
      MAX(DECODE(trim(m.char_type_cd) ,'D2CITY',m.SRCH_CHAR_VAL,NULL))   AS city,
      MAX(DECODE(trim(m.char_type_cd) ,'D2DVCTYP',m.SRCH_CHAR_VAL,NULL)) AS DEVICE_TYPE_CD,
      MAX(DECODE(trim(m.char_type_cd) ,'D2HEADED',m.SRCH_CHAR_VAL,NULL)) AS head_end_system_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2USGGRP',m.SRCH_CHAR_VAL,NULL)) AS usg_calc_grp_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MARKET',m.SRCH_CHAR_VAL,NULL)) AS mkt_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2SPR',m.SRCH_CHAR_VAL,NULL))    AS spr_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2SVCTYP',m.SRCH_CHAR_VAL,NULL)) AS d1_svc_tpe_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MKRLTY',m.SRCH_CHAR_VAL,NULL)) AS mkt_rel_type_flg,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MANUF',m.SRCH_CHAR_VAL,NULL))  AS manufacturer_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MODEL',m.SRCH_CHAR_VAL,NULL))  AS d1_model_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2GEOCD',m.SRCH_CHAR_VAL,NULL))  AS geo_code,
      mc.bus_obj_cd,
      f1.language_cd
    FROM d1_measr_comp mc,
      d1_measr_comp_type mct,
      d1_measr_comp_char m,
      d1_measr_comp_rel mcrel,
      d1_measr_comp mastermc,
      f1_installation f1
    WHERE mc.measr_comp_id    =m.measr_comp_id
    AND m.char_type_cd       IN ('D2POSTCD' ,'D2CITY','D2DVCTYP','D2HEADED','D2USGGRP','D2MARKET','D2SPR','D2SVCTYP','D2MKRLTY','D2MANUF','D2MODEL','D2GEOCD')
    AND mc.bus_obj_cd         = 'D2-MsrmtTimelinessCountAggr '
    AND mc.BO_STATUS_CD       = 'ACTIVE'
    AND mastermc.measr_comp_type_cd = mct.measr_comp_type_cd
    AND mct.mc_class_flg      = 'D1AG'
    AND mcrel.rel_measr_comp_id =mc.measr_comp_id
    AND mastermc.measr_comp_id = mcrel.measr_comp_id
    AND m.effdt               =
      (SELECT MAX (a.effdt)
      FROM d1_measr_comp_char a
      WHERE a.measr_comp_id = m.measr_comp_id
      AND a.char_type_cd    = m.char_type_cd
      )
    GROUP BY mc.measr_comp_id,
      mastermc.measr_comp_type_Cd,
      mc.bus_obj_cd,
      f1.language_cd
    ) T1,
    d1_measr_comp_type_l mctyp,
    d1_dvc_type_l dvtl,
    d1_spr_l sprl,
    d1_usg_grp_l usgrl,
    d1_mkt_l mktl,
    d1_spr_l sprl1,
    d1_svc_type_l svtl,
    ci_lookup_val_l lkpl,
    d1_manufacturer_l dmnl,
    d1_model_l dmdl
  WHERE T1.measr_comp_type_cd=mctyp.measr_comp_type_cd
  AND mctyp.language_cd      = T1.language_cd
  AND T1.DEVICE_TYPE_CD      =dvtl.device_type_cd
  AND T1.language_cd         = dvtl.language_cd
  AND T1.head_end_system_cd  =sprl.d1_spr_cd(+)
  AND T1.language_cd         = sprl.language_cd(+)
  AND T1.usg_calc_grp_cd     =usgrl.usg_grp_cd(+)
  AND T1.language_cd         = usgrl.language_cd(+)
  AND T1.mkt_cd              =mktl.mkt_cd(+)
  AND T1.language_cd         = mktl.language_cd(+)
  AND T1.spr_cd              =sprl1.d1_spr_cd(+)
  AND T1.language_cd         = sprl1.language_cd(+)
  AND T1.d1_svc_tpe_cd       =svtl.d1_svc_type_cd(+)
  AND T1.language_cd         = svtl.language_cd(+)
  AND T1.mkt_rel_type_flg    =lkpl.field_value(+)
  AND T1.language_cd         = lkpl.language_cd(+)
  AND lkpl.field_name(+)     = 'MKT_REL_TYPE_FLG'
  AND T1.manufacturer_cd     =dmnl.manufacturer_cd(+)
  AND T1.manufacturer_cd    = dmdl.manufacturer_cd(+)
  AND T1.language_cd         = dmnl.language_cd(+)
  AND T1.d1_model_cd         =dmdl.d1_model_cd(+)
  AND T1.language_cd         = dmdl.language_cd(+);

-- ----- D2_TIMELINESS_QTY_MV -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D2_TIMELINESS_QTY_MV" ("MEASR_COMP_ID", "MEASR_COMP_TYPE_CD", "POSTAL", "MC_TYPE_DESCR", "CITY", "DEVICE_TYPE_CD", "DEVICE_TYPE_DESCR", "HEAD_END_SYSTEM_CD", "HEAD_END_SYSTEM_DESCR", "USG_CALC_GRP_CD", "USG_CALC_GRP_DESCR", "MKT_CD", "MKT_DESCR", "D1_SPR_CD", "SPR_DESCR", "D1_SVC_TPE_CD", "SVC_TYPE_DESCR", "MKT_REL_TYPE_FLG", "MKT_REL_TYPE_DESCR", "MANUFACTURER_CD", "MANUFACTURER_DESCR", "D1_MODEL_CD", "MODEL_DESCR", "GEO_CODE") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT T1.MEASR_COMP_ID AS  MEASR_COMP_ID,
    T1.measr_comp_type_Cd as MEASR_COMP_TYPE_CD,
    T1.POSTAL AS POSTAL ,
    MCTYP.DESCR100 AS MC_TYPE_DESCR ,
    T1.CITY  AS CITY,
    T1.DEVICE_TYPE_CD AS  DEVICE_TYPE_CD,
    DVTL.DESCR100 AS DEVICE_TYPE_DESCR ,
    T1.HEAD_END_SYSTEM_CD AS HEAD_END_SYSTEM_CD ,
    SPRL.DESCR100 AS HEAD_END_SYSTEM_DESCR ,
    T1.USG_CALC_GRP_CD AS USG_CALC_GRP_CD,
    USGRL.DESCR100 AS USG_CALC_GRP_DESCR ,
    T1.MKT_CD AS MKT_CD,
    MKTL.DESCR100 AS MKT_DESCR ,
    T1.SPR_CD AS D1_SPR_CD ,
    SPRL1.DESCR100 AS SPR_DESCR ,
    T1.D1_SVC_TPE_CD  AS D1_SVC_TPE_CD,
    SVTL.DESCR100 AS SVC_TYPE_DESCR ,
    T1.MKT_REL_TYPE_FLG AS MKT_REL_TYPE_FLG ,
    LKPL.DESCR AS MKT_REL_TYPE_DESCR ,
    T1.MANUFACTURER_CD AS MANUFACTURER_CD,
    DMNL.DESCR100 AS MANUFACTURER_DESCR ,
    T1.D1_MODEL_CD AS D1_MODEL_CD,
    DMDL.DESCR100 AS MODEL_DESCR ,
    T1.GEO_CODE AS GEO_CODE
  FROM
    (SELECT
      /*+ INDEX(mc,D1M252S2) */
      mc.measr_comp_id,
      mastermc.measr_comp_type_Cd,
      MAX(DECODE(m.char_type_cd ,'D2POSTCD',m.SRCH_CHAR_VAL,NULL))       AS postal,
      MAX(DECODE(trim(m.char_type_cd) ,'D2CITY',m.SRCH_CHAR_VAL,NULL))   AS city,
      MAX(DECODE(trim(m.char_type_cd) ,'D2DVCTYP',m.SRCH_CHAR_VAL,NULL)) AS DEVICE_TYPE_CD,
      MAX(DECODE(trim(m.char_type_cd) ,'D2HEADED',m.SRCH_CHAR_VAL,NULL)) AS head_end_system_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2USGGRP',m.SRCH_CHAR_VAL,NULL)) AS usg_calc_grp_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MARKET',m.SRCH_CHAR_VAL,NULL)) AS mkt_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2SPR',m.SRCH_CHAR_VAL,NULL))    AS spr_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2SVCTYP',m.SRCH_CHAR_VAL,NULL)) AS d1_svc_tpe_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MKRLTY',m.SRCH_CHAR_VAL,NULL)) AS mkt_rel_type_flg,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MANUF',m.SRCH_CHAR_VAL,NULL))  AS manufacturer_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MODEL',m.SRCH_CHAR_VAL,NULL))  AS d1_model_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2GEOCD',m.SRCH_CHAR_VAL,NULL))  AS geo_code,
      mc.bus_obj_cd,
      f1.language_cd
    FROM d1_measr_comp mc,
      d1_measr_comp_type mct,
      d1_measr_comp_char m,
      d1_measr_comp_rel mcrel,
      d1_measr_comp mastermc,
      f1_installation f1
    WHERE mc.measr_comp_id    =m.measr_comp_id
    AND m.char_type_cd       IN ('D2POSTCD' ,'D2CITY','D2DVCTYP','D2HEADED','D2USGGRP','D2MARKET','D2SPR','D2SVCTYP','D2MKRLTY','D2MANUF','D2MODEL','D2GEOCD')
    AND mc.bus_obj_cd         = 'D2-MsrmtTimelinessQuantityAggr'
    AND mc.BO_STATUS_CD       = 'ACTIVE'
    AND mastermc.measr_comp_type_cd = mct.measr_comp_type_cd
    AND mct.mc_class_flg      = 'D1AG'
    AND mcrel.rel_measr_comp_id =mc.measr_comp_id
    AND mastermc.measr_comp_id = mcrel.measr_comp_id
    AND m.effdt               =
      (SELECT MAX (a.effdt)
      FROM d1_measr_comp_char a
      WHERE a.measr_comp_id = m.measr_comp_id
      AND a.char_type_cd    = m.char_type_cd
      )
    GROUP BY mc.measr_comp_id,
      mastermc.measr_comp_type_Cd,
      mc.bus_obj_cd,
      f1.language_cd
    ) T1,
    d1_measr_comp_type_l mctyp,
    d1_dvc_type_l dvtl,
    d1_spr_l sprl,
    d1_usg_grp_l usgrl,
    d1_mkt_l mktl,
    d1_spr_l sprl1,
    d1_svc_type_l svtl,
    ci_lookup_val_l lkpl,
    d1_manufacturer_l dmnl,
    d1_model_l dmdl
  WHERE T1.measr_comp_type_cd=mctyp.measr_comp_type_cd
  AND mctyp.language_cd      = T1.language_cd
  AND T1.DEVICE_TYPE_CD      =dvtl.device_type_cd
  AND T1.language_cd         = dvtl.language_cd
  AND T1.head_end_system_cd  =sprl.d1_spr_cd(+)
  AND T1.language_cd         = sprl.language_cd(+)
  AND T1.usg_calc_grp_cd     =usgrl.usg_grp_cd(+)
  AND T1.language_cd         = usgrl.language_cd(+)
  AND T1.mkt_cd              =mktl.mkt_cd(+)
  AND T1.language_cd         = mktl.language_cd(+)
  AND T1.spr_cd              =sprl1.d1_spr_cd(+)
  AND T1.language_cd         = sprl1.language_cd(+)
  AND T1.d1_svc_tpe_cd       =svtl.d1_svc_type_cd(+)
  AND T1.language_cd         = svtl.language_cd(+)
  AND T1.mkt_rel_type_flg    =lkpl.field_value(+)
  AND T1.language_cd         = lkpl.language_cd(+)
  AND lkpl.field_name(+)     = 'MKT_REL_TYPE_FLG'
  AND T1.manufacturer_cd     =dmnl.manufacturer_cd(+)
  AND T1.manufacturer_cd    = dmdl.manufacturer_cd(+)
  AND T1.language_cd         = dmnl.language_cd(+)
  AND T1.d1_model_cd         =dmdl.d1_model_cd(+)
  AND T1.language_cd         = dmdl.language_cd(+);

-- ----- D2_TIMELINES_CNT_AGR_MV -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D2_TIMELINES_CNT_AGR_MV" ("MEASR_COMP_ID", "MSRMT_DTTM", "MSRMT_DT", "MSRMT_LOCAL_DTTM", "LOCAL_DT", "MSRMT_VAL", "MSRMT_VAL1", "MSRMT_VAL2", "MSRMT_VAL3", "MSRMT_VAL4", "MSRMT_VAL5", "MSRMT_VAL6", "MSRMT_VAL7", "MSRMT_VAL8", "MSRMT_VAL9", "MSRMT_VAL10") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT MEASR_COMP_ID,
	   MSRMT_DTTM,
	   TRUNC(MSRMT_DTTM) AS MSRMT_DT,
	   MSRMT_LOCAL_DTTM,
	   TRUNC(MSRMT_LOCAL_DTTM) AS LOCAL_DT,
	   MSRMT_VAL,
	   MSRMT_VAL1,
	   MSRMT_VAL2,
	   MSRMT_VAL3,
	   MSRMT_VAL4,
	   MSRMT_VAL5,
	   MSRMT_VAL6,
	   MSRMT_VAL7,
	   MSRMT_VAL8,
	   MSRMT_VAL9,
	   MSRMT_VAL10
	   FROM D1_AGG_MSRMT WHERE BUS_OBJ_CD = 'D2-TimelinessCountMsrmt';

-- ----- D2_TIMELINES_QTY_AGR_MV -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D2_TIMELINES_QTY_AGR_MV" ("MEASR_COMP_ID", "MSRMT_DTTM", "MSRMT_DT", "MSRMT_LOCAL_DTTM", "LOCAL_DT", "MSRMT_VAL", "MSRMT_VAL1", "MSRMT_VAL2", "MSRMT_VAL3", "MSRMT_VAL4", "MSRMT_VAL5", "MSRMT_VAL6", "MSRMT_VAL7", "MSRMT_VAL8", "MSRMT_VAL9", "MSRMT_VAL10") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT MEASR_COMP_ID,
	   MSRMT_DTTM,
	   TRUNC(MSRMT_DTTM) AS MSRMT_DT,
	   MSRMT_LOCAL_DTTM,
	   TRUNC(MSRMT_LOCAL_DTTM) AS LOCAL_DT,
	   MSRMT_VAL,
	   MSRMT_VAL1,
	   MSRMT_VAL2,
	   MSRMT_VAL3,
	   MSRMT_VAL4,
	   MSRMT_VAL5,
	   MSRMT_VAL6,
	   MSRMT_VAL7,
	   MSRMT_VAL8,
	   MSRMT_VAL9,
	   MSRMT_VAL10
	 FROM D1_AGG_MSRMT WHERE BUS_OBJ_CD = 'D2-TimelinessQuantityMsrmt';

-- ----- F1_ATTACHMENT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_ATTACHMENT_VW" ("ATTACHMENT_ID", "BUS_OBJ_CD", "CRE_DTTM", "USER_ID", "MAINT_OBJ_CD", "PK_VAL1", "PK_VAL2", "PK_VAL3", "PK_VAL4", "PK_VAL5", "ATTACHMENT_DATA", "VERSION", "ATTACHMENT_FILE_NAME", "BO_DATA_AREA") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT "ATTACHMENT_ID","BUS_OBJ_CD","CRE_DTTM","USER_ID","MAINT_OBJ_CD","PK_VAL1","PK_VAL2","PK_VAL3","PK_VAL4","PK_VAL5","ATTACHMENT_DATA","VERSION","ATTACHMENT_FILE_NAME","BO_DATA_AREA" FROM F1_ATTACHMENT WHERE MAINT_OBJ_CD=' ' 

 
 
 ;

-- ----- F1_BATCH_CONF_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_BATCH_CONF_VW" ("BATCH_CD", "CONFIDENCE", "AVG_ELAPSED", "MED_ELAPSED", "STD_DEVIATION", "BEST_ELAPSED", "WORST_ELAPSED", "SAMPLE_SIZE", "BATCH_PERF_COUNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    batch_cd,
    AVG(end_dttm - start_dttm) * 1440 + 3 * ( STDDEV(end_dttm - start_dttm) * 1440 )        AS confidence,
    AVG(end_dttm - start_dttm) * 1440                                                       AS avg_elapsed,
    MEDIAN(end_dttm - start_dttm) * 1440                                                    AS med_elapsed,
    STDDEV(end_dttm - start_dttm) * 1440                                                    AS std_deviation,
    MIN(end_dttm - start_dttm) * 1440                                                       AS best_elapsed,
    MAX(end_dttm - start_dttm) * 1440                                                       AS worst_elapsed,
    COUNT(*)                                                                                AS sample_size,
 1                                                                                      AS batch_perf_count
FROM
    ci_batch_run
WHERE
    start_dttm IS NOT NULL
    AND end_dttm IS NOT NULL
GROUP BY
    batch_cd;

-- ----- F1_BATCH_RUN_HIST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_BATCH_RUN_HIST_VW" ("BATCH_CD", "BATCH_JOB_ID", "BATCH_NBR", "BATCH_RERUN_NBR", "BATCH_BUS_DT", "RUN_STATUS", "PROCESS_DT", "START_DTTM", "END_DTTM", "ELAPSED_TIME", "THREADPOOL", "TOTAL_PROCESSED", "TOTAL_ERROR", "BATCH_RUN_COUNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    r.batch_cd,
    j.batch_job_id,
    r.batch_nbr,
    r.batch_rerun_nbr,
    r.batch_bus_dt,
    r.run_status,
    trunc(r.start_dttm)                                             AS process_dt,
    r.start_dttm,
    r.end_dttm,
    ( r.end_dttm - r.start_dttm ) * 1440                            AS elapsed_time,
    decode(TRIM(p.batch_parm_val), '', 'DEFAULT', p.batch_parm_val) AS threadpool,
    SUM(i.rec_proc_cnt)                                           AS total_processed,
    SUM(i.rec_err_cnt)                                              AS total_error,
    1                                                               AS batch_run_count
FROM
    ci_batch_job     j,
    ci_batch_run     r,
    ci_batch_job_prm p,
    ci_batch_inst    i
WHERE
     j.batch_cd = r.batch_cd
    AND j.batch_nbr = r.batch_nbr
    AND j.batch_rerun_nbr = r.batch_rerun_nbr
    AND p.batch_job_id = j.batch_job_id
    AND p.batch_parm_name = 'DIST-THD-POOL'
    AND r.start_dttm IS NOT NULL
    AND i.batch_cd = r.batch_cd
    AND i.batch_nbr = r.batch_nbr
    AND i.batch_rerun_nbr = r.batch_rerun_nbr
GROUP BY
    r.batch_cd,
    j.batch_job_id,
    j.submit_meth_flg,
    j.submit_user_id,
    j.user_id,
    j.batch_job_stat_flg,
    r.batch_nbr,
    r.batch_rerun_nbr,
    r.batch_bus_dt,
    r.run_status,
    trunc(r.start_dttm),
    r.start_dttm,
    r.end_dttm,
    ( r.end_dttm - r.start_dttm ) * 1440,
    decode(TRIM(p.batch_parm_val), '', 'DEFAULT', p.batch_parm_val);

-- ----- F1_BATCH_THD_CAP_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_BATCH_THD_CAP_VW" ("BATCH_CD", "BATCH_NBR", "BATCH_RERUN_NBR", "BATCH_THREAD_NBR", "THREAD_START_DTTM", "THREAD_END_DTTM", "START_DT", "END_DT", "JOB_START_MINS", "JOB_END_MINS", "START_MINUTES", "END_MINUTES", "BATCH_BUS_DT", "BATCH_JOB_ID", "SUBMIT_METH_FLG", "SUBMIT_USER_ID", "THREADPOOL", "BATCH_THREAD_CAP_COUNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  WITH timeperiod AS (
    SELECT
        to_char(trunc(CURRENT_DATE) +((ROWNUM - 1) / 144), 'HH24":"MI')                                                                                                                                                                                                                                  AS
        start_time,
        to_char(trunc(CURRENT_DATE) + ROWNUM / 144, 'HH24":"MI')                                                                                                                                                                                                                                         AS
        end_time,
        to_number(to_char(trunc(CURRENT_DATE) +((ROWNUM - 1) / 144), 'HH24'), '99') * 60 + to_number(to_char(trunc(CURRENT_DATE) +((ROWNUM - 1) /
        144), 'MI'), '99')                                                                                                                                          AS
        start_minutes,
        decode(to_number(to_char(trunc(CURRENT_DATE) + ROWNUM / 144, 'HH24'), '99') * 60 + to_number(to_char(trunc(CURRENT_DATE) + ROWNUM / 144,
        'MI'), '99'), 0, 1440, to_number(to_char(trunc(CURRENT_DATE) + ROWNUM / 144, 'HH24'), '99') * 60 + to_number(to_char(trunc(CURRENT_DATE) +
        ROWNUM / 144, 'MI'), '99')) AS end_minutes
    FROM
        dual
    CONNECT BY
        ROWNUM <= 144
)
SELECT
    i.batch_cd,
    i.batch_nbr,
    i.batch_rerun_nbr,
    i.batch_thread_nbr,
    i.start_dttm                                                                                   AS thread_start_dttm,
    i.end_dttm                                                                                     AS thread_end_dttm,
    trunc(i.start_dttm)                                                                            AS start_dt,
    trunc(i.end_dttm)                                                                              AS end_dt,
    to_number(to_char(i.start_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.start_dttm, 'MI'), 99) AS job_start_mins,
    to_number(to_char(i.end_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.end_dttm, 'MI'), 99)     AS job_end_mins,
    t.start_minutes,
    t.end_minutes,
    r.batch_bus_dt,
    j.batch_job_id,
    j.submit_meth_flg,
    j.submit_user_id,
    decode(TRIM(p.batch_parm_val), '', 'DEFAULT', p.batch_parm_val)                                AS threadpool,
    1                                                                                           AS batch_thread_cap_count
FROM
      ci_batch_inst    i,
      ci_batch_run     r,
      ci_batch_job     j,
      ci_batch_job_prm p,
    timeperiod       t
WHERE
    i.start_dttm IS NOT NULL
    AND i.end_dttm IS NOT NULL
    AND r.batch_cd = i.batch_cd
    AND r.batch_nbr = i.batch_nbr
    AND r.batch_rerun_nbr = i.batch_rerun_nbr
    AND j.batch_cd = i.batch_cd
    AND j.batch_nbr = i.batch_nbr
    AND j.batch_rerun_nbr = i.batch_rerun_nbr
    AND p.batch_job_id = j.batch_job_id
    AND p.batch_parm_name = 'DIST-THD-POOL'
    AND ( ( t.start_minutes <= to_number(to_char(i.start_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.start_dttm, 'MI'), 99)
            AND t.end_minutes >= to_number(to_char(i.end_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.end_dttm, 'MI'), 99) )
          OR ( t.start_minutes <= to_number(to_char(i.start_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.end_dttm, 'MI'), 99)
               AND t.start_minutes >= to_number(to_char(i.start_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.start_dttm, 'MI'), 99) )
          OR ( t.end_minutes >= to_number(to_char(i.start_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.start_dttm, 'MI'), 99)
               AND t.end_minutes <= to_number(to_char(i.start_dttm, 'HH24'), 99) * 60 + to_number(to_char(i.end_dttm, 'MI'), 99) ) );

-- ----- F1_BATCH_THD_HIST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_BATCH_THD_HIST_VW" ("BATCH_CD", "RUN_STATUS", "BATCH_BUS_DT", "BATCH_NBR", "BATCH_RERUN_NBR", "BATCH_THREAD_NBR", "THREAD_STATUS", "BATCH_JOB_ID", "RETRY_COUNT", "THREADPOOL", "TOTAL_PROCESSED", "TOTAL_ERROR", "PROCESS_DT", "THREAD_START_DTTM", "THREAD_END_DTTM", "ELAPSED_TIME", "RECS_PER_MINUTE", "BATCH_RUN_THD_COUNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    r.batch_cd,
    r.run_status,
    r.batch_bus_dt,
    r.batch_nbr,
    r.batch_rerun_nbr,
    t.batch_thread_nbr,
    t.thread_status,
    j.batch_job_id,
    nvl(t.thd_retry_cnt, 0)                                                  AS retry_count,
    decode(TRIM(p.batch_parm_val), '', 'DEFAULT', p.batch_parm_val)          AS threadpool,
    SUM(i.rec_proc_cnt)                                                      AS total_processed,
    SUM(i.rec_err_cnt)                                                       AS total_error,
    trunc(MIN(i.start_dttm))                                                 AS process_dt,
    MIN(i.start_dttm)                                                        AS thread_start_dttm,
    MAX(i.end_dttm)                                                          AS thread_end_dttm,
    ( MAX(i.end_dttm) - MIN(i.start_dttm) ) * 1440                           AS elapsed_time,
    SUM(i.rec_proc_cnt) / ( ( MAX(i.end_dttm) - MIN(i.start_dttm) ) * 1440 ) AS recs_per_minute,
    1                                                               AS batch_run_thd_count
FROM
      ci_batch_run     r,
      ci_batch_thd     t,
      ci_batch_job     j,
      ci_batch_inst    i,
      ci_batch_job_prm p
WHERE
     t.batch_cd = r.batch_cd
    AND t.batch_nbr = r.batch_nbr
    AND t.batch_rerun_nbr = r.batch_rerun_nbr
    AND i.batch_cd = t.batch_cd
    AND i.batch_nbr = t.batch_nbr
    AND i.batch_rerun_nbr = t.batch_rerun_nbr
    AND i.batch_thread_nbr = t.batch_thread_nbr
    AND j.batch_cd = t.batch_cd
    AND j.batch_nbr = t.batch_nbr
    AND j.batch_rerun_nbr = t.batch_rerun_nbr
    AND p.batch_job_id = j.batch_job_id
    AND p.batch_parm_name = 'DIST-THD-POOL'
    AND i.start_dttm IS NOT NULL
    AND i.end_dttm IS NOT NULL
    AND i.end_dttm != i.start_dttm
GROUP BY
    r.batch_cd,
    r.run_status,
    r.batch_bus_dt,
    r.batch_nbr,
    r.batch_rerun_nbr,
    t.batch_thread_nbr,
    t.thread_status,
    j.batch_job_id,
    j.submit_meth_flg,
    j.submit_user_id,
    j.user_id,
    nvl(t.thd_retry_cnt, 0),
    decode(TRIM(p.batch_parm_val), '', 'DEFAULT', p.batch_parm_val);

-- ----- F1_BATCH_VOL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_BATCH_VOL_VW" ("BATCH_CD", "BATCH_NBR", "BATCH_RERUN_NBR", "TOTAL_PROCESSED", "MAX_PROCESSED", "RECS_PER_MINUTE", "BATCH_THD_VOL_COUNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    batch_cd,
    batch_nbr,
    batch_rerun_nbr,
    SUM(total_processed)                                         AS total_processed,
    MAX(total_processed)                                         AS max_processed,
    MIN(recs_per_minute)                                         AS recs_per_minute,
    1                                                            AS batch_thd_vol_count
FROM
      f1_batch_thd_hist_vw
GROUP BY
    batch_cd,
    batch_nbr,
    batch_rerun_nbr;

-- ----- F1_BO_LIFECYCLE_STATUS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_BO_LIFECYCLE_STATUS_VW" ("BUS_OBJ_CD", "LIFE_CYCLE_BO_CD", "BO_STATUS_CD", "BATCH_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT BO2.BUS_OBJ_CD,BO.LIFE_CYCLE_BO_CD,BOSA.BO_STATUS_CD,LCBOS.BATCH_CD  as LC_BATCH_CD
FROM
F1_BUS_OBJ BO2,
F1_BUS_OBJ BO,
F1_BUS_OBJ_STATUS LCBOS,
F1_BUS_OBJ_STATUS_ALG BOSA
WHERE
BO2.LIFE_CYCLE_BO_CD =  BO.LIFE_CYCLE_BO_CD AND
BO.BUS_OBJ_CD = BOSA.BUS_OBJ_CD AND
BOSA.BO_STATUS_SEVT_FLG = 'F1AT' AND
LCBOS.BUS_OBJ_CD = BO.LIFE_CYCLE_BO_CD AND
LCBOS.BO_STATUS_CD = BOSA.BO_STATUS_CD;

-- ----- F1_CAL_FISC_PERIOD_D -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_CAL_FISC_PERIOD_D" ("F1_FISC_PERIOD_KEY", "F1_FISC_PERIOD_FLG", "F1_FISC_PERIOD_IN_YEAR", "F1_FISC_PERIOD_IN_QUARTER", "F1_FISC_PERIOD_START_DT", "F1_FISC_PERIOD_END_DT", "F1_FISC_QUARTER_KEY", "F1_FISC_QUARTER_FLG", "F1_FISC_QUARTER_IN_YEAR", "F1_FISC_QUARTER_START_DT", "F1_FISC_QUARTER_END_DT", "F1_FISC_YEAR", "F1_FISC_YEAR_START_DT", "F1_FISC_YEAR_END_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT distinct F1_FISC_PERIOD_KEY,F1_FISC_PERIOD_FLG,F1_FISC_PERIOD_IN_YEAR,F1_FISC_PERIOD_IN_QUARTER,F1_FISC_PERIOD_START_DT,F1_FISC_PERIOD_END_DT,F1_FISC_QUARTER_KEY,F1_FISC_QUARTER_FLG,F1_FISC_QUARTER_IN_YEAR,F1_FISC_QUARTER_START_DT,F1_FISC_QUARTER_END_DT,F1_FISC_YEAR,F1_FISC_YEAR_START_DT,F1_FISC_YEAR_END_DT from F1_CALENDAR_D where F1_FISC_PERIOD_KEY is not NULL;

-- ----- F1_CAL_FISC_QUARTER_D -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_CAL_FISC_QUARTER_D" ("F1_FISC_QUARTER_KEY", "F1_FISC_QUARTER_FLG", "F1_FISC_QUARTER_IN_YEAR", "F1_FISC_QUARTER_START_DT", "F1_FISC_QUARTER_END_DT", "F1_FISC_YEAR", "F1_FISC_YEAR_START_DT", "F1_FISC_YEAR_END_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT distinct F1_FISC_QUARTER_KEY, F1_FISC_QUARTER_FLG,F1_FISC_QUARTER_IN_YEAR,F1_FISC_QUARTER_START_DT,F1_FISC_QUARTER_END_DT,F1_FISC_YEAR,F1_FISC_YEAR_START_DT,F1_FISC_YEAR_END_DT from F1_CALENDAR_D where F1_FISC_QUARTER_KEY is not NULL ;

-- ----- F1_CAL_FISC_YEAR_D -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_CAL_FISC_YEAR_D" ("F1_FISC_YEAR", "F1_FISC_YEAR_START_DT", "F1_FISC_YEAR_END_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT distinct F1_FISC_YEAR,F1_FISC_YEAR_START_DT,F1_FISC_YEAR_END_DT from F1_CALENDAR_D where F1_FISC_YEAR is not NULL ;

-- ----- F1_CAL_MONTH_D -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_CAL_MONTH_D" ("F1_MONTH_KEY", "F1_MONTH_IN_QUARTER", "F1_MONTH_IN_YEAR", "F1MONTH_ABBR", "F1_MONTH_START_DT", "F1_MONTH_END_DT", "F1_CAL_QUARTER_KEY", "F1_CAL_QUARTER_FLG", "F1_CAL_QUARTER_IN_YEAR", "F1_CAL_QUARTER_START_DT", "F1_CAL_QUARTER_END_DT", "F1_CAL_YEAR", "F1_CAL_YEAR_NAME", "F1_CAL_YEAR_START_DT", "F1_CAL_YEAR_END_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT distinct F1_MONTH_KEY,F1_MONTH_IN_QUARTER,F1_MONTH_IN_YEAR,F1MONTH_ABBR,F1_MONTH_START_DT,F1_MONTH_END_DT,F1_CAL_QUARTER_KEY,F1_CAL_QUARTER_FLG,F1_CAL_QUARTER_IN_YEAR,F1_CAL_QUARTER_START_DT,F1_CAL_QUARTER_END_DT,F1_CAL_YEAR,F1_CAL_YEAR_NAME,F1_CAL_YEAR_START_DT,F1_CAL_YEAR_END_DT from F1_CALENDAR_D;

-- ----- F1_CAL_QUARTER_D -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_CAL_QUARTER_D" ("F1_CAL_QUARTER_KEY", "F1_CAL_QUARTER_FLG", "F1_CAL_QUARTER_IN_YEAR", "F1_CAL_QUARTER_START_DT", "F1_CAL_QUARTER_END_DT", "F1_CAL_YEAR", "F1_CAL_YEAR_NAME", "F1_CAL_YEAR_START_DT", "F1_CAL_YEAR_END_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT distinct F1_CAL_QUARTER_KEY,F1_CAL_QUARTER_FLG,F1_CAL_QUARTER_IN_YEAR,F1_CAL_QUARTER_START_DT,F1_CAL_QUARTER_END_DT,F1_CAL_YEAR,F1_CAL_YEAR_NAME,F1_CAL_YEAR_START_DT,F1_CAL_YEAR_END_DT from F1_CALENDAR_D;

-- ----- F1_CAL_WEEK_D -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_CAL_WEEK_D" ("F1_WEEK_KEY", "F1_WEEK_NAME", "F1_WEEK_IN_YEAR", "F1_WEEK_START_DT", "F1_WEEK_END_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT distinct F1_WEEK_KEY, F1_WEEK_NAME, F1_WEEK_IN_YEAR, F1_WEEK_START_DT, F1_WEEK_END_DT from F1_CALENDAR_D;

-- ----- F1_CAL_YEAR_D -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_CAL_YEAR_D" ("F1_CAL_YEAR", "F1_CAL_YEAR_NAME", "F1_CAL_YEAR_START_DT", "F1_CAL_YEAR_END_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT distinct F1_CAL_YEAR, F1_CAL_YEAR_NAME, F1_CAL_YEAR_START_DT, F1_CAL_YEAR_END_DT from F1_CALENDAR_D;

-- ----- F1_LCBO_AUTO_ALG_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_LCBO_AUTO_ALG_VW" ("LIFE_CYCLE_BO_CD", "BO_STATUS_CD", "ALG_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT 
   BO.LIFE_CYCLE_BO_CD,
   BOSA.BO_STATUS_CD,
   BOSA.ALG_CD
FROM
   F1_BUS_OBJ BO,
   F1_BUS_OBJ_STATUS_ALG BOSA
WHERE
   BO.BUS_OBJ_CD = BOSA.BUS_OBJ_CD
 AND
   BOSA.BO_STATUS_SEVT_FLG = 'F1AT' 
 
 
 
 ;

-- ----- F1_MENU_APP_SVCS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_MENU_APP_SVCS_VW" ("MENU_LINE_ID", "APP_SVC_ID", "LINE_VISIBILITY_SW") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  with 
linesvc as
(
select /*+ materialize leading(a) use_nl(svc key nav a) */ a.menu_line_id, a.app_svc_id item_app_svc_id, s.svc_name, s.app_svc_id, a.nav_opt_cd
from ci_md_menu_item a,
     ci_md_nav key,
     CI_MD_SVC_PRG svc,
     CI_MD_SVC s,
     ci_nav_opt nav
where nav.target_nav_key = key.navigation_key
and key.prog_com_id = svc.prog_com_id
and svc.svc_name = s.svc_name
and a.nav_opt_cd = nav.nav_opt_cd
),
/* MO associated with the line navigation option =  maintenance BPA MO option, Query Portal MO option, MO page service, All-in-one BO portal */
linemo as
(
SELECT /*+ leading(mo) use_nl(key svc mo) */  mo.maint_obj_cd, ' ' scr_cd, a.menu_line_id
from ci_md_menu_item a,
     ci_md_nav key,
     CI_MD_SVC_PRG svc,
     CI_MD_SVC s,
     ci_nav_opt nav,
     ci_md_mo mo
where a.nav_opt_cd = nav.nav_opt_cd
and nav.target_nav_key = key.navigation_key
and key.prog_com_id = svc.prog_com_id
and svc.svc_name = s.svc_name
and mo.svc_name = s.svc_name
union all
select /*+ leading(moopt) */  moopt.maint_obj_cd, nav.scr_cd, a.menu_line_id
from ci_md_menu_item a,
     ci_md_mo_opt moopt,
     ci_nav_opt nav
where nav.nav_opt_type_flg = 'F1SC'
and nav.scr_cd = rpad(moopt.maint_obj_opt_val,12)
and moopt.maint_obj_opt_flg = 'F1MB'
and a.nav_opt_cd = nav.nav_opt_cd
union all
select /*+ leading(boopt) */  bo.maint_obj_cd, nav.scr_cd, a.menu_line_id
from ci_md_menu_item a,
     f1_bus_obj_opt boopt,
     f1_bus_obj bo,
     ci_nav_opt nav
where nav.nav_opt_type_flg = 'F1SC'
and nav.scr_cd = rpad(boopt.bus_obj_opt_val,12)
and boopt.bus_obj_opt_flg = 'F1MB'
and boopt.bus_obj_cd = bo.bus_obj_cd
and a.nav_opt_cd = nav.nav_opt_cd
union all
select /*+ leading(moopt) */ moopt.maint_obj_cd, ' ' scr_cd, a.menu_line_id
from linesvc a,
     ci_md_mo_opt moopt
where a.nav_opt_cd = rpad(moopt.maint_obj_opt_val,32)
and moopt.maint_obj_opt_flg = 'F1QN'
union all
select /*+ leading(mo) */  mo.maint_obj_cd, ' ' scr_cd, a.menu_line_id
from linesvc a,
     ci_md_mo mo,
     CI_MD_SVC s
where a.app_svc_id = s.app_svc_id
and s.svc_name = mo.svc_name
union all
select /*+ leading(boopt) */  bo.maint_obj_cd, ' ' scr_cd, a.menu_line_id
from linesvc a,
     f1_bus_obj bo,
     f1_bus_obj_opt boopt
where a.nav_opt_cd = rpad(boopt.bus_obj_opt_val,32)
and bo.bus_obj_cd = boopt.bus_obj_cd
and boopt.bus_obj_opt_flg = 'F1NO'
union all
select /*+ leading(mo) */  mo.maint_obj_cd, ' ' scr_cd, a.menu_line_id
from ci_md_menu_item a,
     ci_md_mo mo,
     CI_MD_SVC s
where a.app_svc_id > ' ' 
and a.app_svc_id = s.app_svc_id
and s.svc_name = mo.svc_name
),
/* all MOs include related MOs via MO option */
linemos as
(
select a.maint_obj_cd, a.scr_cd, a.menu_line_id
from linemo a
union
select /*+ leading(a) */ b.maint_obj_cd, ' ' scr_cd, a.menu_line_id
from linemo a, 
     ci_md_mo_opt moopt,
     ci_md_mo b
where a.maint_obj_cd = moopt.maint_obj_cd
and moopt.maint_obj_opt_flg = 'F1CH'
and b.maint_obj_cd = rpad(moopt.maint_obj_opt_val,12)
),
linebos as 
(
select /*+ leading(a) */ bo.bus_obj_cd, bo.app_svc_id, a.menu_line_id 
from linemos a,
     f1_bus_obj bo
where a.maint_obj_cd = bo.maint_obj_cd
and not exists 
(
select /*+ no_unnest  */ 'x' 
from f1_bus_obj_opt boopt, 
     ci_nav_opt bonav, 
     ci_md_menu_item boitm
where a.scr_cd > ' ' 
and bo.bus_obj_cd = boopt.bus_obj_cd 
and boopt.bus_obj_opt_flg = 'F1MB' 
and a.scr_cd <> rpad(boopt.bus_obj_opt_val,12)
and rpad(boopt.bus_obj_opt_val,12) = bonav.scr_cd 
and bonav.nav_opt_cd = boitm.nav_opt_cd 
)     
),
/* navigation options associated with the line = directly and via the BOs of the line MO */
linenavopts as
(
select a.menu_line_id, a.nav_opt_cd
from ci_md_menu_item a
union 
select /*+ leading(boopt) */ a.menu_line_id, rpad(boopt.bus_obj_opt_val,32) nav_opt_cd
from linebos a,
     f1_bus_obj_opt boopt
where a.bus_obj_cd = boopt.bus_obj_cd
and boopt.bus_obj_opt_flg = 'F1NO'
),
/* portals associated with the line */
linenavportals as 
(
select /*+ leading(a) */ a.menu_line_id, prtl.portal_cd, s.app_svc_id, prtl.prog_com_id 
from linenavopts a,
     ci_nav_opt nav,
     ci_md_nav key,
     ci_portal prtl,
     CI_MD_SVC_PRG svc,
     CI_MD_SVC s     
where a.nav_opt_cd = nav.nav_opt_cd
and nav.target_nav_key = key.navigation_key
and key.prog_com_id = prtl.prog_com_id 
and key.prog_com_id = svc.prog_com_id
and svc.svc_name = s.svc_name
),
lineportals as 
(
select a.menu_line_id, a.portal_cd, a.app_svc_id, a.prog_com_id
from linenavportals a
union all
select /*+ leading(prtlo) */ a.menu_line_id, a.portal_cd, s.app_svc_id, prtl.prog_com_id
from linenavportals a,
     ci_portal_opt prtlo,
     ci_portal prtl,
     CI_MD_SVC_PRG svc,
     CI_MD_SVC s        
where a.portal_cd = prtlo.portal_cd
and prtlo.portal_opt_flg = 'F1RP'
and rpad(prtlo.portal_opt_val,12) = prtl.portal_cd 
and prtl.prog_com_id = svc.prog_com_id
and svc.svc_name = s.svc_name
)
select distinct menu_line_id, app_svc_id, line_visibility_sw
from 
(
/* menu line and items */
/* */
/* application service directly defined on the menu line */
select a.menu_line_id, 'MENU_ITEM' itemtype, a.menu_item_id item, a.app_svc_id app_svc_id, 'Y' line_visibility_sw 
from ci_md_menu_item a
where a.app_svc_id > ' '
union all
/* application service of the page or portal defined on the menu line */
select menu_line_id, 'SVC_NAME' itemtype, linesvc.svc_name item, linesvc.app_svc_id, 'Y' line_visibility_sw
from linesvc
union all
/* application services associated with all portals of all navigation options. Inlcudes all BO maintenance portals for the MO. */
select menu_line_id, 'PORTAL' itemtype, a.portal_cd item, a.app_svc_id, ' ' line_visibility_sw
from lineportals a
union all 
/* application services associated with all zones of all portals */
select /*+ leading(a) */ a.menu_line_id, 'ZONE' item_type, zone.zone_cd item, zone.app_svc_id, ' ' line_visibility_sw
from lineportals a,
     ci_portal_zone pz,
     ci_zone zone
where a.portal_cd = pz.portal_cd 
and pz.zone_cd = zone.zone_cd 
union all
/* application services associated with all zones of all tab portals of all portals */
select /*+ leading(a) */ a.menu_line_id, 'ZONE' item_type, zone.zone_cd item, zone.app_svc_id, ' ' line_visibility_sw
from lineportals a,
     ci_md_prg_tab q,
     ci_portal b,
     ci_md_nav nav,
     CI_MD_PRG_VAR var,
     ci_portal_zone pz,
     ci_zone zone
where a.prog_com_id = q.prog_com_id
and q.navigation_key = nav.navigation_key
and nav.prog_com_id = var.PROG_COM_ID
and var.var_name = 'portalName          '
and trim(var.VAR_VAL) = trim(b.portal_cd)
and b.portal_cd <> a.portal_cd
and b.portal_cd = pz.portal_cd 
and pz.zone_cd = zone.zone_cd 
union all
select /*+ leading(var) */ distinct a.menu_line_id, 'ZONE' item_type, zone.zone_cd item, zone.app_svc_id, ' ' line_visibility_sw
from ci_md_menu_item a,
     ci_nav_opt nav,
     ci_md_nav key,
     ci_md_prg_tab tab,
     ci_md_nav tabkey,
     ci_md_prg_var var,
     ci_portal prtl,
     ci_portal_zone pz,
     ci_zone zone     
where a.nav_opt_cd = nav.nav_opt_cd
and nav.target_nav_key = key.navigation_key
and key.prog_com_id = tab.prog_com_id
and tab.navigation_key = tabkey.navigation_key
and tabkey.prog_com_id = var.prog_com_id
and var.var_name = 'PORTAL'
and rpad(var.var_val,12) = prtl.portal_cd
and prtl.portal_cd = pz.portal_cd
and pz.zone_cd = zone.zone_cd
union all
/* application services associated with the MO */
select /*+ leading(a) */ a.menu_line_id, 'MO' itemtype, a.maint_obj_cd item, s.app_svc_id, ' ' line_visibility_sw 
from linemos a,
     ci_md_mo mo,
     CI_MD_SVC s
where a.maint_obj_cd = mo.maint_obj_cd
and mo.svc_name = s.svc_name
union all
/* application services associated with all BOs */
select bo.menu_line_id, 'BO' itemtype, bo.bus_obj_cd item, bo.app_svc_id, ' ' line_visibility_sw
from linebos bo
where bo.app_svc_id > ' '
union all
/* application services related to all BOs */
select /*+ leading(boopt) */ a.menu_line_id, 'APP SVC' itemtype, a.bus_obj_cd item, svc.app_svc_id,  ' ' line_visibility_sw
from linebos a,
     f1_bus_obj_opt boopt,
     sc_app_service svc
where a.bus_obj_cd = boopt.bus_obj_cd
and boopt.bus_obj_opt_flg = 'F1SV'
and svc.app_svc_id = rpad(boopt.bus_obj_opt_val,20)
union all
/* application service of the item BPA script */
select /*+ leading(a) */ a.menu_line_id, 'BPA' itemtype, q.scr_cd item, q.app_svc_id, ' ' line_visibility_sw 
from ci_md_menu_item a,
     ci_scr q,
     ci_nav_opt nav
where nav.scr_cd = q.scr_cd
and q.app_svc_id > ' '
and a.nav_opt_cd = nav.nav_opt_cd
union all
/* detail fixed page from a summary fixed page */
Select /*+ leading(elm) */ a.menu_line_id, 'RELATED_SVC' itemtype, svc.svc_name item, svc.app_svc_id, ' ' line_visibility_sw
from linesvc a, ci_md_svc_prg tabsvcprg, ci_md_prg_tab tab, ci_md_nav elmpgnav, ci_md_prg_elem elmpg, ci_md_prg_com secpg, ci_md_prg_sec sec, ci_md_prg_elem elm, ci_md_nav nav, ci_md_svc_prg spg, ci_md_svc svc     
where tabsvcprg.svc_name = a.svc_name
and tab.prog_com_id = tabsvcprg.prog_com_id 
and elmpgnav.navigation_key = tab.navigation_key 
and elmpg.prog_com_id = elmpgnav.prog_com_id 
and elmpg.url = secpg.prog_com_name
and secpg.prog_com_id = sec.prog_com_id
and sec.prog_com_id = elm.prog_com_id 
and elm.script > ' '
and elm.script not like '%Search%'
and elm.script like '%'||trim(nav.navigation_key)||'%'
and not exists (select 'x' from ci_nav_opt npt, ci_md_menu_item itm where npt.target_nav_key = nav.navigation_key and npt.nav_opt_cd =  itm.nav_opt_cd)
and spg.prog_com_id = nav.prog_com_id
and svc.svc_name = spg.svc_name
and nav.owner_flg = elm.owner_flg
and nav.navigation_key in ('algorithmTab','toDoEntryMaint')
);

-- ----- F1_TD_FK_CHAR_ENTRY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_TD_FK_CHAR_ENTRY_VW" ("TD_ENTRY_ID", "CHAR_TYPE_CD", "CHAR_VAL_FK1", "CHAR_VAL_FK2", "CHAR_VAL_FK3", "CHAR_VAL_FK4", "CHAR_VAL_FK5") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT 
      C.TD_ENTRY_ID,
      CT.CHAR_TYPE_CD,
      C.CHAR_VAL_FK1,
      C.CHAR_VAL_FK2,
      C.CHAR_VAL_FK3,
      C.CHAR_VAL_FK4,
      C.CHAR_VAL_FK5
FROM
      CI_TD_ENTRY_CHA C,
      CI_CHAR_TYPE CT
WHERE
          C.CHAR_TYPE_CD = CT.CHAR_TYPE_CD
      AND CT.CHAR_TYPE_FLG = 'FKV'
 
 
 
 ;

-- ----- W1_ASSET_CUR_DPOS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ASSET_CUR_DPOS_VW" ("ASSET_ID", "EFF_DTTM", "ASSET_DPOS_FLG", "ATTCH_TO_ASSET_ID", "ATTCH_TO_ASSET_DPOS_FLG", "NODE_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT A.ASSET_ID, 
A.EFF_DTTM,
       A.ASSET_DPOS_FLG,         
       ' ' AS ATTCH_TO_ASSET_ID,
       ' ' ATTCH_TO_ASSET_DPOS_FLG,
	    A.NODE_ID
FROM W1_ASSET_NODE A
WHERE A.CURR_NODE_ID IS NOT NULL
UNION
SELECT A.ASSET_ID, 
	    A.EFF_DTTM,
       A.ASSET_DPOS_FLG,         
       A.ATTCH_TO_ASSET_ID,
       B.ASSET_DPOS_FLG AS ATTCH_TO_ASSET_DPOS_FLG,
	    B.NODE_ID
FROM W1_ASSET_NODE A,
       W1_ASSET_NODE B
WHERE B.CURR_ASSET_ID = A.CURR_ATTCH_TO_ASSET_ID
 
 ;

-- ----- W1_BI_ACTIVITY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_ACTIVITY_VW" ("ACT_ID", "BO_STATUS_CD", "BO_STATUS_REASON_CD", "CRE_DTTM", "USER_ID", "DESCR100", "ACT_TYPE_CD", "PRNT_ACT_ID", "NODE_ID", "ASSET_ID", "WO_ID", "ACTVN_DTTM", "WORK_WIN_START_DTTM", "WORK_WIN_END_DTTM", "ACT_DPOS_FLG", "SERVICE_CLASS_CD", "WORK_REQ_ID", "REQUESTOR_ID", "DELIVER_TO_LOC", "W1_CREW_ID", "PHASE_FLG", "WORK_PRIORITY_FLG", "DESCRLONG", "TMPL_ACT_ID", "PRJ_ID", "OUTAGE_TYPE_FLG", "BACK_LOG_GRP_FLG", "HELD_FOR_PARTS_FLG", "MAT_DISP_ID", "MAINT_SCHED_ID", "MAINT_TRIGGER_ID", "MEASUREMENT_ID", "ORIGINAL_WORK_DT", "ANNIVERSARY_DT", "ANNIVERSARY_VALUE", "MEASUREMENT_UOM_CD", "EMERGENCY_FLG", "ACT_NUM", "PLANNER_CD", "MAINT_EVENT_ID", "APPROVAL_PROF_CD", "WORK_LOC_ID", "TOTAL_PRIORITY", "WORK_CLASS_CD", "WORK_CATEGORY_CD", "COMPLIANCE_TYPE_CD", "COMPLIANCE_DATE", "COMPLIANCE_UPD_DATE_RSN_FLG", "SVC_HIST_ID", "SEQ_NUM", "OWNING_ACCESS_GRP_CD", "REQUIRED_BY_DT", "ACT_CNT", "FIELD_ACT_CNT", "CONSTR_ACT_CNT", "MAINT_ACT_CNT", "CM_ACT_CNT", "PM_ACT_CNT", "OVERDUE_ACT_CNT", "OVERDUE_MAINT_ACT_CNT", "OVERDUE_CONSTR_ACT_CNT", "OVERDUE_FIELD_ACT_CNT", "OVERDUE_PM_ACT_CNT", "CYCLES_OVERDUE_PM_ACT_CNT", "OVERDUE_CM_ACT_CNT", "OPEN_ACT_CNT", "OPEN_MAINT_ACT_CNT", "OPEN_CONSTR_ACT_CNT", "PLANNED_ACT_CNT", "WAIT_SCHED_ACT_CNT", "HELD_MAINT_ACT_CNT", "HELD_CM_ACT_CNT", "HELD_PM_ACT_CNT", "HELD_COMPLIANCE_ACT_CNT", "HELD_CONSTR_ACT_CNT", "COMPLIANCE_ACT_CNT", "OPEN_COMPLIANCE_ACT_CNT", "DUE_1WK_OPEN_COMPL_ACT_CNT", "DUE_30DY_OPEN_COMPL_ACT_CNT", "LATE_OPEN_COMPL_ACT_CNT", "LATE_CMPL_COMPL_ACT_CNT", "ONTIME_CMPL_COMPL_ACT_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
     act_id,
     bo_status_cd,
     bo_status_reason_cd,
     cre_dttm,
     user_id,
     descr100,
     act_type_cd,
     prnt_act_id,
     node_id,
     asset_id,
     wo_id,
     actvn_dttm,
     work_win_start_dttm,
     work_win_end_dttm,
     act_dpos_flg,
     service_class_cd,
     work_req_id,
     requestor_id,
     deliver_to_loc,
     w1_crew_id,
     phase_flg,
     work_priority_flg,
     descrlong,
     tmpl_act_id,
     prj_id,
     outage_type_flg,
     back_log_grp_flg,
     held_for_parts_flg,
     mat_disp_id,
     maint_sched_id,
     maint_trigger_id,
     measurement_id,
     original_work_dt,
     anniversary_dt,
     anniversary_value,
     measurement_uom_cd,
     emergency_flg,
     act_num,
     planner_cd,
     maint_event_id,
     approval_prof_cd,
     work_loc_id,
     total_priority,
     work_class_cd,
     work_category_cd,
     compliance_type_cd,
     compliance_date,
     compliance_upd_date_rsn_flg,
     svc_hist_id,
     seq_num,
     owning_access_grp_cd,
     required_by_dt,
     act_cnt,
     field_act_cnt,
     constr_act_cnt,
     maint_act_cnt,
     cm_act_cnt,
     pm_act_cnt,
     overdue_act_cnt,
     CASE
         WHEN maint_act_cnt = 1
              AND overdue_act_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_maint_act_cnt,
     CASE
         WHEN constr_act_cnt = 1
              AND overdue_act_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_constr_act_cnt,
     CASE
         WHEN field_act_cnt = 1
              AND overdue_act_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_field_act_cnt,
     CASE
         WHEN pm_act_cnt = 1
              AND overdue_act_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_pm_act_cnt,
     CASE
         WHEN open_act_cnt = 1
              AND pm_act_cnt = 1
              AND overdue_no_stat_act_cnt = 1 THEN nvl( (
             SELECT
                 CASE
                     WHEN(mt.f1_years > 0
                            OR mt.f1_months > 0)
                          AND mt.f1_days = 0 THEN floor(months_between(current_date,original_work_dt) / (f1_years * 12 + f1_months
                          ) )
                     ELSE floor( (current_date - original_work_dt) / (f1_years * 365 + f1_months * 30 + f1_days) )
                 END
             FROM
                 w1_maint_trigger mt
             WHERE
                 mt.maint_trigger_id = a.maint_trigger_id
                 AND mt.trigger_type_flg IN(
                     'W1CA','W1CI'
                 )
         ),0)
         ELSE 0
     END AS cycles_overdue_pm_act_cnt,
     CASE
         WHEN cm_act_cnt = 1
              AND overdue_act_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_cm_act_cnt,
     open_act_cnt,
     CASE
         WHEN maint_act_cnt = 1
              AND open_act_cnt = 1 THEN 1
         ELSE 0
     END AS open_maint_act_cnt,
     CASE
         WHEN constr_act_cnt = 1
              AND open_act_cnt = 1 THEN 1
         ELSE 0
     END AS open_constr_act_cnt,
     planned_act_cnt,
     wait_sched_act_cnt,
     CASE
         WHEN maint_act_cnt = 1
              AND planned_act_cnt = 1
              AND held_for_parts_flg = 'W1YS' THEN 1
         ELSE 0
     END AS held_maint_act_cnt,
     CASE
         WHEN cm_act_cnt = 1
              AND planned_act_cnt = 1
              AND held_for_parts_flg = 'W1YS' THEN 1
         ELSE 0
     END AS held_cm_act_cnt,
     CASE
         WHEN pm_act_cnt = 1
              AND planned_act_cnt = 1
              AND held_for_parts_flg = 'W1YS' THEN 1
         ELSE 0
     END AS held_pm_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND planned_act_cnt = 1
              AND held_for_parts_flg = 'W1YS' THEN 1
         ELSE 0
     END AS held_compliance_act_cnt,
     CASE
         WHEN constr_act_cnt = 1
              AND planned_act_cnt = 1
              AND held_for_parts_flg = 'W1YS' THEN 1
         ELSE 0
     END AS held_constr_act_cnt,
     compliance_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND open_act_cnt = 1 THEN 1
         ELSE 0
     END AS open_compliance_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND open_act_cnt = 1
              AND compliance_date - current_date <= 7 THEN 1
         ELSE 0
     END AS due_1wk_open_compl_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND open_act_cnt = 1
              AND compliance_date - current_date <= 30 THEN 1
         ELSE 0
     END AS due_30dy_open_compl_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND open_act_cnt = 1
              AND compliance_date < current_date THEN 1
         ELSE 0
     END AS late_open_compl_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND completed_act_cnt = 1
              AND compliance_date < completion_dt THEN 1
         ELSE 0
     END AS late_cmpl_compl_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND completed_act_cnt = 1
              AND compliance_date >= completion_dt THEN 1
         ELSE 0
     END AS ontime_cmpl_compl_act_cnt
 FROM
     (
         SELECT
             ac.act_id,
             ac.bo_status_cd,
             ac.bo_status_reason_cd,
             ac.cre_dttm,
             ac.user_id,
             ac.descr100,
             ac.act_type_cd,
             ac.prnt_act_id,
             ac.node_id,
             ac.asset_id,
             ac.wo_id,
             ac.actvn_dttm,
             ac.work_win_start_dttm,
             ac.work_win_end_dttm,
             ac.act_dpos_flg,
             ac.service_class_cd,
             ac.work_req_id,
             ac.requestor_id,
             ac.deliver_to_loc,
             ac.w1_crew_id,
             ac.phase_flg,
             ac.work_priority_flg,
             ac.descrlong,
             ac.tmpl_act_id,
             ac.prj_id,
             ac.outage_type_flg,
             ac.back_log_grp_flg,
             ac.held_for_parts_flg,
             ac.mat_disp_id,
             ac.maint_sched_id,
             ac.maint_trigger_id,
             ac.measurement_id,
             ac.original_work_dt,
             ac.anniversary_dt,
             ac.anniversary_value,
             ac.measurement_uom_cd,
             ac.emergency_flg,
             ac.act_num,
             ac.planner_cd,
             ac.maint_event_id,
             ac.approval_prof_cd,
             ac.work_loc_id,
             ac.total_priority,
             ac.work_class_cd,
             ac.work_category_cd,
             ac.compliance_type_cd,
             ac.compliance_date,
             ac.compliance_upd_date_rsn_flg,
             ac.svc_hist_id,
             ac.seq_num,
             ac.owning_access_grp_cd,
             ac.required_by_dt,
             act.constr_related_flg,
             wo.work_type_flg,
             1 AS act_cnt,
             CASE
                 WHEN act.category_flg = 'W1FA' THEN 1
                 ELSE 0
             END AS field_act_cnt,
             CASE
                 WHEN act.constr_related_flg = 'W1YS' THEN 1
                 ELSE 0
             END AS constr_act_cnt,
             CASE
                 WHEN wo.wo_id IS NOT NULL
                      AND wo.work_type_flg IN (
                     'W1PM',
                     'W1RG'
                 ) THEN 1
                 ELSE 0
             END AS maint_act_cnt,
             CASE
                 WHEN wo.wo_id IS NOT NULL
                      AND wo.work_type_flg = 'W1PM' THEN 1
                 ELSE 0
             END AS pm_act_cnt,
             CASE
                 WHEN wo.wo_id IS NOT NULL
                      AND wo.work_type_flg = 'W1RG' THEN 1
                 ELSE 0
             END AS cm_act_cnt,
             CASE
                 WHEN act.category_flg = 'W1FA'
                      AND ac.bo_status_cd IN (
                     'WORK'
                 )
                      AND trunc(ac.work_win_end_dttm) < current_date THEN 1
                 WHEN ac.wo_id IS NOT NULL
                      AND ac.bo_status_cd IN (
                     'ACTIVE',
                     'INPROGRESS'
                 )
                      AND wo.work_type_flg = 'W1PM'
                      AND ac.original_work_dt < current_date THEN 1
                 WHEN ac.wo_id IS NOT NULL
                      AND ac.bo_status_cd IN (
                     'ACTIVE',
                     'INPROGRESS'
                 )
                      AND ac.required_by_dt < current_date THEN 1
                 ELSE 0
             END AS overdue_act_cnt,
             CASE
                 WHEN act.category_flg = 'W1FA'
                      AND trunc(ac.work_win_end_dttm) < current_date THEN 1
                 WHEN ac.wo_id IS NOT NULL
                      AND wo.work_type_flg = 'W1PM'
                      AND ac.original_work_dt < current_date THEN 1
                 WHEN ac.wo_id IS NOT NULL
                      AND ac.required_by_dt < current_date THEN 1
                 ELSE 0
             END AS overdue_no_stat_act_cnt,
             CASE
                 WHEN ac.bo_status_cd IN (
                     'PLANNING',
                     'PENDAPPROVAL',
                     'APPROVED',
                     'ACTIVE',
                     'INPROGRESS',
                     'PENDING',
                     'SENT',
                     'WORK'
                 ) THEN 1
                 ELSE 0
             END AS open_act_cnt,
             CASE
                 WHEN ac.bo_status_cd IN (
                     'APPROVED',
                     'ACTIVE'
                 )
                      AND (
                     SELECT
                         COUNT(*)
                     FROM
                         w1_act_resrc_reqmt arr,
                         w1_crew_shift_act_sched csa,
                         w1_crew_shift cs
                     WHERE
                         arr.act_id = ac.act_id
                         AND csa.act_resrc_reqmt_id = arr.act_resrc_reqmt_id
                         AND cs.crew_shift_id = csa.crew_shift_id
                         AND cs.bo_status_cd IN ( 'ACTIVE','PLANNING')
                 ) = 0 THEN 1
                 ELSE 0
             END AS wait_sched_act_cnt,
             CASE
                 WHEN ac.bo_status_cd IN (
                     'APPROVED',
                     'ACTIVE'
                 ) THEN 1
                 ELSE 0
             END AS planned_act_cnt,
             CASE
                 WHEN ac.bo_status_cd = 'COMPLETE' THEN 1
                 ELSE 0
             END AS completed_act_cnt,
             CASE
                 WHEN ac.bo_status_cd = 'COMPLETE' THEN trunc(ac.status_upd_dttm)
                 ELSE NULL
             END AS completion_dt,
             CASE
                 WHEN ac.compliance_type_cd IS NOT NULL THEN 1
                 ELSE 0
             END AS compliance_act_cnt
         FROM
             w1_activity ac
             JOIN w1_activity_type act ON act.act_type_cd = ac.act_type_cd
             LEFT OUTER JOIN w1_wo wo ON wo.wo_id = ac.wo_id
      )a;

-- ----- W1_BI_ASSETACTCOST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_ASSETACTCOST_VW" ("ACT_ID", "ASSET_ID", "W1_FT_ID", "W1_RESRC_CLASS_FLG", "COST_CATEGORY_CD", "WO_ID", "NODE_ID", "ACT_CRE_DTTM", "RENEWAL_FLG", "MAINTENANCE_COST", "RENEWAL_COST", "W1_BI_TOTAL_COST", "FAILURE_REPAIR_COST", "FAILURE_COUNT", "ACQUISITION_DT", "IN_SERVICE_DT", "PREDCTD_WEAR_OUT_DT", "W1_CREW_ID", "FINISH_DTTM", "ASSET_ACT_COUNT", "ACTVN_DTTM", "ORIGINAL_WORK_DT", "REQUIRED_BY_DT", "WORK_WIN_START_DTTM", "WORK_WIN_END_DTTM", "FT_CRE_DTTM", "EXPENSE_CD", "COST_CENTER_CD", "PRJ_ID", "PLANNER_CD", "TMPL_ACT_ID", "OWNING_ACCESS_GRP_CD", "USER_ID", "WORK_CLASS_CD", "WORK_CATEGORY_CD", "ACT_TYPE_CD", "SERVICE_CLASS_CD", "MAINTENANCE_LABOR_COST", "MAINTENANCE_MATL_COST", "MAINTENANCE_EQUIP_COST", "MAINTENANCE_ODC_COST", "MAINTENANCE_CM_COST", "MAINTENANCE_CM_LABOR_COST", "MAINTENANCE_CM_MATL_COST", "MAINTENANCE_CM_EQUIP_COST", "MAINTENANCE_CM_ODC_COST", "MAINTENANCE_PM_COST", "MAINTENANCE_PM_LABOR_COST", "MAINTENANCE_PM_MATL_COST", "MAINTENANCE_PM_EQUIP_COST", "MAINTENANCE_PM_ODC_COST", "MAINTENANCE_EM_COST", "MAINTENANCE_EM_LABOR_COST", "MAINTENANCE_EM_MATL_COST", "MAINTENANCE_EM_EQUIP_COST", "MAINTENANCE_EM_ODC_COST", "TOTAL_EST_COST", "EST_LABOR_COST", "EST_MATERIAL_COST", "EST_EQUIPMENT_COST", "EST_ODC_COST", "PLANNED_EST_COST", "PLANNED_EST_LABOR_COST", "PLANNED_EST_MATL_COST", "PLANNED_EST_EQUIP_COST", "PLANNED_EST_ODC_COST", "COMPL_EST_COST", "COMPL_EST_LABOR_COST", "COMPL_EST_MATL_COST", "COMPL_EST_EQUIP_COST", "COMPL_EST_ODC_COST", "COMPL_ACTUAL_COST", "COMPL_ACTUAL_LABOR_COST", "COMPL_ACTUAL_MATL_COST", "COMPL_ACTUAL_EQUIP_COST", "COMPL_ACTUAL_ODC_COST", "OPEN_ACTUAL_COST", "OPEN_ACTUAL_LABOR_COST", "OPEN_ACTUAL_MATL_COST", "OPEN_ACTUAL_EQUIP_COST", "OPEN_ACTUAL_ODC_COST") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
      act_id,
      asset_id,
      w1_ft_id,
      w1_resrc_class_flg,
      cost_category_cd,
      wo_id,
      node_id,
      act_cre_dttm,
      renewal_flg,
      maintenance_cost,
      renewal_cost,
      w1_bi_total_cost,
      failure_repair_cost,
      failure_count,
      acquisition_dt,
      in_service_dt,
      predctd_wear_out_dt,
      w1_crew_id,
      finish_dttm,
      asset_act_count,
      actvn_dttm,
      original_work_dt,
      required_by_dt,
      work_win_start_dttm,
      work_win_end_dttm,
      ft_cre_dttm,
      expense_cd,
	  cost_center_cd,
      prj_id,
      planner_cd,
      tmpl_act_id,
      owning_access_grp_cd,
      user_id,
      work_class_cd,
      work_category_cd,
      act_type_cd,
      service_class_cd,
      CASE
          WHEN labor_cnt = 1 THEN 
              maintenance_cost
          ELSE 
              0
      END AS maintenance_labor_cost,
      CASE
          WHEN material_cnt = 1 THEN 
               maintenance_cost
          ELSE 
               0
      END AS maintenance_matl_cost,
      CASE
          WHEN equipment_cnt = 1 THEN 
               maintenance_cost
          ELSE
                0
      END AS maintenance_equip_cost,
      CASE
          WHEN odc_cnt = 1 THEN 
              maintenance_cost
          ELSE 
              0
      END AS maintenance_odc_cost,
      CASE
          WHEN cm_act_cnt = 1 THEN 
               maintenance_cost
          ELSE
                0
      END AS maintenance_cm_cost,
      CASE
          WHEN cm_act_cnt = 1
               AND labor_cnt = 1 THEN 
            maintenance_cost
          ELSE
             0
      END AS maintenance_cm_labor_cost,
      CASE
          WHEN cm_act_cnt = 1
               AND material_cnt = 1 THEN
             maintenance_cost
          ELSE 
            0
      END AS maintenance_cm_matl_cost,
      CASE
          WHEN cm_act_cnt = 1
               AND equipment_cnt = 1 THEN 
               maintenance_cost
          ELSE 
               0
      END AS maintenance_cm_equip_cost,
      CASE
          WHEN cm_act_cnt = 1
               AND odc_cnt = 1 THEN
                 maintenance_cost
          ELSE 
              0
      END AS maintenance_cm_odc_cost,
      CASE
          WHEN pm_act_cnt = 1 THEN 
               maintenance_cost
          ELSE 
               0
      END AS maintenance_pm_cost,
      CASE
          WHEN pm_act_cnt = 1
               AND labor_cnt = 1 THEN 
                maintenance_cost
          ELSE 
               0
      END AS maintenance_pm_labor_cost,
      CASE
          WHEN pm_act_cnt = 1
               AND material_cnt = 1 THEN 
               maintenance_cost
          ELSE 
               0
      END AS maintenance_pm_matl_cost,
      CASE
          WHEN pm_act_cnt = 1
               AND equipment_cnt = 1 THEN 
              maintenance_cost
          ELSE 
              0
      END AS maintenance_pm_equip_cost,
      CASE
          WHEN pm_act_cnt = 1
               AND odc_cnt = 1 THEN 
               maintenance_cost
          ELSE 
            0
      END AS maintenance_pm_odc_cost,
      CASE
          WHEN emergency_flg = 'W1YS' THEN
            maintenance_cost
          ELSE
            0
      END AS maintenance_em_cost,
      CASE
          WHEN emergency_flg = 'W1YS'
               AND labor_cnt = 1 THEN 
            maintenance_cost
          ELSE 
            0
      END AS maintenance_em_labor_cost,
      CASE
          WHEN emergency_flg = 'W1YS'
               AND material_cnt = 1 THEN
              maintenance_cost
          ELSE 
              0
      END AS maintenance_em_matl_cost,
      CASE
          WHEN emergency_flg = 'W1YS'
               AND equipment_cnt = 1 THEN 
              maintenance_cost
          ELSE 
              0
      END AS maintenance_em_equip_cost,
      CASE
          WHEN emergency_flg = 'W1YS'
               AND odc_cnt = 1 THEN
            maintenance_cost
          ELSE
           0
      END AS maintenance_em_odc_cost,
      total_est_cost,
      CASE
          WHEN labor_cnt = 1 THEN 
               total_est_cost
          ELSE
              0
      END AS est_labor_cost,
      CASE
          WHEN material_cnt = 1 THEN 
               total_est_cost
          ELSE 
              0
      END AS est_material_cost,
      CASE
          WHEN equipment_cnt = 1 THEN 
          total_est_cost
          ELSE 
         0
      END AS est_equipment_cost,
      CASE
        WHEN odc_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS est_odc_cost,
      CASE
        WHEN planned_act_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS planned_est_cost,
      CASE
          WHEN planned_act_cnt = 1
             AND labor_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS planned_est_labor_cost,
     CASE
          WHEN planned_act_cnt = 1
             AND material_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS planned_est_matl_cost,
      CASE
          WHEN planned_act_cnt = 1
             AND equipment_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS planned_est_equip_cost,
      CASE
          WHEN planned_act_cnt = 1
             AND odc_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS planned_est_odc_cost,
      CASE
        WHEN completed_act_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS compl_est_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND labor_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS compl_est_labor_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND material_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS compl_est_matl_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND equipment_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS compl_est_equip_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND odc_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS compl_est_odc_cost,
      CASE
        WHEN completed_act_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS compl_actual_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND labor_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS compl_actual_labor_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND material_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS compl_actual_matl_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND equipment_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS compl_actual_equip_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND odc_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS compl_actual_odc_cost,
      CASE
        WHEN open_act_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS open_actual_cost,
      CASE
          WHEN open_act_cnt = 1
             AND labor_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS open_actual_labor_cost,
      CASE
          WHEN open_act_cnt = 1
             AND material_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS open_actual_matl_cost,
      CASE
          WHEN open_act_cnt = 1
             AND equipment_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS open_actual_equip_cost,
      CASE
          WHEN open_act_cnt = 1
             AND odc_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS open_actual_odc_cost
  FROM
      (
          SELECT
              act_id,
              asset_id,
              w1_ft_id,
              w1_resrc_class_flg,
              wo_id,
              node_id,
              act_cre_dttm,
              renewal_flg,
              failure_repair_cost,
              failure_count,
              acquisition_dt,
              in_service_dt,
              predctd_wear_out_dt,
              w1_crew_id,
              finish_dttm,
              --asset_act_count,
              actvn_dttm,
              original_work_dt,
              required_by_dt,
              work_win_start_dttm,
              work_win_end_dttm,
              maintenance_cost,
              renewal_cost,
              w1_bi_total_cost,
              ft_cre_dttm,
              expense_cd,
			  cost_center_cd,
              prj_id,
              planner_cd,
              tmpl_act_id,
              owning_access_grp_cd,
              user_id,
              work_class_cd,
              work_category_cd,
              act_type_cd,
              service_class_cd,
            1 AS asset_act_count,
              CASE
                WHEN w1_resrc_class_flg = 'W1CR' THEN
                    1
                ELSE
                    0
              END AS labor_cnt,
              CASE
                WHEN w1_resrc_class_flg = 'W1MT' THEN
                    1
                ELSE
                    0
              END AS material_cnt,
              CASE
                WHEN w1_resrc_class_flg = 'W1EQ' THEN
                    1
                ELSE
                    0
              END AS equipment_cnt,
              CASE
                WHEN w1_resrc_class_flg = 'W1OT' THEN
                    1
                ELSE
                    0
              END AS odc_cnt,
              cost_category_cd,
            ( total_est_cost * a.percentage * a.costcenterpercentage ) / 10000 AS total_est_cost,
              completed_act_cnt,
              planned_act_cnt,
              open_act_cnt,
              pm_act_cnt,
              cm_act_cnt,
              emergency_flg
          FROM
              (
                  SELECT
                    act.act_id                AS act_id,
                      actal.asset_id            AS asset_id,
                    cost.w1_ft_id             AS w1_ft_id,
                    cost.w1_resrc_class_flg   AS w1_resrc_class_flg,
                      act.wo_id                 AS wo_id,
                      actal.node_id             AS node_id,
                      act.cre_dttm              AS act_cre_dttm,
                      sc.renewal_flg            AS renewal_flg,
                      actal.percentage,
                    acc.percentage            AS costcenterpercentage,
                    cost.amount               AS amount,
                    cost.total_est_cost       AS total_est_cost,
                      CASE
                        WHEN sc.renewal_flg = 'W1NO' THEN
                            ( cost.amount * actal.percentage / 100 )
                        ELSE
                            0
                      END maintenance_cost,
                      CASE
                        WHEN sc.renewal_flg = 'W1YS' THEN
                            ( cost.amount * actal.percentage / 100 )
                        ELSE
                            0
                      END renewal_cost,
                    ( cost.amount * actal.percentage / 100 ) AS w1_bi_total_cost,
                      CASE
                        WHEN actal.shcount > 0 THEN
                            ( cost.amount * actal.percentage / 100 )
                        ELSE
                            0
                      END failure_repair_cost,
                      CASE
                          WHEN wo.wo_id IS NOT NULL
                             AND wo.work_type_flg = 'W1PM' THEN
                            1
                        ELSE
                            0
                      END AS pm_act_cnt,
                      CASE
                          WHEN wo.wo_id IS NOT NULL
                             AND wo.work_type_flg = 'W1RG' THEN
                            1
                        ELSE
                            0
                      END AS cm_act_cnt,
                      CASE
                          WHEN act.bo_status_cd IN (
                              'COMPLETE'
                              ,'CLOSED'
                        ) THEN
                            1
                        ELSE
                            0
                      END AS completed_act_cnt,
                      CASE
                          WHEN act.bo_status_cd IN (
                              'APPROVED',
                              'ACTIVE'
                        ) THEN
                            1
                        ELSE
                            0
                      END AS planned_act_cnt,
                      CASE
                          WHEN NOT ( act.bo_status_cd IN (
                              'COMPLETE'
                              ,'CLOSED'
                        ) ) THEN
                            1
                        ELSE
                            0
                      END AS open_act_cnt,
                      act.emergency_flg,
                       actal.shcount * acc.percentage / 100  AS failure_count,
                      --actal.shcount             AS failure_count,
                      ast.acquisition_dt        AS acquisition_dt,
                      trunc(ast.in_service_dt) AS in_service_dt,
                      ast.predctd_wear_out_dt   AS predctd_wear_out_dt,
                      1 AS asset_act_count,
                      act.w1_crew_id            AS w1_crew_id,
                    decode(TRIM(wo.bo_status_cd), 'COMPLETED', wo.status_upd_dttm,(
                          SELECT
                              MAX(lg.log_dttm)
                          FROM
                              w1_wo_log lg
                          WHERE
                             lg.wo_id = wo.wo_id
                              AND lg.bo_status_cd = 'COMPLETED'
                      ) ) AS finish_dttm,
                      act.actvn_dttm,
                      act.original_work_dt,
                      act.required_by_dt,
                      act.work_win_start_dttm,
                      act.work_win_end_dttm,
                    cost.cost_category_cd,
                    cost.ft_cre_dttm,
                    cost.expense_cd,
                    cost.cost_center_cd,
                      act.prj_id,
                      act.planner_cd,
                      act.tmpl_act_id,
                      act.owning_access_grp_cd,
                      act.user_id,
                      act.work_class_cd,
                      act.work_category_cd,
                      act.act_type_cd,     
                      act.service_class_cd
                  FROM
                      w1_activity act
                      JOIN (
                         SELECT
                              z.act_id,
                              z.asset_id,
                              node_id,
                              z.percentage,
                              z.participation_flg,
                              (
                                  SELECT
                                      COUNT(*)
                                  FROM
                                      w1_svc_hist sh,
                                      w1_svc_hist_type sht
                                  WHERE
                                      sht.svc_hist_type_cd = sh.svc_hist_type_cd
                                      AND sht.svc_hist_category_flg = 'W1FA'
                                      AND sh.act_id = z.act_id
                                      AND sh.asset_id = z.asset_id
                              ) AS shcount
                          FROM
                              w1_activity_asset z
                          WHERE
                              z.participation_flg = 'W1AW'
                      ) actal ON actal.act_id = act.act_id
                      JOIN w1_service_class sc ON sc.service_class_cd = act.service_class_cd
                                                  AND sc.renewal_flg IN (
                          'W1NO',
                          'W1YS'
                      )
                      JOIN w1_asset ast ON ast.asset_id = actal.asset_id
                      JOIN w1_wo wo ON wo.wo_id = act.wo_id
                      JOIN (
                          SELECT
                            act_id,
                            w1_ft_id,
                            w1_resrc_class_flg,
                            amount,
                            CASE
                                WHEN amount <= 0 THEN
                                    0
                                ELSE
                                    (
                                        SELECT
                                            nvl(SUM(round(arr.orig_estimate / resrcreqmtcount,2)),0)
                                        FROM
                                            w1_act_resrc_reqmt arr
                                        WHERE
                                            arr.act_resrc_reqmt_id = ft2.act_resrc_reqmt_id
                                    )
                            END AS total_est_cost,
                            cost_category_cd,
                            ft_cre_dttm,
                            expense_cd,
                            cost_center_cd
                        FROM
                            (
                                SELECT
                                    ft.act_id     AS act_id,
                                    ft.w1_ft_id   AS w1_ft_id,
                                    CASE
                                        WHEN ft.timesheet_detail_id IS NOT NULL THEN
                                            'W1CR'
                                        WHEN ft.mat_iss_line_id IS NOT NULL
                                             OR ft.mat_ret_line_id IS NOT NULL THEN
                                            'W1MT'
                                        WHEN ft.odc_dtl_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    w1_resrc_class_flg
                                                FROM
                                                    w1_odc_dtl      odc,
                                                    w1_resrc_type   rt
                                                WHERE
                                                    odc.odc_dtl_id = ft.odc_dtl_id
                                                    AND rt.resrc_type_id = odc.resrc_type_id
                                            )
                                        WHEN ft.acpt_line_id IS NOT NULL THEN
                                            nvl2((
                                                SELECT
                                                    stock_item_dtl_id
                                                FROM
                                                    w1_acpt_line al
                                                WHERE
                                                    al.acpt_line_id = ft.acpt_line_id
                                            ), 'W1MT',(
                                                SELECT
                                                    w1_resrc_class_flg
                                                FROM
                                                    w1_acpt_line    al, w1_resrc_type   rt
                                                WHERE
                                                    al.acpt_line_id = ft.acpt_line_id
                                                    AND rt.resrc_type_id = al.resrc_type_id
                                            ))
                                        WHEN ft.rtn_line_id IS NOT NULL THEN
                                            nvl2((
                                                SELECT
                                                    trim(stock_item_dtl_id)
                                                FROM
                                                    w1_rtn_line rl
                                                WHERE
                                                    rl.rtn_line_id = ft.rtn_line_id
                                            ), 'W1MT',(
                                                SELECT
                                                    w1_resrc_class_flg
                                                FROM
                                                    w1_rtn_line     rl, w1_resrc_type   rt, w1_po_line      pl
                                                WHERE
                                                    rl.rtn_line_id = ft.rtn_line_id
                                                    AND pl.po_line_id = rl.po_line_id
                                                    AND rt.resrc_type_id = pl.resrc_type_id
                                            ))
                                        WHEN ft.invoice_line_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    w1_resrc_class_flg
                                                FROM
                                                    w1_invoice_line   il,
                                                    w1_resrc_type     rt
                                                WHERE
                                                    il.invoice_line_id = ft.invoice_line_id
                                                    AND rt.resrc_type_id = il.resrc_type_id
                                            )
                                        ELSE
                                            NULL
                                    END AS w1_resrc_class_flg,
                                    CASE
                                        WHEN ft.timesheet_detail_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    t.act_resrc_reqmt_id
                                                FROM
                                                    w1_timesheet_detail t
                                                WHERE
                                                    t.timesheet_detail_id = ft.timesheet_detail_id
                                            )
                                        WHEN ft.rtn_line_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    p.act_resrc_reqmt_id
                                                FROM
                                                    w1_rtn_line   rl,
                                                    w1_po_line    p
                                                WHERE
                                                    rl.rtn_line_id = ft.rtn_line_id
                                                    AND p.po_line_id = rl.po_line_id
                                            )
                                        WHEN ft.mat_iss_line_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    m.act_resrc_reqmt_id
                                                FROM
                                                    w1_mat_req_line   m,
                                                    w1_mat_iss_line   n
                                                WHERE
                                                    n.mat_iss_line_id = ft.mat_iss_line_id
                                                    AND m.mat_req_line_id = n.mat_req_line_id
                                            )
                                        WHEN ft.mat_ret_line_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    m.act_resrc_reqmt_id
                                                FROM
                                                    w1_mat_req_line   m,
                                                    w1_mat_iss_line   n,
                                                    w1_mat_ret_line   l
                                                WHERE
                                                    l.mat_ret_line_id = ft.mat_ret_line_id
                                                    AND n.mat_iss_line_id = l.mat_iss_line_id
                                                    AND m.mat_req_line_id = n.mat_req_line_id
                                            )
                                        WHEN ft.odc_dtl_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    o.act_resrc_reqmt_id
                                                FROM
                                                    w1_odc_dtl o
                                                WHERE
                                                    o.odc_dtl_id = ft.odc_dtl_id
                                            )
                                        WHEN ft.acpt_line_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    p.act_resrc_reqmt_id
                                                FROM
                                                    w1_po_line     p,
                                                    w1_rcpt_line   r,
                                                    w1_acpt_line   l
                                                WHERE
                                                    l.acpt_line_id = ft.acpt_line_id
                                                    AND r.rcpt_line_id = l.rcpt_line_id
                                                    AND p.po_line_id = r.po_line_id
                                            )
                                        WHEN ft.invoice_line_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    p.act_resrc_reqmt_id
                                                FROM
                                                    w1_po_line        p,
                                                    w1_invoice_line   i
                                                WHERE
                                                    i.invoice_line_id = ft.invoice_line_id
                                                    AND p.po_line_id = i.po_line_id
                                            )
                                        ELSE
                                            NULL
                                    END AS act_resrc_reqmt_id,
                                    CASE
                                        WHEN ft.timesheet_detail_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    COUNT(*)
                                                FROM
                                                    w1_timesheet_detail dt
                                                WHERE
                                                    dt.act_resrc_reqmt_id = (
                                                        SELECT
                                                            ftdt.act_resrc_reqmt_id
                                                        FROM
                                                            w1_timesheet_detail ftdt
                                                        WHERE
                                                            ftdt.timesheet_detail_id = ft.timesheet_detail_id
                                                    )
                                            )
                                          WHEN ft.mat_iss_line_id IS NOT NULL THEN
                                              (
                                                 SELECT count(*)  FROM
                                                  w1_mat_req_line   dm1
                                                WHERE
                                                  dm1.act_resrc_reqmt_id = (
                                                SELECT 
                                                  dm.act_resrc_reqmt_id
                                                FROM
                                                  w1_mat_req_line   dm,
                                                  w1_mat_iss_line   dn
                                                WHERE
                                                  dn.mat_iss_line_id = ft.mat_iss_line_id
                                                  AND dm.mat_req_line_id = dn.mat_req_line_id
                                                  )
                                              )                                                    
                                      WHEN ft.odc_dtl_id IS NOT NULL THEN
                                            (
                                              select count(*) from w1_odc_dtl od1 
                                              where od1.act_resrc_reqmt_id=(
                                                SELECT
                                                    od.act_resrc_reqmt_id
                                                FROM
                                                    w1_odc_dtl od
                                                WHERE
                                                    od.odc_dtl_id = ft.odc_dtl_id)
                                            )
                                    
                                                                         
                                         WHEN ft.acpt_line_id IS NOT NULL THEN
                                            (
                                               select count(*) from w1_po_line dpp
                                               where dpp.act_resrc_reqmt_id = (
                                                
                                                SELECT
                                                    dp.act_resrc_reqmt_id
                                                FROM
                                                    w1_po_line     dp,
                                                    w1_rcpt_line   dr,
                                                    w1_acpt_line   dl
                                                WHERE
                                                    dl.acpt_line_id = ft.acpt_line_id
                                                    AND dr.rcpt_line_id = dl.rcpt_line_id
                                                    AND dp.po_line_id = dr.po_line_id
                                                    )
                                            )
                                        WHEN ft.invoice_line_id IS NOT NULL THEN
                                            (
                                               select count(*) from w1_po_line dpi 
                                               where dpi.act_resrc_reqmt_id = 
                                               ( SELECT
                                                    dp.act_resrc_reqmt_id
                                                FROM
                                                    w1_po_line        dp,
                                                    w1_invoice_line   di
                                                WHERE
                                                    di.invoice_line_id = ft.invoice_line_id
                                                    AND dp.po_line_id = di.po_line_id)
                                            )  
                                            
                                        ELSE
                                            1
                                    END AS resrcreqmtcount,
                                    amount        AS amount,
                                    ft.cost_category_cd,
                                    ft.ft_cre_dttm,
                                    ft.expense_cd,
                                    ft.cost_center_cd
                                FROM
                                    (
                                        SELECT
                              ft.w1_ft_id,
                              ft.act_id,
                              ft.timesheet_detail_id,
                              ft.odc_dtl_id,
                              ft.mat_iss_line_id,
                             ft.mat_ret_line_id,
                              ft.acpt_line_id,
                              ft.rtn_line_id,
                              ft.invoice_line_id,
                               ec.cost_category_cd,
                              ft.cre_dttm   AS ft_cre_dttm,
                              gl.expense_cd,
							  gl.cost_center_cd,
                              SUM(gl.amt) amount
                          FROM
                              w1_ft ft,
                              w1_ft_gl_dtl gl,
                              w1_expense_cd ec
                          WHERE
                              ft.sibling_cancelled_flg = 'W1NO'
                              AND gl.w1_ft_id = ft.w1_ft_id
                              AND ( gl.amt * ft.amt ) * nvl2(nvl(ft.rtn_line_id,ft.mat_ret_line_id),-1,1) > 0
                              AND ft.bo_status_cd = 'FROZEN'
                              AND ec.expense_cd = gl.expense_cd
                          GROUP BY
                             ft.w1_ft_id,
                              ft.act_id,
                              ft.timesheet_detail_id,
                              ft.odc_dtl_id,
                              ft.mat_iss_line_id,
                              ft.mat_ret_line_id,
                              ft.acpt_line_id,
                              ft.rtn_line_id,
                              ft.invoice_line_id,
                              ec.cost_category_cd,
                              ft.cre_dttm,
                              gl.expense_cd,
                              gl.cost_center_cd
                                    ) ft
                            ) ft2
                        UNION
                        ( SELECT
                            arr.act_id          AS act_id,
                            NULL AS w1_ft_id,
                            arr.w1_resrc_class_flg,
                            0 AS amount,
                            arr.orig_estimate   AS orig_estimate,
                            arr.cost_category_cd,
                            NULL AS ft_cre_dttm,
                            arr.expense_cd,
                            arr.cost_center_cd
                        FROM
                            (
                                SELECT
                                    ar.act_id,
                                    ec.cost_category_cd,
                                    ar.expense_cd,
                                    rt.w1_resrc_class_flg,
                                    acc.cost_center_cd,
                                    SUM(ar.orig_estimate) AS orig_estimate
                                FROM
                                    w1_act_resrc_reqmt        ar,
                                    w1_expense_cd             ec,
                                    w1_resrc_type             rt,
                                    w1_activity               act,
                                    w1_activity_cost_center   acc
                                WHERE
                                    ar.act_id = act.act_id
                                    AND act.bo_status_cd <> 'CANCELED'
                                    AND ec.expense_cd = ar.expense_cd
                                    AND ar.bo_status_cd <> 'CANCELED'
                                    AND acc.act_id = act.act_id
                                    AND rt.resrc_type_id = decode(ar.stock_item_dtl_id, NULL, ar.resrc_type_id,(
                                        SELECT
                                            sid.resrc_type_id
                                        FROM
                                            w1_stock_item_dtl sid
                                        WHERE
                                            sid.stock_item_dtl_id = ar.stock_item_dtl_id
                                    ))
                                    AND NOT EXISTS (
                                        SELECT
                                            'x'
                                        FROM
                                            w1_timesheet_detail t
                                        WHERE
                                            t.act_resrc_reqmt_id = ar.act_resrc_reqmt_id
                                            and   t.bo_status_cd in ('POSTED')
                                    )
                                    AND NOT EXISTS (
                                        SELECT
                                            'x'
                                        FROM
                                            w1_po_line p
                                        WHERE
                                            p.act_resrc_reqmt_id = ar.act_resrc_reqmt_id
                                            and p.bo_status_cd  in ('ISSUED','CLOSED')
                                    )
                                    AND NOT EXISTS (
                                        SELECT
                                            'x'
                                        FROM
                                            w1_mat_req_line m
                                        WHERE
                                            m.act_resrc_reqmt_id = ar.act_resrc_reqmt_id
                                             and  m.bo_status_cd  in ('ISSUED')
                                    )
                                    AND NOT EXISTS (
                                        SELECT
                                            'x'
                                        FROM
                                            w1_odc_dtl o
                                        WHERE
                                            o.act_resrc_reqmt_id = ar.act_resrc_reqmt_id
                                             and  o.bo_status_cd  in ('POSTED')
                                    )
                                GROUP BY
                                    ar.act_id,
                                    ec.cost_category_cd,
                                    rt.w1_resrc_class_flg,
                                    ar.expense_cd,
                                    acc.cost_center_cd
                            ) arr
                        )
                    ) cost ON cost.act_id = act.act_id
                    JOIN w1_activity_cost_center   acc ON act.act_id = acc.act_id
                                                        AND acc.cost_center_cd = cost.cost_center_cd
             ) a
      );

-- ----- W1_BI_ASSETCOST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_ASSETCOST_VW" ("ASSET_ID", "NODE_ID", "TOTAL_MAINTENANCE_COST", "TOTAL_RENEWAL_COST", "TOTAL_CM_MAINT_COST", "TOTAL_PM_MAINT_COST", "W1_BI_TOTAL_COST", "TOTAL_FAIL_REPR_COST", "TOTAL_FAILURE_COUNT", "AVG_FAIL_REPR_COST", "ASSET_LIFE_TO_DT_COST", "PAST_12MONTHS_COST", "PAST_13_24MONTHS_COST", "PAST_25_36MONTHS_COST", "PAST_3YEARS_COST", "AVG_PAST_3YEARS_COST", "PERCENT_PURCHASE", "ACQUISITION_DT", "AVG_OUT_REPR_COST", "CORE_CHRG_EXP_DT", "IN_SERVICE_DT", "PREDCTD_WEAR_OUT_DT", "OWNING_ACCESS_GRP_CD", "ASSET_COUNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    a.asset_id AS asset_id,
    nvl(an.curr_node_id,(
        SELECT
            an2.curr_node_id
        FROM
            w1_asset_node an2
        WHERE
            an2.curr_asset_id = an.curr_attch_to_asset_id
    )) AS node_id,
    nvl(total_maint_cost, 0) AS total_maintenance_cost,
    nvl(total_renewal_cost, 0) AS total_renewal_cost,
    nvl(total_cm_maint_cost, 0) AS total_cm_maint_cost,
    nvl(total_pm_maint_cost, 0) AS total_pm_maint_cost,
    nvl((total_maint_cost + total_renewal_cost), 0) AS w1_bi_total_cost,
    nvl(total_failure_repair_cost, 0) AS total_fail_repr_cost,
    nvl(total_failure_cnt, 0) AS total_failure_count,
    nvl(
        CASE
            WHEN total_failure_cnt > 0 THEN
                round((total_failure_repair_cost / total_failure_cnt), 2)
            ELSE
                0
        END, 0) AS avg_fail_repr_cost,
    nvl(nvl(a.acquisition_cost, 0) + total_cost, 0) AS asset_life_to_dt_cost,
    nvl(cost_past_12months, 0) AS past_12months_cost,
    nvl(cost_past13_24months, 0) AS past_13_24months_cost,
    nvl(cost_past25_36months, 0) AS past_25_36months_cost,
    nvl(cost_past_3years, 0) AS past_3years_cost,
    nvl(avg_cost_past_3years, 0) AS avg_past_3years_cost,
    decode(nvl(a.replacement_cost, 0), 0, 0, round(((cost_purchase / a.replacement_cost) * 100), 2)) AS percent_purchase,
    trunc(a.acquisition_dt) AS acquisition_dt,
    nvl(a.avg_out_repr_cost, 0) AS avg_out_repr_cost,
    trunc(a.core_chrg_exp_dt) AS core_chrg_exp_dt,
    trunc(a.in_service_dt) AS in_service_dt,
    trunc(a.predctd_wear_out_dt) AS predctd_wear_out_dt,
    a.owning_access_grp_cd as owning_access_grp_cd,
    1 AS asset_count
FROM
    w1_asset        a
    JOIN w1_asset_node   an ON an.curr_asset_id = a.asset_id
    LEFT OUTER JOIN (
        SELECT
            asset_id,
            SUM(maintenance_cost) AS total_maint_cost,
            SUM(renewal_cost) AS total_renewal_cost,
            SUM(w1_bi_total_cost) AS total_cost,
            SUM(failure_repair_cost) AS total_failure_repair_cost,
            SUM(failure_count) AS total_failure_cnt,
            SUM(
                CASE
                    WHEN renewal_flg = 'W1NO' THEN
                        maintenance_cm_cost
                    ELSE
                        0
                END
            ) AS total_cm_maint_cost,
            SUM(
                CASE
                    WHEN renewal_flg = 'W1NO' THEN
                        maintenance_pm_cost
                    ELSE
                        0
                END
            ) AS total_pm_maint_cost,
            SUM(
                CASE
                    WHEN add_months(current_date, - 12) <= cost.act_cre_dttm THEN
                        w1_bi_total_cost
                    ELSE
                        0
                END
            ) AS cost_past_12months,
            SUM(
                CASE
                    WHEN cost.act_cre_dttm >= add_months(current_date, - 24)
                         AND cost.act_cre_dttm < add_months(current_date, - 12) THEN
                        w1_bi_total_cost
                    ELSE
                        0
                END
            ) AS cost_past13_24months,
            SUM(
                CASE
                    WHEN cost.act_cre_dttm >= add_months(current_date, - 36)
                         AND cost.act_cre_dttm < add_months(current_date, - 24) THEN
                        w1_bi_total_cost
                    ELSE
                        0
                END
            ) AS cost_past25_36months,
            SUM(
                CASE
                    WHEN add_months(current_date, - 36) <= cost.act_cre_dttm THEN
                        w1_bi_total_cost
                    ELSE
                        0
                END
            ) AS cost_past_3years,
            round(SUM(
                CASE
                    WHEN add_months(current_date, - 36) <= cost.act_cre_dttm THEN
                        w1_bi_total_cost
                    ELSE
                        0
                END
            ) / 3, 2) AS avg_cost_past_3years,
            ( SUM(
                CASE
                    WHEN add_months(current_date, - 36) <= cost.act_cre_dttm THEN
                        w1_bi_total_cost
                    ELSE
                        0
                END
            ) / 3 ) cost_purchase
        FROM
            w1_bi_assetactcost_vw cost
        GROUP BY
            cost.asset_id
    ) vw ON vw.asset_id = a.asset_id;

-- ----- W1_BI_ASSET_BN_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_ASSET_BN_VW" ("ASSET_ID", "W1_BI_ID_VALUE") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ASSET_ID, W1_ID_VALUE AS W1_BI_ID_VALUE
FROM W1_ASSET_IDENTIFIER AI
WHERE AI.ASSET_ID_TYPE_FLG = 'W1BN';

-- ----- W1_BI_ASSET_SN_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_ASSET_SN_VW" ("ASSET_ID", "SERIAL_NO") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ASSET_ID, W1_ID_VALUE AS SERIAL_NO
FROM W1_ASSET_IDENTIFIER AI
WHERE AI.ASSET_ID_TYPE_FLG = 'W1SN';

-- ----- W1_BI_ASTAVAILDWNTM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_ASTAVAILDWNTM_VW" ("ASSET_ID", "NODE_ID", "WO_ID", "ACT_ID", "DOWNTIME_SVC_HIST_ID", "W1_CREW_ID", "DOWNTIME_RSN", "DOWNTIME_START_DTTM", "DOWNTIME_END_DTTM", "FAILURE_COUNT", "IN_SERVICE_DT", "TOT_DOWNTIME_SEC", "ACQUISITION_DT", "WO_CRE_DTTM", "FINISH_DTTM", "PREDCTD_WEAR_OUT_DT", "OWNING_ACCESS_GRP_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    asset_id AS ASSET_ID,
    node_id AS NODE_ID,
    wo_id AS WO_ID,
    act_id AS ACT_ID,
    svc_hist_id AS DOWNTIME_SVC_HIST_ID,
    w1_crew_id AS W1_CREW_ID,
    reason AS DOWNTIME_RSN,
    event_start AS DOWNTIME_START_DTTM,
    nvl(event_end_dt, nvl2(fail_svc_hist_id, (select z.end_dttm from w1_svc_hist z where z.svc_hist_id = fail_svc_hist_id), wo_end)) AS DOWNTIME_END_DTTM,
    1 AS FAILURE_COUNT,
    trunc(in_service_dt) AS IN_SERVICE_DT,
    ROUND(((nvl(event_end_dt, nvl2(fail_svc_hist_id, (select z.end_dttm from w1_svc_hist z where z.svc_hist_id = fail_svc_hist_id), wo_end)) - event_start)*24*60*60),0) AS TOT_DOWNTIME_SEC,
    acquisition_dt as ACQUISITION_DT,
    wo_cre_dt as WO_CRE_DTTM,
    wo_end as FINISH_DTTM,
    predctd_wear_out_dt as PREDCTD_WEAR_OUT_DT,
    owning_access_grp_cd as OWNING_ACCESS_GRP_CD
FROM
  ( SELECT
       aa.asset_id,
       aa.node_id,
       wo.wo_id,
       sh.act_id,
       sh.svc_hist_id svc_hist_id,
       -- pick a failure SH if any
       (select min(shf.svc_hist_id)
        from w1_svc_hist shf,
             w1_svc_hist_type shtf
        where shf.asset_id = aa.asset_id
        AND shf.act_id = aa.act_id
        AND shtf.svc_hist_type_cd = shf.svc_hist_type_cd
        AND shtf.svc_hist_category_flg = 'W1FA') fail_svc_hist_id,
        act.W1_CREW_ID,
        shc.char_val reason,
        ast.in_service_dt as in_service_dt,
        -- downtime start date is in CLOB
        to_date(regexp_substr(sh.bo_data_area,'<startDateTime>([^<]*)</startDateTime>',1,1,'i',1),'YYYY-MM-DD-HH24.MI.SS') event_start,
        sh.end_dttm event_end_dt,
        decode(trim(wo.bo_status_cd), 'COMPLETED',wo.status_upd_dttm,
                 (select max(lg.log_dttm) from w1_wo_log lg where lg.wo_id = wo.wo_id and lg.bo_status_cd = 'COMPLETED')) as wo_end,
        nvl2(wo.work_req_id,(select wr.cre_dttm from w1_work_req wr where wr.work_req_id = wo.work_req_id),wo.cre_dttm) as wo_cre_dt,
        ast.acquisition_dt,
        ast.predctd_wear_out_dt,
        nvl(ast.owning_access_grp_cd, sh.owning_access_grp_cd) owning_access_grp_cd
    FROM
        w1_wo wo,
        w1_activity act,
        w1_activity_asset aa,
        w1_svc_hist sh,
        w1_svc_hist_type sht,
       (select distinct svc_hist_id, char_val  from w1_svc_hist_char  where char_type_cd = 'W1-DTRSN' AND srch_char_val = 'NPL') shc,
        w1_asset ast
     WHERE
        act.wo_id = wo.wo_id
        AND aa.act_id = act.act_id
        AND wo.bo_status_cd IN ( 'COMPLETED', 'CLOSED' )
        AND act.bo_status_cd = 'COMPLETE'
        AND sh.asset_id = aa.asset_id
        and sh.act_id = act.act_id
        AND sht.svc_hist_type_cd = sh.svc_hist_type_cd
        AND sht.svc_hist_category_flg = 'W1DT'
        AND shc.svc_hist_id = sh.svc_hist_id
        AND aa.asset_id = ast.asset_id
 );

-- ----- W1_BI_ASTAVAILWO_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_ASTAVAILWO_VW" ("ASSET_ID", "NODE_ID", "WO_ID", "ACT_ID", "W1_CREW_ID", "WO_CRE_DTTM", "FINISH_DTTM", "FAILURE_COUNT", "IN_SERVICE_DT", "TOT_DOWNTIME_SEC", "ACQUISITION_DT", "REMAIN_LIFE_YRS", "ECONOMIC_REMAIN_LIFE_YRS", "PREDICT_WEAR_OUT_DT", "OWNING_ACCESS_GRP_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
     asset_id            AS ASSET_ID,
     node_id             AS NODE_ID,
     wo_id               AS WO_ID,
     act_id              AS ACT_ID,
     w1_crew_id          AS W1_CREW_ID,
     event_start         AS WO_CRE_DTTM,
     event_end           AS FINISH_DTTM,
     1                    AS FAILURE_COUNT,
    trunc(in_service_dt) AS IN_SERVICE_DT,
     round((event_end - event_start)* 24 * 60 * 60) AS TOT_DOWNTIME_SEC,
     trunc(acquisition_dt)       AS ACQUISITION_DT,
     decode(useful_life,0,null,nvl2(in_service_dt, round((useful_life - (current_date - in_service_dt))/365,1), null)) AS REMAIN_LIFE_YRS,
     decode(economic_life,0,null,nvl2(in_service_dt, round((economic_life - (current_date - in_service_dt))/365,1), null)) AS ECONOMIC_REMAIN_LIFE_YRS,
     predctd_wear_out_dt AS PREDICT_WEAR_OUT_DT,
     owning_access_grp_cd as owning_access_grp_cd
 FROM
     (
         SELECT
             aa.asset_id,
             aa.node_id,
             wo.wo_id,
             act.act_id,
             act.W1_CREW_ID,
             ast.in_service_dt as in_service_dt,
             ast.acquisition_dt,
             decode(nvl(ast.useful_life,0),0,nvl(asty.useful_life,0),ast.useful_life) * 365 AS useful_life,
             nvl(ast.eco_life,0) * 365 AS economic_life,
             ast.predctd_wear_out_dt,
             nvl2(wo.work_req_id,(select wr.cre_dttm from w1_work_req wr where wr.work_req_id = wo.work_req_id),wo.cre_dttm) AS event_start,
             act.status_upd_dttm AS event_end,
             nvl(ast.owning_access_grp_cd,wo.owning_access_grp_cd) owning_access_grp_cd
         FROM
             w1_wo wo,
             w1_activity act,
             w1_activity_asset aa,
             w1_asset ast,
             w1_asset_type asty
         WHERE act.wo_id = wo.wo_id
           AND aa.act_id = act.act_id
           AND aa.asset_id = ast.asset_id
           and asty.asset_type_cd = ast.asset_type_cd
           AND wo.bo_status_cd IN (
                 'COMPLETED',
                 'CLOSED'
             )
           AND act.bo_status_cd = 'COMPLETE' 
           AND exists
             (select 'x'
              from w1_svc_hist sh,
                   w1_svc_hist_type sht
              where
                  sh.asset_id = aa.asset_id
              AND sh.act_id = act.act_id
              AND sht.svc_hist_type_cd = sh.svc_hist_type_cd
              AND sht.svc_hist_category_flg = 'W1FA'
             )        
     )
 ORDER BY
     asset_id,
     wo_id,
     act_id;

-- ----- W1_BI_FORECASTEDACTHOURS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_FORECASTEDACTHOURS_VW" ("ACT_ID", "RESRC_TYPE_ID", "BO_STATUS_CD", "BO_STATUS_REASON_CD", "USER_ID", "DESCR100", "ACT_TYPE_CD", "NODE_ID", "ASSET_ID", "WO_ID", "ACTVN_DTTM", "WORK_WIN_START_DTTM", "WORK_WIN_END_DTTM", "SERVICE_CLASS_CD", "W1_CREW_ID", "WORK_PRIORITY_FLG", "TMPL_ACT_ID", "OUTAGE_TYPE_FLG", "BACK_LOG_GRP_FLG", "HELD_FOR_PARTS_FLG", "ORIGINAL_WORK_DT", "EMERGENCY_FLG", "PLANNER_CD", "TOTAL_PRIORITY", "WORK_CLASS_CD", "WORK_CATEGORY_CD", "REQUIRED_BY_DT", "OWNING_ACCESS_GRP_CD", "ACT_RESRC_CNT", "OPEN_ACT_FC_LABOR_HRS", "MAINT_ACT_FC_LABOR_HRS", "CONSTR_ACT_FC_LABOR_HRS", "UNSCHED_MAINT_FC_LABOR_HRS") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
     act_id,
     resrc_type_id,
     bo_status_cd,
     bo_status_reason_cd,
     user_id,
     descr100,
     act_type_cd,
     node_id,
     asset_id,
     wo_id,
     actvn_dttm,
     work_win_start_dttm,
     work_win_end_dttm,
     service_class_cd,
     w1_crew_id,
     work_priority_flg,
     tmpl_act_id,
     outage_type_flg,
     back_log_grp_flg,
     held_for_parts_flg,
     original_work_dt,
     emergency_flg,
     planner_cd,
     total_priority,
     work_class_cd,
     work_category_cd,
     required_by_dt,
     owning_access_grp_cd,
     1 as act_resrc_cnt,
     CASE
         WHEN planned_labor_hrs > actual_labor_hrs THEN planned_labor_hrs - actual_labor_hrs
         ELSE 0
     END AS open_act_fc_labor_hrs,
     CASE
         WHEN maint_act_cnt = 1
              AND planned_labor_hrs > actual_labor_hrs THEN planned_labor_hrs - actual_labor_hrs
         ELSE 0
     END AS maint_act_fc_labor_hrs,
     CASE
         WHEN constr_act_cnt = 1
              AND planned_labor_hrs > actual_labor_hrs THEN planned_labor_hrs - actual_labor_hrs
         ELSE 0
     END AS constr_act_fc_labor_hrs,
     CASE
         WHEN maint_act_cnt = 1
              AND wait_sched_act_cnt = 1
              AND planned_labor_hrs > actual_labor_hrs THEN planned_labor_hrs - actual_labor_hrs
         ELSE 0
     END AS unsched_maint_fc_labor_hrs
 FROM
     (
         SELECT
             ac.act_id,
             arr.resrc_type_id,
             ac.bo_status_cd,
             ac.bo_status_reason_cd,
             ac.user_id,
             ac.descr100,
             ac.tmpl_act_id,
             ac.node_id,
             ac.asset_id,
             ac.planner_cd,
             ac.wo_id,
             ac.act_type_cd,
             ac.service_class_cd,
             ac.emergency_flg,
             ac.held_for_parts_flg,
             ac.work_priority_flg,
             ac.total_priority,
             ac.outage_type_flg,
             ac.back_log_grp_flg,
             ac.work_class_cd,
             ac.work_category_cd,
             ac.w1_crew_id,
             ac.required_by_dt,
             ac.actvn_dttm,
             ac.work_win_start_dttm,
             ac.work_win_end_dttm,
             ac.owning_access_grp_cd,
             ac.original_work_dt,
             CASE
                 WHEN act.constr_related_flg = 'W1YS' THEN 1
                 ELSE 0
             END AS constr_act_cnt,
             CASE
                 WHEN wo.wo_id IS NOT NULL
                      AND wo.work_type_flg IN (
                     'W1PM',
                     'W1RG'
                 ) THEN 1
                 ELSE 0
             END AS maint_act_cnt,
             CASE
                 WHEN ac.bo_status_cd IN (
                     'APPROVED',
                     'ACTIVE',
                     'INPROGRESS'
                 ) THEN 1
                 ELSE 0
             END AS active_act_cnt,
             CASE
                 WHEN ac.bo_status_cd IN (
                     'APPROVED',
                     'ACTIVE'
                 )
                      AND (
                     SELECT
                         COUNT(*)
                     FROM
                         w1_act_resrc_reqmt arr,
                         w1_crew_shift_act_sched csa,
                         w1_crew_shift cs
                     WHERE
                         arr.act_id = ac.act_id
                         AND csa.act_resrc_reqmt_id = arr.act_resrc_reqmt_id
                         AND cs.crew_shift_id = csa.crew_shift_id
                         AND cs.bo_status_cd IN (
                             'ACTIVE',
                             'PLANNING'
                         )
                 ) = 0 THEN 1
                 ELSE 0
             END AS wait_sched_act_cnt,
             arr.w1_duration * arr.w1_quantity AS planned_labor_hrs,
             nvl( (
                 SELECT
                     SUM(hours)
                 FROM
                     w1_timesheet_detail tsd
                 WHERE
                     tsd.act_resrc_reqmt_id = arr.act_resrc_reqmt_id
                     AND tsd.bo_status_cd = 'POSTED'
             ),0) AS actual_labor_hrs
         FROM
             w1_activity ac
             JOIN w1_activity_type act ON act.act_type_cd = ac.act_type_cd
             JOIN w1_act_resrc_reqmt arr ON arr.act_id = ac.act_id
                                            AND NOT arr.bo_status_cd IN (
                 'FULFILLED',
                 'CANCELED'
             )
             JOIN w1_resrc_type rt ON rt.resrc_type_id = arr.resrc_type_id
                                      AND rt.w1_resrc_class_flg = 'W1CR'
             LEFT OUTER JOIN w1_wo wo ON wo.wo_id = ac.wo_id
         WHERE
             ac.bo_status_cd IN (
                 'PLANNING',
                 'PENDAPPROVAL',
                 'APPROVED',
                 'ACTIVE',
                 'INPROGRESS'
             )
     ) a;

-- ----- W1_BI_FORECASTEDASSETPMCOST_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_FORECASTEDASSETPMCOST_VW" ("ASSET_ID", "NODE_ID", "IN_SERVICE_DT", "PREDCTD_WEAR_OUT_DT", "ACQUISITION_DT", "REMAIN_LIFE_YRS", "COST_NEXT_YR", "COST_NEXT_2_YRS", "COST_NEXT_5_YRS", "COST_NEXT_10_YRS", "COST_REMAIN_LIFE", "LABOR_COST_NEXT_YR", "LABOR_COST_NEXT_2_YRS", "LABOR_COST_NEXT_5_YRS", "LABOR_COST_NEXT_10_YRS", "LABOR_COST_REMAIN_LIFE", "MATL_COST_NEXT_YR", "MATL_COST_NEXT_2_YRS", "MATL_COST_NEXT_5_YRS", "MATL_COST_NEXT_10_YRS", "MATL_COST_REMAIN_LIFE", "EQUIP_COST_NEXT_YR", "EQUIP_COST_NEXT_2_YRS", "EQUIP_COST_NEXT_5_YRS", "EQUIP_COST_NEXT_10_YRS", "EQUIP_COST_REMAIN_LIFE", "MISC_COST_NEXT_YR", "MISC_COST_NEXT_2_YRS", "MISC_COST_NEXT_5_YRS", "MISC_COST_NEXT_10_YRS", "MISC_COST_REMAIN_LIFE", "OWNING_ACCESS_GRP_CD", "ASSET_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  WITH assetfcst AS (
    SELECT
        fc.asset_id,
        fc.maint_trigger_id,
        MIN(fc.forecast_dt) AS next_maint_dt
    FROM
        w1_asset_maint_trigger_fcst fc
    WHERE
        fc.forecast_dt >= current_date
    GROUP BY
        fc.asset_id,
        fc.maint_trigger_id
)
SELECT
    asset_id              AS asset_id,
    node_id               AS node_id,
    in_service_dt         AS in_service_dt,
    predctd_wear_out_dt   AS predctd_wear_out_dt,
    acquisition_dt        AS acquisition_dt,
    remain_life_yrs       AS remain_life_yrs,
    SUM(cost_next_yr) AS cost_next_yr,
    SUM(cost_next_2yrs) AS cost_next_2_yrs,
    SUM(cost_next_5yrs) AS cost_next_5_yrs,
    SUM(cost_next_10yrs) AS cost_next_10_yrs,
    SUM(cost_remain_life) AS cost_remain_life,
    SUM(labor_cost_next_yr) AS labor_cost_next_yr,
    SUM(labor_cost_next_2yrs) AS labor_cost_next_2_yrs,
    SUM(labor_cost_next_5yrs) AS labor_cost_next_5_yrs,
    SUM(labor_cost_next_10yrs) AS labor_cost_next_10_yrs,
    SUM(labor_cost_remain_life) AS labor_cost_remain_life,
    SUM(matl_cost_next_yr) AS matl_cost_next_yr,
    SUM(matl_cost_next_2yrs) AS matl_cost_next_2_yrs,
    SUM(matl_cost_next_5yrs) AS matl_cost_next_5_yrs,
    SUM(matl_cost_next_10yrs) AS matl_cost_next_10_yrs,
    SUM(matl_cost_remain_life) AS matl_cost_remain_life,
    SUM(equip_cost_next_yr) AS equip_cost_next_yr,
    SUM(equip_cost_next_2yrs) AS equip_cost_next_2_yrs,
    SUM(equip_cost_next_5yrs) AS equip_cost_next_5_yrs,
    SUM(equip_cost_next_10yrs) AS equip_cost_next_10_yrs,
    SUM(equip_cost_remain_life) AS equip_cost_remain_life,
    SUM(misc_cost_next_yr) AS misc_cost_next_yr,
    SUM(misc_cost_next_2yrs) AS misc_cost_next_2_yrs,
    SUM(misc_cost_next_5yrs) AS misc_cost_next_5_yrs,
    SUM(misc_cost_next_10yrs) AS misc_cost_next_10_yrs,
    SUM(misc_cost_remain_life) AS misc_cost_remain_life,
    owning_access_grp_cd,
    1 AS asset_cnt
FROM
    (
        SELECT
            ast.asset_id,
            trg.node_id,
            trg.tmpl_wo_id,
            trunc(ast.in_service_dt) AS in_service_dt,
            trunc(ast.predctd_wear_out_dt) AS predctd_wear_out_dt,
            trunc(ast.acquisition_dt) AS acquisition_dt,
            trg.months_bet_pm,
            trg.days_bet_pm,
            trg.next_maint_dt,
            wo_cost.tot_cost_amt,
            wo_cost.tot_cost_amt * asset_percentage * num_triggers_next_yr AS cost_next_yr,
            wo_cost.tot_cost_amt * asset_percentage * num_triggers_next_2yrs AS cost_next_2yrs,
            wo_cost.tot_cost_amt * asset_percentage * num_triggers_next_5yrs AS cost_next_5yrs,
            wo_cost.tot_cost_amt * asset_percentage * num_triggers_next_10yrs AS cost_next_10yrs,
            CASE
                WHEN trg.months_bet_pm > 0 THEN
                    wo_cost.tot_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 12) - months_between(current_date, trunc(ast.in_service_dt)), 0), 1), 0)) /
                    trg.months_bet_pm)
                ELSE
                    wo_cost.tot_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 365) -(current_date - trunc(ast.in_service_dt)), 0), 1), 0)) / trg.days_bet_pm
                    )
            END AS cost_remain_life,
            nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.useful_life, aty.useful_life, 0) * 365) -(current_date - trunc
            (ast.in_service_dt)), 0) / 365, 1), 0) AS remain_life_yrs,
            wo_cost.tot_labor_cost_amt * asset_percentage * num_triggers_next_yr AS labor_cost_next_yr,
            wo_cost.tot_labor_cost_amt * asset_percentage * num_triggers_next_2yrs AS labor_cost_next_2yrs,
            wo_cost.tot_labor_cost_amt * asset_percentage * num_triggers_next_5yrs AS labor_cost_next_5yrs,
            wo_cost.tot_labor_cost_amt * asset_percentage * num_triggers_next_10yrs AS labor_cost_next_10yrs,
            CASE
                WHEN trg.months_bet_pm > 0 THEN
                    wo_cost.tot_labor_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 12) - months_between(current_date, trunc(ast.in_service_dt)), 0), 1), 0)) /
                    trg.months_bet_pm)
                ELSE
                    wo_cost.tot_labor_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 365) -(current_date - trunc(ast.in_service_dt)), 0), 1), 0)) / trg.days_bet_pm
                    )
            END AS labor_cost_remain_life,
            wo_cost.tot_matl_cost_amt * asset_percentage * num_triggers_next_yr AS matl_cost_next_yr,
            wo_cost.tot_matl_cost_amt * asset_percentage * num_triggers_next_2yrs AS matl_cost_next_2yrs,
            wo_cost.tot_matl_cost_amt * asset_percentage * num_triggers_next_5yrs AS matl_cost_next_5yrs,
            wo_cost.tot_matl_cost_amt * asset_percentage * num_triggers_next_10yrs AS matl_cost_next_10yrs,
            CASE
                WHEN trg.months_bet_pm > 0 THEN
                    wo_cost.tot_matl_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 12) - months_between(current_date, trunc(ast.in_service_dt)), 0), 1), 0)) /
                    trg.months_bet_pm)
                ELSE
                    wo_cost.tot_matl_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 365) -(current_date - trunc(ast.in_service_dt)), 0), 1), 0)) / trg.days_bet_pm
                    )
            END AS matl_cost_remain_life,
            wo_cost.tot_equip_cost_amt * asset_percentage * num_triggers_next_yr AS equip_cost_next_yr,
            wo_cost.tot_equip_cost_amt * asset_percentage * num_triggers_next_2yrs AS equip_cost_next_2yrs,
            wo_cost.tot_equip_cost_amt * asset_percentage * num_triggers_next_5yrs AS equip_cost_next_5yrs,
            wo_cost.tot_equip_cost_amt * asset_percentage * num_triggers_next_10yrs AS equip_cost_next_10yrs,
            CASE
                WHEN trg.months_bet_pm > 0 THEN
                    wo_cost.tot_equip_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 12) - months_between(current_date, trunc(ast.in_service_dt)), 0), 1), 0)) /
                    trg.months_bet_pm)
                ELSE
                    wo_cost.tot_equip_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 365) -(current_date - trunc(ast.in_service_dt)), 0), 1), 0)) / trg.days_bet_pm
                    )
            END AS equip_cost_remain_life,
            wo_cost.tot_misc_cost_amt * asset_percentage * num_triggers_next_yr AS misc_cost_next_yr,
            wo_cost.tot_misc_cost_amt * asset_percentage * num_triggers_next_2yrs AS misc_cost_next_2yrs,
            wo_cost.tot_misc_cost_amt * asset_percentage * num_triggers_next_5yrs AS misc_cost_next_5yrs,
            wo_cost.tot_misc_cost_amt * asset_percentage * num_triggers_next_10yrs AS misc_cost_next_10yrs,
            CASE
                WHEN trg.months_bet_pm > 0 THEN
                    wo_cost.tot_misc_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 12) - months_between(current_date, trunc(ast.in_service_dt)), 0), 1), 0)) /
                    trg.months_bet_pm)
                ELSE
                    wo_cost.tot_misc_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 365) -(current_date - trunc(ast.in_service_dt)), 0), 1), 0)) / trg.days_bet_pm
                    )
            END AS misc_cost_remain_life,
            ast.owning_access_grp_cd
        FROM
            (
                SELECT
                    asset_id,
                    maint_trigger_id,
                    node_id,
                    tmpl_wo_id,
                    tmpl_act_id,
                    next_maint_dt,
                    months_bet_pm,
                    days_bet_pm,
                    CASE
                        WHEN months_bet_pm > 0 THEN
                            floor(((months_between(add_months(current_date, 12), next_maint_dt))) / months_bet_pm) + 1
                        ELSE
                            floor(((add_months(current_date, 12) - next_maint_dt)) / days_bet_pm) + 1
                    END AS num_triggers_next_yr,
                    CASE
                        WHEN months_bet_pm > 0 THEN
                            floor(((months_between(add_months(current_date, 24), next_maint_dt))) / months_bet_pm) + 1
                        ELSE
                            floor(((add_months(current_date, 24) - next_maint_dt)) / days_bet_pm) + 1
                    END AS num_triggers_next_2yrs,
                    CASE
                        WHEN months_bet_pm > 0 THEN
                            floor(((months_between(add_months(current_date, 60), next_maint_dt))) / months_bet_pm) + 1
                        ELSE
                            floor(((add_months(current_date, 60) - next_maint_dt)) / days_bet_pm) + 1
                    END AS num_triggers_next_5yrs,
                    CASE
                        WHEN months_bet_pm > 0 THEN
                            floor(((months_between(add_months(current_date, 120), next_maint_dt))) / months_bet_pm) + 1
                        ELSE
                            floor(((add_months(current_date, 120) - next_maint_dt)) / days_bet_pm) + 1
                    END AS num_triggers_next_10yrs,
                    asset_percentage
                FROM
                    (
                        SELECT
                            f.asset_id,
                            f.maint_trigger_id,
                            nvl(an2.curr_node_id,(
                                SELECT
                                    z.curr_node_id
                                FROM
                                    w1_asset_node z
                                WHERE
                                    an2.curr_attch_to_asset_id = z.curr_asset_id
                            )) AS node_id,
                            mt.tmpl_wo_id,
                            ta.tmpl_act_id,
                            next_maint_dt,
                            CASE
                                WHEN ( mt.f1_years > 0
                                       OR mt.f1_months > 0 )
                                     AND mt.f1_days = 0 THEN
                                    ( mt.f1_years * 12 ) + mt.f1_months
                                ELSE
                                    0
                            END AS months_bet_pm,
                            CASE
                                WHEN mt.f1_days > 0 THEN
                                    ( mt.f1_years * 365 ) + ( mt.f1_months * 30 ) + mt.f1_days
                                ELSE
                                    0
                            END AS days_bet_pm,
                            1 AS asset_percentage
                        FROM
                            assetfcst          f,
                            w1_maint_trigger   mt,
                            w1_tmpl_wo         tw,
                            w1_tmpl_act        ta,
                            w1_asset_node      an2
                        WHERE
                            mt.maint_trigger_id = f.maint_trigger_id
                            AND tw.tmpl_wo_id = ta.tmpl_wo_id
                            AND tw.tmpl_wo_id = mt.tmpl_wo_id
                            AND tw.tmpl_class_flg = 'W1GN'
                            AND f.asset_id = an2.curr_asset_id
                        UNION ALL
                        SELECT
                            assettw.asset_id,
                            assetmt.maint_trigger_id,
                            assettw.curr_node_id,
                            assettw.tmpl_wo_id,
                            assettw.tmpl_act_id,
                            assetmt.next_maint_dt,
                            assetmt.months_bet_pm,
                            assetmt.days_bet_pm,
                            assettw.asset_percentage / 100 AS asset_percentage
                        FROM
                            (
                                SELECT
                                    tacast.asset_id,
                                    tacast.curr_node_id,
                                    tacast.asset_type_cd,
                                    tacast.tmpl_wo_id,
                                    tacast.tmpl_act_id,
                                                                                                                                                --tacast.costDistAT,
                                    round(tacast.percentage / COUNT(DISTINCT tacast.asset_id) OVER(
                                        PARTITION BY tacast.tmpl_act_id, tacast.curr_node_id, tacast.costdistat
                                    ), 2) AS asset_percentage
                                FROM
                                    (
                                        SELECT
                                            a1.asset_id,
                                            a1.asset_type_cd,
                                            an.curr_node_id,
                                            tac.percentage,
                                            tac.tmpl_act_id,
                                            ta.tmpl_wo_id,
                                            tac.asset_type_cd AS costdistat
                                        FROM
                                            w1_tmpl_act_cost_dist   tac,
                                            w1_asset_node           an,
                                            w1_asset                a1,
                                            w1_tmpl_act             ta
                                        WHERE
                                            tac.node_id = an.curr_node_id
                                            AND a1.asset_id = an.asset_id
                                            AND decode(tac.asset_type_cd, ' ', a1.asset_type_cd, tac.asset_type_cd) = a1.asset_type_cd
                                            AND ta.tmpl_act_id = tac.tmpl_act_id
                                            AND an.asset_dpos_flg LIKE 'IN%'
                                        UNION ALL
                                        SELECT
                                            a1.asset_id,
                                            a1.asset_type_cd,
                                            an.curr_node_id,
                                            tac.percentage,
                                            tac.tmpl_act_id,
                                            ta.tmpl_wo_id,
                                            tac.asset_type_cd AS costdistat
                                        FROM
                                            w1_tmpl_act_cost_dist   tac,
                                            w1_asset_node           an,
                                            w1_asset_node           cmp,
                                            w1_asset                a1,
                                            w1_tmpl_act             ta
                                        WHERE
                                            tac.node_id = an.curr_node_id
                                            AND cmp.curr_attch_to_asset_id = an.asset_id
                                            AND a1.asset_id = cmp.asset_id
                                            AND decode(tac.asset_type_cd, ' ', a1.asset_type_cd, tac.asset_type_cd) = a1.asset_type_cd
                                            AND ta.tmpl_act_id = tac.tmpl_act_id
                                            AND an.asset_dpos_flg LIKE 'IN%'
                                            AND cmp.asset_dpos_flg LIKE 'AT%'
                                    ) tacast
                            ) assettw,
                            (
                                SELECT
                                    mt.maint_trigger_id,
                                    mt.tmpl_wo_id,
                                    f.next_maint_dt,
                                    f.asset_id,
                                    nvl(an2.curr_node_id,(
                                        SELECT
                                            z.curr_node_id
                                        FROM
                                            w1_asset_node z
                                        WHERE
                                            an2.curr_attch_to_asset_id = z.curr_asset_id
                                    )) AS node_id,
                                    CASE
                                        WHEN ( mt.f1_years > 0
                                               OR mt.f1_months > 0 )
                                             AND mt.f1_days = 0 THEN
                                            ( mt.f1_years * 12 ) + mt.f1_months
                                        ELSE
                                            0
                                    END AS months_bet_pm,
                                    CASE
                                        WHEN mt.f1_days > 0 THEN
                                            ( mt.f1_years * 365 ) + ( mt.f1_months * 30 ) + mt.f1_days
                                        ELSE
                                            0
                                    END AS days_bet_pm
                                FROM
                                    assetfcst          f,
                                    w1_maint_trigger   mt,
                                    w1_asset_node      an2
                                WHERE
                                    f.maint_trigger_id = mt.maint_trigger_id
                                    AND an2.curr_asset_id = f.asset_id
                            ) assetmt
                        WHERE
                            assetmt.tmpl_wo_id = assettw.tmpl_wo_id
                    )
            ) trg,
            (
                SELECT
                    z.tmpl_act_id,
                    SUM(z.tot_cost_amt) as tot_cost_amt,
                    sum(case when z.w1_resrc_class_flg = 'W1CR' then z.tot_cost_amt else 0 end) as tot_labor_cost_amt,
                    sum(case when z.w1_resrc_class_flg = 'W1EQ' then z.tot_cost_amt else 0 end) as tot_equip_cost_amt,
                    sum(case when z.w1_resrc_class_flg = 'W1MT' then z.tot_cost_amt else 0 end) as tot_matl_cost_amt,
                    sum(case when z.w1_resrc_class_flg = 'W1OT' then z.tot_cost_amt else 0 end) as tot_misc_cost_amt
                FROM
                    (
                        SELECT
                            tar.tmpl_act_id,
                            CASE
                                WHEN rt.w1_resrc_class_flg IN (
                                    'W1CR',
                                    'W1EQ'
                                ) THEN
                                    tar.w1_quantity * tar.unit_price * tar.w1_duration
                                ELSE
                                    tar.w1_quantity * tar.unit_price
                            END AS tot_cost_amt,
                            CASE
                                WHEN rt.w1_resrc_class_flg <> ' ' THEN
                                    rt.w1_resrc_class_flg
                                ELSE
                                    'W1MT'
                            END AS w1_resrc_class_flg
                        FROM
                            w1_tmpl_act_rsrc   tar,
                            w1_tmpl_act        ta,
                            w1_resrc_type      rt
                        WHERE
                            tar.tmpl_act_id = ta.tmpl_act_id
                            AND rt.resrc_type_id (+) = tar.resrc_type_id
                    ) z
                GROUP BY
                    z.tmpl_act_id
            ) wo_cost,
            w1_asset        ast,
            w1_asset_type   aty
        WHERE
            trg.asset_id = ast.asset_id
            AND wo_cost.tmpl_act_id = trg.tmpl_act_id
            AND ast.asset_type_cd = aty.asset_type_cd
    )
GROUP BY
    asset_id,
    node_id,
    in_service_dt,
    predctd_wear_out_dt,
    acquisition_dt,
    remain_life_yrs,
    owning_access_grp_cd;

-- ----- W1_BI_FORECASTEDASSETPMHRS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_FORECASTEDASSETPMHRS_VW" ("ASSET_ID", "RESRC_TYPE_ID", "NODE_ID", "IN_SERVICE_DT", "PREDCTD_WEAR_OUT_DT", "ACQUISITION_DT", "LABOR_HRS_NEXT_YR", "LABOR_HRS_NEXT_2_YRS", "LABOR_HRS_NEXT_5_YRS", "LABOR_HRS_NEXT_10_YRS", "LABOR_HRS_REMAIN_LIFE", "REMAIN_LIFE_YRS", "OWNING_ACCESS_GRP_CD", "ASSET_RESRC_TYPE_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  with assetFcst as
(     SELECT
          fc.asset_id,
          fc.maint_trigger_id,
          MIN(fc.forecast_dt) AS next_maint_dt
      FROM
          w1_asset_maint_trigger_fcst fc
      WHERE
          fc.forecast_dt >= current_date
      GROUP BY
          fc.asset_id,
          fc.maint_trigger_id  )
  SELECT
      asset_id              as ASSET_ID,
      resrc_type_id         as RESRC_TYPE_ID,
      node_id               as NODE_ID,
      in_service_dt         as IN_SERVICE_DT,
      predctd_wear_out_dt   as PREDCTD_WEAR_OUT_DT,
      acquisition_dt        as ACQUISITION_DT,
      SUM(labor_hours_next_yr) as LABOR_HRS_NEXT_YR,
      SUM(labor_hours_next_2yrs) as LABOR_HRS_NEXT_2_YRS,
      SUM(labor_hours_next_5yrs) as LABOR_HRS_NEXT_5_YRS,
      SUM(labor_hours_next_10yrs) as LABOR_HRS_NEXT_10_YRS,
      SUM(labor_hours_remain_life) as LABOR_HRS_REMAIN_LIFE,
      remain_life_yrs as REMAIN_LIFE_YRS,
      owning_access_grp_cd as OWNING_ACCESS_GRP_CD,
      1 as ASSET_RESRC_TYPE_CNT
  FROM
      (
          SELECT
              ast.asset_id,
              wo_hours.resrc_type_id,
              trg.node_id,
              trg.tmpl_wo_id,
              trunc(ast.in_service_dt) AS in_service_dt,
              trunc(ast.predctd_wear_out_dt) as predctd_wear_out_dt,
              trunc(ast.acquisition_dt) as acquisition_dt,
              trg.days_bet_pm,
              trg.next_maint_dt,
              wo_hours.tot_labor_hours,
              wo_hours.tot_labor_hours * asset_percentage * num_triggers_next_yr AS labor_hours_next_yr,
              wo_hours.tot_labor_hours * asset_percentage * num_triggers_next_2yrs AS labor_hours_next_2yrs,
              wo_hours.tot_labor_hours * asset_percentage * num_triggers_next_5yrs AS labor_hours_next_5yrs,
              wo_hours.tot_labor_hours * asset_percentage * num_triggers_next_10yrs AS labor_hours_next_10yrs,
             CASE
                 WHEN trg.months_bet_pm > 0 THEN wo_hours.tot_labor_hours * asset_percentage * floor( (nvl2(trunc(ast.in_service_dt),round
                 (greatest( (coalesce(ast.useful_life,aty.useful_life,0) * 12) - months_between(current_date,trunc(ast.in_service_dt
                 ) ),0),1),0) ) / trg.months_bet_pm)
                 ELSE wo_hours.tot_labor_hours * asset_percentage * floor( (nvl2(trunc(ast.in_service_dt),round(greatest( (coalesce(ast.useful_life,aty.useful_life,0) * 365) - (current_date - trunc(ast.in_service_dt) ),0),1),0) ) / trg.days_bet_pm
                 )
             END AS labor_hours_remain_life,
             nvl2(trunc(ast.in_service_dt),round(greatest( (coalesce(ast.useful_life,aty.useful_life,0) * 365) - (current_date - trunc
             (ast.in_service_dt) ),0) / 365,1),0) AS remain_life_yrs,
             ast.owning_access_grp_cd
          FROM
              (
                  SELECT
                      asset_id,
                      maint_trigger_id,
                      node_id,
                      tmpl_wo_id,
                      tmpl_act_id,
                      next_maint_dt,
                      months_bet_pm,
                      days_bet_pm,
                      CASE
                          WHEN months_bet_pm > 0 THEN floor( ( (months_between(add_months(current_date,12),next_maint_dt) ) ) / months_bet_pm
                          ) + 1
                          ELSE floor( ( (add_months(current_date,12) - next_maint_dt) ) / days_bet_pm) + 1
                      END AS num_triggers_next_yr,
                      CASE
                          WHEN months_bet_pm > 0 THEN floor( ( (months_between(add_months(current_date,24),next_maint_dt) ) ) / months_bet_pm
                          ) + 1
                          ELSE floor( ( (add_months(current_date,24) - next_maint_dt) ) / days_bet_pm) + 1
                      END AS num_triggers_next_2yrs,
                      CASE
                          WHEN months_bet_pm > 0 THEN floor( ( (months_between(add_months(current_date,60),next_maint_dt) ) ) / months_bet_pm
                          ) + 1
                          ELSE floor( ( (add_months(current_date,60) - next_maint_dt) ) / days_bet_pm) + 1
                      END AS num_triggers_next_5yrs,
                      CASE
                          WHEN months_bet_pm > 0 THEN floor( ( (months_between(add_months(current_date,120),next_maint_dt) ) ) / months_bet_pm
                          ) + 1
                          ELSE floor( ( (add_months(current_date,120) - next_maint_dt) ) / days_bet_pm) + 1
                      END AS num_triggers_next_10yrs,
                      asset_percentage
                  FROM
                      (
                          SELECT
                              f.asset_id,
                              f.maint_trigger_id,
                              nvl(an2.curr_node_id, (
                                  select
                                      z.curr_node_id
                                  from
                                      w1_asset_node z
                                  where
                                      an2.curr_attch_to_asset_id = z.curr_asset_id
                              ) ) as node_id,
                              mt.tmpl_wo_id,
                              ta.tmpl_act_id,
                              next_maint_dt,
                              CASE
                                  WHEN ( mt.f1_years > 0
                                         OR mt.f1_months > 0 )
                                       AND mt.f1_days = 0 THEN ( mt.f1_years * 12 ) + mt.f1_months
                                  ELSE 0
                              END AS months_bet_pm,
                              CASE
                                  WHEN mt.f1_days > 0 THEN ( mt.f1_years * 365 ) + ( mt.f1_months * 30 ) + mt.f1_days
                                  ELSE 0
                              END AS days_bet_pm,
                              1 AS asset_percentage
                          FROM
                              assetFcst f,
                              w1_maint_trigger mt,
                              w1_tmpl_wo tw,
                              w1_tmpl_act ta,
                              w1_asset_node an2
                          WHERE
                              mt.maint_trigger_id = f.maint_trigger_id
                              AND tw.tmpl_wo_id = ta.tmpl_wo_id
                              AND tw.tmpl_wo_id = mt.tmpl_wo_id
                              AND tw.tmpl_class_flg = 'W1GN'
                              AND f.asset_id = an2.curr_asset_id
                          UNION ALL
                          SELECT
                              assettw.asset_id,
                              assetmt.maint_trigger_id,
                              assettw.curr_node_id,
                              assettw.tmpl_wo_id,
                              assettw.tmpl_act_id,
                              assetmt.next_maint_dt,
                              assetmt.months_bet_pm,
                              assetmt.days_bet_pm,
                              assettw.asset_percentage / 100 AS asset_percentage
                          FROM
                              (
                                  SELECT
                                      tacast.asset_id,
                                      tacast.curr_node_id,
                                      tacast.asset_type_cd,
                                      tacast.tmpl_wo_id,
                                      tacast.tmpl_act_id,
                                      round(tacast.percentage / COUNT(DISTINCT tacast.asset_id) OVER(
                                          PARTITION BY tacast.tmpl_act_id,tacast.curr_node_id,tacast.costDistAT
                                      ),2) AS asset_percentage
                                  FROM
                                      (
                                          SELECT
                                              a1.asset_id,
                                              a1.asset_type_cd,
                                              an.curr_node_id,
                                              tac.percentage,
                                              tac.tmpl_act_id,
                                              ta.tmpl_wo_id,
                                              tac.asset_type_cd as costDistAT
                                          FROM
                                              w1_tmpl_act_cost_dist tac,
                                              w1_asset_node an,
                                              w1_asset a1,
                                              w1_tmpl_act ta
                                          WHERE
                                              tac.node_id = an.curr_node_id
                                              and a1.asset_id = an.asset_id
                                              AND decode(tac.asset_type_cd,' ',a1.asset_type_cd,tac.asset_type_cd) = a1.asset_type_cd
                                              AND ta.tmpl_act_id = tac.tmpl_act_id
                                             AND an.asset_dpos_flg like 'IN%'
                                          union all
                                          SELECT
                                              a1.asset_id,
                                              a1.asset_type_cd,
                                              an.curr_node_id,
                                              tac.percentage,
                                              tac.tmpl_act_id,
                                              ta.tmpl_wo_id,
                                              tac.asset_type_cd as costDistAT
                                          FROM
                                              w1_tmpl_act_cost_dist tac,
                                              w1_asset_node an,
                                              w1_asset_node cmp,
                                              w1_asset a1,
                                              w1_tmpl_act ta
                                          WHERE
                                              tac.node_id = an.curr_node_id
                                              and cmp.curr_attch_to_asset_id = an.asset_id
                                              and a1.asset_id = cmp.asset_id
                                              AND decode(tac.asset_type_cd,' ',a1.asset_type_cd,tac.asset_type_cd) = a1.asset_type_cd
                                              AND ta.tmpl_act_id = tac.tmpl_act_id
                                             AND an.asset_dpos_flg like 'IN%'
                                             AND cmp.asset_dpos_flg like 'AT%'
                                      ) tacast
                              ) assettw,
                              (
                                  SELECT
                                      mt.maint_trigger_id,
                                      mt.tmpl_wo_id,
                                      f.next_maint_dt,
                                      f.asset_id,
                                     nvl(an2.curr_node_id, (
                                         SELECT
                                             z.curr_node_id
                                         FROM
                                             w1_asset_node z
                                         WHERE
an2.curr_attch_to_asset_id = z.curr_asset_id
                                     ) ) AS node_id,
                                      CASE
                                          WHEN ( mt.f1_years > 0
                                                 OR mt.f1_months > 0 )
                                               AND mt.f1_days = 0 THEN ( mt.f1_years * 12 ) + mt.f1_months
                                          ELSE 0
                                      END AS months_bet_pm,
                                      CASE
                                          WHEN mt.f1_days > 0 THEN ( mt.f1_years * 365 ) + ( mt.f1_months * 30 ) + mt.f1_days
                                          ELSE 0
                                      END AS days_bet_pm
                                  FROM
                                      assetFcst f,
                                      w1_maint_trigger mt,
                                     w1_asset_node an2
                                  WHERE
                                      f.maint_trigger_id = mt.maint_trigger_id
                                      AND an2.curr_asset_id = f.asset_id
                              ) assetmt
                          WHERE
                              assetmt.tmpl_wo_id = assettw.tmpl_wo_id
                      )
              ) trg,
              (
                  SELECT
                      tar.tmpl_act_id,
                      rt.resrc_type_id,
                      sum(tar.w1_quantity * tar.w1_duration) AS tot_labor_hours
                  FROM
                      w1_tmpl_act_rsrc tar,
                      w1_resrc_type rt
                  WHERE
                      rt.resrc_type_id = tar.resrc_type_id
                      AND rt.w1_resrc_class_flg = 'W1CR'
                  group by
                      tar.tmpl_act_id,
                      rt.resrc_type_id
             ) wo_hours,
              w1_asset ast,
              w1_asset_type aty
         WHERE
              trg.asset_id = ast.asset_id
              AND wo_hours.tmpl_act_id = trg.tmpl_act_id
              AND ast.asset_type_cd = aty.asset_type_cd
      )
  GROUP BY
      asset_id,
      resrc_type_id,
      node_id,
      in_service_dt,
      predctd_wear_out_dt,
       acquisition_dt,
       remain_life_yrs,
       owning_access_grp_cd;

-- ----- W1_BI_LABORHOURS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_LABORHOURS_VW" ("TIMESHEET_DETAIL_ID", "W1_FT_ID", "RESRC_TYPE_ID", "COST_CENTER_CD", "COST_CATEGORY_CD", "ACT_ID", "ASSET_ID", "ACT_TYPE_CD", "SERVICE_CLASS_CD", "WORK_CATEGORY_CD", "WORK_CLASS_CD", "USER_ID", "TMPL_ACT_ID", "NODE_ID", "PLANNER_CD", "WO_ID", "W1_CREW_ID", "REQUIRED_BY_DT", "ACTVN_DTTM", "WORK_WIN_START_DTTM", "WORK_WIN_END_DTTM", "OWNING_ACCESS_GRP_CD", "ORIGINAL_WORK_DT", "PRJ_ID", "AMT", "FT_CRE_DTTM", "EXPENSE_CD", "ACT_RESRC_FT_CNT", "CHARGED_LABOR_HRS", "MAINT_ACT_LABOR_HRS", "CM_ACT_LABOR_HRS", "PM_ACT_LABOR_HRS", "CONSTR_ACT_LABOR_HRS", "REGULAR_LABOR_HRS", "OVERTIME_LABOR_HRS", "REGULAR_CM_ACT_LABOR_HRS", "OVERTIME_CM_ACT_LABOR_HRS", "REGULAR_PM_ACT_LABOR_HRS", "OVERTIME_PM_ACT_LABOR_HRS", "REGULAR_CONSTR_ACT_LABOR_HRS", "OVERTIME_CONSTR_ACT_LABOR_HRS", "EMERGENCY_LABOR_HRS", "REGULAR_EMERGENCY_LABOR_HRS", "OVERTIME_EMERGENCY_LABOR_HRS") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
      timesheet_detail_id,
      w1_ft_id,
      resrc_type_id,
      cost_center_cd,
      cost_category_cd,
      act_id,
      asset_id,
      act_type_cd,
      service_class_cd,
     work_category_cd,
      work_class_cd,
      user_id,
      tmpl_act_id,
      node_id,
      planner_cd,
      wo_id,
      w1_crew_id,
      required_by_dt,
      actvn_dttm,
      work_win_start_dttm,
      work_win_end_dttm,
      owning_access_grp_cd,
      original_work_dt,
      prj_id,
      amt,
      ft_cre_dttm,
      expense_cd,
	  act_resrc_ft_cnt,
      charged_labor_hrs,
      CASE
          WHEN maint_act_cnt = 1
               AND act_charge_type_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS maint_act_labor_hrs,
      CASE
          WHEN cm_act_cnt = 1
               AND act_charge_type_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS cm_act_labor_hrs,
      CASE
          WHEN pm_act_cnt = 1
               AND act_charge_type_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS pm_act_labor_hrs,
      CASE
          WHEN constr_act_cnt = 1
               AND act_charge_type_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS constr_act_labor_hrs,
      CASE
          WHEN regular_ft_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS regular_labor_hrs,
      CASE
          WHEN overtime_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS overtime_labor_hrs,
      CASE
          WHEN regular_ft_cnt = 1
               AND cm_act_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS regular_cm_act_labor_hrs,
      CASE
          WHEN overtime_cnt = 1
               AND cm_act_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS overtime_cm_act_labor_hrs,
      CASE
          WHEN regular_ft_cnt = 1
               AND pm_act_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS regular_pm_act_labor_hrs,
      CASE
          WHEN overtime_cnt = 1
               AND pm_act_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS overtime_pm_act_labor_hrs,
      CASE
          WHEN regular_ft_cnt = 1
               AND constr_act_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS regular_constr_act_labor_hrs,
      CASE
          WHEN overtime_cnt = 1
               AND constr_act_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS overtime_constr_act_labor_hrs,
      CASE
          WHEN emergency_flg = 'W1YS' THEN charged_labor_hrs
          ELSE 0
      END AS emergency_labor_hrs,
      CASE
          WHEN regular_ft_cnt = 1
               AND emergency_flg = 'W1YS' THEN charged_labor_hrs
          ELSE 0
      END AS regular_emergency_labor_hrs,
      CASE
          WHEN overtime_cnt = 1
               AND emergency_flg = 'W1YS' THEN charged_labor_hrs
          ELSE 0
      END AS overtime_emergency_labor_hrs
  FROM
      (
          SELECT
              ac.act_id,
              td.resrc_type_id,
              ac.user_id,
              ac.tmpl_act_id,
              ac.node_id,
              aa.asset_id,
              ac.act_type_cd,
              ac.service_class_cd,
             ac.work_category_cd,
              ac.work_class_cd,
              ac.planner_cd,
              ac.wo_id,
              ac.emergency_flg,
              ac.w1_crew_id,
              ac.required_by_dt,
              ac.actvn_dttm,
              ac.work_win_start_dttm,
              ac.work_win_end_dttm,
              ac.owning_access_grp_cd,
              ac.original_work_dt,
              td.prj_id,
              ft.w1_ft_id,
              ft.timesheet_detail_id,
              CASE
                  WHEN aa.act_id IS NOT NULL THEN ( ft.amt * aa.percentage ) / 100
                  ELSE ft.amt
              END AS amt,
              ft.ft_cre_dttm,
              td.expense_cd,
             CASE
                  WHEN aa.act_id IS NOT NULL THEN ( td.hours * aa.percentage * tc.percentage ) / 10000
                  ELSE ( td.hours * tc.percentage ) / 100
              END AS charged_labor_hrs,
              ft.cost_category_cd,
              ft.cost_center_cd,
			  1 AS ACT_RESRC_FT_CNT, 
              CASE
                  WHEN act.constr_related_flg = 'W1YS' THEN 1
                  ELSE 0
              END AS constr_act_cnt,
              CASE
                  WHEN wo.wo_id IS NOT NULL
                       AND wo.work_type_flg IN (
                      'W1PM',
                      'W1RG'
                  ) THEN 1
                  ELSE 0
              END AS maint_act_cnt,
              CASE
                  WHEN wo.wo_id IS NOT NULL
                       AND wo.work_type_flg = 'W1PM' THEN 1
                  ELSE 0
             END AS pm_act_cnt,
              CASE
                  WHEN wo.wo_id IS NOT NULL
                       AND wo.work_type_flg = 'W1RG' THEN 1
                  ELSE 0
              END AS cm_act_cnt,
              CASE
                  WHEN td.reg_overtime_flg = 'W1RE' THEN 1
                  ELSE 0
              END AS regular_ft_cnt,
              CASE
                  WHEN td.reg_overtime_flg = 'W1OT' THEN 1
                  ELSE 0
              END AS overtime_cnt,
              CASE
                  WHEN td.charge_type_flg = 'W1AC' THEN 1
                  ELSE 0
              END AS act_charge_type_cnt
          FROM
              w1_timesheet_detail td
              JOIN (
                  SELECT
                      ft.timesheet_detail_id,
                      ft.w1_ft_id,
                      ft.w1_ft_type_flg,
                      ft.act_id,
                      gl.cost_center_cd,
                      ec.cost_category_cd,
                      ft.cre_dttm   AS ft_cre_dttm,
                      SUM(gl.amt) amt
                  FROM
                      w1_ft ft,
                      w1_ft_gl_dtl gl,
                      w1_expense_cd ec
                  WHERE
                      ft.sibling_cancelled_flg = 'W1NO'
                      AND gl.w1_ft_id = ft.w1_ft_id
                      AND ( gl.amt * ft.amt ) * nvl2(nvl(ft.rtn_line_id,ft.mat_ret_line_id),-1,1) > 0
                      AND ft.bo_status_cd = 'FROZEN'
                      AND ec.expense_cd = gl.expense_cd
                  GROUP BY
                      ft.timesheet_detail_id,
                      ft.w1_ft_id,
                      ft.w1_ft_type_flg,
                      ft.act_id,
                      gl.cost_center_cd,
                      ec.cost_category_cd,
                      ft.cre_dttm
              ) ft ON ft.timesheet_detail_id = td.timesheet_detail_id
              JOIN w1_resrc_type rt ON rt.resrc_type_id = td.resrc_type_id
                                       AND rt.w1_resrc_class_flg = 'W1CR'
 
             JOIN w1_timsheetdtl_cost_ctr tc ON tc.timesheet_detail_id = td.timesheet_detail_id
                                                 AND tc.cost_center_cd = ft.cost_center_cd
              LEFT OUTER JOIN w1_activity ac ON ac.act_id = ft.act_id
                                                AND NOT ac.bo_status_cd IN (
                  'CANCELED'
              )
              LEFT OUTER JOIN w1_activity_type act ON act.act_type_cd = ac.act_type_cd
                                                      AND act.track_cost_flg = 'W1YS'
              LEFT OUTER JOIN w1_activity_asset aa ON aa.act_id = ac.act_id
                                                      AND aa.participation_flg = 'W1AW'
              LEFT OUTER JOIN w1_wo wo ON wo.wo_id = ac.wo_id
          WHERE
              NOT td.bo_status_cd IN (
                  'CANCELLED'
              )
      );

-- ----- W1_BI_NODE_HIERARCHY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_NODE_HIERARCHY_VW" ("NODE_ID", "DESCR100", "NODE_BUS_OBJ_DESCR100", "NODE_ID_LVL1", "DESCR100_LVL1", "NODE_BUS_OBJ_DESCR100_LVL1", "NODE_ID_LVL2", "DESCR100_LVL2", "NODE_BUS_OBJ_DESCR100_LVL2", "NODE_ID_LVL3", "DESCR100_LVL3", "NODE_BUS_OBJ_DESCR100_LVL3", "NODE_ID_LVL4", "DESCR100_LVL4", "NODE_BUS_OBJ_DESCR100_LVL4", "NODE_ID_LVL5", "DESCR100_LVL5", "NODE_BUS_OBJ_DESCR100_LVL5", "NODE_ID_LVL6", "DESCR100_LVL6", "NODE_BUS_OBJ_DESCR100_LVL6", "NODE_ID_LVL7", "DESCR100_LVL7", "NODE_BUS_OBJ_DESCR100_LVL7", "NODE_ID_LVL8", "DESCR100_LVL8", "NODE_BUS_OBJ_DESCR100_LVL8", "NODE_ID_LVL9", "DESCR100_LVL9", "NODE_BUS_OBJ_DESCR100_LVL9", "NODE_ID_LVL10", "DESCR100_LVL10", "NODE_BUS_OBJ_DESCR100_LVL10", "NODE_ID_LVL11", "DESCR100_LVL11", "NODE_BUS_OBJ_DESCR100_LVL11", "NODE_ID_LVL12", "DESCR100_LVL12", "NODE_BUS_OBJ_DESCR100_LVL12", "NODE_ID_LVL13", "DESCR100_LVL13", "NODE_BUS_OBJ_DESCR100_LVL13", "NODE_ID_LVL14", "DESCR100_LVL14", "NODE_BUS_OBJ_DESCR100_LVL14", "NODE_ID_LVL15", "DESCR100_LVL15", "NODE_BUS_OBJ_DESCR100_LVL15") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  with hierarchynodes as
(select /*+ materialize */ node_id, parent_node_id, bus_obj_cd, descr100
from w1_node q
WHERE q.parent_node_id is not null 
 union 
 select node_id, parent_node_id, bus_obj_cd, descr100
from w1_node q
WHERE q.parent_node_id is null and exists (select 'x' from W1_NODE NX where q.NODE_ID = NX.PARENT_NODE_ID)
)
select NODE_ID, descr100, bus_obj_cd AS NODE_BUS_OBJ_DESCR100, 
NODE_ID_LVL1, nvl2(descrs1, trim(substr(descrs1,1,100)), descr100) as DESCR100_LVL1, nvl2(descrs1, substr(descrs1,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL1,
NODE_ID_LVL2, nvl2(descrs2, trim(substr(descrs2,1,100)), descr100) as DESCR100_LVL2, nvl2(descrs2, substr(descrs2,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL2,
NODE_ID_LVL3, nvl2(descrs3, trim(substr(descrs3,1,100)), descr100) as DESCR100_LVL3, nvl2(descrs3, substr(descrs3,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL3,
NODE_ID_LVL4, nvl2(descrs4, trim(substr(descrs4,1,100)), descr100) as DESCR100_LVL4, nvl2(descrs4, substr(descrs4,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL4,
NODE_ID_LVL5, nvl2(descrs5, trim(substr(descrs5,1,100)), descr100) as DESCR100_LVL5, nvl2(descrs5, substr(descrs5,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL5,
NODE_ID_LVL6, nvl2(descrs6, trim(substr(descrs6,1,100)), descr100) as DESCR100_LVL6, nvl2(descrs6, substr(descrs6,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL6,
NODE_ID_LVL7, nvl2(descrs7, trim(substr(descrs7,1,100)), descr100) as DESCR100_LVL7, nvl2(descrs7, substr(descrs7,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL7,
NODE_ID_LVL8, nvl2(descrs8, trim(substr(descrs8,1,100)), descr100) as DESCR100_LVL8, nvl2(descrs8, substr(descrs8,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL8,
NODE_ID_LVL9, nvl2(descrs9, trim(substr(descrs9,1,100)), descr100) as DESCR100_LVL9, nvl2(descrs9, substr(descrs9,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL9,
NODE_ID_LVL10, nvl2(descrs10, trim(substr(descrs10,1,100)), descr100) as DESCR100_LVL10, nvl2(descrs10, substr(descrs10,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL10,
NODE_ID_LVL11, nvl2(descrs11, trim(substr(descrs11,1,100)), descr100) as DESCR100_LVL11, nvl2(descrs11, substr(descrs11,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL11,
NODE_ID_LVL12, nvl2(descrs12, trim(substr(descrs12,1,100)), descr100) as DESCR100_LVL12, nvl2(descrs12, substr(descrs12,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL12,
NODE_ID_LVL13, nvl2(descrs13, trim(substr(descrs13,1,100)), descr100) as DESCR100_LVL13, nvl2(descrs13, substr(descrs13,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL13,
NODE_ID_LVL14, nvl2(descrs14, trim(substr(descrs14,1,100)), descr100) as DESCR100_LVL14, nvl2(descrs14, substr(descrs14,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL14,
NODE_ID_LVL15, nvl2(descrs15, trim(substr(descrs15,1,100)), descr100) as DESCR100_LVL15, nvl2(descrs15, substr(descrs15,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL15
from
(
select vw.*,
decode(sign(hierarchyLevel),   1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL1), null) descrs1,
decode(sign(hierarchyLevel-1), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL2), null) descrs2,
decode(sign(hierarchyLevel-2), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL3), null) descrs3,
decode(sign(hierarchyLevel-3), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL4), null) descrs4,
decode(sign(hierarchyLevel-4), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL5), null) descrs5,
decode(sign(hierarchyLevel-5), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL6), null) descrs6,
decode(sign(hierarchyLevel-6), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL7), null) descrs7,
decode(sign(hierarchyLevel-7), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL8), null) descrs8,
decode(sign(hierarchyLevel-8), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL9), null) descrs9,
decode(sign(hierarchyLevel-9), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL10), null) descrs10,
decode(sign(hierarchyLevel-10), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL11), null) descrs11,
decode(sign(hierarchyLevel-11), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL12), null) descrs12,
decode(sign(hierarchyLevel-12), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL13), null) descrs13,
decode(sign(hierarchyLevel-13), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL14), null) descrs14,
decode(sign(hierarchyLevel-14), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL15), null) descrs15
from 
(
select NODE_ID, bus_obj_cd, descr100, hierarchyLevel, hierarchyPath,
decode(sign(hierarchyLevel), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,1)+1,12), NODE_ID) NODE_ID_LVL1,
decode(sign(hierarchyLevel-1), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,2)+1,12), NODE_ID) NODE_ID_LVL2,
decode(sign(hierarchyLevel-2), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,3)+1,12), NODE_ID) NODE_ID_LVL3,
decode(sign(hierarchyLevel-3), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,4)+1,12), NODE_ID) NODE_ID_LVL4,
decode(sign(hierarchyLevel-4), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,5)+1,12), NODE_ID) NODE_ID_LVL5,
decode(sign(hierarchyLevel-5), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,6)+1,12), NODE_ID) NODE_ID_LVL6,
decode(sign(hierarchyLevel-6), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,7)+1,12), NODE_ID) NODE_ID_LVL7,
decode(sign(hierarchyLevel-7), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,8)+1,12), NODE_ID) NODE_ID_LVL8,
decode(sign(hierarchyLevel-8), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,9)+1,12), NODE_ID) NODE_ID_LVL9,
decode(sign(hierarchyLevel-9), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,10)+1,12), NODE_ID) NODE_ID_LVL10,
decode(sign(hierarchyLevel-10), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,11)+1,12), NODE_ID) NODE_ID_LVL11,
decode(sign(hierarchyLevel-11), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,12)+1,12), NODE_ID) NODE_ID_LVL12,
decode(sign(hierarchyLevel-12), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,13)+1,12), NODE_ID) NODE_ID_LVL13,
decode(sign(hierarchyLevel-13), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,14)+1,12), NODE_ID) NODE_ID_LVL14,
decode(sign(hierarchyLevel-14), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,15)+1,12), NODE_ID) NODE_ID_LVL15
from
(
SELECT NODE_ID, bus_obj_cd, nvl(trim(descr100),' ') descr100, LEVEL-1 hierarchyLevel, SYS_CONNECT_BY_PATH(node_id, '/') hierarchyPath
FROM hierarchynodes q
start with q.parent_node_id is null
CONNECT BY PRIOR NODE_ID = PARENT_NODE_ID 
)
where hierarchyLevel <=15
) vw
);

-- ----- W1_BI_SERVICEHISTORY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_SERVICEHISTORY_VW" ("SVC_HIST_ID", "SVC_HIST_TYPE_CD", "SVC_HIST_CATEGORY_FLG", "BO_STATUS_CD", "BO_STATUS_REASON_CD", "SVC_HIST_CRE_DTTM", "END_DTTM", "SVC_HIST_STATUS_UPD_DTTM", "ASSET_ID", "IN_SERVICE_DT", "ACQUISITION_DT", "PREDCTD_WEAR_OUT_DT", "NODE_ID", "ACT_ID", "WO_ID", "FAILURE_MODE_CD", "FAILURE_TYPE_CD", "FAILURE_REPAIR_CD", "FAILURE_COMP_CD", "USER_ID", "EFF_DTTM", "ASSET_SCORE_FLG", "INSPECTED_BY_USER", "ANNIVERSARY_DT", "ANNIVERSARY_VALUE", "PERMIT_ID", "MAINT_SCHED_ID", "MAINT_TRIGGER_ID", "OWNING_ACCESS_GRP_CD", "SVC_HIST_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
     sh.svc_hist_id as SVC_HIST_ID,
     sh.svc_hist_type_cd as SVC_HIST_TYPE_CD,
     sht.svc_hist_category_flg as SVC_HIST_CATEGORY_FLG,
     sh.bo_status_cd as BO_STATUS_CD,
     sh.bo_status_reason_cd as BO_STATUS_REASON_CD,
     sh.cre_dttm as SVC_HIST_CRE_DTTM,
     sh.end_dttm as END_DTTM,
     sh.status_upd_dttm as SVC_HIST_STATUS_UPD_DTTM,
     sh.asset_id as ASSET_ID,
     trunc(ast.in_service_dt) as IN_SERVICE_DT,
     ast.acquisition_dt as ACQUISITION_DT,
     ast.predctd_wear_out_dt as PREDCTD_WEAR_OUT_DT,
     sh.node_id as NODE_ID,
     ac.act_id as ACT_ID,
     ac.wo_id as WO_ID,
     sh.failure_mode_cd as FAILURE_MODE_CD,
     sh.failure_type_cd as FAILURE_TYPE_CD,
     sh.failure_repair_cd as FAILURE_REPAIR_CD,
     sh.failure_comp_cd as FAILURE_COMP_CD,
     sh.user_id as USER_ID,
     sh.eff_dttm as EFF_DTTM,
     sh.asset_score_flg as ASSET_SCORE_FLG,
     sh.inspected_by_user as INSPECTED_BY_USER,
     sh.anniversary_dt as ANNIVERSARY_DT,
     sh.anniversary_value as ANNIVERSARY_VALUE,
     sh.permit_id as PERMIT_ID,
     sh.maint_sched_id as MAINT_SCHED_ID,
     sh.maint_trigger_id as MAINT_TRIGGER_ID,
     nvl(ast.owning_access_grp_cd, sh.owning_access_grp_cd) as OWNING_ACCESS_GRP_CD,
     1 as SVC_HIST_CNT
 FROM
    w1_svc_hist sh
 inner join w1_svc_hist_type sht on sht.svc_hist_type_cd = sh.svc_hist_type_cd
 left join w1_activity ac on ac.act_id = sh.act_id
 left join w1_asset ast on ast.asset_id = sh.asset_id;

-- ----- W1_BI_SPECIFICATION_MODEL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_SPECIFICATION_MODEL_VW" ("SPECIFICATION_CD", "W1_BI_MODEL") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
      specification_cd,
      w1_id_value   AS w1_bi_model
  FROM
      w1_specification_identifier si
  WHERE
      si.specification_id_type_flg = 'W1MD';

-- ----- W1_BI_STOCK_ITEM_DTLS_F_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_STOCK_ITEM_DTLS_F_VW" ("STOCK_ITEM_DTL_ID", "STOREROOM", "STOCK_ITEM_ID", "TOTAL_INVENTORY_COST", "TOTAL_INVENTORY_ON_HAND_QTY", "TOTAL_INV_OUT_STOCK_CNT", "TOTAL_RESERVED_QTY", "TOTAL_ON_DEMAND_QTY", "TOTAL_ON_ORDER_QTY", "TOTAL_IN_TRANSFER_QTY", "TOTAL_IN_RECEIPT_QTY", "TOTAL_PEND_RET_QTY", "TOTAL_INVENTORY_AVAILABLE_QTY", "SI_BELOW_SAFETY_STOCK_CNT", "SI_BELOW_MIN_QTY_CNT", "SI_BELOW_REORDER_PT_CNT", "OWNING_ACCESS_GRP_CD", "STOCK_ITEM_DTL_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    sid.stock_item_dtl_id,
    sid.node_id         AS storeroom,
    sid.resrc_type_id   AS stock_item_id,
    nvl(st.total_inventory_cost, 0) as total_inventory_cost,
    nvl(st.total_inventory_on_hand_qty, 0) as total_inventory_on_hand_qty,
    CASE
        WHEN total_inventory_on_hand_qty <= 0 THEN
            1
        ELSE
            0
    END AS total_inv_out_stock_cnt,
    nvl(st.total_reserved_qty, 0) as total_reserved_qty,
    nvl(st.total_on_demand_qty, 0) as total_on_demand_qty,
    nvl(st.total_on_order_qty, 0) as total_on_order_qty,
    nvl(st.total_in_transfer_qty, 0) as total_in_transfer_qty,
    nvl(st.total_in_receipt_qty, 0) as total_in_receipt_qty,
    nvl(materialretun.total_pend_ret_qty, 0) as total_pend_ret_qty,
    nvl(st.total_inventory_available_qty, 0) as total_inventory_available_qty,
    CASE
        WHEN sid.sid_class_flg IN (
            'W1IN',
            'W1IT',
            'W1IL'
        )
             AND st.total_inventory_available_qty < sid.safety_stock_qty THEN
            1
        ELSE
            0
    END AS si_below_safety_stock_cnt,
    CASE
        WHEN sid.sid_class_flg IN (
            'W1IN',
            'W1IT',
            'W1IL'
        )
             AND st.total_inventory_available_qty < sid.min_qty THEN
            1
        ELSE
            0
    END AS si_below_min_qty_cnt,
    CASE
        WHEN sid.sid_class_flg IN (
            'W1IN',
            'W1IT',
            'W1IL'
        )
             AND st.total_inventory_available_qty < sid.reorder_point THEN
            1
        ELSE
            0
    END AS si_below_reorder_pt_cnt,
    sid.owning_access_grp_cd,
    1 AS stock_item_dtl_cnt
FROM
    w1_stock_item_dtl   sid,
    (
        SELECT
            stock_item_dtl_id,
            SUM(total_inventory_on_hand_qty) AS total_inventory_on_hand_qty,
            SUM(total_inventory_cost) AS total_inventory_cost,
            SUM(total_on_demand_qty) AS total_on_demand_qty,
            SUM(total_on_order_qty) AS total_on_order_qty,
            SUM(total_in_transfer_qty) AS total_in_transfer_qty,
            SUM(total_in_receipt_qty) AS total_in_receipt_qty,
            SUM(total_reserved_qty) AS total_reserved_qty,
            ( SUM(total_inventory_on_hand_qty) + SUM(total_on_order_qty) + SUM(total_in_receipt_qty) + SUM(total_in_transfer_qty)
            ) - ( SUM(total_on_demand_qty) + SUM(total_reserved_qty) ) AS total_inventory_available_qty
        FROM
            (
                (
              -- Considering all SIDs except inv tracked for all quanities
                 SELECT
                    st1.stock_item_dtl_id,
                    SUM(inventory_qty) AS total_inventory_on_hand_qty,
                    SUM(st1.inventory_qty * st1.unit_price) AS total_inventory_cost,
                    SUM(st1.on_demand_qty) AS total_on_demand_qty,
                    SUM(st1.on_order_qty) AS total_on_order_qty,
                    SUM(st1.in_transfer_qty) AS total_in_transfer_qty,
                    SUM(st1.in_receipt_qty) AS total_in_receipt_qty,
                    SUM(st1.reserved_qty) AS total_reserved_qty
                FROM
                    w1_stock_trans      st1,
                    w1_stock_item_dtl   invsid
                WHERE
                    st1.st_rel_flg = 'W1YS'
                    AND invsid.stock_item_dtl_id = st1.stock_item_dtl_id
                    AND invsid.sid_class_flg != 'W1IT'
                GROUP BY
                    st1.stock_item_dtl_id
                )
                UNION
                (
                -- Considering only master SIDs of on hand quanities i.e lot managed sids only
                 SELECT
                    sidm.stock_item_dtl_id,
                    SUM(inventory_qty) total_inventory_on_hand_qty,
                    SUM(st2.inventory_qty * st2.unit_price) total_inventory_cost,
                    0 AS total_on_demand_qty,
                    0 AS total_on_order_qty,
                    SUM(in_transfer_qty) AS total_in_transfer_qty,
                    0 AS total_in_receipt_qty,
                    0 AS total_reserved_qty
                FROM
                    w1_stock_item_dtl   sid1,
                    w1_stock_trans      st2,
                    w1_stock_item_dtl   sidm
                WHERE
                    sid1.master_stock_item_dtl_id = sidm.stock_item_dtl_id
                    AND st2.stock_item_dtl_id = sid1.stock_item_dtl_id
                    AND st2.st_rel_flg = 'W1YS'
                GROUP BY
                    sidm.stock_item_dtl_id
                )
                UNION
                (
                -- Considering only inventory tracked SIDs for calculation of on hand quanities
                 SELECT
                    sid.stock_item_dtl_id,
                    COUNT(1) total_inventory_on_hand_qty,
                    SUM(ast.unit_price) total_inventory_cost,
                    0 AS total_on_demand_qty,
                    0 AS total_on_order_qty,
                    0 AS total_in_transfer_qty,
                    0 AS total_in_receipt_qty,
                    0 AS total_reserved_qty
                 --, 0 as total_pend_ret_qty
                FROM
                    w1_asset            ast,
                    w1_specification    spec,
                    w1_asset_node       an,
                    w1_stock_item_dtl   sid
                WHERE
                    spec.resrc_type_id = sid.resrc_type_id
                    AND ast.specification_cd = spec.specification_cd
                    AND an.asset_id = ast.asset_id
                    AND an.curr_node_id = sid.node_id
                    AND an.asset_dpos_flg = 'NI-INSTORE'
                GROUP BY
                    sid.stock_item_dtl_id
                )
                UNION
                (
              -- Considering only inv tracked SIDs
                 SELECT
                    st1.stock_item_dtl_id,
                    0 AS total_inventory_on_hand_qty,
                    0 AS total_inventory_cost,
                    SUM(st1.on_demand_qty) AS total_on_demand_qty,
                    SUM(st1.on_order_qty) AS total_on_order_qty,
                    SUM(st1.in_transfer_qty) AS total_in_transfer_qty,
                    SUM(st1.in_receipt_qty) AS total_in_receipt_qty,
                    SUM(st1.reserved_qty) AS total_reserved_qty
                FROM
                    w1_stock_trans      st1,
                    w1_stock_item_dtl   invtrackedsid
                WHERE
                    st1.st_rel_flg = 'W1YS'
                    AND invtrackedsid.stock_item_dtl_id = st1.stock_item_dtl_id
                    AND invtrackedsid.sid_class_flg = 'W1IT'
                GROUP BY
                    st1.stock_item_dtl_id
                )
            )
        GROUP BY
            stock_item_dtl_id
    ) st,
    (
        ( SELECT
            mt.stock_item_dtl_id,
            SUM(mt.return_qty) AS total_pend_ret_qty
        FROM
           -- w1_stock_trans    st111,
            w1_mat_ret_line   mt
        WHERE
           -- mt.mat_ret_line_id = st111.parent_pk1
           -- AND st111.parent_mo_cd = 'W1-MATRTNLIN'
            --AND
            mt.bo_status_cd = 'CREATED'
        GROUP BY
            mt.stock_item_dtl_id
        )
        UNION
        ( SELECT
            mastersid.master_stock_item_dtl_id,
            SUM(mt.return_qty) AS total_pend_ret_qty
        FROM
            --w1_stock_trans      st111,
            w1_mat_ret_line     mt,
            w1_stock_item_dtl   mastersid
        WHERE
          --  mt.mat_ret_line_id = st111.parent_pk1
            -- AND st111.parent_mo_cd = 'W1-MATRTNLIN' AND
             mt.bo_status_cd = 'CREATED'
             and mt.stock_item_dtl_id=mastersid.stock_item_dtl_id
            --AND mastersid.stock_item_dtl_id = st111.stock_item_dtl_id
            AND mastersid.master_stock_item_dtl_id IS NOT NULL
        GROUP BY
            mastersid.master_stock_item_dtl_id
        )
    ) materialretun,
    w1_resrc_type       si
WHERE
    sid.stock_item_dtl_id = st.stock_item_dtl_id (+)
    AND si.resrc_type_id = sid.resrc_type_id(+)
    AND sid.stock_item_dtl_id = materialretun.stock_item_dtl_id (+)
    AND sid.sid_class_flg IN (
        'W1IN',
        'W1IT',
        'W1IL',
        'W1SL'
    );

-- ----- W1_BI_STOCK_ITEM_DTL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_STOCK_ITEM_DTL_VW" ("STOCK_ITEM_DTL_ID", "SID_CLASS_FLG", "BO_STATUS_CD", "BUYER_CD", "COST_CENTER_CD", "MAX_QTY", "MIN_QTY", "SAFETY_STOCK_QTY", "REORDER_POINT", "REORDER_QTY", "AUTO_REORDER_FLG", "ABC_CLASS_FLG", "LEAD_TIME", "UOP", "UOI", "PI_RATIO", "TAX_RATE_SCHED_CD", "BIN_SEQNO", "BIN", "BIN_TYPE_FLG", "VENDOR_LOC_ID", "VENDOR_PART_NO", "VENDOR_PRI_FLG", "W1_MANUFACTURER_CD", "COPY_TO_PO_FLG", "MANUFACTURER_PART_NO", "MASTER_STOCK_ITEM_DTL_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    sid.stock_item_dtl_id,
    sid.sid_class_flg,
    sid.bo_status_cd,
    sid.buyer_cd,
    sid.cost_center_cd,
    sid.max_qty,
    sid.min_qty,
    sid.safety_stock_qty,
    sid.reorder_point,
    sid.reorder_qty,
    sid.auto_reorder_flg,
    sid.abc_class_flg,
    sid.lead_time,
    sid.uop,
    sid.uoi,
    sid.pi_ratio,
    sid.tax_rate_sched_cd,
    b.seqno AS bin_seqno,
    b.bin,
    b.bin_type_flg,
    vl.vendor_loc_id,
    vl.vendor_part_no,
    vl.vendor_pri_flg,
    (select  imfr.w1_manufacturer_cd
    from w1_resrc_type_mfr imfr
    where rownum=1 and imfr.RESRC_TYPE_ID=SID.RESRC_TYPE_ID and imfr.w1_manufacturer_cd= (
    SELECT
            MIN(m.w1_manufacturer_cd)
        FROM
            w1_resrc_type_mfr m
        WHERE
            m.resrc_type_id = sid.resrc_type_id
       )
    )
      as w1_manufacturer_cd,
    (select  imfr.copy_to_po_flg
    from w1_resrc_type_mfr imfr
    where rownum=1 and imfr.RESRC_TYPE_ID=SID.RESRC_TYPE_ID and imfr.w1_manufacturer_cd= (
    SELECT
            MIN(m.w1_manufacturer_cd)
        FROM
            w1_resrc_type_mfr m
        WHERE
            m.resrc_type_id = sid.resrc_type_id
       )
    ) as copy_to_po_flg,
    (select  imfr.manufacturer_part_no
    from w1_resrc_type_mfr imfr
    where rownum=1 and imfr.RESRC_TYPE_ID=SID.RESRC_TYPE_ID and imfr.w1_manufacturer_cd=(
    SELECT
            MIN(m.w1_manufacturer_cd)
        FROM
            w1_resrc_type_mfr m
        WHERE
            m.resrc_type_id = sid.resrc_type_id
       )
    ) as manufacturer_part_no,
    sid.master_stock_item_dtl_id
 
FROM
    w1_stock_item_dtl              sid
    LEFT OUTER JOIN w1_stock_item_dtl_bin          b ON b.stock_item_dtl_id = sid.stock_item_dtl_id
                                               AND b.bin_type_flg = 'W1PR'
    LEFT OUTER JOIN w1_stock_item_dtl_vendor_loc   vl ON vl.stock_item_dtl_id = sid.stock_item_dtl_id
                                                       AND vl.vendor_pri_flg = 'W1PR';

-- ----- W1_BI_STOCK_ITEM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_STOCK_ITEM_VW" ("STOCK_ITEM_ID", "BO_STATUS_CD", "STOCK_ITEM_CODE", "STOCK_INFORMATION", "DESCR100", "DESCRLONG", "STOCK_CAT_FLG", "HAZARDOUS_FLG", "HAZARD_TYPE_FLG", "LOT_MANAGED_FLG", "SHELF_LIFE", "CAPITAL_SPARE_FLG", "TRACKABLE_FLG", "REPAIRABLE_FLG", "TRUCK_STOCK_FLG", "ACPT_ON_RCPT_FLG", "PURCHASE_CMDTY_CD", "DO_NOT_SUB_FLG", "CMDTY_CAT_CD", "CMDTY_NAME_CD", "CMDTY_TYPE_CD", "INVENTORY_EXPENSE_CD", "EXPENSE_CD", "UNIT_PRICE", "ADD_TO_BOM_FLG") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    rt.resrc_type_id   AS stock_item_id,
    rt.bo_status_cd,
    rti.w1_id_value    AS stock_item_code,
    (rti.w1_id_value || ' (' || rtl.descr100 || ')') as stock_information,
    rtl.descr100,
    rtl.descrlong,
    rt.stock_cat_flg,
    rt.hazardous_flg,
    rt.hazard_type_flg,
    rt.lot_managed_flg,
    rt.shelf_life,
    rt.capital_spare_flg,
    rt.trackable_flg,
    rt.repairable_flg,
    rt.truck_stock_flg,
    rt.acpt_on_rcpt_flg,
    rt.purchase_cmdty_cd,
    rt.do_not_sub_flg,
    rt.cmdty_cat_cd,
    rt.cmdty_name_cd,
    rt.cmdty_type_cd,
    rt.inventory_expense_cd,
    rt.expense_cd,
    rt.unit_price,
    rt.add_to_bom_flg
FROM
    w1_resrc_type              rt,
    w1_resrc_type_l            rtl,
    w1_resrc_type_identifier   rti
WHERE
    rt.w1_resrc_class_flg = 'W1MT'
    AND rtl.resrc_type_id = rt.resrc_type_id
    AND rtl.language_cd = 'ENG'
    AND rti.resrc_type_id = rt.resrc_type_id
    AND rti.resrc_type_id_type_flg = 'W1RC';

-- ----- W1_BI_STOCK_TRANS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_STOCK_TRANS_VW" ("STOCK_TRANS_ID", "STOCK_ITEM_DTL_ID", "STOCK_ITEM_ID", "STOREROOM", "W1_TRANS_DT", "TOTAL_INVENTORY_ON_HAND_QTY", "TOTAL_ON_DEMAND_QTY", "TOTAL_ON_ORDER_QTY", "TOTAL_IN_TRANSFER_QTY", "TOTAL_IN_RECEIPT_QTY", "TOTAL_RESERVED_QTY", "TOTAL_INVENTORY_COST", "UNIT_PRICE", "INITIATED_BY_MO_CD", "MAT_ISSUE_LINE_ID", "MAT_RET_LINE_ID", "PI_CNT_LINE_ID", "INV_ADJ_ID", "ACCEPT_LINE_ID", "RTN_LINE_ID", "PO_LINE_ID", "REQUESTED_BY_MO_CD", "OWNING_ACCESS_GRP_CD", "STOCK_TRANS_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    st.stock_trans_id,
    st.stock_item_dtl_id,
    sid.resrc_type_id    AS stock_item_id,
    sid.node_id          AS storeroom,
    st.w1_trans_dt,
    
    case
        when sid.sid_class_flg  ='W1IT' THEN
          0
        ELSE
          st.inventory_qty
     END AS  total_inventory_on_hand_qty,  
    st.on_demand_qty     AS total_on_demand_qty,
    st.on_order_qty      AS total_on_order_qty,
    st.in_transfer_qty   AS total_in_transfer_qty,
    st.in_receipt_qty    AS total_in_receipt_qty,
    st.reserved_qty      AS total_reserved_qty,
     
    case
        when sid.sid_class_flg  ='W1IT' THEN
          0
        ELSE
          st.inventory_qty * st.unit_price
     END AS  total_inventory_cost,      
    st.unit_price,
    st.parent_mo_cd      AS initiated_by_mo_cd,
    CASE
        WHEN st.parent_mo_cd = 'W1-MATISSLIN' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS mat_issue_line_id,
    CASE
        WHEN st.parent_mo_cd = 'W1-MATRTNLIN' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS mat_ret_line_id,
    CASE
        WHEN st.parent_mo_cd = 'W1-PILINE' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS pi_cnt_line_id,
    CASE
        WHEN st.parent_mo_cd = 'W1-INVADJ' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS inv_adj_id,
    CASE
        WHEN st.parent_mo_cd = 'W1-ACPTLINE' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS accept_line_id,
    CASE
        WHEN st.parent_mo_cd = 'W1-RTNLINE' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS rtn_line_id,
    CASE
        WHEN st.parent_mo_cd = 'W1-POLINE' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS po_line_id,
    SIBLING_MO_CD  as REQUESTED_BY_MO_CD,
    sid.owning_access_grp_cd,
    1 AS STOCK_TRANS_CNT
FROM
    w1_stock_trans      st,
    w1_stock_item_dtl   sid
WHERE
    st.st_rel_flg = 'W1YS'
    AND sid.stock_item_dtl_id = st.stock_item_dtl_id
    and sid.sid_class_flg in ('W1IN','W1IT','W1IL','W1SL');

-- ----- W1_BI_STOREROOM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_STOREROOM_VW" ("STOREROOM", "NODE_TYPE_CD", "NODE_DPOS_FLG", "DESCR100", "PARENT_NODE_ID", "ADDRESS1", "ADDRESS2", "ADDRESS3", "ADDRESS4", "COUNTRY", "CITY", "W1_SUBURB", "STATE", "POSTAL", "LOCATION_CLASS_FLG", "W1_MAIN_CONTACT_ID", "SUPERVISOR_ID", "BUYER_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    a.node_id as STOREROOM,
    a.node_type_cd,
    a.node_dpos_flg,
    a.descr100,
    a.parent_node_id,
    a.address1,
    a.address2,
    a.address3,
    a.address4,
    a.country,
    a.city,
    a.w1_suburb,
    a.state,
    a.postal,
    a.location_class_flg,
    (
        SELECT
            w1_contact_id
        FROM
            w1_node_contact nc
        WHERE
            nc.node_id = a.node_id
            AND nc.node_contact_rel_flg = 'W1MC'
    ) AS w1_main_contact_id,
    (
        SELECT
            w1_contact_id
        FROM
            w1_node_contact nc
        WHERE
            nc.node_id = a.node_id
            AND nc.node_contact_rel_flg = 'W1SV'
    ) AS supervisor_id,
    buyer_cd
FROM
    w1_node a,
    w1_node_type nt
WHERE
    nt.node_type_cd = a.node_type_cd
    and nt.NODE_SUBCLASS_FLG = 'W1IN';

-- ----- W1_BI_WO_FINISHDT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_WO_FINISHDT_VW" ("WO_ID", "FINISH_DTTM") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
   WO_ID,
   MAX(LOG_DTTM) AS FINISH_DTTM
FROM
   W1_WO_LOG
WHERE
   BO_STATUS_CD = 'COMPLETED'
GROUP by WO_ID;

-- ----- W1_BI_WO_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_WO_VW" ("WO_ID", "BO_STATUS_CD", "BO_STATUS_REASON_CD", "CRE_DTTM", "USER_ID", "DESCR100", "TEMPLATE_NAME", "SVC_HIST_TYPE_CD", "SVC_SCHED_WO_ID", "WORK_REQ_ID", "WORK_PRIORITY_FLG", "DESCRLONG", "PRJ_ID", "REQUESTOR_ID", "W1_CREW_ID", "REQUIRED_BY_DT", "WORK_TYPE_FLG", "MAINT_SCHED_ID", "EMERGENCY_FLG", "WO_NUM", "CONSTR_RELATED_FLG", "WORK_DESIGN_ID", "WORK_CLASS_CD", "WORK_CATEGORY_CD", "OVERHEAD_CD", "PLANNER_CD", "OWNING_ACCESS_GRP_CD", "NODE_ID", "ASSET_ID", "WO_CRE_DTTM", "FINISH_DTTM", "ORIGINAL_WORK_DT", "CONSTR_WO_CNT", "MAINT_WO_CNT", "PM_WO_CNT", "CM_WO_CNT", "ADHERED_PM_DUE_DT_CNT", "ADHERED_CM_DUE_DT_CNT", "CRE_MAINT_WO_CNT", "CMPL_MAINT_WO_CNT", "CRE_CONSTR_WO_CNT", "CMPL_CONSTR_WO_CNT", "OPEN_WO_CNT", "OVERDUE_WO_CNT", "OVERDUE_MAINT_WO_CNT", "OVERDUE_CONSTR_WO_CNT", "OVERDUE_PM_WO_CNT", "OVERDUE_CM_WO_CNT", "OPEN_MAINT_WO_CNT", "OPEN_CONSTR_WO_CNT", "PLANNED_WO_CNT", "PLANNING_WO_CNT", "WO_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
     wo_id,
     bo_status_cd,
     bo_status_reason_cd,
     cre_dttm,
     user_id,
     descr100,
     template_name,
     svc_hist_type_cd,
     svc_sched_wo_id,
     work_req_id,
     work_priority_flg,
     descrlong,
     prj_id,
     requestor_id,
     w1_crew_id,
     required_by_dt,
     work_type_flg,
     maint_sched_id,
     emergency_flg,
     wo_num,
     constr_related_flg,
     work_design_id,
     work_class_cd,
     work_category_cd,
     overhead_cd,
     planner_cd,
     owning_access_grp_cd,
     node_id,
     asset_id,
     wo_cre_dttm,
     finish_dttm,
     original_work_dt,
     constr_wo_cnt,
     maint_wo_cnt,
     pm_wo_cnt,
     cm_wo_cnt,

     CASE
         WHEN work_type_flg = 'W1PM'
              AND finish_dttm IS NOT NULL
              AND trunc(finish_dttm) <= original_work_dt THEN 1
         ELSE 0
     END AS adhered_pm_due_dt_cnt,
     CASE
         WHEN work_type_flg = 'W1RG'
              AND finish_dttm IS NOT NULL
              AND trunc(finish_dttm) <= required_by_dt THEN 1
         ELSE 0
     END AS adhered_cm_due_dt_cnt,
     CASE
         WHEN bo_status_cd <> 'CANCELED' THEN maint_wo_cnt
         ELSE 0
     END AS cre_maint_wo_cnt,
     CASE
         WHEN bo_status_cd IN (
             'COMPLETED',
             'CLOSED'
         ) THEN maint_wo_cnt
         ELSE 0
     END AS cmpl_maint_wo_cnt,
     CASE
         WHEN bo_status_cd <> 'CANCELED' THEN constr_wo_cnt
         ELSE 0
     END AS cre_constr_wo_cnt,
     CASE
         WHEN bo_status_cd IN (
             'COMPLETED',
             'CLOSED'
         ) THEN constr_wo_cnt
         ELSE 0
     END AS cmpl_constr_wo_cnt,
     open_wo_cnt,
     overdue_wo_cnt,
     CASE
         WHEN maint_wo_cnt = 1
              AND overdue_wo_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_maint_wo_cnt,
     CASE
         WHEN constr_wo_cnt = 1
              AND overdue_wo_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_constr_wo_cnt,
       
     CASE
         WHEN pm_wo_cnt = 1
              AND bo_status_cd = 'ACTIVE'
              AND original_work_dt < current_date THEN 1
         ELSE 0
     END AS overdue_pm_wo_cnt,
     CASE
         WHEN cm_wo_cnt = 1
              AND overdue_wo_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_cm_wo_cnt,
     CASE
         WHEN open_wo_cnt = 1
              AND maint_wo_cnt = 1 THEN 1
         ELSE 0
     END AS open_maint_wo_cnt,
     CASE
         WHEN open_wo_cnt = 1
              AND constr_wo_cnt = 1 THEN 1
         ELSE 0
     END AS open_constr_wo_cnt,
     planned_wo_cnt,
     planning_wo_cnt,
     1 as wo_cnt
 FROM
     (
         SELECT
             wo_id,
             bo_status_cd,
             bo_status_reason_cd,
             cre_dttm,
             user_id,
             descr100,
             template_name,
             svc_hist_type_cd,
             svc_sched_wo_id,
             work_req_id,
             work_priority_flg,
             descrlong,
             prj_id,
             requestor_id,
             w1_crew_id,
             required_by_dt,
             work_type_flg,
             maint_sched_id,
             emergency_flg,
             wo_num,
             constr_related_flg,
             work_design_id,
             work_class_cd,
             work_category_cd,
             overhead_cd,
             planner_cd,
             owning_access_grp_cd,
             (
                 SELECT
                     ac.node_id
                 FROM
                     w1_activity ac
                 WHERE
                     ac.wo_id = wo.wo_id
                     AND ac.act_num = (
                         SELECT
                             MIN(ac2.act_num)
                         FROM
                             w1_activity ac2
                         WHERE
                             ac2.wo_id = ac.wo_id
                            AND ac2.bo_status_cd NOT IN('DISCARD','CANCELED','REJECTED')
                     )
             ) AS node_id,
             (
                 SELECT
                     ac.asset_id
                 FROM
                     w1_activity ac
                 WHERE
                     ac.wo_id = wo.wo_id
                     AND ac.act_num = (
                         SELECT
                             MIN(ac2.act_num)
                         FROM
                             w1_activity ac2
                         WHERE
                             ac2.wo_id = ac.wo_id
                             AND ac2.bo_status_cd NOT IN('DISCARD','CANCELED','REJECTED')
                     )
             ) AS asset_id,
             nvl2(wo.work_req_id, (
                 SELECT
                     wr.cre_dttm
                 FROM
                     w1_work_req wr
                 WHERE
                     wr.work_req_id = wo.work_req_id
             ),wo.cre_dttm) AS wo_cre_dttm,
             DECODE(TRIM(wo.bo_status_cd),'COMPLETED',wo.status_upd_dttm,(
                 SELECT
                     MAX(lg.log_dttm)
                 FROM
                     w1_wo_log lg
                 WHERE
                     lg.wo_id = wo.wo_id
                     AND lg.bo_status_cd = 'COMPLETED'
             ) ) AS finish_dttm,
             CASE
                 WHEN constr_related_flg = 'W1YS' THEN 1
                 ELSE 0
             END AS constr_wo_cnt,
             CASE
                 WHEN work_type_flg IN (
                     'W1PM',
                     'W1RG'
                 ) THEN 1
                 ELSE 0
             END AS maint_wo_cnt,
             CASE
                 WHEN work_type_flg = 'W1PM' THEN 1
                 ELSE 0
             END AS pm_wo_cnt,
             CASE
                 WHEN work_type_flg = 'W1RG' THEN 1
                 ELSE 0
             END AS cm_wo_cnt,
             (
                 SELECT
                     MIN(ac.original_work_dt)
                 FROM
                     w1_activity ac
                 WHERE
                     ac.wo_id = wo.wo_id
             ) AS original_work_dt,
             CASE
                 WHEN bo_status_cd IN (
                     'PLANNING',
                     'PENDAPPROVAL',
                     'APPROVED',
                     'ACTIVE',
                     'REOPENED'
                 ) THEN 1
                 ELSE 0
             END AS open_wo_cnt,
             CASE
                 WHEN bo_status_cd IN (
                     'APPROVED',
                     'ACTIVE'
                 ) THEN 1
                 ELSE 0
             END AS planned_wo_cnt,
             CASE
                 WHEN bo_status_cd = 'PLANNING' THEN 1
                 ELSE 0
             END AS planning_wo_cnt,
             CASE
                 WHEN bo_status_cd = 'ACTIVE'
                      AND required_by_dt < current_date THEN 1
                 ELSE 0
             END AS overdue_wo_cnt
         FROM
             w1_wo wo
         WHERE
              WORK_ROLE_FLG = 'W1PL'
     );

-- ----- W1_INI_ACTIVITY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_INI_ACTIVITY_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,
    EXT_PK_VALUE1,
    PK_VALUE1
  FROM F1_SYNC_REQ_IN
  WHERE MAINT_OBJ_CD        = 'W1-ACT'
  AND F1_COMPOSITE_SYNC_FLG = 'F1SS';

-- ----- W1_INI_ASSET_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_INI_ASSET_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,
EXT_PK_VALUE1,
PK_VALUE1
FROM F1_SYNC_REQ_IN
WHERE MAINT_OBJ_CD = 'W1-ASSET'
AND F1_COMPOSITE_SYNC_FLG = 'F1SS'
 
 
 ;

-- ----- W1_INI_CONTACT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_INI_CONTACT_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,
EXT_PK_VALUE1,
PK_VALUE1
FROM F1_SYNC_REQ_IN
WHERE MAINT_OBJ_CD = 'W1-CONTACT'
AND F1_COMPOSITE_SYNC_FLG = 'F1SS'
 
 
 ;

-- ----- W1_INI_COST_CENTER_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_INI_COST_CENTER_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,
EXT_PK_VALUE1,
PK_VALUE1
FROM F1_SYNC_REQ_IN
WHERE MAINT_OBJ_CD = 'W1-COSTCTR'
AND F1_COMPOSITE_SYNC_FLG = 'F1SS';

-- ----- W1_INI_EXPENSE_CODE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_INI_EXPENSE_CODE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,
    EXT_PK_VALUE1,
    PK_VALUE1
  FROM F1_SYNC_REQ_IN
  WHERE MAINT_OBJ_CD        = 'W1-EXPCODE'
  AND F1_COMPOSITE_SYNC_FLG = 'F1SS';

-- ----- W1_INI_MAINT_SCHEDULE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_INI_MAINT_SCHEDULE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,
    EXT_PK_VALUE1,
    PK_VALUE1
  FROM F1_SYNC_REQ_IN
  WHERE MAINT_OBJ_CD        = 'W1-MNTSCHED'
  AND F1_COMPOSITE_SYNC_FLG = 'F1SS';

-- ----- W1_INI_NODE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_INI_NODE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,
EXT_PK_VALUE1,
PK_VALUE1
FROM F1_SYNC_REQ_IN
WHERE MAINT_OBJ_CD = 'W1-NODE'
AND F1_COMPOSITE_SYNC_FLG = 'F1SS'
 
 
 ;

-- ----- W1_INI_PLANNER_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_INI_PLANNER_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,
    EXT_PK_VALUE1,
    PK_VALUE1
  FROM F1_SYNC_REQ_IN
  WHERE MAINT_OBJ_CD        = 'W1-PLANNER'
  AND F1_COMPOSITE_SYNC_FLG = 'F1SS';

-- ----- W1_INI_PROJECT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_INI_PROJECT_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,
    EXT_PK_VALUE1,
    PK_VALUE1
  FROM F1_SYNC_REQ_IN
  WHERE MAINT_OBJ_CD        = 'W1-PRJ'
  AND F1_COMPOSITE_SYNC_FLG = 'F1SS';

-- ----- W1_INI_TML_ACTIVITY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_INI_TML_ACTIVITY_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,
    EXT_PK_VALUE1,
    PK_VALUE1
  FROM F1_SYNC_REQ_IN
  WHERE MAINT_OBJ_CD        = 'W1-TMPACT'
  AND F1_COMPOSITE_SYNC_FLG = 'F1SS';

-- ----- W1_INI_TML_WORK_ORDER_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_INI_TML_WORK_ORDER_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,
    EXT_PK_VALUE1,
    PK_VALUE1
  FROM F1_SYNC_REQ_IN
  WHERE MAINT_OBJ_CD        = 'W1-TMPLWO'
  AND F1_COMPOSITE_SYNC_FLG = 'F1SS';

-- ----- W1_INI_WORK_LOCATION_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_INI_WORK_LOCATION_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,
    EXT_PK_VALUE1,
    PK_VALUE1
  FROM F1_SYNC_REQ_IN
  WHERE MAINT_OBJ_CD        = 'W1-WORKLOC'
  AND F1_COMPOSITE_SYNC_FLG = 'F1SS';

-- ----- W1_INI_WORK_ORDER_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_INI_WORK_ORDER_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NT_XID_CD,
    EXT_PK_VALUE1,
    PK_VALUE1
  FROM F1_SYNC_REQ_IN
  WHERE MAINT_OBJ_CD        = 'W1-WORKORDER'
  AND F1_COMPOSITE_SYNC_FLG = 'F1SS';

-- ----- W1_ON_ASSET_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_ASSET_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT ASSET_ID_TYPE_FLG,
W1_ID_VALUE,
ASSET_ID
FROM W1_ASSET_IDENTIFIER
 
 
 ;

-- ----- W1_ON_BLANKET_CONTRACT_LINE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_BLANKET_CONTRACT_LINE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    CHAR_TYPE_CD as NT_XID_CD,
ADHOC_CHAR_VAL as  EXT_PK_VALUE1,
BC_LINE_ID as PK_VALUE1
FROM      W1_BC_LINE_CHAR;

-- ----- W1_ON_BLANKET_CONTRACT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_BLANKET_CONTRACT_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    BC_HEADER_ID_TYPE_FLG as NT_XID_CD,
W1_ID_VALUE as  EXT_PK_VALUE1,
BC_HEADER_ID as PK_VALUE1
FROM      W1_BC_HEADER_IDENTIFIER;

-- ----- W1_ON_CONTACT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_CONTACT_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT W1_CONTACT_ID_TYPE_FLG,
W1_ID_VALUE,
W1_CONTACT_ID
FROM W1_CONTACT_IDENTIFIER
 
 
 ;

-- ----- W1_ON_COST_CENTER_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_COST_CENTER_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT COST_CENTER_ID_TYPE_FLG as NT_XID_CD,
    W1_ID_VAL as EXT_PK_VALUE1,
    COST_CENTER_CD as PK_VALUE1
FROM W1_COST_CENTER_IDENTIFIER;

-- ----- W1_ON_CRAFT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_CRAFT_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT RESRC_TYPE_ID_TYPE_FLG,
W1_ID_VALUE,
RESRC_TYPE_ID 
FROM W1_RESRC_TYPE_IDENTIFIER RTI
WHERE 
RESRC_TYPE_ID IN (
  SELECT RESRC_TYPE_ID
FROM W1_RESRC_TYPE
WHERE W1_RESRC_CLASS_FLG='W1CR');

-- ----- W1_ON_EMPLOYEE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_EMPLOYEE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT EMPLOYEE_ID_TYPE_FLG,
    W1_ID_VALUE,
    EMPLOYEE_ID
FROM W1_EMPLOYEE_IDENTIFIER;

-- ----- W1_ON_EU_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_EU_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT EU_ID_TYPE_FLG,
W1_ID_VALUE,
EU_ID 
FROM W1_EU_IDENTIFIER;

-- ----- W1_ON_FINANCIAL_TRANS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_FINANCIAL_TRANS_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    CHAR_TYPE_CD as NT_XID_CD,
ADHOC_CHAR_VAL as  EXT_PK_VALUE1,
W1_FT_ID as PK_VALUE1
FROM      W1_FT_CHAR;

-- ----- W1_ON_INVOICE_LINE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_INVOICE_LINE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    CHAR_TYPE_CD as NT_XID_CD,
ADHOC_CHAR_VAL as  EXT_PK_VALUE1,
INVOICE_LINE_ID as PK_VALUE1
FROM      W1_INVOICE_LINE_CHAR;

-- ----- W1_ON_INVOICE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_INVOICE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    INVOICE_HEADER_ID_TYPE_FLG as NT_XID_CD,
W1_ID_VALUE as  EXT_PK_VALUE1,
INVOICE_HEADER_ID as PK_VALUE1
FROM      W1_INVOICE_HEADER_IDENTIFIER;

-- ----- W1_ON_MATERIAL_ISSUE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_MATERIAL_ISSUE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    CHAR_TYPE_CD as NT_XID_CD,
ADHOC_CHAR_VAL as  EXT_PK_VALUE1,
MAT_ISS_LINE_ID as PK_VALUE1
FROM      W1_MAT_ISS_LINE_CHAR;

-- ----- W1_ON_MATERIAL_RETURN_LINE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_MATERIAL_RETURN_LINE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    CHAR_TYPE_CD as NT_XID_CD,
ADHOC_CHAR_VAL as  EXT_PK_VALUE1,
MAT_RET_LINE_ID as PK_VALUE1
FROM      W1_MAT_RET_LINE_CHAR;

-- ----- W1_ON_MATERIAL_RETURN_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_MATERIAL_RETURN_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    CHAR_TYPE_CD as NT_XID_CD,
ADHOC_CHAR_VAL as  EXT_PK_VALUE1,
MAT_RET_HEADER_ID as PK_VALUE1
FROM      W1_MAT_RET_HEADER_CHAR;

-- ----- W1_ON_NODE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_NODE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT NODE_ID_TYPE_FLG,
W1_ID_VALUE,
NODE_ID
FROM W1_NODE_IDENTIFIER
 
 
 ;

-- ----- W1_ON_PURCHASE_ORDER_LINE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_PURCHASE_ORDER_LINE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    CHAR_TYPE_CD as NT_XID_CD,
ADHOC_CHAR_VAL as  EXT_PK_VALUE1,
PO_LINE_ID as PK_VALUE1
FROM      W1_PO_LINE_CHAR;

-- ----- W1_ON_PURCHASE_ORDER_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_PURCHASE_ORDER_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    PO_HEADER_ID_TYPE_FLG as NT_XID_CD,
W1_ID_VALUE as  EXT_PK_VALUE1,
PO_HEADER_ID as PK_VALUE1
FROM      W1_PO_HEADER_IDENTIFIER;

-- ----- W1_ON_RECEIPT_LINE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_RECEIPT_LINE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    CHAR_TYPE_CD as NT_XID_CD,
ADHOC_CHAR_VAL as  EXT_PK_VALUE1,
RCPT_LINE_ID as  PK_VALUE1
FROM      W1_RCPT_LINE_CHAR;

-- ----- W1_ON_RECEIPT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_RECEIPT_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    RCPT_HDR_ID_TYPE_FLG as NT_XID_CD,
W1_ID_VALUE as  EXT_PK_VALUE1,
RCPT_HDR_ID as  PK_VALUE1
FROM      W1_RCPT_HDR_IDENTIFIER;

-- ----- W1_ON_RETURN_LINE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_RETURN_LINE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    CHAR_TYPE_CD as NT_XID_CD,
ADHOC_CHAR_VAL as  EXT_PK_VALUE1,
RTN_LINE_ID as PK_VALUE1
FROM      W1_RTN_LINE_CHAR;

-- ----- W1_ON_STOCK_ITEM_DTL_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_STOCK_ITEM_DTL_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT  STOCK_ITEM_DTL_ID_TYPE_FLG as NT_XID_CD,
W1_ID_VALUE as EXT_PK_VALUE1,
STOCK_ITEM_DTL_ID as PK_VALUE1
FROM  W1_STOCK_ITEM_DTL_IDENTIFIER;

-- ----- W1_ON_STOCK_ITEM_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_STOCK_ITEM_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT 		RESRC_TYPE_ID_TYPE_FLG as NT_XID_CD,
W1_ID_VALUE as EXT_PK_VALUE1,
RESRC_TYPE_ID as PK_VALUE1
FROM 		W1_RESRC_TYPE_IDENTIFIER;

-- ----- W1_ON_STOCK_TRANS_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_STOCK_TRANS_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT    CHAR_TYPE_CD as NT_XID_CD,
ADHOC_CHAR_VAL as  EXT_PK_VALUE1,
STOCK_TRANS_ID as PK_VALUE1
FROM      W1_STOCK_TRANS_CHAR;

-- ----- W1_ON_VENDOR_LOC_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_ON_VENDOR_LOC_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT VENDOR_LOC_ID_TYPE_FLG as NT_XID_CD,
    W1_ID_VAL as EXT_PK_VALUE1,
    VENDOR_LOC_ID as PK_VALUE1
FROM W1_VENDOR_LOC_IDENTIFIER;

-- ----- W1_PARENT_ORG_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_PARENT_ORG_VW" ("PARENT_NODE_ID", "NODE_ID") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  WITH R (NODE_ID,PARENT_NODE_ID,IS_ORG) AS
  (SELECT NODE.NODE_ID,
    NODE.PARENT_NODE_ID ,
    (
    CASE
      WHEN NTYP.INST_ASSET_REL_FLG    = 'W1NO'
      AND NTYP.NOT_INST_ASSET_REL_FLG = 'W1NO'
      THEN'Y'
      ELSE 'N'
    END) AS IS_ORG
  FROM W1_NODE NODE,
    W1_NODE PNODE,
    W1_NODE_TYPE NTYP
  WHERE PNODE.NODE_TYPE_CD = NTYP.NODE_TYPE_CD
  AND NODE.PARENT_NODE_ID  = PNODE.NODE_ID
  UNION ALL
  SELECT R.NODE_ID,
    NODE.PARENT_NODE_ID ,
    (
    CASE
      WHEN NTYP.INST_ASSET_REL_FLG    = 'W1NO'
      AND NTYP.NOT_INST_ASSET_REL_FLG = 'W1NO'
      THEN'Y'
      ELSE 'N'
    END) AS IS_ORG
  FROM W1_NODE NODE ,
    W1_NODE PNODE,
    W1_NODE_TYPE NTYP,
    R
  WHERE PNODE.NODE_TYPE_CD = NTYP.NODE_TYPE_CD
  AND NODE.NODE_ID         = R.PARENT_NODE_ID
  AND NODE.PARENT_NODE_ID  = PNODE.NODE_ID
  AND R.IS_ORG             = 'N'
  )
SELECT DISTINCT PARENT_NODE_ID,NODE_ID FROM R WHERE IS_ORG = 'Y';

-- ----- X1_BI_ACTIVITY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."X1_BI_ACTIVITY_VW" ("D1_ACTIVITY_ID", "ACTIVITY_TYPE_CD", "BO_STATUS_CD", "BO_STATUS_REASON_CD", "BO_STATUS_COND_FLG", "ACTIVITY_TYPE_CAT_FLG", "CRE_DTTM", "STATUS_UPD_DTTM", "START_DTTM", "END_DTTM", "EFF_DTTM", "ACT_DUR_SEC", "D1_SPR_CD", "D1_DEVICE_ID", "D1_SP_ID", "D1_SP_TYPE_CD", "FACILITY_ID", "PREM_ID", "SA_ID", "ACCT_ID", "PER_ID", "ILM_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  with DS as (
    select AC.D1_ACTIVITY_ID,
           cast(AD.PK_VALUE1 as varchar2(12)) as D1_DEVICE_ID,
           nvl(DS.D1_SP_ID, cast(AP.PK_VALUE1 as varchar2(12))) D1_SP_ID
     from      D1_ACTIVITY         AC
     left join D1_ACTIVITY_REL_OBJ AP on AP.D1_ACTIVITY_ID = AC.D1_ACTIVITY_ID and AP.MAINT_OBJ_CD = 'D1-SP'        and AP.ACTIVITY_REL_OBJ_TYPE_FLG = 'D1RO'
     left join D1_ACTIVITY_REL_OBJ AD on AD.D1_ACTIVITY_ID = AC.D1_ACTIVITY_ID and AD.MAINT_OBJ_CD = 'D1-DEVICE'    and AD.ACTIVITY_REL_OBJ_TYPE_FLG = 'D1RO'
     left join (select D1.D1_DEVICE_ID,
                    last_value(I1.D1_SP_ID) over (partition by D1.D1_DEVICE_ID order by I1.D1_INSTALL_DTTM) D1_SP_ID
                     from D1_DVC_CFG     D1
               inner join D1_INSTALL_EVT I1 on D1.DEVICE_CONFIG_ID = I1.DEVICE_CONFIG_ID
                                ) DS on DS.D1_DEVICE_ID = AD.PK_VALUE1
), SS as (
    select SP_ID, max(SA_ID) SA_ID
      from CI_SA_SP S1
     where START_DTTM = (select min(START_DTTM) START_DTTM from CI_SA_SP /* longest active */
                          where SP_ID = S1.SP_ID and STOP_DTTM is null)
     group by SP_ID
)
select AC.D1_ACTIVITY_ID,
       AC.ACTIVITY_TYPE_CD,
       AC.BO_STATUS_CD,
       AC.BO_STATUS_REASON_CD,
       BS.BO_STATUS_COND_FLG,
       AT.ACTIVITY_TYPE_CAT_FLG,
       AC.CRE_DTTM,
       AC.STATUS_UPD_DTTM,
       AC.START_DTTM,
       AC.END_DTTM,
       AC.EFF_DTTM,
  case when BS.BO_STATUS_COND_FLG = 'F1FL' then
       round((greatest(AC.CRE_DTTM, AC.STATUS_UPD_DTTM, nvl(AC.END_DTTM, AC.STATUS_UPD_DTTM)) - AC.CRE_DTTM)*24*60*60)
  else round((CURRENT_DATE - AC.CRE_DTTM)*24*60*60) end as ACT_DUR_SEC,
       cast(AR.PK_VALUE1 as varchar2(30)) as D1_SPR_CD,
       DS.D1_DEVICE_ID,
       DS.D1_SP_ID,
       ST.D1_SP_TYPE_CD,
       SF.FACILITY_ID,
       cast(nvl(PI.ID_VALUE, SC.PREM_ID) as char(10)) as PREM_ID,
       SS.SA_ID,
       SA.ACCT_ID,
       PE.PER_ID,
       AC.ILM_DT
 from      D1_ACTIVITY         AC
inner join                     DS  on DS.D1_ACTIVITY_ID = AC.D1_ACTIVITY_ID
inner join D1_ACTIVITY_TYPE    AT  on AT.ACTIVITY_TYPE_CD = AC.ACTIVITY_TYPE_CD
inner join F1_BUS_OBJ          BO  on BO.BUS_OBJ_CD     = AC.BUS_OBJ_CD
inner join F1_BUS_OBJ_STATUS   BS  on BS.BUS_OBJ_CD     = BO.LIFE_CYCLE_BO_CD  and BS.BO_STATUS_CD   = AC.BO_STATUS_CD
 left join D1_ACTIVITY_REL_OBJ AR  on AR.D1_ACTIVITY_ID = AC.D1_ACTIVITY_ID    and AR.MAINT_OBJ_CD   = 'D1-SVCPROVDR' and AR.ACTIVITY_REL_OBJ_TYPE_FLG = 'D1RC'
 left join D1_SP_IDENTIFIER    SI  on SI.D1_SP_ID       = DS.D1_SP_ID          and SI.SP_ID_TYPE_FLG = 'D1EI'
 left join D1_SP_IDENTIFIER    PI  on PI.D1_SP_ID       = DS.D1_SP_ID          and PI.SP_ID_TYPE_FLG = 'D1EP'
 left join D1_SP               ST  on ST.D1_SP_ID       = DS.D1_SP_ID
 left join D1_SP_FACILITY      SF  on SF.D1_SP_ID       = DS.D1_SP_ID          and SF.FACILITY_REL_TYPE_FLG = 'D1CD'
 left join                     SS  on SS.SP_ID          = SI.ID_VALUE
 left join CI_SP               SC  on SC.SP_ID          = SS.SP_ID
 left join CI_SA               SA  on SA.SA_ID          = SS.SA_ID
 left join CI_ACCT_PER         PE  on PE.ACCT_ID        = SA.ACCT_ID           and PE.MAIN_CUST_SW = 'Y';

-- ----- X1_BI_CASE_LOG_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."X1_BI_CASE_LOG_VW" ("CASE_ID", "SEQ_NUM", "CASE_LOG_TYPE_FLG", "CASE_TYPE_CD", "CASE_STATUS_CD", "ACCT_ID", "PER_ID", "PREM_ID", "USER_ID", "LOG_DTTM", "PREV_LOG_DTTM", "PREV_CASE_STATUS_CD", "PREV_STATE_DUR", "CURR_STATE_DUR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  select
  clog.case_id,clog.seq_num,   clog.case_log_type_flg,  ca.case_type_cd,  clog.case_status_cd,
  ca.acct_id,  ca.per_id,  ca.prem_id ,  ca.user_id,
  clog.log_dttm ,
  LAG(clog.log_dttm) OVER (PARTITION BY clog.case_id ORDER BY clog.log_dttm,clog.seq_num) AS prev_log_dttm,
  LAG(clog.case_status_cd) OVER (PARTITION BY clog.case_id ORDER BY clog.log_dttm,clog.seq_num) AS prev_case_status,
  decode(clog.case_log_type_flg, 'CASC',0, round((log_dttm - LAG(clog.log_dttm) OVER (PARTITION BY clog.case_id ORDER BY clog.log_dttm,clog.seq_num))*24*60 , 2)) as prev_state_dur,
 CASE
       when st.status_cond_flg <> 'FINL' and  LEAD(clog.log_dttm) OVER( PARTITION BY clog.case_id  ORDER BY clog.log_dttm,clog.seq_num) is null  then round((current_date -  clog.log_dttm)*24*60,2)
       when st.status_cond_flg <> 'FINL' and not(LEAD(clog.log_dttm) OVER( PARTITION BY clog.case_id  ORDER BY clog.log_dttm,clog.seq_num) is null) then round((LEAD(clog.log_dttm) OVER (PARTITION BY clog.case_id  ORDER BY clog.log_dttm,clog.seq_num) - clog.log_dttm)*24*60,2)
       else 0
   END as curr_state_dur
from
     ci_case_log clog,
     ci_case ca ,ci_case_status st
WHERE
     clog.case_log_type_flg IN (
         'CASC',
         'STAT'
     )
AND ca.case_id = clog.case_id
AND st.case_type_cd = ca.case_type_cd
AND st.case_status_cd = clog.case_status_cd
ORDER BY clog.case_id ,clog.seq_num ;

-- ----- X1_BI_CASE_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."X1_BI_CASE_VW" ("CASE_ID", "CASE_TYPE_CD", "CASE_STATUS_CD", "ACCT_ID", "PER_ID", "PREM_ID", "USER_ID", "CASE_CRE_DTTM", "CASE_COND_FLG", "CLOSED_DTTM", "ILM_DT", "ILM_ARCH_SW", "CASE_DUR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  select CA.CASE_ID, CA.CASE_TYPE_CD, CA.CASE_STATUS_CD,
     ACCT_ID, PER_ID, PREM_ID , CA.USER_ID,
     CRE_DTTM AS CASE_CRE_DTTM, CASE_COND_FLG,CLOSED_DTTM,
     CA.ILM_DT, CA.ILM_ARCH_SW,
 CASE
       when CLOSED_DTTM is null  then round((current_date -  cre_dttm)*24*60,2)
       else round((closed_dttm -  cre_dttm)*24*60,2)
     END as CASE_DUR
from CI_CASE CA
inner join
    (select C1.CASE_ID, max(CL.LOG_DTTM) CRE_DTTM, max(CR.LOG_DTTM) CLOSED_DTTM
          from CI_CASE     C1
    inner join CI_CASE_LOG CL on CL.CASE_ID = C1.CASE_ID   and CL.CASE_LOG_TYPE_FLG = 'CASC'
     left join CI_CASE_LOG CR on C1.CASE_COND_FLG = 'CLSD' and CR.CASE_ID = C1.CASE_ID  and CR.CASE_LOG_TYPE_FLG = 'STAT'
    group by C1.CASE_ID) C2 on C2.CASE_ID = CA.CASE_ID
order by CA.CASE_ID;

-- ----- X1_BI_DVC_EVT_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."X1_BI_DVC_EVT_VW" ("DVC_EVT_ID", "DVC_EVT_TYPE_CD", "BO_STATUS_CD", "BO_STATUS_REASON_CD", "EXT_EVT_NAME_FLG", "CRE_DTTM", "STATUS_UPD_DTTM", "DVC_EVT_DTTM", "D1_SPR_CD", "D1_DEVICE_ID", "MEASR_COMP_ID", "D1_SP_ID", "PREM_ID", "SA_ID", "ACCT_ID", "PER_ID", "ILM_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  select DE.DVC_EVT_ID,
       DE.DVC_EVT_TYPE_CD,
       DE.BO_STATUS_CD,
       DE.BO_STATUS_REASON_CD,
       DE.EXT_EVT_NAME_FLG,
       DE.CRE_DTTM,
       DE.STATUS_UPD_DTTM,
       DE.DVC_EVT_DTTM,
       DE.D1_SPR_CD,
       DE.D1_DEVICE_ID,
       cast('' as char(12))     as MEASR_COMP_ID,
       DS.D1_SP_ID,
       cast(nvl(SP.ID_VALUE, SC.PREM_ID) as char(10)) as PREM_ID,
       SS.SA_ID,
       SA.ACCT_ID,
       PE.PER_ID,
       DE.ILM_DT
 from D1_DVC_EVT DE
 left join (select D1.D1_DEVICE_ID,
                last_value(I1.D1_SP_ID) over (partition by D1.D1_DEVICE_ID order by I1.D1_INSTALL_DTTM) D1_SP_ID
                 from D1_DVC_CFG     D1
           inner join D1_INSTALL_EVT I1 on D1.DEVICE_CONFIG_ID = I1.DEVICE_CONFIG_ID
                            ) DS on DS.D1_DEVICE_ID = DE.D1_DEVICE_ID
 left join D1_SP_IDENTIFIER   SI on SI.D1_SP_ID     = DS.D1_SP_ID and SI.SP_ID_TYPE_FLG = 'D1EI'
 left join D1_SP_IDENTIFIER   SP on SP.D1_SP_ID     = DS.D1_SP_ID and SP.SP_ID_TYPE_FLG = 'D1EP'
 left join (select SP_ID, max(SA_ID) SA_ID from CI_SA_SP S1
             where START_DTTM = (select min(START_DTTM) START_DTTM from CI_SA_SP /* longest active */
                                 where SP_ID = S1.SP_ID and STOP_DTTM is null)
             group by SP_ID)  SS on SS.SP_ID = SI.ID_VALUE
 left join CI_SP              SC on SC.SP_ID        = SS.SP_ID
 left join CI_SA              SA on SA.SA_ID        = SS.SA_ID
 left join CI_ACCT_PER        PE on PE.ACCT_ID      = SA.ACCT_ID and PE.MAIN_CUST_SW = 'Y';

-- ----- X1_BI_DVC_INFO_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."X1_BI_DVC_INFO_VW" ("DEVICE_ID", "DEVICE_TYPE_CD", "D1_MODEL_CD", "D1_SPR_CD", "IN_DATA_SHIFT_FLG", "MANUFACTURER_CD", "ARMING_REQ_FLG", "SERIAL_NUMBER", "BADGE_NUMBER") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
      DVC.D1_DEVICE_ID as DEVICE_ID ,DVC.DEVICE_TYPE_CD, DVC.D1_MODEL_CD, DVC.D1_SPR_CD, DVC.IN_DATA_SHIFT_FLG,DVC.MANUFACTURER_CD,DVC.ARMING_REQ_FLG,
      D.ID_VALUE as SERIAL_NUMBER,
      D.ID_VALUE as BADGE_NUMBER
FROM
      D1_DVC DVC
      left join (select D1_DEVICE_ID,DVC_ID_TYPE_FLG,ID_VALUE from  D1_DVC_IDENTIFIER DID where DID.DVC_ID_TYPE_FLG = 'D1BN') D
      on D.D1_DEVICE_ID = DVC.D1_DEVICE_ID
      left join (select D1_DEVICE_ID,DVC_ID_TYPE_FLG,ID_VALUE from  D1_DVC_IDENTIFIER DID where DID.DVC_ID_TYPE_FLG = 'D1SN') S
      on S.D1_DEVICE_ID = DVC.D1_DEVICE_ID;

-- ----- X1_BI_TD_ENTRY_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."X1_BI_TD_ENTRY_VW" ("TD_ENTRY_ID", "TD_TYPE_CD", "ENTRY_STATUS_FLG", "TD_PRIORITY_FLG", "SA_ID", "ACCT_ID", "PER_ID", "PREM_ID", "D1_SP_ID", "D1_DEVICE_ID", "MEASR_COMP_ID", "CONTACT_ID", "US_ID", "ASSET_ID", "TD_CRE_DTTM", "ASSIGNED_DTTM", "COMPLETE_DTTM", "ASSIGNED_TO_USER_ID", "COMPLETE_USER_ID", "UNASSIGNED_TM_MINS", "ASSIGNED_TM_MINS", "COMPLETE_TM_MINS", "MESSAGE_CAT_NBR", "MESSAGE_NBR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    tde.td_entry_id,
    tde.td_type_cd,
    tde.entry_status_flg,
    tde.td_priority_flg,
    cast(sa_id as char(10)) sa_id,
    cast(acct_id as char(10)) acct_id ,
    cast(per_id as char(10)) per_id,
    cast(prem_id as char(10)) prem_id,
    cast(d1_sp_id as char(12)) d1_sp_id,
    cast(d1_device_id as char(12)) d1_device_id,
    cast(measr_comp_id as char(12)) measr_comp_id,
    cast(contact_id as char(12)) contact_id,
    cast(us_id as char(12)) us_id,
    cast(asset_id as char(12)) asset_id,
    tde.cre_dttm AS td_cre_dttm,
    tde.assigned_dttm,
    tde.complete_dttm,
    tde.assigned_to AS assigned_to_user_id,
    tde.complete_user_id,
    CASE
        WHEN tde.entry_status_flg = 'O' THEN
            round(current_date - cre_dttm, 2) * 24 * 60
        ELSE
            round(assigned_dttm - cre_dttm, 2) * 24 * 60
    END AS unassigned_tm_mins,
    CASE
        WHEN tde.entry_status_flg = 'W' THEN
            round(current_date - assigned_dttm, 2) * 24 * 60
        WHEN tde.entry_status_flg = 'C' THEN
            round(complete_dttm - assigned_dttm, 2) * 24 * 60
        ELSE
            0
    END AS assigned_tm_mins,
    CASE
        WHEN tde.entry_status_flg = 'C' THEN
            round(complete_dttm - cre_dttm,2) * 24 * 60
         ELSE 0
    END AS complete_tm_mins,
    tde.message_cat_nbr,
    tde.message_nbr
FROM
    ci_td_entry tde
    LEFT OUTER JOIN (
        SELECT
            td_entry_id,
            MIN(sa_id) sa_id,
            MIN(acct_id) acct_id,
            MIN(per_id) per_id,
            MIN(prem_id) prem_id,
            MIN(d1_sp_id) d1_sp_id,
            MIN(d1_device_id) d1_device_id,
            MIN(measr_comp_id) measr_comp_id,
            MIN(contact_id) contact_id,
            MIN(us_id) us_id,
            MIN(asset_id) asset_id
        FROM
            (
                SELECT
                    td.td_entry_id,
                    DECODE(TRIM(fkr.tbl_name), 'CI_SA', tdc.char_val_fk1, NULL) AS sa_id,
                    DECODE(TRIM(fkr.tbl_name), 'CI_ACCT', tdc.char_val_fk1, NULL) AS acct_id,
                    DECODE(TRIM(fkr.tbl_name), 'CI_PER', tdc.char_val_fk1, NULL) AS per_id,
                    DECODE(TRIM(fkr.tbl_name), 'CI_PREM', tdc.char_val_fk1, NULL) AS prem_id,
                    DECODE(TRIM(fkr.tbl_name), 'D1_SP', tdc.char_val_fk1, NULL) AS d1_sp_id,
                    DECODE(TRIM(fkr.tbl_name), 'D1_DVC', tdc.char_val_fk1, NULL) AS d1_device_id,
                    DECODE(TRIM(fkr.tbl_name), 'D1_MEASR_COMP', tdc.char_val_fk1, NULL) AS measr_comp_id,
                    DECODE(TRIM(fkr.tbl_name), 'D1_CONTACT', tdc.char_val_fk1, NULL) AS contact_id,
                   DECODE(TRIM(fkr.tbl_name), 'D1_US', tdc.char_val_fk1, NULL) AS us_id,
                    DECODE(TRIM(fkr.tbl_name), 'W1_ASSET', tdc.char_val_fk1, NULL) AS asset_id
                FROM
                    ci_td_entry       td,
                    ci_td_entry_cha   tdc,
                    ci_char_type      ct,
                    ci_fk_ref         fkr
                WHERE
                    tdc.td_entry_id = td.td_entry_id
                    AND ct.char_type_cd = tdc.char_type_cd
                    AND ct.char_type_flg = 'FKV'
                    AND fkr.fk_ref_cd = ct.fk_ref_cd
                    AND TRIM(fkr.tbl_name) IN (
                        'CI_SA',
                        'CI_ACCT',
                        'CI_PER',
                        'CI_PREM',
                        'D1_SP',
                        'D1_DVC',
                        'D1_MEASR_COMP',
                        'D1_CONTACT',
                        'D1_US',
                        'W1_ASSET'
                    )
            )
        GROUP BY
            td_entry_id
    ) fks ON ( fks.td_entry_id = tde.td_entry_id );

-- ----- X1_BI_USG_EXCEPTION_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."X1_BI_USG_EXCEPTION_VW" ("USAGE_EXCP_ID", "USG_EXCP_TYPE_CD", "EXCP_SEVERITY_FLG", "OPEN_CLOSE_FLG", "MESSAGE_CAT_NBR", "MESSAGE_NBR", "MESSAGE_TEXT", "USG_GRP_CD", "USG_RULE_CD", "EXCP_CRE_DTTM", "EXCP_STATUS_DTTM", "TD_ENTRY_ID", "TD_TYPE_CD", "D1_USAGE_ID", "US_ID", "CSTMR_NM", "MDM_SP_ID", "CCB_SP_ID", "PREM_ID", "SA_ID", "SA_TYPE_CD", "CIS_DIV", "CCB_ACC_ID", "PER_ID", "CCB_BILL_CYC_CD", "ILM_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  select
  E.USAGE_EXCP_ID,
  E.USAGE_EXCP_TYPE_CD as USG_EXCP_TYPE_CD,
  E.EXCP_SEVERITY_FLG,
  E.OPEN_CLOSE_FLG,
  E.MESSAGE_CAT_NBR,
  E.MESSAGE_NBR,
  MSG.MESSAGE_TEXT,
  E.USG_GRP_CD,
  E.USG_RULE_CD,
  E.CRE_DTTM           as EXCP_CRE_DTTM,
  E.STATUS_UPD_DTTM    as EXCP_STATUS_DTTM,
  null                 as TD_ENTRY_ID,
  null                 as TD_TYPE_CD,
  E.D1_USAGE_ID,
  USSP.US_ID,
  CNT.NAME_VALUE       as CSTMR_NM,
  SP.D1_SP_ID          as MDM_SP_ID,
  CSP.SP_ID            as CCB_SP_ID,
  CSP.PREM_ID          as PREM_ID,
  SA.SA_ID,
  SA.SA_TYPE_CD,
  DIV.DESCR            as CIS_DIV,
  ACP.ACCT_ID          as CCB_ACC_ID,
  ACP.PER_ID,
  CBC.BILL_CYC_CD      as CCB_BILL_CYC_CD,
  E.ILM_DT
from
  D1_USAGE_EXCP E
  left join D1_USAGE              USG on USG.D1_USAGE_ID = E.D1_USAGE_ID
  left join (select distinct U1.US_ID,
                last_value(U1.D1_SP_ID) over (partition by U1.US_ID order by U1.START_DTTM) as D1_SP_ID
               from D1_US_SP U1) USSP on USG.US_ID = USSP.US_ID
  left join D1_US_CONTACT         USC on USSP.US_ID = USC.US_ID
  left join D1_CONTACT_NAME       CNT on CNT.CONTACT_ID = USC.CONTACT_ID
  left join D1_SP                  SP on USSP.D1_SP_ID = SP.D1_SP_ID
  left join D1_MSRMT_CYC_BILL_CYC MBC on SP.MSRMT_CYC_CD = MBC.MSRMT_CYC_CD
  left join CI_BILL_CYC           CBC on MBC.D1_BILL_CYC_CD = CBC.BILL_CYC_CD
  left join D1_SP_IDENTIFIER      SPI on SP.D1_SP_ID = SPI.D1_SP_ID and SPI.SP_ID_TYPE_FLG = 'D1EI'
  left join D1_SP_IDENTIFIER     SPID on SP.D1_SP_ID = SPID.D1_SP_ID and SPID.SP_ID_TYPE_FLG = 'D1EP'
  left join (select SP_ID, max(SA_ID) SA_ID from CI_SA_SP S1
              where START_DTTM = (select min(START_DTTM) START_DTTM from CI_SA_SP /* longest active */
                                  where SP_ID = S1.SP_ID and STOP_DTTM is null)
              group by SP_ID)      SS on SS.SP_ID = SPI.ID_VALUE
  left join CI_SP                 CSP on SPI.ID_VALUE = CSP.SP_ID
  left join CI_SA                  SA on SS.SA_ID = SA.SA_ID
  left join CI_CIS_DIVISION_L     DIV on SA.CIS_DIVISION = DIV.CIS_DIVISION and DIV.LANGUAGE_CD  = 'ENG'
  left join CI_ACCT_PER           ACP on SA.ACCT_ID = ACP.ACCT_ID and ACP.MAIN_CUST_SW = 'Y'
  left join CI_MSG_L              MSG on E.MESSAGE_CAT_NBR = MSG.MESSAGE_CAT_NBR
                                     and E.MESSAGE_NBR = MSG.MESSAGE_NBR and MSG.LANGUAGE_CD  = 'ENG';

-- ----- X1_BI_VEE_EXCEPTION_VW -----
CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."X1_BI_VEE_EXCEPTION_VW" ("VEE_EXCP_ID", "EXCP_TYPE_CD", "EXCP_SEVERITY_FLG", "MESSAGE_CAT_NBR", "MESSAGE_NBR", "MESSAGE_TEXT", "VEE_GRP_CD", "VEE_RULE_CD", "EXCP_CRE_DTTM", "EXCP_STATUS_DTTM", "OPEN_CLOSE_FLG", "TD_ENTRY_ID", "TD_TYPE_CD", "INIT_MSRMT_DATA_ID", "MEASR_COMP_ID", "D1_DEVICE_ID", "D1_SPR_CD", "MDM_SP_ID", "CCB_SP_ID", "PREM_ID", "SA_ID", "PER_ID", "CCB_ACCT_ID", "CCB_BILL_CYC_CD", "US_ID", "CSTMR_NM", "INSTALL_EVT_ID", "ILM_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  select
    E.VEE_EXCP_ID  ,
    E.EXCP_TYPE_CD   ,
    E.EXCP_SEVERITY_FLG ,
    E.MESSAGE_CAT_NBR ,
    E.MESSAGE_NBR ,
    null MESSAGE_TEXT,
    E.VEE_GRP_CD  ,
    E.VEE_RULE_CD  ,
    E.CRE_DTTM as EXCP_CRE_DTTM ,
    E.STATUS_UPD_DTTM as EXCP_STATUS_DTTM ,
    E.OPEN_CLOSE_FLG ,
    null TD_ENTRY_ID,
    null TD_TYPE_CD,
    IMDC.INIT_MSRMT_DATA_ID ,
    MC.MEASR_COMP_ID ,
    D.D1_DEVICE_ID ,
    D.D1_SPR_CD ,
    SP.D1_SP_ID as MDM_SP_ID,
    SS.SP_ID CCB_SP_ID,
    cast(nvl(SPID.ID_VALUE, SC.PREM_ID) as char(10)) as PREM_ID,
    SS.SA_ID,
    PE.PER_ID,
    SA.ACCT_ID CCB_ACCT_ID,
    MBC.D1_BILL_CYC_CD CCB_BILL_CYC_CD,
    USSP.US_ID,
    CNT.NAME_VALUE as CSTMR_NM,
    IE.INSTALL_EVT_ID,
    E.ILM_DT
from
    D1_VEE_EXCP E
    left join D1_IMD_CTRL IMDC on  E.INIT_MSRMT_DATA_ID = IMDC.INIT_MSRMT_DATA_ID
    left join D1_MEASR_COMP MC          on IMDC.IMD_CTRL_MC_ID = MC.MEASR_COMP_ID
    left join D1_DVC_CFG DC             on MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
    left join D1_DVC D                  on DC.D1_DEVICE_ID = D.D1_DEVICE_ID
    left join D1_INSTALL_EVT IE         on DC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
    left join D1_SP SP                  on IE.D1_SP_ID = SP.D1_SP_ID
    left join D1_US_SP USSP             on SP.D1_SP_ID = USSP.D1_SP_ID
    left join D1_US_CONTACT USC         on USSP.US_ID = USC.US_ID
    left join D1_CONTACT_NAME CNT       on CNT.CONTACT_ID = USC.CONTACT_ID
    left join D1_MSRMT_CYC_BILL_CYC MBC on SP.MSRMT_CYC_CD = MBC.MSRMT_CYC_CD
    left join D1_SP_IDENTIFIER SPI      on SP.D1_SP_ID = SPI.D1_SP_ID
                                        and SPI.SP_ID_TYPE_FLG = 'D1EI'
    left join D1_SP_IDENTIFIER SPID      on SP.D1_SP_ID = SPID.D1_SP_ID
                                        and SPID.SP_ID_TYPE_FLG = 'D1EP'
 left join (select SP_ID, max(SA_ID) SA_ID from CI_SA_SP S1
             where START_DTTM = (select min(START_DTTM) START_DTTM from CI_SA_SP /* longest active */
                                 where SP_ID = S1.SP_ID and STOP_DTTM is null)
             group by SP_ID)  SS on SS.SP_ID = SPI.ID_VALUE
 left join CI_SP              SC on SC.SP_ID        = SS.SP_ID
 left join CI_SA              SA on SA.SA_ID        = SS.SA_ID
 left join CI_ACCT_PER        PE on PE.ACCT_ID      = SA.ACCT_ID and PE.MAIN_CUST_SW = 'Y';

