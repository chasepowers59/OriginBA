-- SELECT logic for CISADM.CMS_CI_CASE_LOG_VW
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
             , clog.seq_num
