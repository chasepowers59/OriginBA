-- SELECT logic for CISADM.C1_BI_BILLED_USAGE_VW
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
      AND bi.cre_dttm  between add_months(current_date, -60) and current_date
