-- SELECT logic for CISADM.C1_BI_FT_VW
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
      )
