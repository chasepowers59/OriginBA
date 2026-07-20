-- SELECT logic for CISADM.C1_BI_SEVPROC_VW
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
      )
