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
