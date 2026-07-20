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
