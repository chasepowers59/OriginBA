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
